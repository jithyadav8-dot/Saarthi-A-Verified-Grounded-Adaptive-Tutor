"""Exercise the real captioner contract without invoking remote providers."""

import io
import sys
import types

from fastapi import HTTPException, UploadFile
import pytest

from tests.test_service_reliability import service  # noqa: F401


def install_captioner(monkeypatch, result):
    calls = []
    captioner = types.ModuleType("src.ingestion.vision.image_captioner")

    def describe_educational_image(path):
        calls.append(path)
        return result

    # Expose only the name actually provided by the ingestion module.
    captioner.describe_educational_image = describe_educational_image
    monkeypatch.setitem(sys.modules, captioner.__name__, captioner)
    return calls


def test_image_upload_calls_existing_captioner_and_indexes_its_evidence(service, monkeypatch):
    caption = "The diagram plots a tangent line and labels the derivative."
    calls = install_captioner(monkeypatch, caption)
    response = service.upload_material(
        file=UploadFile(filename="derivative.png", file=io.BytesIO(b"synthetic image")),
        files=None,
    )
    assert len(calls) == 1
    assert response["units_created"] == 1
    unit = service.rt.bundle.store.get("derivative_diag1")
    assert unit is not None
    assert unit.image_caption == caption
    assert caption in unit.text


def test_existing_image_uses_same_captioner_contract_at_startup(service, monkeypatch):
    caption = "A tree diagram shows the conditional probability of two events."
    calls = install_captioner(monkeypatch, caption)
    (service.UPLOAD_DIR / "probability.png").write_bytes(b"synthetic image")
    service._init_existing_uploads()
    assert len(calls) == 1
    unit = service.rt.bundle.store.get("probability_diag1")
    assert unit is not None
    assert unit.image_caption == caption


def test_non_educational_image_does_not_create_fabricated_evidence(service, monkeypatch):
    calls = install_captioner(monkeypatch, "NOT_EDUCATIONAL")
    with pytest.raises(HTTPException) as exc:
        service.upload_material(
            file=UploadFile(filename="decorative.png", file=io.BytesIO(b"synthetic image")),
            files=None,
        )
    assert len(calls) == 1
    assert exc.value.status_code == 422
    assert service.rt.bundle.store.get("decorative_diag1") is None
