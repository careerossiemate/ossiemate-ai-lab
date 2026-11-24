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
        timeout=120.0,
        max_retries=2
    )


def generate_response(
    prompt: str,
    instructions: str = "You are a helpful AI assistant.",
    previous_response_id: str | None = None,
    tools: list[dict[str, Any]] | None = None,
    model: str | None = None
) -> dict[str, Any]:

    settings = get_settings()
    client = get_foundry_client()

    request = {
        "model": model or settings.model_deployment,
        "instructions": instructions,
        "input": prompt,
        "store": True
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

    return {
        "response_id": response.id,
        "response": response.output_text,
        "model": response.model,
        "status": response.status,
        "execution_time_seconds": execution_time,
        "input_tokens": usage.input_tokens if usage else 0,
        "output_tokens": usage.output_tokens if usage else 0,
        "total_tokens": usage.total_tokens if usage else 0,
        "tool_calls": tool_calls
    }
