"""Health endpoint behavior and safe failure responses."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.schemas.errors import ErrorResponse
from app.schemas.health import ApiHealthResponse, HealthResponse


def test_basic_health_returns_minimal_payload(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    assert response.json() == {"status": "ok"}
    HealthResponse.model_validate(response.json())


def test_versioned_health_returns_api_identity(client: TestClient) -> None:
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload == {
        "status": "ok",
        "service": "Festivo AI",
        "api_version": "v1",
    }
    ApiHealthResponse.model_validate(payload)


def test_unhandled_exceptions_return_safe_structured_errors(app: FastAPI) -> None:
    secret = "never-return-this-secret"
    filesystem_marker = "C:\\private\\festivo\\credentials.txt"

    def explode() -> None:
        raise RuntimeError(f"failed with {secret} at {filesystem_marker}")

    app.add_api_route("/test/explode", explode, methods=["GET"], include_in_schema=False)

    with TestClient(app, raise_server_exceptions=False) as test_client:
        response = test_client.get("/test/explode")

    assert response.status_code == 500
    assert response.headers["content-type"].startswith("application/json")
    assert response.json() == {
        "error": {
            "code": "internal_error",
            "message": "An internal server error occurred.",
        }
    }
    body = response.text
    assert secret not in body
    assert filesystem_marker not in body
    assert "Traceback" not in body
    ErrorResponse.model_validate(response.json())


def test_unknown_routes_and_methods_use_the_error_envelope(client: TestClient) -> None:
    not_found = client.get("/does-not-exist")
    wrong_method = client.post("/health")

    assert not_found.status_code == 404
    assert not_found.json()["error"]["code"] == "not_found"
    assert "Traceback" not in not_found.text
    assert "C:\\" not in not_found.text

    assert wrong_method.status_code == 405
    assert wrong_method.json()["error"]["code"] == "method_not_allowed"
    assert wrong_method.headers["content-type"].startswith("application/json")
