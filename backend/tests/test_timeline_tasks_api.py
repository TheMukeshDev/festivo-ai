"""API coverage for timeline generation, tasks, and report exports."""

from fastapi.testclient import TestClient


def _create_event(client: TestClient, event_payload) -> str:
    response = client.post("/api/v1/events", json=event_payload())
    assert response.status_code == 201
    return response.json()["event_id"]


def test_timeline_generate_get_and_regenerate(client: TestClient, event_payload):
    event_id = _create_event(client, event_payload)

    generated = client.post(f"/api/v1/events/{event_id}/timeline")
    assert generated.status_code == 201
    timeline = generated.json()
    assert timeline["event_id"] == event_id
    assert timeline["timeline_id"]

    fetched = client.get(f"/api/v1/events/{event_id}/timeline")
    assert fetched.status_code == 200
    assert fetched.json()["timeline_id"] == timeline["timeline_id"]

    regenerate = client.post(f"/api/v1/events/{event_id}/timeline/regenerate")
    assert regenerate.status_code == 200
    assert regenerate.json()["timeline_id"] == timeline["timeline_id"]

    tasks = client.get(f"/api/v1/events/{event_id}/tasks")
    assert tasks.status_code == 200
    assert tasks.json()["total"] == 8


def test_timeline_generate_rejects_duplicate(client: TestClient, event_payload):
    event_id = _create_event(client, event_payload)
    assert client.post(f"/api/v1/events/{event_id}/timeline").status_code == 201
    duplicate = client.post(f"/api/v1/events/{event_id}/timeline")
    assert duplicate.status_code == 422


def test_task_accepts_iso_datetime_with_offset(client: TestClient, event_payload):
    event_id = _create_event(client, event_payload)

    created = client.post(
        f"/api/v1/events/{event_id}/tasks",
        json={
            "title": "Confirm catering headcount",
            "priority": "high",
            "due_at": "2030-06-10T09:00:00+05:30",
            "assigned_to": "Ananya",
        },
    )
    assert created.status_code == 201
    task = created.json()
    assert task["due_at"] == "2030-06-10T03:30:00Z"

    updated = client.patch(
        f"/api/v1/events/{event_id}/tasks/{task['task_id']}",
        json={"due_at": "2030-06-11T10:00:00Z"},
    )
    assert updated.status_code == 200
    assert updated.json()["due_at"] == "2030-06-11T10:00:00Z"


def test_task_rejects_naive_datetime(client: TestClient, event_payload):
    event_id = _create_event(client, event_payload)
    response = client.post(
        f"/api/v1/events/{event_id}/tasks",
        json={"title": "Naive deadline", "due_at": "2030-06-10T09:00:00"},
    )
    assert response.status_code == 422
    fields = response.json()["error"]["fields"]
    assert fields[0]["field"] == "body.due_at"


def test_task_lifecycle_and_filters(client: TestClient, event_payload):
    event_id = _create_event(client, event_payload)
    created = client.post(
        f"/api/v1/events/{event_id}/tasks",
        json={"title": "Book photographer", "priority": "urgent"},
    )
    assert created.status_code == 201
    task_id = created.json()["task_id"]

    listed = client.get(f"/api/v1/events/{event_id}/tasks?priority=urgent")
    assert listed.status_code == 200
    assert any(item["task_id"] == task_id for item in listed.json()["items"])

    completed = client.patch(
        f"/api/v1/events/{event_id}/tasks/{task_id}",
        json={"status": "completed"},
    )
    assert completed.status_code == 200
    assert completed.json()["completed_at"] is not None

    deleted = client.delete(f"/api/v1/events/{event_id}/tasks/{task_id}")
    assert deleted.status_code == 204
    assert client.get(f"/api/v1/events/{event_id}/tasks/{task_id}").status_code == 404


def test_event_exports_return_downloads(client: TestClient, event_payload):
    event_id = _create_event(client, event_payload)
    assert client.post(f"/api/v1/events/{event_id}/timeline").status_code == 201

    pdf = client.get(f"/api/v1/events/{event_id}/export/pdf")
    assert pdf.status_code == 200
    assert pdf.headers["content-type"] == "application/pdf"
    assert pdf.content.startswith(b"%PDF")

    csv = client.get(f"/api/v1/events/{event_id}/export/csv")
    assert csv.status_code == 200
    assert csv.headers["content-type"].startswith("text/csv")
    assert "event" in csv.text.lower()
