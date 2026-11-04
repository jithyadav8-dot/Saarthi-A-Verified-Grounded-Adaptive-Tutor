from pathlib import Path

import pytest

from src.retrieval.schemas import ContentUnit
from tests.test_step5 import build_app, new_unit


def test_failed_persistence_never_publishes_new_bundle(tmp_path, monkeypatch):
    app, _, _ = build_app(tmp_path)
    runtime = app.state.runtime
    old = runtime.bundle
    seen = []
    def unavailable(store, graph):
        seen.append(runtime.bundle)
        raise OSError("synthetic disk failure")
    monkeypatch.setattr(runtime, "_persist", unavailable)
    with pytest.raises(OSError):
        runtime.ingest([ContentUnit(**new_unit("uncommitted", "A new definition."))])
    assert seen == [old]
    assert runtime.bundle is old
    assert runtime.bundle.store.get("uncommitted") is None


def test_graph_write_failure_preserves_previous_file(tmp_path, graph, monkeypatch):
    path = tmp_path / "graph.json"
    graph.save(path)
    before = path.read_bytes()
    original = Path.write_text
    def incomplete_write(self, data, *args, **kwargs):
        original(self, "{incomplete", *args, **kwargs)
        raise OSError("synthetic full disk")
    monkeypatch.setattr(Path, "write_text", incomplete_write)
    with pytest.raises(OSError):
        graph.save(path)
    assert path.read_bytes() == before
    assert list(tmp_path.iterdir()) == [path]
