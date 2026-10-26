"""OpenAPI and request/response contract tests."""

from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel, Field

from app.schemas.health import (
    ApiHealthResponse,
    ConfigurationStatusResponse,
    DatabaseHealthResponse,
    HealthResponse,
)


class PlanRequest(BaseModel):
    """Minimal test-only model used to verify request validation responses."""

    guest_count: int = Field(ge=1, le=1_000)


def test_openapi_schema_generation_and_routes(client: TestClient) -> None:
    response = client.get("/openapi.json")

    assert response.status_code == 200
    schema = response.json()
    assert schema["info"]["title"] == "Festivo AI"
    assert schema["info"]["version"] == "0.8.0"
    assert "/api/v1/events/{event_id}/vendors" in schema["paths"]
    assert "/api/v1/events/{event_id}/vendors/{vendor_id}" in schema["paths"]
    assert "/api/v1/events/{event_id}/vendors/compare" in schema["paths"]
    assert "/api/v1/events/{event_id}/proposals" in schema["paths"]
    assert "/api/v1/events/{event_id}/proposals/generate" in schema["paths"]
    assert "/api/v1/events/{event_id}/proposals/{proposal_id}/approve" in schema["paths"]
    assert "/api/v1/events/{event_id}/proposals/{proposal_id}/reject" in schema["paths"]
    assert "/api/v1/events/{event_id}/export/pdf" in schema["paths"]
    assert "/api/v1/events/{event_id}/export/csv" in schema["paths"]



def test_health_endpoints_conform_to_declared_models(client: TestClient) -> None:
    basic_payload = client.get("/health").json()
    versioned_payload = client.get("/api/v1/health").json()
    database_payload = client.get("/api/v1/health/database").json()

    HealthResponse.model_validate(basic_payload)
    ApiHealthResponse.model_validate(versioned_payload)
    DatabaseHealthResponse.model_validate(database_payload)


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
