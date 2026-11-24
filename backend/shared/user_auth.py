from functools import lru_cache
from typing import Any

import jwt

from jwt import PyJWKClient
from jwt.exceptions import (
    InvalidTokenError,
    PyJWKClientError,
    PyJWKClientConnectionError
)

from fastapi import Depends, HTTPException, status

from fastapi.security import (
    HTTPBearer,
    HTTPAuthorizationCredentials
)

from shared.config import get_settings


bearer_scheme = HTTPBearer(auto_error=False)


def authentication_error() -> HTTPException:

    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing access token.",
        headers={"WWW-Authenticate": "Bearer"}
    )


@lru_cache
def get_jwks_client() -> PyJWKClient:

    settings = get_settings()

    if not settings.azure_tenant_id:
        raise ValueError(
            "AZURE_TENANT_ID must be configured."
        )

    jwks_url = (
        "https://login.microsoftonline.com/"
        f"{settings.azure_tenant_id}/"
        "discovery/v2.0/keys"
    )

    return PyJWKClient(
        jwks_url,
        cache_jwk_set=True,
        lifespan=300,
        timeout=10
    )


def validate_access_token(
    token: str
) -> dict[str, Any]:

    settings = get_settings()

    if not all([
        settings.azure_tenant_id,
        settings.api_client_id,
        settings.spa_client_id,
        settings.api_scope
    ]):

        raise HTTPException(
            status_code=503,
            detail="Authentication is not configured."
        )

    issuer = (
        "https://login.microsoftonline.com/"
        f"{settings.azure_tenant_id}/v2.0"
    )

    try:

        signing_key = (
            get_jwks_client()
            .get_signing_key_from_jwt(token)
        )

        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            audience=settings.api_client_id,
            issuer=issuer,
            options={
                "require": [
                    "exp",
                    "nbf",
                    "iat",
                    "iss",
                    "aud",
                    "tid",
                    "oid",
                    "ver",
                    "azp",
                    "scp"
                ]
            }
        )

    except PyJWKClientConnectionError:

        raise HTTPException(
            status_code=503,
            detail="Authentication service unavailable."
        )

    except (InvalidTokenError, PyJWKClientError):

        raise authentication_error()

    if claims.get("tid") != settings.azure_tenant_id:

        raise authentication_error()

    if claims.get("ver") != "2.0":

        raise authentication_error()

    if claims.get("azp") != settings.spa_client_id:

        raise HTTPException(
            status_code=403,
            detail="Client application is not authorised."
        )

    scope_claim = claims.get("scp")

    if not isinstance(scope_claim, str):

        raise authentication_error()

    scopes = scope_claim.split()

    if settings.api_scope not in scopes:

        raise HTTPException(
            status_code=403,
            detail="Required API permission is missing."
        )

    return claims


def get_authenticated_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(
        bearer_scheme
    )
) -> dict[str, Any]:

    if credentials is None:

        raise authentication_error()

    if credentials.scheme.lower() != "bearer":

        raise authentication_error()

    claims = validate_access_token(
        credentials.credentials
    )

    return {
        "user_id": claims["oid"],
        "tenant_id": claims["tid"],
        "client_id": claims["azp"],
        "scopes": claims["scp"].split()
    }
