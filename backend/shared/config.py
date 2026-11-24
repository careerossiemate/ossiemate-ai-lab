from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):

    # Application configuration
    app_name: str = "Ossiemate AI Lab"
    app_version: str = "0.1.0"
    environment: str = "development"

    # Microsoft Foundry
    azure_openai_endpoint: str
    model_deployment: str = "gpt-5.2"
    foundry_project_endpoint: str = ""

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


@lru_cache
def get_settings() -> Settings:
    return Settings()

