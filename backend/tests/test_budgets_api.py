"""Budget and expense HTTP contracts, validation, and safe errors."""

from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.core.exceptions import StorageUnavailableError
from app.repositories.memory_budget_repository import InMemoryBudgetRepository


def create_event(client: TestClient, event_payload) -> str:
    response = client.post("/api/v1/events", json=event_payload())
    assert response.status_code == 201
    return response.json()["event_id"]


def budget_url(event_id: str) -> str:
    return f"/api/v1/events/{event_id}/budget"


def create_budget(
    client: TestClient,
    event_id: str,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    response = client.post(budget_url(event_id), json=payload or {})
    assert response.status_code == 201, response.text
    return response.json()


def create_expense(
    client: TestClient,
    event_id: str,
    version: int,
    **overrides: Any,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "expected_version": version,
        "category": "Catering and Refreshments",
        "name": "Dinner service",
        "amount": "180000.00",
        "amount_status": "quoted",
    }
    payload.update(overrides)
    response = client.post(f"{budget_url(event_id)}/expenses", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def test_create_and_get_budget_uses_event_defaults(
    client: TestClient,
    event_payload,
) -> None:
    event_id = create_event(client, event_payload)

    created = create_budget(client, event_id)

    assert created["event_id"] == event_id
    assert created["total_limit"] == "750000.00"
    assert created["currency"] == "INR"
    assert created["reserve"] == {
        "type": "percentage",
        "value": "0.00",
        "amount": "0.00",
    }
    assert created["planned_spending"] == "0.00"
    assert created["available_for_planning"] == "750000.00"
    assert created["remaining_total"] == "750000.00"
    assert created["remaining_after_reserve"] == "750000.00"
    assert created["budget_overrun"] == "0.00"
    assert created["reserve_consumed"] == "0.00"
    assert created["cost_per_guest"] == "0.00"
    assert created["status"] == "within_allocation"
    assert created["version"] == 1
    assert created["issues"] == []
    assert created["category_totals"] == []
    assert created["expenses"] == []

    fetched = client.get(budget_url(event_id))
    assert fetched.status_code == 200
    assert fetched.json() == created


def test_budget_creation_accepts_custom_limit_and_percentage_reserve(
    client: TestClient,
    event_payload,
) -> None:
    event_id = create_event(client, event_payload)

    budget = create_budget(
        client,
        event_id,
        {
            "total_limit": "1000.00",
            "reserve": {"type": "percentage", "value": "10"},
        },
    )

    assert budget["total_limit"] == "1000.00"
    assert budget["reserve"]["amount"] == "100.00"
    assert budget["available_for_planning"] == "900.00"


def test_duplicate_budget_is_a_safe_conflict(client: TestClient, event_payload) -> None:
    event_id = create_event(client, event_payload)
    create_budget(client, event_id)

    response = client.post(budget_url(event_id), json={})

    assert response.status_code == 409
    assert response.json() == {
        "error": {
            "code": "conflict",
            "message": "The request conflicts with the current resource state.",
        }
    }


def test_missing_event_and_budget_return_safe_not_found_errors(
    client: TestClient,
    event_payload,
) -> None:
    missing = client.get(budget_url("not-a-valid-event-id"))
    assert missing.status_code == 404

    event_id = create_event(client, event_payload)
    no_budget = client.get(budget_url(event_id))
    assert no_budget.status_code == 404
    assert no_budget.json()["error"]["code"] == "not_found"

    bad_budget = client.get(budget_url("00000000-0000-4000-8000-000000000000"))
    assert bad_budget.status_code == 404


def test_update_budget_increments_version(
    client: TestClient,
    event_payload,
) -> None:
    event_id = create_event(client, event_payload)
    create_budget(client, event_id)

    response = client.patch(
        budget_url(event_id),
        json={
            "expected_version": 1,
            "total_limit": "1000.00",
            "reserve": {"type": "fixed_amount", "value": "125.00"},
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["version"] == 2
    assert payload["total_limit"] == "1000.00"
    assert payload["reserve"] == {
        "type": "fixed_amount",
        "value": "125.00",
        "amount": "125.00",
    }


def test_stale_budget_version_returns_conflict(client: TestClient, event_payload) -> None:
    event_id = create_event(client, event_payload)
    create_budget(client, event_id)
    client.patch(budget_url(event_id), json={"expected_version": 1, "total_limit": "900.00"})

    response = client.patch(
        budget_url(event_id),
        json={"expected_version": 1, "total_limit": "800.00"},
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "conflict"


@pytest.mark.parametrize(
    "payload",
    [
        {"expected_version": 1, "total_limit": None},
        {"expected_version": 1, "reserve": None},
        {"total_limit": "1000.00"},
        {"expected_version": "1", "total_limit": "1000.00"},
        {"expected_version": 0, "total_limit": "1000.00"},
        {"expected_version": 1, "total_limit": "0"},
        {"expected_version": 1, "total_limit": "10.001"},
        {"expected_version": 1, "total_limit": "100000000.01"},
        {"expected_version": 1, "reserve": {"type": "percentage", "value": "100.01"}},
        {"expected_version": 1, "reserve": {"type": "unknown", "value": "10"}},
        {"expected_version": 1, "reserve": {"type": "fixed_amount", "value": "-1"}},
        {"expected_version": 1, "currency": "USD"},
    ],
)
def test_invalid_budget_updates_are_rejected(
    client: TestClient,
    event_payload,
    payload: dict[str, Any],
) -> None:
    event_id = create_event(client, event_payload)
    create_budget(client, event_id)

    response = client.patch(budget_url(event_id), json=payload)

    assert response.status_code == 422, response.text
    assert response.json()["error"]["code"] == "validation_error"


def test_fixed_reserve_above_total_is_a_domain_validation_error(
    client: TestClient,
    event_payload,
) -> None:
    event_id = create_event(client, event_payload)

    response = client.post(
        budget_url(event_id),
        json={
            "total_limit": "100.00",
            "reserve": {"type": "fixed_amount", "value": "100.01"},
        },
    )

    assert response.status_code == 422
    fields = response.json()["error"]["fields"]
    assert fields[0]["field"] == "body.reserve.value"
    assert "cannot exceed" in fields[0]["message"]


def test_add_expense_returns_recalculated_summary(
    client: TestClient,
    event_payload,
) -> None:
    event_id = create_event(client, event_payload)
    budget = create_budget(
        client,
        event_id,
        {
            "total_limit": "1000.00",
            "reserve": {"type": "percentage", "value": "10"},
        },
    )

    updated = create_expense(client, event_id, budget["version"], amount="950.00")

    assert updated["version"] == 2
    assert len(updated["expenses"]) == 1
    expense = updated["expenses"][0]
    assert expense["category"] == "Catering and Refreshments"
    assert expense["name"] == "Dinner service"
    assert expense["amount"] == "950.00"
    assert expense["amount_status"] == "quoted"
    assert expense["notes"] is None
    assert updated["planned_spending"] == "950.00"
    assert updated["remaining_total"] == "50.00"
    assert updated["remaining_after_reserve"] == "-50.00"
    assert updated["reserve_consumed"] == "50.00"
    assert updated["status"] == "reserve_consumed"
    assert updated["issues"][0]["code"] == "reserve_consumed"
    assert updated["category_totals"] == [
        {"category": "Catering and Refreshments", "amount": "950.00"}
    ]


def test_over_budget_response_is_explicit(client: TestClient, event_payload) -> None:
    event_id = create_event(client, event_payload)
    budget = create_budget(
        client,
        event_id,
        {"total_limit": "1000.00", "reserve": {"type": "percentage", "value": "10"}},
    )

    updated = create_expense(client, event_id, budget["version"], amount="1100.00")

    assert updated["status"] == "over_budget"
    assert updated["budget_overrun"] == "100.00"
    assert updated["reserve_consumed"] == "200.00"
    assert updated["issues"] == [
        {
            "code": "total_budget_exceeded",
            "severity": "error",
            "message": "Planned spending exceeds the total budget by INR 100.00.",
        }
    ]


def test_update_and_delete_expense_versions(client: TestClient, event_payload) -> None:
    event_id = create_event(client, event_payload)
    budget = create_budget(client, event_id, {"total_limit": "1000.00"})
    added = create_expense(client, event_id, budget["version"], amount="100.00")
    expense_id = added["expenses"][0]["expense_id"]

    updated = client.patch(
        f"{budget_url(event_id)}/expenses/{expense_id}",
        json={
            "expected_version": 2,
            "name": "Updated dinner",
            "amount": "250.00",
            "amount_status": "confirmed",
            "notes": "Contract signed",
        },
    )
    assert updated.status_code == 200, updated.text
    payload = updated.json()
    assert payload["version"] == 3
    assert payload["expenses"][0]["name"] == "Updated dinner"
    assert payload["expenses"][0]["amount"] == "250.00"
    assert payload["expenses"][0]["amount_status"] == "confirmed"
    assert payload["planned_spending"] == "250.00"

    deleted = client.delete(
        f"{budget_url(event_id)}/expenses/{expense_id}",
        params={"expected_version": 3},
    )
    assert deleted.status_code == 200, deleted.text
    assert deleted.json()["version"] == 4
    assert deleted.json()["expenses"] == []
    assert deleted.json()["planned_spending"] == "0.00"


def test_delete_expense_requires_version_query(client: TestClient, event_payload) -> None:
    event_id = create_event(client, event_payload)
    budget = create_budget(client, event_id)
    added = create_expense(client, event_id, budget["version"])
    expense_id = added["expenses"][0]["expense_id"]

    response = client.delete(f"{budget_url(event_id)}/expenses/{expense_id}")

    assert response.status_code == 422


def test_unknown_expense_is_a_consistent_not_found(
    client: TestClient,
    event_payload,
) -> None:
    event_id = create_event(client, event_payload)
    create_budget(client, event_id)
    unknown = "00000000-0000-4000-8000-000000000000"

    patched = client.patch(
        f"{budget_url(event_id)}/expenses/{unknown}",
        json={"expected_version": 1, "amount": "10.00"},
    )
    deleted = client.delete(
        f"{budget_url(event_id)}/expenses/{unknown}",
        params={"expected_version": 1},
    )

    assert patched.status_code == 404
    assert deleted.status_code == 404
    assert patched.json()["error"]["code"] == "not_found"


@pytest.mark.parametrize(
    "payload",
    [
        {"category": "Catering", "name": "Dinner", "amount": "0"},
        {"category": "", "name": "Dinner", "amount": "10.00"},
        {"category": "Catering", "name": "", "amount": "10.00"},
        {"category": "Catering", "name": "Dinner", "amount": "10.001"},
        {"category": "Catering", "name": "Dinner", "amount": "100000000.01"},
        {"category": "Catering", "name": "Dinner", "amount": "10", "amount_status": "paid"},
        {"category": "Catering", "name": "Dinner", "amount": "10", "notes": "x" * 501},
        {"category": "Catering", "name": "Dinner", "amount": "10", "currency": "USD"},
        {"category": "Catering", "name": "Dinner", "amount": None},
    ],
)
def test_invalid_expenses_are_rejected(
    client: TestClient,
    event_payload,
    payload: dict[str, Any],
) -> None:
    event_id = create_event(client, event_payload)
    create_budget(client, event_id)
    payload["expected_version"] = 1

    response = client.post(f"{budget_url(event_id)}/expenses", json=payload)

    assert response.status_code == 422, response.text
    assert response.json()["error"]["code"] == "validation_error"


def test_stale_expense_mutation_returns_conflict_and_preserves_data(
    client: TestClient,
    event_payload,
) -> None:
    event_id = create_event(client, event_payload)
    budget = create_budget(client, event_id)
    added = create_expense(client, event_id, budget["version"])
    expense_id = added["expenses"][0]["expense_id"]

    response = client.patch(
        f"{budget_url(event_id)}/expenses/{expense_id}",
        json={"expected_version": 1, "amount": "1.00"},
    )

    assert response.status_code == 409
    fetched = client.get(budget_url(event_id)).json()
    assert fetched["version"] == 2
    assert fetched["expenses"][0]["amount"] == "180000.00"


def test_deleting_event_makes_its_budget_unreachable(client: TestClient, event_payload) -> None:
    event_id = create_event(client, event_payload)
    create_budget(client, event_id)

    deleted = client.delete(f"/api/v1/events/{event_id}")

    assert deleted.status_code == 204
    assert client.get(budget_url(event_id)).status_code == 404


def test_database_outage_returns_safe_service_unavailable(
    client: TestClient,
    event_payload,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    event_id = create_event(client, event_payload)

    def unavailable(*_args: object, **_kwargs: object) -> None:
        raise StorageUnavailableError("internal database detail")

    monkeypatch.setattr(InMemoryBudgetRepository, "get_by_event", unavailable)

    response = client.post(budget_url(event_id), json={})

    assert response.status_code == 503
    assert response.json() == {
        "error": {
            "code": "service_unavailable",
            "message": "The database is temporarily unavailable.",
        }
    }
    assert "internal database detail" not in response.text
