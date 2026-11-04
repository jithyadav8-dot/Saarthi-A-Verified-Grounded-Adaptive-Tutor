"""Failed parsing/persistence must not change the active graph."""
import io

import pytest
from fastapi import HTTPException, UploadFile

from tests.test_service_reliability import service  # noqa: F401


def upload(name, content):
    return UploadFile(filename=name, file=io.BytesIO(content))


def test_failed_upload_persistence_leaves_graph_unchanged(service, monkeypatch):
    before = service.rt.bundle
    graph_before = before.graph.to_dict()
    def unavailable(*args):
        raise OSError("synthetic disk failure")
    monkeypatch.setattr(service.rt, "_persist", unavailable)
    with pytest.raises(HTTPException):
        service.upload_material(file=upload("notes.txt", b"A derivative is a rate of change."), files=None)
    assert service.rt.bundle is before
    assert service.rt.bundle.graph.to_dict() == graph_before


def test_empty_second_file_does_not_publish_first_file_concept(service):
    graph_before = service.rt.bundle.graph.to_dict()
    with pytest.raises(HTTPException) as error:
        service.upload_material(file=None, files=[upload("notes.txt", b"Useful notes"), upload("empty.txt", b"")])
    assert error.value.status_code == 422
    assert service.rt.bundle.graph.to_dict() == graph_before


def test_successful_replacement_refreshes_document_evidence(service):
    service.upload_material(file=upload("notes.txt", b"Short notes"), files=None)
    response = service.upload_material(file=upload("notes.txt", b"a" * 1800), files=None)
    assert response["units_created"] == 2
    concept = service.rt.bundle.graph.concepts["doc_notes"]
    assert concept.evidence_units == ["notes_c1", "notes_c2"]
    assert all(service.rt.bundle.store.get(uid) is not None for uid in concept.evidence_units)
