from fastapi.testclient import TestClient


def create_event(client: TestClient, event_payload):
    client.headers.update({"Authorization": "Bearer test-token"})
    response = client.post("/api/v1/events", json=event_payload())
    assert response.status_code == 201
    return response.json()["event_id"]


def test_vendor_crud_and_compare(client: TestClient, event_payload):
    client.headers.update({"Authorization": "Bearer test-token"})
    event_id = create_event(client, event_payload)
    r = client.post(
        f"/api/v1/events/{event_id}/vendors",
        json={
            "name": "Dream Venue",
            "category": "venue",
            "price_min": "50000.00",
            "price_max": "100000.00",
            "currency": "INR",
        },
    )
    assert r.status_code == 201
    v = r.json()
    vid = v["vendor_id"]
    assert v["name"] == "Dream Venue"
    r2 = client.get(f"/api/v1/events/{event_id}/vendors")
    assert r2.status_code == 200
    r3 = client.get(f"/api/v1/events/{event_id}/vendors/{vid}")
    assert r3.status_code == 200
    r4 = client.patch(f"/api/v1/events/{event_id}/vendors/{vid}", json={"status": "shortlisted"})
    assert r4.status_code == 200
    r5 = client.post(f"/api/v1/events/{event_id}/vendors/compare", json={"vendor_ids": [vid]})
    assert r5.status_code == 422
    # add second
    r6 = client.post(
        f"/api/v1/events/{event_id}/vendors",
        json={
            "name": "Budget Caterers",
            "category": "catering",
            "price_min": "20000.00",
            "price_max": "40000.00",
            "currency": "INR",
        },
    )
    assert r6.status_code == 201
    v2 = r6.json()
    r7 = client.post(
        f"/api/v1/events/{event_id}/vendors/compare", json={"vendor_ids": [vid, v2["vendor_id"]]}
    )
    assert r7.status_code == 200
    res = r7.json()
    assert "criteria" in res and "items" in res
