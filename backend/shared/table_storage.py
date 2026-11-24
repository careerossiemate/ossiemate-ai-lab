from functools import lru_cache
from typing import Any
from datetime import datetime, timezone
from uuid import uuid4

from azure.data.tables import (
    TableServiceClient,
    TableClient,
    UpdateMode
)

from azure.core.exceptions import ResourceNotFoundError

from shared.config import get_settings
from shared.auth import get_azure_credential


@lru_cache
def get_table_service_client() -> TableServiceClient:

    settings = get_settings()

    return TableServiceClient(
        endpoint=settings.table_service_url,
        credential=get_azure_credential()
    )


@lru_cache
def get_table_client(table_name: str) -> TableClient:

    client = get_table_service_client()

    return client.get_table_client(
        table_name=table_name
    )


def create_record(
    table_name: str,
    partition_key: str,
    data: dict[str, Any],
    row_key: str | None = None
) -> dict[str, Any]:

    client = get_table_client(table_name)

    entity = {
        **data,
        "PartitionKey": partition_key,
        "RowKey": row_key or str(uuid4()),
        "CreatedAt": datetime.now(timezone.utc)
    }

    client.create_entity(entity=entity)

    return entity


def upsert_record(
    table_name: str,
    partition_key: str,
    row_key: str,
    data: dict[str, Any]
) -> dict[str, Any]:

    client = get_table_client(table_name)

    entity = {
        **data,
        "PartitionKey": partition_key,
        "RowKey": row_key,
        "UpdatedAt": datetime.now(timezone.utc)
    }

    client.upsert_entity(
        entity=entity,
        mode=UpdateMode.MERGE
    )

    return entity


def get_record(
    table_name: str,
    partition_key: str,
    row_key: str
) -> dict[str, Any] | None:

    client = get_table_client(table_name)

    try:
        entity = client.get_entity(
            partition_key=partition_key,
            row_key=row_key
        )

        return dict(entity)

    except ResourceNotFoundError:
        return None


def list_records(
    table_name: str,
    partition_key: str,
    limit: int = 100
) -> list[dict[str, Any]]:

    if not 1 <= limit <= 1000:
        raise ValueError("Limit must be between 1 and 1000.")

    client = get_table_client(table_name)

    entities = client.query_entities(
        query_filter="PartitionKey eq @partition",
        parameters={
            "partition": partition_key
        },
        results_per_page=min(limit, 100)
    )

    records = []

    for entity in entities:
        records.append(dict(entity))

        if len(records) >= limit:
            break

    return records


def delete_record(
    table_name: str,
    partition_key: str,
    row_key: str
) -> None:

    client = get_table_client(table_name)

    client.delete_entity(
        partition_key=partition_key,
        row_key=row_key
    )
