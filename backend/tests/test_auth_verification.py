"""Firebase ID-token verification branches, including failure translation."""

from types import SimpleNamespace
from typing import Any
from uuid import NAMESPACE_URL, uuid5

import firebase_admin
import jwt
import pytest
from firebase_admin import auth as firebase_auth
from jwt import PyJWKClientConnectionError, PyJWKClientError

import app.core.auth as auth_module
from app.core.auth import (
    AuthenticationError,
    AuthenticationUnavailableError,
    FirebaseTokenVerifier,
    RejectAllTokenVerifier,
)

PROJECT_ID = "festivo-test"
FIREBASE_UID = "google-oauth2|10493817265"
CLIENT_EMAIL = "firebase-adminsdk@test.iam.gserviceaccount.com"
PRIVATE_KEY = "-----BEGIN PRIVATE KEY-----\\nfake-key\\n-----END PRIVATE KEY-----"


class StubSigningKeyClient:
    """JWK client double that never touches the network."""

    def __init__(self, error: Exception | None = None) -> None:
        self.error = error
        self.requested_tokens: list[str] = []

    def get_signing_key_from_jwt(self, token: str) -> SimpleNamespace:
        self.requested_tokens.append(token)
        if self.error is not None:
            raise self.error
        return SimpleNamespace(key="public-key")


class RecordingDecoder:
    """Captures the arguments used to decode a token."""

    def __init__(self, claims: dict[str, Any] | None = None, error: Exception | None = None):
        self.claims = claims or {}
        self.error = error
        self.calls: list[dict[str, Any]] = []

    def decode(self, token: str, key: Any, **kwargs: Any) -> dict[str, Any]:
        self.calls.append({"token": token, "key": key, **kwargs})
        if self.error is not None:
            raise self.error
        return self.claims


def make_verifier(**overrides: Any) -> FirebaseTokenVerifier:
    values: dict[str, Any] = {"project_id": PROJECT_ID}
    values.update(overrides)
    return FirebaseTokenVerifier(**values)


class TestRejectAllVerifier:
    def test_rejects_every_token(self) -> None:
        with pytest.raises(AuthenticationError):
            RejectAllTokenVerifier().verify("any-token")


class TestTokenShapeValidation:
    def test_an_empty_token_is_rejected_before_decoding(self) -> None:
        verifier = make_verifier()
        verifier._jwk_client = StubSigningKeyClient()

        with pytest.raises(AuthenticationError):
            verifier.verify("")

        assert verifier._jwk_client.requested_tokens == []

    @pytest.mark.parametrize(
        "claims",
        [
            {"aud": PROJECT_ID},
            {"sub": "", "aud": PROJECT_ID},
            {"sub": None, "aud": PROJECT_ID},
            {"sub": 42, "aud": PROJECT_ID},
        ],
    )
    def test_a_token_without_a_usable_subject_is_rejected(
        self,
        monkeypatch: pytest.MonkeyPatch,
        claims: dict[str, Any],
    ) -> None:
        verifier = make_verifier()
        verifier._jwk_client = StubSigningKeyClient()
        decoder = RecordingDecoder(claims=claims)
        monkeypatch.setattr(auth_module.jwt, "decode", decoder.decode)

        with pytest.raises(AuthenticationError):
            verifier.verify("token")

    def test_a_token_issued_for_another_project_is_rejected(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        verifier = make_verifier()
        verifier._jwk_client = StubSigningKeyClient()
        decoder = RecordingDecoder(claims={"sub": FIREBASE_UID, "aud": "other-project"})
        monkeypatch.setattr(auth_module.jwt, "decode", decoder.decode)

        with pytest.raises(AuthenticationError):
            verifier.verify("token")


class TestJwkVerificationPath:
    def test_a_valid_token_maps_to_a_stable_user_identity(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        verifier = make_verifier()
        jwk_client = StubSigningKeyClient()
        verifier._jwk_client = jwk_client
        decoder = RecordingDecoder(claims={"sub": FIREBASE_UID, "aud": PROJECT_ID})
        monkeypatch.setattr(auth_module.jwt, "decode", decoder.decode)

        user = verifier.verify("header.payload.signature")

        assert user.firebase_uid == FIREBASE_UID
        assert user.user_id == uuid5(NAMESPACE_URL, f"firebase:{PROJECT_ID}:{FIREBASE_UID}")
        assert jwk_client.requested_tokens == ["header.payload.signature"]
        assert decoder.calls[0]["audience"] == PROJECT_ID
        assert decoder.calls[0]["issuer"] == f"https://securetoken.google.com/{PROJECT_ID}"

    def test_an_invalid_signature_is_reported_as_an_auth_failure(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        verifier = make_verifier()
        verifier._jwk_client = StubSigningKeyClient()
        decoder = RecordingDecoder(error=jwt.InvalidTokenError("bad signature"))
        monkeypatch.setattr(auth_module.jwt, "decode", decoder.decode)

        with pytest.raises(AuthenticationError):
            verifier.verify("token")

    def test_an_unreachable_key_set_is_reported_as_unavailable(self) -> None:
        verifier = make_verifier()
        verifier._jwk_client = StubSigningKeyClient(PyJWKClientError("no matching key"))

        with pytest.raises(AuthenticationError):
            verifier.verify("token")

    def test_a_network_failure_while_fetching_keys_is_not_an_auth_failure(self) -> None:
        verifier = make_verifier()
        verifier._jwk_client = StubSigningKeyClient(PyJWKClientConnectionError("offline"))

        with pytest.raises(AuthenticationUnavailableError):
            verifier.verify("token")


class TestFirebaseAdminPath:
    def test_credentials_initialize_one_named_app_and_verify_claims(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        app = object()
        created: dict[str, Any] = {}

        def certificate(info: dict[str, Any]) -> dict[str, Any]:
            created["certificate"] = info
            return info

        def initialize_app(credential: Any, name: str) -> Any:
            created["name"] = name
            return app

        def get_app(name: str) -> Any:
            msg = "app does not exist"
            raise ValueError(msg)

        monkeypatch.setattr(auth_module.credentials, "Certificate", certificate)
        monkeypatch.setattr(auth_module.firebase_admin, "initialize_app", initialize_app)
        monkeypatch.setattr(auth_module.firebase_admin, "get_app", get_app)

        verifier = make_verifier(
            client_email=CLIENT_EMAIL,
            private_key=PRIVATE_KEY,
        )
        monkeypatch.setattr(
            auth_module.firebase_auth,
            "verify_id_token",
            lambda *_args, **_kwargs: {"sub": FIREBASE_UID, "aud": PROJECT_ID},
        )

        user = verifier.verify("token")

        assert user.firebase_uid == FIREBASE_UID
        assert created["name"] == f"festivo-{PROJECT_ID}"
        assert created["certificate"]["private_key"].count("\n") == 2

    def test_an_already_initialized_app_is_reused(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        app = object()
        calls: list[str] = []

        def get_app(name: str) -> Any:
            calls.append(name)
            return app

        monkeypatch.setattr(auth_module.firebase_admin, "get_app", get_app)
        monkeypatch.setattr(
            auth_module.firebase_auth,
            "verify_id_token",
            lambda *_args, **_kwargs: {"sub": FIREBASE_UID, "aud": PROJECT_ID},
        )
        verifier = make_verifier(
            client_email=CLIENT_EMAIL,
            private_key=PRIVATE_KEY,
        )
        verifier._app = app

        assert verifier.verify("token").firebase_uid == FIREBASE_UID
        assert calls == []

    @pytest.mark.parametrize(
        "error",
        [
            firebase_auth.RevokedIdTokenError("token revoked"),
            firebase_auth.UserDisabledError("account disabled"),
            firebase_admin.exceptions.FirebaseError(500, "admin sdk failure"),
            ValueError("malformed token"),
        ],
    )
    def test_admin_sdk_failures_are_reported_as_auth_failures(
        self,
        monkeypatch: pytest.MonkeyPatch,
        error: Exception,
    ) -> None:
        verifier = make_verifier(
            client_email=CLIENT_EMAIL,
            private_key=PRIVATE_KEY,
        )
        verifier._app = object()

        def raise_error(token: str, app: Any, check_revoked: bool) -> dict[str, Any]:
            raise error

        monkeypatch.setattr(auth_module.firebase_auth, "verify_id_token", raise_error)

        with pytest.raises(AuthenticationError):
            verifier.verify("token")
