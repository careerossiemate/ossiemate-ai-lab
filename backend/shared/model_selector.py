from typing import Literal

from shared.config import get_settings


ModelProfile = Literal["standard", "advanced"]


def resolve_chat_model(
    profile: ModelProfile = "standard"
) -> str:

    settings = get_settings()

    model_mapping = {
        "standard": settings.model_deployment,
        "advanced": settings.advanced_model_deployment
    }

    if profile not in model_mapping:
        raise ValueError("Unsupported AI model profile.")

    deployment = model_mapping[profile]

    if deployment not in settings.allowed_chat_models:
        raise ValueError("Model deployment is not permitted.")

    return deployment


def get_embedding_model() -> str:

    settings = get_settings()

    return settings.embedding_model_deployment


def get_available_model_profiles() -> list[dict[str, str]]:

    return [
        {
            "id": "standard",
            "name": "Standard AI",
            "description": (
                "Suitable for routine AI demonstrations."
            )
        },
        {
            "id": "advanced",
            "name": "Advanced AI",
            "description": (
                "Suitable for complex reasoning and analysis."
            )
        }
    ]