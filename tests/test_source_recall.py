from fastapi.testclient import TestClient

from tests.test_service_reliability import service  # noqa: F401


def test_uploaded_notes_create_source_scoped_recall_and_feedback(service):
    client = TestClient(service.app)
    name = "motion.md"
    text = "Momentum equals mass multiplied by velocity. Impulse measures a change in momentum."
    assert client.post("/ingest/upload", files={"file": (name, text)}).status_code == 200
    assert name in client.get("/practice/sources").json()["sources"]
    cards = client.get("/practice/cards", params={"source_id": name}).json()["cards"]
    assert len(cards) == 2
    assert all("answer" not in card and "quote" not in card for card in cards)
    body = {"source_id": name, "item_id": cards[0]["item_id"], "answer": "  the MOMENTUM "}
    feedback = client.post("/practice/check", json=body).json()
    assert feedback["matches"] and feedback["term"] == "Momentum"
    cite = feedback["citation"]
    assert cite["source_id"] == name
    indexed = client.get('/evidence/' + cite['unit_id']).json()['text']
    assert indexed[cite["excerpt_start"]:cite["excerpt_end"]] == cite["excerpt"]
    assert cite["excerpt"] in text
    assert not client.post("/practice/check", json={**body, "answer": "force"}).json()["matches"]
    assert client.post("/practice/check", json={**body, "source_id": "other.txt"}).status_code == 409
    assert client.post("/practice/check", json={**body, "answer": " "}).status_code == 422
    assert client.post("/ingest/upload", files={"file": (name, "Velocity describes speed and direction.")}).status_code == 200
    assert client.post("/practice/check", json=body).status_code == 409


def test_source_without_definition_and_missing_source(service):
    client = TestClient(service.app)
    assert client.post("/ingest/upload", files={"file": ("memo.txt", "Read chapter five before the next class.")}).status_code == 200
    assert client.get("/practice/cards", params={"source_id": "memo.txt"}).json() == {"cards": []}
    assert client.get("/practice/cards", params={"source_id": "absent"}).status_code == 404
