from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):

    # Application configuration
    app_name: str = "Ossiemate AI Lab"
    app_version: str = "0.1.0"
    environment: str = "development"

    # Microsoft Foundry
    azure_openai_endpoint: str
    model_deployment: str = "gpt-5-mini-2"
    advanced_model_deployment: str = "gpt-5.2"
    embedding_model_deployment: str = "text-embedding-3-small"
    foundry_project_endpoint: str = ""

    # AI execution configuration
    max_prompt_characters: int = Field(
        default=8000,
        ge=1,
        le=32000
    )

    max_output_tokens: int = Field(
        default=1024,
        ge=1,
        le=8192
    )

    ai_request_timeout: float = Field(
        default=120.0,
        ge=10.0,
        le=300.0
    )

    ai_max_retries: int = Field(
        default=0,
        ge=0,
        le=2
    )

    max_concurrent_requests: int = Field(
        default=3,
        ge=1,
        le=10
    )

    # AI feature controls
    store_ai_responses: bool = True
    token_monitoring_enabled: bool = True
    execution_metrics_enabled: bool = True
    fine_tuning_enabled: bool = False

    # Managed Identity
    azure_client_id: str

    # Azure Storage
    storage_account_name: str = "stossiemateailab"

    # Blob containers
    brochures_container: str = "brochures"
    training_container: str = "training-data"
    results_container: str = "demonstration-results"
    config_container: str = "lab-config"
    backups_container: str = "backups"

    # Storage tables
    progress_table: str = "ExerciseProgress"
    conversation_table: str = "ConversationHistory"
    metrics_table: str = "ExecutionMetrics"
    configuration_table: str = "LabConfiguration"
    training_jobs_table: str = "TrainingJobs"

    # Frontend configuration
    frontend_origin: str = (
        "https://mango-sea-0589cd400.6.azurestaticapps.net"
    )

    # User authentication configuration
    azure_tenant_id: str = ""
    api_client_id: str = ""
    spa_client_id: str = ""
    allowed_user_ids: str = ""
    api_scope: str = "access_as_user"

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore"
    )

    @property
    def blob_service_url(self) -> str:
        return (
            f"https://{self.storage_account_name}"
            ".blob.core.windows.net"
        )

    @property
    def table_service_url(self) -> str:
        return (
            f"https://{self.storage_account_name}"
            ".table.core.windows.net"
        )

    @property
    def allowed_chat_models(self) -> tuple[str, ...]:
        return tuple(dict.fromkeys((
            self.model_deployment,
            self.advanced_model_deployment
        )))


@lru_cache
def get_settings() -> Settings:
    return Settings()