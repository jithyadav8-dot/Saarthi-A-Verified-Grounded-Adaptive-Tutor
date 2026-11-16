"""Real HTTP assessment lifecycle with isolated SQLite and offline fixtures."""
import sqlite3

import pytest
from fastapi.testclient import TestClient

from tests.test_service_reliability import service  # noqa: F401


def issue(client, student="learner", diagnostic=False):
    response = (client.post(f"/diagnostic?student_id={student}") if diagnostic else
                client.post("/quiz", json={"student_id": student, "size": 1}))
    assert response.status_code == 200
    return response.json()["questions"][0]


def payload(service, item, student="learner", answer=None):
    return {"student_id": student, "q_id": item["q_id"],
            "answer": answer if answer is not None else service.QUESTION_BANK[item["q_id"]].answer,
            "attempt_id": item.get("attempt_id")}


def test_unissued_answer_is_rejected(service):
    client = TestClient(service.app)
    q = next(iter(service.QUESTION_BANK.values()))
    response = client.post("/answer", json={"student_id": "learner", "q_id": q.q_id, "answer": q.answer})
    assert response.status_code == 409
    assert service.get_student("learner").mastery(service.get_question_concept_id(q)) == .3


def test_retry_updates_once_and_survives_restart(service):
    client = TestClient(service.app)
    item = issue(client)
    request = payload(service, item)
    first = client.post("/answer", json=request)
    assert first.status_code == 200
    second = client.post("/answer", json=request)
    assert second.status_code == 200
    assert second.json()["new_mastery"] == first.json()["new_mastery"]
    assert len(service.SESSIONS["learner"]) == 1
    service.STUDENTS.clear(); service.SESSIONS.clear(); service.USED_QIDS.clear()
    third = client.post("/answer", json=request)
    assert third.json()["new_mastery"] == first.json()["new_mastery"]
    assert third.json()["replayed"] is True
    assert len(client.get("/completed-quizzes?student_id=learner").json()) == 1


def test_conflicting_retry_and_other_student_are_rejected(service):
    client = TestClient(service.app)
    item = issue(client)
    assert client.post("/answer", json=payload(service, item)).status_code == 200
    assert client.post("/answer", json=payload(service, item, answer="different answer")).status_code == 409
    assert client.post("/answer", json=payload(service, item, student="other")).status_code == 409


def test_diagnostic_observes_without_teaching_transition(service):
    client = TestClient(service.app)
    item = issue(client, diagnostic=True)
    result = client.post("/answer", json=payload(service, item))
    assert result.status_code == 200
    # P(L|correct) = .3*.9 / (.3*.9 + .7*.2); no + (1-p)*.15 learning step.
    assert result.json()["new_mastery"] == round(.27 / .41, 4)
    assert result.json()["learning_opportunity"] is False


def test_failed_attempt_transaction_rolls_back_and_can_retry(service, monkeypatch):
    client = TestClient(service.app)
    item = issue(client)
    original = service._save_student
    before = service.get_student("learner").all_masteries()
    def fail(*args, **kwargs):
        raise sqlite3.OperationalError("simulated write failure")
    monkeypatch.setattr(service, "_save_student", fail)
    assert client.post("/answer", json=payload(service, item)).status_code == 503
    assert service.get_student("learner").all_masteries() == before
    monkeypatch.setattr(service, "_save_student", original)
    assert client.post("/answer", json=payload(service, item)).status_code == 200
    assert len(service.SESSIONS["learner"]) == 1


def test_issued_questions_have_distinct_durable_attempts(service):
    client = TestClient(service.app)
    first = issue(client)
    assert first.get("attempt_id")
    service.STUDENTS.clear(); service.SESSIONS.clear(); service.USED_QIDS.clear()
    assert client.post("/answer", json=payload(service, first)).status_code == 200
    second = issue(client)
    assert second["attempt_id"] != first["attempt_id"]


def test_concurrent_retries_only_record_one_observation(service):
    from concurrent.futures import ThreadPoolExecutor
    client = TestClient(service.app)
    item = issue(client)
    request = service.AnswerRequest(**payload(service, item))
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda _: service.submit_answer(request), range(4)))
    assert len({r["new_mastery"] for r in results}) == 1
    assert sum(not r["replayed"] for r in results) == 1
    assert len(service.SESSIONS["learner"]) == 1


def test_second_practice_cycle_rotates_all_eligible_items(service):
    client = TestClient(service.app)
    request = {"student_id": "cycle", "size": 25}
    first = client.post("/quiz", json=request).json()["questions"]
    assert len(first) > 1
    second = [issue(client, student="cycle") for _ in first]
    assert {item["q_id"] for item in second} == {item["q_id"] for item in first}
    assert {item["attempt_id"] for item in second}.isdisjoint(item["attempt_id"] for item in first)


def test_chat_verification_metadata_survives_reload(service):
    client = TestClient(service.app)
    session = client.post("/sessions", json={"student_id": "learner"}).json()["id"]
    result = client.post(f"/sessions/{session}/chat", json={"question": "What is the chain rule?", "student_id": "learner"})
    assert result.status_code == 200
    saved = client.get(f"/sessions/{session}").json()["messages"][-1]
    assert saved["confidence_kind"] == result.json()["confidence_kind"] == "retrieval_score"
    assert saved["verification"] == "extractive"
    assert saved["claims"] == result.json()["claims"]


def test_structured_slide_upload_reaches_search_and_source_view(service, tmp_path):
    from tests.test_structured_slides import write_fixture
    path = tmp_path / "physics.pptx"
    write_fixture(path)
    client = TestClient(service.app)
    result = client.post("/ingest/upload", files={"file": (path.name, path.read_bytes())})
    assert result.status_code == 200
    units = service.rt.bundle.store.by_source(path.name)
    assert any("a = (F)/(m)" in unit.text for unit in units)
    hits = service.rt.bundle.retriever.search("distinguish mass from weight", source_ids=[path.name])
    assert hits and "Speaker reminder" in hits[0].unit.text
    assert client.get("/sources/physics.pptx").status_code == 200


def test_wrong_answer_report_has_location_without_claiming_diagnosis(service):
    client = TestClient(service.app)
    item = issue(client)
    assert client.post("/answer", json=payload(service, item, answer="wrong")).status_code == 200
    report = client.get("/report/learner").json()["report"]
    assert "Slide 12" in report
    assert "not a diagnosis" in report
