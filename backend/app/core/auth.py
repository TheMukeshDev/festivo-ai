"""Firebase ID-token verification and authenticated user identity."""

from dataclasses import dataclass
from typing import Protocol
from uuid import NAMESPACE_URL, UUID, uuid5

import firebase_admin
from firebase_admin import auth as firebase_auth
from firebase_admin import credentials


class AuthenticationError(Exception):
    """The supplied access token is missing, invalid, or expired."""


class AuthenticationUnavailableError(Exception):
    """The identity provider's signing keys cannot be reached."""


@dataclass(frozen=True, slots=True)
class AuthenticatedUser:
    """The verified user identity derived from a Firebase ID token."""

    user_id: UUID
    firebase_uid: str | None = None


class TokenVerifier(Protocol):
    """Verification boundary used by API dependencies and test doubles."""

    def verify(self, token: str) -> AuthenticatedUser:
        """Return a verified user or raise an authentication error."""


class RejectAllTokenVerifier:
    """Fail closed when authentication has not been configured."""

    def verify(self, token: str) -> AuthenticatedUser:
        raise AuthenticationError


class FirebaseTokenVerifier:
    """Verify Firebase ID tokens with the Firebase Admin SDK."""

    def __init__(
        self,
        *,
        project_id: str,
        client_email: str,
        private_key: str,
    ) -> None:
        self._project_id = project_id
        self._client_email = client_email
        self._private_key = private_key
        self._app = None

    @staticmethod
    def _get_or_create_app(project_id: str, client_email: str, private_key: str):
        app_name = f"festivo-{project_id}"
        try:
            return firebase_admin.get_app(app_name)
        except ValueError:
            credential = credentials.Certificate(
                {
                    "type": "service_account",
                    "project_id": project_id,
                    "private_key": private_key.replace("\\n", "\n"),
                    "client_email": client_email,
                    "token_uri": "https://oauth2.googleapis.com/token",
                }
            )
            return firebase_admin.initialize_app(credential, name=app_name)

    def verify(self, token: str) -> AuthenticatedUser:
        if not token:
            raise AuthenticationError

        try:
            if self._app is None:
                self._app = self._get_or_create_app(
                    self._project_id,
                    self._client_email,
                    self._private_key,
                )
            claims = firebase_auth.verify_id_token(token, app=self._app, check_revoked=True)
        except firebase_auth.RevokedIdTokenError:
            raise AuthenticationError from None
        except firebase_auth.UserDisabledError:
            raise AuthenticationError from None
        except (firebase_admin.exceptions.FirebaseError, ValueError) as exc:
            raise AuthenticationError from exc

        raw_user_id = claims.get("sub")
        if not isinstance(raw_user_id, str) or not raw_user_id:
            raise AuthenticationError
        if claims.get("aud") != self._project_id:
            raise AuthenticationError
        return AuthenticatedUser(
            user_id=uuid5(NAMESPACE_URL, f"firebase:{self._project_id}:{raw_user_id}"),
            firebase_uid=raw_user_id,
        )
