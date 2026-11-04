"""Optional audio credentials must not prevent PDF/PPT pipeline imports."""

from pathlib import Path
import runpy
import sys
import types

import pytest


ROOT = Path(__file__).resolve().parents[1]
TRANSCRIBERS = [
    "src/ingestion/ingestion/video_transcriber.py",
    "backend/app/ingestion/video_transcriber.py",
]


def load_transcriber(path, monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT / "backend"))
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    dotenv = types.ModuleType("dotenv")
    dotenv.load_dotenv = lambda: None
    monkeypatch.setitem(sys.modules, "dotenv", dotenv)
    constructed = []
    requests = []

    def create(**kwargs):
        requests.append(kwargs)
        assert kwargs["file"].read() == b"synthetic audio"
        return types.SimpleNamespace(segments=[{"start": 1.5, "end": 8.5,
                                               "text": "A derivative is a rate of change."}])

    def client_factory(**kwargs):
        constructed.append(kwargs)
        return types.SimpleNamespace(audio=types.SimpleNamespace(
            transcriptions=types.SimpleNamespace(create=create)))

    groq = types.ModuleType("groq")
    groq.Groq = client_factory
    monkeypatch.setitem(sys.modules, "groq", groq)
    namespace = runpy.run_path(str(ROOT / path))
    return namespace, constructed, requests


@pytest.mark.parametrize("path", TRANSCRIBERS)
def test_transcriber_import_needs_no_key_but_call_has_clear_error(path, monkeypatch):
    namespace, constructed, requests = load_transcriber(path, monkeypatch)
    assert constructed == []
    with pytest.raises(ValueError, match="GROQ_API_KEY"):
        namespace["transcribe_audio"]("unused.mp3", "lecture.mp4")
    assert constructed == []
    assert requests == []


@pytest.mark.parametrize("path", TRANSCRIBERS)
def test_client_is_created_only_for_transcription_and_preserves_segments(path, monkeypatch, tmp_path):
    namespace, constructed, requests = load_transcriber(path, monkeypatch)
    assert constructed == []
    monkeypatch.setenv("GROQ_API_KEY", "synthetic-test-key")
    audio = tmp_path / "lecture.mp3"
    audio.write_bytes(b"synthetic audio")
    units = namespace["transcribe_audio"](str(audio), "lecture.mp4")
    assert len(constructed) == len(requests) == 1
    assert requests[0]["file"].closed
    assert len(units) == 1
    assert units[0].source_id == "lecture.mp4"
    assert units[0].text == "A derivative is a rate of change."
    assert units[0].location == {"timestamp": {"start": 1.5, "end": 8.5}}
