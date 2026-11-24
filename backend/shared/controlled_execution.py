"""Authenticated service entry point for future exercise routers."""
import hashlib
import json
from datetime import datetime, timezone
from threading import BoundedSemaphore
from uuid import uuid4
from functools import lru_cache

from azure.core import MatchConditions
from azure.core.exceptions import ResourceExistsError, ResourceModifiedError, ResourceNotFoundError
from fastapi import HTTPException
from shared.config import get_settings
from shared.table_storage import get_table_client
from shared.blob_storage import save_json
from shared.foundry_client import generate_response, validate_prompt
from shared.model_selector import resolve_chat_model

# Conservative provisional limits; review before enabling live routes.
DAILY_REQUESTS = 20
MINUTE_REQUESTS = 3
DAILY_OUTPUT_BUDGET = 20480

@lru_cache
def slots():
    return BoundedSemaphore(get_settings().max_concurrent_requests)


def reserve(user_id):
    """Atomic daily reservation; failed requests retain their reservation."""
    settings = get_settings()
    table = get_table_client(settings.metrics_table)
    now = datetime.now(timezone.utc)
    day = now.strftime('%Y%m%d')
    minute = now.strftime('%Y%m%d%H%M')
    key = 'quota-' + day
    for _ in range(8):
        try:
            row = table.get_entity(user_id, key)
        except ResourceNotFoundError:
            try:
                table.create_entity({'PartitionKey': user_id, 'RowKey': key,
                    'Requests': 0, 'ReservedOutput': 0, 'Minute': minute, 'MinuteRequests': 0})
            except ResourceExistsError:
                pass
            continue
        count = int(row['Requests'])
        reserved = int(row['ReservedOutput'])
        minute_count = int(row['MinuteRequests']) if row['Minute'] == minute else 0
        if (count >= DAILY_REQUESTS or minute_count >= MINUTE_REQUESTS or
                reserved + settings.max_output_tokens > DAILY_OUTPUT_BUDGET):
            raise HTTPException(429, 'AI usage limit reached.')
        update = dict(row)
        update.update(Requests=count+1, ReservedOutput=reserved+settings.max_output_tokens,
                      Minute=minute, MinuteRequests=minute_count+1)
        try:
            table.update_entity(update, etag=row.metadata['etag'],
                                match_condition=MatchConditions.IfNotModified)
            return
        except ResourceModifiedError:
            continue
    raise HTTPException(503, 'Usage reservation unavailable; retry later.')


def execute(user, prompt, profile='standard', conversation_id=None):
    """Call only after server-side require_authorised_user dependency."""
    if user.get('authorised') is not True:
        raise HTTPException(403, 'Access denied.')
    user_id = user['user_id']
    settings = get_settings()
    prompt = validate_prompt(prompt)
    model = resolve_chat_model(profile)
    history = get_table_client(settings.conversation_table)
    previous = None
    if conversation_id:
        try:
            row = history.get_entity(user_id, conversation_id)
        except ResourceNotFoundError:
            raise HTTPException(404, 'Conversation not found.')
        if row['Deployment'] != model:
            raise HTTPException(400, 'Start a new conversation to change models.')
        previous = row['ResponseId']
    if not slots().acquire(blocking=False):
        raise HTTPException(429, 'AI service busy.')
    try:
        reserve(user_id)
        result = generate_response(prompt, model=model, previous_response_id=previous)
        run_id = uuid4().hex
        # Each turn gets its own immutable conversation handle; no lost updates.
        if settings.store_ai_responses and result['response_id']:
            history.create_entity({'PartitionKey': user_id, 'RowKey': run_id,
                'ResponseId': result['response_id'], 'Deployment': model,
                'Parent': conversation_id or ''})
        path = f'{user_id}/{run_id}.json'
        save_json(settings.results_container, path, result)
        get_table_client(settings.metrics_table).create_entity({
            'PartitionKey': user_id, 'RowKey': 'run-' + run_id,
            'Deployment': model, 'InputTokens': result['input_tokens'],
            'OutputTokens': result['output_tokens'], 'TotalTokens': result['total_tokens'],
            'DurationSeconds': result['execution_time_seconds'],
            'Status': result['status'] or 'unknown', 'ResultBlob': path})
        return {**result, 'conversation_id': run_id if settings.store_ai_responses else None}
    finally:
        slots().release()
