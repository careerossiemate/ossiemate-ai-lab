from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException

from pydantic import BaseModel, Field

from shared.config import get_settings

from shared.auth import get_azure_credential

from shared.user_authorization import (
    require_authorised_user
)

from shared.blob_storage import (
    get_blob_service_client
)

from shared.table_storage import (
    get_table_client,
    list_records,
    upsert_record
)


router = APIRouter(
    prefix="/api",
    tags=["Protected APIs"],
    dependencies=[Depends(require_authorised_user)]
)


class ProgressRequest(BaseModel):

    exercise_id: Literal["03", "04", "05", "06"]

    status: Literal[
        "not_started",
        "in_progress",
        "completed"
    ]

    completion_percentage: int = Field(
        ge=0,
        le=100
    )

    notes: str = Field(
        default="",
        max_length=2000
    )


@router.get("/auth/me")
def get_current_user(
    user: dict[str, Any] = Depends(
        require_authorised_user
    )
):

    return {
        "authenticated": True,
        "authorised": True,
        "user_id": user["user_id"],
        "tenant_id": user["tenant_id"],
        "scopes": user["scopes"]
    }


@router.get("/diagnostics")
def get_diagnostics():

    settings = get_settings()

    checks = {}

    try:

        credential = get_azure_credential()

        credential.get_token(
            "https://cognitiveservices.azure.com/.default"
        )

        checks["managed_identity"] = "connected"

    except Exception:

        checks["managed_identity"] = "failed"

    try:

        blob_client = get_blob_service_client()

        container = blob_client.get_container_client(
            settings.brochures_container
        )

        container.get_container_properties()

        checks["blob_storage"] = "connected"

    except Exception:

        checks["blob_storage"] = "failed"

    try:

        table = get_table_client(
            settings.progress_table
        )

        next(
            iter(table.list_entities(results_per_page=1)),
            None
        )

        checks["table_storage"] = "connected"

    except Exception:

        checks["table_storage"] = "failed"

    checks["foundry_model"] = "not_tested"

    all_connected = all(
        checks[name] == "connected"
        for name in [
            "managed_identity",
            "blob_storage",
            "table_storage"
        ]
    )

    return {
        "status": (
            "healthy" if all_connected else "degraded"
        ),
        "checks": checks
    }


@router.get("/progress")
def get_exercise_progress(
    user: dict[str, Any] = Depends(
        require_authorised_user
    )
):

    settings = get_settings()

    records = list_records(
        table_name=settings.progress_table,
        partition_key=user["user_id"],
        limit=100
    )

    return {
        "total": len(records),
        "progress": records
    }


@router.post("/progress")
def save_exercise_progress(
    request: ProgressRequest,
    user: dict[str, Any] = Depends(
        require_authorised_user
    )
):

    settings = get_settings()

    if (
        request.status == "completed"
        and request.completion_percentage != 100
    ):

        raise HTTPException(
            status_code=422,
            detail="Completed exercises must have 100 percent progress."
        )

    record = upsert_record(
        table_name=settings.progress_table,
        partition_key=user["user_id"],
        row_key=request.exercise_id,
        data={
            "ExerciseId": request.exercise_id,
            "Status": request.status,
            "CompletionPercentage": request.completion_percentage,
            "Notes": request.notes
        }
    )

    return {
        "message": "Exercise progress saved.",
        "progress": record
    }

