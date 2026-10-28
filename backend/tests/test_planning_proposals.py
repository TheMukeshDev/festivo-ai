"""Phase 8 proposal, approval, security, and export integration tests."""

import csv
import io
from collections.abc import Callable
from datetime import timedelta
from typing import Any
from uuid import UUID

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.auth import AuthenticatedUser, TokenVerifier
from app.core.config import Settings
from app.main import create_app
from app.repositories.event_repository import InMemoryEventRepository
from app.repositories.memory_proposal_repository import InMemoryProposalRepository
from app.repositories.memory_vendor_repository import InMemoryVendorRepository
from app.services.ai.base import AIRateLimitError
from app.services.ai.planning_service import AIPlanningService
from app.services.budget_service import BudgetService
from app.services.event_service import EventService
from app.services.planning_orchestration_service import PlanningOrchestrationService
from app.services.proposal_service import ProposalService
from app.services.report_service import ReportService
from app.services.task_service import TaskService
from app.services.timeline_service import TimelineService
from app.services.vendor_service import VendorService
from tests.conftest import FIXED_NOW, MutableClock

OWNER_TOKEN = "owner-token"
OTHER_TOKEN = "other-token"
OTHER_USER_ID = UUID("00000000-0000-0000-0000-000000000002")

EventPayloadFactory = Callable[..., dict[str, Any]]


class MultiUserVerifier(TokenVerifier):
    def __init__(self, owner_id: UUID) -> None:
        self._owner_id = owner_id

    def verify(self, token: str) -> AuthenticatedUser:
        if token == OWNER_TOKEN:
            return AuthenticatedUser(user_id=self._owner_id)
        if token == OTHER_TOKEN:
            return AuthenticatedUser(user_id=OTHER_USER_ID)
        raise AssertionError("Unexpected test token.")


class StaticProvider:
    def __init__(self, payload: dict[str, Any]) -> None:
        self._payload = payload
        self.calls = 0

    def generate_structured(self, *, system: str, user: str) -> dict[str, Any]:
        self.calls += 1
        return dict(self._payload)


class FailingProvider:
    def generate_structured(self, *, system: str, user: str) -> dict[str, Any]:
        raise AIRateLimitError("quota exceeded for secret-provider-token")


PLAN_PAYLOAD = {
    "summary": "Focus first on the venue and catering, then lock the guest list.",
    "task_suggestions": [
        {
            "title": "Book the venue",
            "explanation": "Confirm the shortlisted venue before dates fill up.",
            "priority": "high",
        }
    ],
    "budget_suggestions": [
        {
            "category": "Catering",
            "description": "Plan catering allocation",
            "currency": "INR",
            "suggested_amount": "150000.00",
            "rationale": "Catering is typically the largest planned expense.",
            "source": "suggested_allocation",
        }
    ],
    "recommendations": [
        {
            "category": "Guest experience",
            "description": "Send save-the-dates early.",
            "rationale": "Early notice improves attendance for destination events.",
            "priority": "medium",
        }
    ],
}


@pytest.fixture
def proposal_repository() -> InMemoryProposalRepository:
    return InMemoryProposalRepository()


@pytest.fixture
def vendor_service(
    event_repository: InMemoryEventRepository,
    event_service: EventService,
    task_service: TaskService,
    clock: MutableClock,
) -> VendorService:
    return VendorService(
        event_repository,
        InMemoryVendorRepository(),
        event_service,
        task_service,
        clock,
    )


@pytest.fixture
def proposal_service(
    proposal_repository: InMemoryProposalRepository,
    event_service: EventService,
    budget_service: BudgetService,
    task_service: TaskService,
    vendor_service: VendorService,
    clock: MutableClock,
) -> ProposalService:
    return ProposalService(
        proposal_repository,
        event_service,
        budget_service,
        task_service,
        vendor_service,
        clock,
        ttl=timedelta(days=7),
    )


@pytest.fixture
def ai_planning_service(
    make_settings: Callable[..., Settings],
    event_service: EventService,
    budget_service: BudgetService,
    timeline_service: TimelineService,
    task_service: TaskService,
    vendor_service: VendorService,
) -> AIPlanningService:
    return AIPlanningService(
        provider=StaticProvider(PLAN_PAYLOAD),
        settings=make_settings(llm_model="test-model"),
        event_service=event_service,
        budget_service=budget_service,
        timeline_service=timeline_service,
        task_service=task_service,
        vendor_service=vendor_service,
    )


@pytest.fixture
def planning_app(
    make_settings: Callable[..., Settings],
    event_service: EventService,
    budget_service: BudgetService,
    timeline_service: TimelineService,
    task_service: TaskService,
    vendor_service: VendorService,
    proposal_service: ProposalService,
    ai_planning_service: AIPlanningService,
) -> FastAPI:
    orchestration = PlanningOrchestrationService(proposal_service, ai_planning_service)
    report_service = ReportService(
        event_service,
        budget_service,
        task_service,
        vendor_service,
        timeline_service,
        proposal_service,
    )
    return create_app(
        make_settings(),
        event_service=event_service,
        budget_service=budget_service,
        timeline_service=timeline_service,
        task_service=task_service,
        vendor_service=vendor_service,
        auth_verifier=MultiUserVerifier(UUID("00000000-0000-0000-0000-000000000001")),
        proposal_service=proposal_service,
        ai_planning_service=ai_planning_service,
        orchestration_service=orchestration,
        report_service=report_service,
    )


@pytest.fixture
def planning_client(planning_app: FastAPI) -> TestClient:
    with TestClient(planning_app) as client:
        client.headers.update({"Authorization": f"Bearer {OWNER_TOKEN}"})
        yield client


def _create_event(
    client: TestClient,
    event_payload: EventPayloadFactory,
    **overrides: Any,
) -> dict[str, Any]:
    response = client.post("/api/v1/events", json=event_payload(**overrides))
    assert response.status_code == 201, response.text
    return response.json()


def _create_budget(client: TestClient, event_id: str) -> dict[str, Any]:
    response = client.post(
        f"/api/v1/events/{event_id}/budget",
        json={"total_limit": "750000.00", "reserve": {"type": "percentage", "value": "10"}},
    )
    assert response.status_code == 201, response.text
    return response.json()


def _generate(client: TestClient, event_id: str) -> dict[str, Any]:
    response = client.post(f"/api/v1/events/{event_id}/proposals/generate", json={})
    assert response.status_code == 201, response.text
    return response.json()


def _task_total(client: TestClient, event_id: str) -> int:
    response = client.get(f"/api/v1/events/{event_id}/tasks")
    assert response.status_code == 200, response.text
    return response.json()["total"]


def test_generation_persists_pending_owner_scoped_proposal_without_applying(
    planning_client: TestClient,
    event_payload: EventPayloadFactory,
) -> None:
    event = _create_event(planning_client, event_payload)
    budget = _create_budget(planning_client, event["event_id"])

    proposal = _generate(planning_client, event["event_id"])

    assert proposal["status"] == "pending"
    assert proposal["pending_item_count"] == 3
    assert proposal["applied_item_count"] == 0
    assert _task_total(planning_client, event["event_id"]) == 0
    assert planning_client.get(f"/api/v1/events/{event['event_id']}/budget").json() == budget

    listed = planning_client.get(f"/api/v1/events/{event['event_id']}/proposals")
    assert listed.status_code == 200
    assert listed.json()["total"] == 1
    assert listed.json()["items"][0]["proposal_id"] == proposal["proposal_id"]


def test_explicit_approval_applies_once_and_never_mutates_budget(
    planning_client: TestClient,
    event_payload: EventPayloadFactory,
) -> None:
    event = _create_event(planning_client, event_payload)
    budget = _create_budget(planning_client, event["event_id"])
    proposal = _generate(planning_client, event["event_id"])

    approved = planning_client.post(
        f"/api/v1/events/{event['event_id']}/proposals/{proposal['proposal_id']}/approve",
        json={},
    )

    assert approved.status_code == 200, approved.text
    body = approved.json()
    assert body["proposal"]["status"] == "approved"
    assert body["proposal"]["applied_item_count"] == 3
    assert len(body["applied"]) == 3
    assert body["skipped"] == []
    assert _task_total(planning_client, event["event_id"]) == 1
    assert planning_client.get(f"/api/v1/events/{event['event_id']}/budget").json() == budget
    assert any(
        "no budget or expense records were changed" in item["message"] for item in body["applied"]
    )

    repeated = planning_client.post(
        f"/api/v1/events/{event['event_id']}/proposals/{proposal['proposal_id']}/approve",
        json={},
    )
    assert repeated.status_code == 200
    assert repeated.json()["applied"] == []
    assert len(repeated.json()["skipped"]) == 3
    assert _task_total(planning_client, event["event_id"]) == 1


def test_partial_approvals_are_resumable_without_reapplying_items(
    planning_client: TestClient,
    event_payload: EventPayloadFactory,
) -> None:
    event = _create_event(planning_client, event_payload)
    proposal = _generate(planning_client, event["event_id"])
    item_ids = [item["item_id"] for item in proposal["items"]]

    first = planning_client.post(
        f"/api/v1/events/{event['event_id']}/proposals/{proposal['proposal_id']}/approve",
        json={"item_ids": [item_ids[0]]},
    )
    assert first.status_code == 200, first.text
    assert first.json()["proposal"]["status"] == "partially_approved"
    assert first.json()["proposal"]["pending_item_count"] == 2
    assert _task_total(planning_client, event["event_id"]) == 1

    second = planning_client.post(
        f"/api/v1/events/{event['event_id']}/proposals/{proposal['proposal_id']}/approve",
        json={"item_ids": item_ids},
    )
    assert second.status_code == 200, second.text
    assert second.json()["proposal"]["status"] == "approved"
    assert len(second.json()["applied"]) == 2
    assert len(second.json()["skipped"]) == 1
    assert _task_total(planning_client, event["event_id"]) == 1


def test_stale_proposal_is_rejected_after_event_data_changes(
    planning_client: TestClient,
    event_payload: EventPayloadFactory,
) -> None:
    event = _create_event(planning_client, event_payload)
    proposal = _generate(planning_client, event["event_id"])
    created_task = planning_client.post(
        f"/api/v1/events/{event['event_id']}/tasks",
        json={"title": "User-created task", "priority": "low"},
    )
    assert created_task.status_code == 201, created_task.text

    response = planning_client.post(
        f"/api/v1/events/{event['event_id']}/proposals/{proposal['proposal_id']}/approve",
        json={},
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "conflict"
    assert _task_total(planning_client, event["event_id"]) == 1


def test_rejection_marks_pending_items_and_keeps_them_out_of_reports(
    planning_client: TestClient,
    event_payload: EventPayloadFactory,
) -> None:
    event = _create_event(planning_client, event_payload)
    proposal = _generate(planning_client, event["event_id"])

    rejected = planning_client.post(
        f"/api/v1/events/{event['event_id']}/proposals/{proposal['proposal_id']}/reject",
        json={"reason": "Not this month."},
    )

    assert rejected.status_code == 200, rejected.text
    assert rejected.json()["proposal"]["status"] == "rejected"
    assert len(rejected.json()["rejected_items"]) == 3
    assert _task_total(planning_client, event["event_id"]) == 0

    csv_response = planning_client.get(f"/api/v1/events/{event['event_id']}/export/csv")
    assert csv_response.status_code == 200
    rows = list(csv.reader(io.StringIO(csv_response.text)))
    assert not any(row[0] == "recommendation" for row in rows)


def test_exports_are_owner_scoped_and_reports_include_approved_advice(
    planning_client: TestClient,
    event_payload: EventPayloadFactory,
) -> None:
    event = _create_event(planning_client, event_payload)
    proposal = _generate(planning_client, event["event_id"])

    pending_csv = planning_client.get(f"/api/v1/events/{event['event_id']}/export/csv")
    assert pending_csv.status_code == 200
    assert "Catering is typically" not in pending_csv.text

    approved = planning_client.post(
        f"/api/v1/events/{event['event_id']}/proposals/{proposal['proposal_id']}/approve",
        json={},
    )
    assert approved.status_code == 200, approved.text

    pdf = planning_client.get(f"/api/v1/events/{event['event_id']}/export/pdf")
    assert pdf.status_code == 200, pdf.text
    assert pdf.headers["content-type"].startswith("application/pdf")
    assert pdf.headers["content-disposition"].endswith('.pdf"')
    assert pdf.headers["cache-control"] == "no-store, private"
    assert pdf.content.startswith(b"%PDF")
    assert len(pdf.content) > 1000

    csv_response = planning_client.get(f"/api/v1/events/{event['event_id']}/export/csv")
    assert csv_response.status_code == 200
    assert csv_response.headers["content-type"].startswith("text/csv")
    assert csv_response.headers["content-disposition"].endswith('.csv"')
    rows = list(csv.reader(io.StringIO(csv_response.text)))
    assert rows[0] == [
        "section",
        "record_type",
        "name",
        "category",
        "status",
        "date",
        "amount",
        "currency",
        "details",
    ]
    recommendation_rows = [row for row in rows if row[0] == "recommendation"]
    assert len(recommendation_rows) == 2
    assert all("advisory only" in row[8] for row in recommendation_rows)


def test_csv_formula_cells_are_escaped(
    planning_client: TestClient,
    event_payload: EventPayloadFactory,
) -> None:
    event = _create_event(planning_client, event_payload)
    task = planning_client.post(
        f"/api/v1/events/{event['event_id']}/tasks",
        json={"title": '=HYPERLINK("https://example.test")', "priority": "low"},
    )
    assert task.status_code == 201, task.text

    response = planning_client.get(f"/api/v1/events/{event['event_id']}/export/csv")

    assert response.status_code == 200
    rows = list(csv.reader(io.StringIO(response.text)))
    task_row = next(row for row in rows if row[1] == "task")
    assert task_row[2].startswith("'=")


def test_provider_errors_are_mapped_without_leaking_details(
    planning_client: TestClient,
    ai_planning_service: AIPlanningService,
    event_payload: EventPayloadFactory,
) -> None:
    event = _create_event(planning_client, event_payload)
    ai_planning_service._provider = FailingProvider()

    response = planning_client.post(
        f"/api/v1/events/{event['event_id']}/proposals/generate",
        json={},
    )

    assert response.status_code == 429
    assert response.json()["error"]["code"] == "too_many_requests"
    assert "secret-provider-token" not in response.text


def test_planning_endpoints_require_authentication(
    planning_app: FastAPI,
    event_payload: EventPayloadFactory,
) -> None:
    with TestClient(planning_app) as unauthenticated:
        response = unauthenticated.get("/api/v1/events/anything/proposals")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


def test_other_users_cannot_read_or_approve_a_proposal(
    planning_client: TestClient,
    event_payload: EventPayloadFactory,
) -> None:
    event = _create_event(planning_client, event_payload)
    proposal = _generate(planning_client, event["event_id"])

    response = planning_client.get(
        f"/api/v1/events/{event['event_id']}/proposals/{proposal['proposal_id']}",
        headers={"Authorization": f"Bearer {OTHER_TOKEN}"},
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_proposal_errors_are_safe_and_do_not_leak_provider_details(
    planning_client: TestClient,
    event_payload: EventPayloadFactory,
) -> None:
    event = _create_event(planning_client, event_payload)

    response = planning_client.get(f"/api/v1/events/{event['event_id']}/proposals/not-a-uuid")

    assert response.status_code == 404
    assert response.json()["error"]["message"] == "The requested resource was not found."


def test_expired_proposals_cannot_be_approved(
    planning_client: TestClient,
    event_payload: EventPayloadFactory,
    clock: MutableClock,
    proposal_service: ProposalService,
) -> None:
    event = _create_event(planning_client, event_payload)
    proposal = _generate(planning_client, event["event_id"])
    clock.now = FIXED_NOW + timedelta(days=8)

    response = planning_client.post(
        f"/api/v1/events/{event['event_id']}/proposals/{proposal['proposal_id']}/approve",
        json={},
    )

    assert response.status_code == 409
    fetched = proposal_service.get(
        UUID("00000000-0000-0000-0000-000000000001"),
        event["event_id"],
        proposal["proposal_id"],
    )
    assert fetched.status.value == "expired"
    assert _task_total(planning_client, event["event_id"]) == 0
