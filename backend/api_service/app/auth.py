"""Validate Keycloak bearer access tokens for protected API routes."""

import logging
from functools import lru_cache

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient, PyJWKClientConnectionError

from app.config import settings

logger = logging.getLogger(__name__)
bearer_scheme = HTTPBearer(auto_error=False)
DOCUMENT_ADMIN_ROLE = "document-admin"


@lru_cache(maxsize=1)
def _jwks_client() -> PyJWKClient:
    return PyJWKClient(settings.keycloak_jwks_url, cache_jwk_set=True, lifespan=300)


def require_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> dict:
    # Explicit local-only opt-in for running the UI without a Keycloak server.
    # Never permit this in staging or production. The bypass identity is used
    # only for requests WITHOUT a token: a token that is present is always
    # validated, so a real Keycloak login keeps its roles (document-admin).
    if (
        settings.environment.lower() == "development"
        and settings.auth_disabled
        and credentials is None
    ):
        return {"sub": "local-development", "preferred_username": "Local preview", "auth_bypass": True}

    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="A valid Keycloak access token is required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        signing_key = _jwks_client().get_signing_key_from_jwt(credentials.credentials)
        return jwt.decode(
            credentials.credentials,
            signing_key.key,
            algorithms=["RS256"],
            audience=settings.keycloak_audience,
            issuer=settings.keycloak_issuer_url,
            options={"require": ["exp", "iat", "iss", "sub", "aud"]},
        )
    except PyJWKClientConnectionError as exc:
        logger.exception("Unable to reach the Keycloak JWKS endpoint")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Identity service is unavailable",
        ) from exc
    except (jwt.InvalidTokenError, jwt.PyJWKClientError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


def require_document_admin(user: dict = Depends(require_current_user)) -> dict:
    """Allow document-management actions only to explicitly assigned admins."""
    if user.get("auth_bypass"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Document administration requires a Keycloak login: the AUTH_DISABLED development bypass carries no role.",
        )
    realm_roles = user.get("realm_access", {}).get("roles", [])
    if DOCUMENT_ADMIN_ROLE not in realm_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The document-admin role is required",
        )
    return user
