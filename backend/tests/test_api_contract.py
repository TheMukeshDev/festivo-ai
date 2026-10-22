"""OpenAPI and request/response contract tests."""

from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel, Field

from app.schemas.health import ApiHealthResponse, ConfigurationStatusResponse, HealthResponse


class PlanRequest(BaseModel):
    """Minimal test-only model used to verify request validation responses."""

    guest_count: int = Field(ge=1, le=1_000)


def test_openapi_schema_generation_and_routes(client: TestClient) -> None:
    response = client.get("/openapi.json")

    assert response.status_code == 200
    schema = response.json()
    assert schema["info"]["title"] == "Festivo AI"
    assert schema["info"]["version"] == "0.3.0"
    assert set(schema["paths"]) == {
        "/health",
        "/api/v1/health",
        "/api/v1/config/status",
        "/api/v1/events",
        "/api/v1/events/{event_id}",
        "/api/v1/events/{event_id}/budget",
        "/api/v1/events/{event_id}/budget/expenses",
        "/api/v1/events/{event_id}/budget/expenses/{expense_id}",
    }


def test_health_endpoints_conform_to_declared_models(client: TestClient) -> None:
    basic_payload = client.get("/health").json()
    versioned_payload = client.get("/api/v1/health").json()

    HealthResponse.model_validate(basic_payload)
    ApiHealthResponse.model_validate(versioned_payload)


def test_configuration_status_conforms_to_declared_model(client: TestClient) -> None:
    response = client.get("/api/v1/config/status")

    assert response.status_code == 200
    ConfigurationStatusResponse.model_validate(response.json())


def test_validation_errors_include_frontend_friendly_field_details(app: FastAPI) -> None:
    def create_plan(payload: PlanRequest) -> PlanRequest:
        return payload

    app.add_api_route(
        "/test/plans",
        create_plan,
        methods=["POST"],
        include_in_schema=False,
    )

    with TestClient(app) as test_client:
        response = test_client.post("/test/plans", json={"guest_count": 0})

    assert response.status_code == 422
    payload = response.json()
    assert payload["error"]["code"] == "validation_error"
    assert payload["error"]["message"] == "Request validation failed."
    assert payload["error"]["fields"][0]["field"] == "body.guest_count"
    assert "greater than or equal to 1" in payload["error"]["fields"][0]["message"]
    assert payload["error"]["fields"][0]["type"] == "greater_than_equal"
