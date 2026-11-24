from functools import lru_cache
from typing import Any
from uuid import UUID

from fastapi import Depends, HTTPException, status

from shared.config import get_settings
from shared.user_auth import get_authenticated_user


@lru_cache
def get_allowed_user_ids() -> frozenset[str]:

    settings = get_settings()

    configured_ids = [
        user_id.strip()
        for user_id in settings.allowed_user_ids.split(",")
        if user_id.strip()
    ]

    try:

        return frozenset(
            str(UUID(user_id))
            for user_id in configured_ids
        )

    except ValueError:

        raise HTTPException(
            status_code=503,
            detail="User authorisation is not configured correctly."
        )


def is_user_authorised(user_id: str) -> bool:

    allowed_users = get_allowed_user_ids()

    try:

        normalised_user_id = str(UUID(user_id))

    except (ValueError, TypeError, AttributeError):

        return False

    return normalised_user_id in allowed_users


def require_authorised_user(
    user: dict[str, Any] = Depends(
        get_authenticated_user
    )
) -> dict[str, Any]:

    allowed_users = get_allowed_user_ids()

    if not allowed_users:

        raise HTTPException(
            status_code=503,
            detail="User authorisation is not configured."
        )

    if not is_user_authorised(user["user_id"]):

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorised to execute live AI demonstrations."
        )

    return {
        **user,
        "authorised": True
    }
