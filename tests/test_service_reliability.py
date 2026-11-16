"""Unified service checks with isolated storage and no remote providers."""
import importlib
import sys
import types

import pytest
from fastapi.testclient import TestClient

from tests.conftest import make_settings


@pytest.fixture
def service(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setitem(sys.modules, "env_loader", types.ModuleType("env_loader"))
    from src.retrieval.config import Settings
    settings = make_settings(embedding_provider="hash", rerank_provider="lexical",
                             llm_provider="none", cache_dir=tmp_path / "cache")
    monkeypatch.setattr(Settings, "from_env", classmethod(lambda cls: settings))
    sys.modules.pop("src.api.service", None)
    module = importlib.import_module("src.api.service")
    yield module
    sys.modules.pop("src.api.service", None)


def test_unknown_evidence_is_not_invented(service):
    response = TestClient(service.app).get("/evidence/not-in-corpus")
    assert response.status_code == 404


def test_graph_never_fabricates_missing_evidence(service):
    graph = service.get_graph()
    for node in graph["nodes"]:
        for evidence in node["evidence_details"]:
            assert service.rt.bundle.store.get(evidence["unit_id"]) is not None


def test_diagnostic_returns_real_questions_without_changing_priors(service):
    model = service.get_student("learner")
    before = model.all_masteries()
    result = service.run_diagnostic("learner")
    assert result["status"] == "diagnostic_ready"
    assert result["questions"]
    assert model.all_masteries() == before
    assert all("answer" not in question for question in result["questions"])


def test_ragas_is_explicitly_not_measured(service):
    result = service.get_ragas_metrics()
    assert result["status"] == "not_measured"
    assert result["metrics"] is None


def test_quiz_has_no_duplicates_and_unknown_concept_is_rejected(service):
    client = TestClient(service.app)
    response = client.post("/quiz", json={"concept_id": "c-prob-basics", "size": 25})
    questions = response.json()["questions"]
    assert len(questions) == len({q["q_id"] for q in questions})
    assert client.post("/quiz", json={"concept_id": "missing"}).status_code == 404


def test_upload_rejects_traversal_and_unsupported_files(service):
    client = TestClient(service.app)
    for name in ("../escape.txt", "..\\escape.txt", "page.html"):
        response = client.post("/ingest/upload", files={"file": (name, b"hello")})
        assert response.status_code == 400, (name, response.json())
    assert not list(service.UPLOAD_DIR.iterdir())


def test_multipart_windows_absolute_filename_is_reduced_to_a_safe_basename(service):
    response = TestClient(service.app).post("/ingest/upload", files={"file": ("C:\\escape.txt", b"hello")})
    # The multipart parser normalizes browser-supplied Windows paths first.
    assert response.status_code == 200
    assert response.json()["filenames"] == ["escape.txt"]
    assert (service.UPLOAD_DIR / "escape.txt").is_file()


def test_empty_upload_is_not_success(service):
    response = TestClient(service.app).post("/ingest/upload", files={"file": ("empty.txt", b"")})
    assert response.status_code == 422


def test_source_preview_rejects_windows_traversal(service):
    (service.UPLOAD_DIR.parent / "outside.txt").write_text("private", encoding="utf-8")
    response = TestClient(service.app).get("/uploads/..%5Coutside.txt")
    assert response.status_code == 400


def test_text_upload_roundtrip(service):
    client = TestClient(service.app)
    response = client.post("/ingest/upload", files={"file": ("notes.txt", b"A derivative measures the rate of change.")})
    assert response.status_code == 200
    assert response.json()["units_created"] == 1
    assert client.get("/uploads/notes.txt").text == "A derivative measures the rate of change."
    assert client.get("/sources/notes.txt").text == "A derivative measures the rate of change."


def test_citation_filename_delimiters_are_encoded():
    from src.retrieval.schemas import Location
    assert Location(page=2).open_url("lecture #1.pdf") == "/sources/lecture%20%231.pdf#page=2"


def test_learner_mastery_and_feedback_survive_memory_reset(service):
    question = next(iter(service.QUESTION_BANK.values()))
    service.get_student("persistent")
    service._issue_questions("persistent", [question])
    result = service.submit_answer(service.AnswerRequest(student_id="persistent", q_id=question.q_id, answer=question.answer))
    service.STUDENTS.clear()
    service.SESSIONS.clear()
    service.USED_QIDS.clear()
    model = service.get_student("persistent")
    assert round(model.mastery(result["concept_id"]), 4) == result["new_mastery"]
    assert len(service.SESSIONS["persistent"]) == 1


def test_failed_progress_write_does_not_change_mastery(service, monkeypatch):
    import sqlite3
    from fastapi import HTTPException
    question = next(iter(service.QUESTION_BANK.values()))
    student = service.get_student("disk-error")
    before = student.all_masteries()
    service._issue_questions("disk-error", [question])
    def failed_save(student_id, **kwargs):
        raise sqlite3.OperationalError("synthetic disk failure")
    monkeypatch.setattr(service, "_save_student", failed_save)
    with pytest.raises(HTTPException) as exc:
        service.submit_answer(service.AnswerRequest(student_id="disk-error", q_id=question.q_id, answer=question.answer))
    assert exc.value.status_code == 503
    assert student.all_masteries() == before
    assert service.SESSIONS["disk-error"] == []


def test_unified_chat_rate_limit_and_workload_validation(service):
    from src.retrieval.security import RateLimiter
    service.chat_limiter = RateLimiter(1)
    client = TestClient(service.app)
    assert client.post("/chat", json={"question": "What is the chain rule?"}).status_code == 200
    assert client.post("/chat", json={"question": "What is the chain rule?"}).status_code == 429
    assert client.get("/eval/ablation?students=0").status_code == 422
    assert client.get("/eval/ablation?sessions=100000").status_code == 422
