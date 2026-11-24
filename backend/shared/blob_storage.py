import json

from functools import lru_cache
from typing import Any

from azure.storage.blob import (
    BlobServiceClient,
    ContentSettings
)

from shared.config import get_settings
from shared.auth import get_azure_credential


@lru_cache
def get_blob_service_client() -> BlobServiceClient:

    settings = get_settings()

    return BlobServiceClient(
        account_url=settings.blob_service_url,
        credential=get_azure_credential()
    )


def upload_blob(
    container: str,
    blob_name: str,
    data: bytes,
    content_type: str = "application/octet-stream",
    overwrite: bool = False
) -> dict[str, Any]:

    client = get_blob_service_client()

    blob = client.get_blob_client(
        container=container,
        blob=blob_name
    )

    blob.upload_blob(
        data,
        overwrite=overwrite,
        content_settings=ContentSettings(
            content_type=content_type
        )
    )

    return {
        "container": container,
        "blob_name": blob_name,
        "size_bytes": len(data),
        "url": blob.url,
        "status": "uploaded"
    }


def download_blob(
    container: str,
    blob_name: str
) -> bytes:

    client = get_blob_service_client()

    blob = client.get_blob_client(
        container=container,
        blob=blob_name
    )

    return blob.download_blob().readall()


def list_blobs(
    container: str,
    prefix: str | None = None
) -> list[dict[str, Any]]:

    client = get_blob_service_client()

    container_client = client.get_container_client(
        container
    )

    return [
        {
            "name": blob.name,
            "size_bytes": blob.size,
            "last_modified": (
                blob.last_modified.isoformat()
                if blob.last_modified else None
            )
        }
        for blob in container_client.list_blobs(
            name_starts_with=prefix
        )
    ]


def blob_exists(
    container: str,
    blob_name: str
) -> bool:

    client = get_blob_service_client()

    return client.get_blob_client(
        container=container,
        blob=blob_name
    ).exists()


def save_json(
    container: str,
    blob_name: str,
    data: Any,
    overwrite: bool = False
) -> dict[str, Any]:

    content = json.dumps(
        data,
        indent=2,
        ensure_ascii=False
    ).encode("utf-8")

    return upload_blob(
        container=container,
        blob_name=blob_name,
        data=content,
        content_type="application/json",
        overwrite=overwrite
    )


def load_json(
    container: str,
    blob_name: str
) -> Any:

    content = download_blob(
        container=container,
        blob_name=blob_name
    )

    return json.loads(content.decode("utf-8"))


def delete_blob(
    container: str,
    blob_name: str
) -> None:

    client = get_blob_service_client()

    client.get_blob_client(
        container=container,
        blob=blob_name
    ).delete_blob()
