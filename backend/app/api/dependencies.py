"""Shared FastAPI dependencies for authentication and authorization boundaries."""

from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.auth import (
    AuthenticatedUser,
    AuthenticationError,
    AuthenticationUnavailableError,
    TokenVerifier,
)

_bearer = HTTPBearer(auto_error=False, scheme_name="FirebaseBearer")


def get_current_user(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> AuthenticatedUser:
    """Verify a bearer token and return its user, failing closed on errors."""
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication is required.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    verifier: TokenVerifier = request.app.state.auth_verifier
    try:
        return verifier.verify(credentials.credentials)
    except AuthenticationError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication is required.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None
    except AuthenticationUnavailableError:
        raise AuthenticationUnavailableError from None
