import importlib
import io
from pathlib import Path
import runpy
import sys
import types

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("namespace", ["src.ingestion", "backend.app"])
def test_bounded_upload_preserves_existing_file_and_cleans_temporary_files(namespace, tmp_path):
    safety = importlib.import_module(f"{namespace}.upload_safety")
    existing = tmp_path / "notes.txt"
    existing.write_bytes(b"original")
    with pytest.raises(safety.UploadTooLargeError):
        safety.save_upload(io.BytesIO(b"too long"), tmp_path, "notes.txt", max_bytes=4)
    assert existing.read_bytes() == b"original"
    assert list(tmp_path.iterdir()) == [existing]
    assert safety.save_upload(io.BytesIO(b"new!"), tmp_path, "notes.txt", max_bytes=4).read_bytes() == b"new!"


@pytest.mark.parametrize("filename", ["../x.txt", "..\\x.txt", "C:\\x.txt", "/x.txt", "a:b.txt", "NUL.txt", "x.", "x\x00.txt"])
def test_portable_path_validation(filename, tmp_path):
    from src.ingestion.upload_safety import resolve_upload_path
    with pytest.raises(ValueError):
        resolve_upload_path(tmp_path, filename)
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize("namespace", ["src.ingestion", "backend.app"])
def test_chunker_stops_after_covering_final_character(namespace):
    chunk = importlib.import_module(f"{namespace}.processing.chunker").chunk_text
    assert chunk("hello") == ["hello"]
    assert chunk("a" * 1200) == ["a" * 1200]
    assert chunk("a" * 2200) == ["a" * 1200, "a" * 1200]
    for size, overlap in ((0, 0), (10, 10), (10, -1)):
        with pytest.raises(ValueError):
            chunk("text", size, overlap)


@pytest.mark.parametrize("path", ["src/ingestion/vectorstore/qdrant_service.py", "backend/app/vectorstore/qdrant_service.py"])
def test_persistent_database_failure_does_not_fall_back_to_memory(path, monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    calls = []
    def unavailable(*args, **kwargs):
        calls.append((args, kwargs))
        raise RuntimeError("synthetic locked database")
    fake = types.ModuleType("qdrant_client")
    fake.QdrantClient = unavailable
    monkeypatch.setitem(sys.modules, "qdrant_client", fake)
    models = types.ModuleType("qdrant_client.models")
    models.Distance = types.SimpleNamespace(COSINE="cosine")
    models.VectorParams = dict
    monkeypatch.setitem(sys.modules, "qdrant_client.models", models)
    with pytest.raises(RuntimeError, match="Persistent Qdrant"):
        runpy.run_path(str(ROOT / path))
    assert len(calls) == 1


def test_checkpoint_service_can_be_imported_and_roundtrips(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    namespace = runpy.run_path(str(ROOT / "src/ingestion/checkpoints/checkpoint_service.py"))
    namespace["save_semantic_checkpoint"]("u1", "topic", None, ["c1"])
    assert namespace["load_semantic_checkpoint"]("u1")["concept_ids"] == ["c1"]
