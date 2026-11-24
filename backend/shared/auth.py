from functools import lru_cache

from azure.identity import (
    ManagedIdentityCredential,
    get_bearer_token_provider
)

from shared.config import get_settings


@lru_cache
def get_azure_credential() -> ManagedIdentityCredential:

    settings = get_settings()

    if not settings.azure_client_id:
        raise ValueError(
            "AZURE_CLIENT_ID must be configured."
        )

    return ManagedIdentityCredential(
        client_id=settings.azure_client_id
    )


@lru_cache
def get_foundry_token_provider():

    credential = get_azure_credential()

    return get_bearer_token_provider(
        credential,
        "https://cognitiveservices.azure.com/.default"
    )
