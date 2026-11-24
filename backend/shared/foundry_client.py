from functools import lru_cache
from time import perf_counter
from typing import Any

from openai import OpenAI

from shared.config import get_settings
from shared.auth import get_foundry_token_provider


@lru_cache
def get_foundry_client() -> OpenAI:

    settings = get_settings()

    return OpenAI(
        base_url=settings.azure_openai_endpoint,
        api_key=get_foundry_token_provider(),
        timeout=settings.ai_request_timeout,
        max_retries=settings.ai_max_retries
    )


def validate_prompt(prompt: str) -> str:

    settings = get_settings()

    if not isinstance(prompt, str):
        raise ValueError("Prompt must be a string.")

    if not prompt.strip():
        raise ValueError("Prompt cannot be empty.")

    if len(prompt) > settings.max_prompt_characters:
        raise ValueError(
            f"Prompt exceeds the maximum limit of "
            f"{settings.max_prompt_characters} characters."
        )

    return prompt.strip()


def generate_response(
    prompt: str,
    instructions: str = "You are a helpful AI assistant.",
    previous_response_id: str | None = None,
    tools: list[dict[str, Any]] | None = None,
    model: str | None = None
) -> dict[str, Any]:

    settings = get_settings()

    validated_prompt = validate_prompt(prompt)

    selected_model = model or settings.model_deployment

    if selected_model not in settings.allowed_chat_models:
        raise ValueError("Model deployment is not permitted.")

    if previous_response_id and not settings.store_ai_responses:
        raise ValueError(
            "Stored response context is disabled."
        )

    client = get_foundry_client()

    request = {
        "model": selected_model,
        "instructions": instructions,
        "input": validated_prompt,
        "max_output_tokens": settings.max_output_tokens,
        "store": settings.store_ai_responses
    }

    if previous_response_id:
        request["previous_response_id"] = previous_response_id

    if tools:
        request["tools"] = tools

    start_time = perf_counter()

    response = client.responses.create(**request)

    execution_time = round(
        perf_counter() - start_time,
        3
    )

    usage = response.usage

    tool_calls = []

    for item in response.output:
        if item.type.endswith("_call"):
            tool_calls.append({
                "type": item.type,
                "status": getattr(item, "status", None)
            })

    incomplete_details = getattr(
        response,
        "incomplete_details",
        None
    )

    incomplete_reason = (
        getattr(incomplete_details, "reason", None)
        if incomplete_details
        else None
    )

    return {
        "response_id": response.id,
        "response": response.output_text,
        "deployment": selected_model,
        "model": response.model,
        "status": response.status,
        "incomplete_reason": incomplete_reason,
        "execution_time_seconds": execution_time,
        "input_tokens": usage.input_tokens if usage else 0,
        "output_tokens": usage.output_tokens if usage else 0,
        "total_tokens": usage.total_tokens if usage else 0,
        "tool_calls": tool_calls
    }