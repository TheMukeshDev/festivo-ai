"""Supabase access-token verification and authenticated user identity."""

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

import jwt
from jwt import PyJWKClient, PyJWKClientConnectionError, PyJWKClientError


class AuthenticationError(Exception):
    """The supplied access token is missing, invalid, or expired."""


class AuthenticationUnavailableError(Exception):
    """The identity provider's signing keys cannot be reached."""


@dataclass(frozen=True, slots=True)
class AuthenticatedUser:
    """The verified user identity derived from a Supabase access token."""

    user_id: UUID


class TokenVerifier(Protocol):
    """Verification boundary used by API dependencies and test doubles."""

    def verify(self, token: str) -> AuthenticatedUser:
        """Return a verified user or raise an authentication error."""


class RejectAllTokenVerifier:
    """Fail closed when authentication has not been configured."""

    def verify(self, token: str) -> AuthenticatedUser:
        raise AuthenticationError


class SupabaseTokenVerifier:
    """Verify Supabase ES256/RS256 access tokens against the project JWKS."""

    _ALGORITHMS = ("ES256", "RS256")

    def __init__(
        self,
        *,
        jwks_url: str,
        issuer: str,
        audience: str = "authenticated",
        leeway_seconds: int = 30,
        jwk_client: PyJWKClient | None = None,
    ) -> None:
        self._issuer = issuer.rstrip("/")
        self._audience = audience
        self._leeway_seconds = leeway_seconds
        self._jwk_client = jwk_client or PyJWKClient(
            jwks_url,
            cache_keys=True,
            cache_jwk_set=True,
            lifespan=300,
            timeout=10,
        )

    def verify(self, token: str) -> AuthenticatedUser:
        if not token:
            raise AuthenticationError

        try:
            signing_key = self._jwk_client.get_signing_key_from_jwt(token)
            claims = jwt.decode(
                token,
                signing_key.key,
                algorithms=list(self._ALGORITHMS),
                audience=self._audience,
                issuer=self._issuer,
                leeway=self._leeway_seconds,
                options={
                    "require": ["exp", "iat", "sub", "aud", "iss"],
                    "verify_exp": True,
                    "verify_iat": True,
                    "verify_aud": True,
                    "verify_iss": True,
                    "verify_signature": True,
                },
            )
        except PyJWKClientConnectionError as exc:
            raise AuthenticationUnavailableError from exc
        except (PyJWKClientError, jwt.PyJWTError, ValueError) as exc:
            raise AuthenticationError from exc

        if claims.get("role") != "authenticated":
            raise AuthenticationError
        raw_user_id = claims.get("sub")
        if not isinstance(raw_user_id, str):
            raise AuthenticationError
        try:
            user_id = UUID(raw_user_id)
        except ValueError as exc:
            raise AuthenticationError from exc
        if str(user_id) != raw_user_id.lower():
            raise AuthenticationError
        return AuthenticatedUser(user_id=user_id)
