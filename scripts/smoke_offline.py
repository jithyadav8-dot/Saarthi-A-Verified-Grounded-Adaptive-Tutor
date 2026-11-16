"""Start the real API on loopback with isolated state, check it, and stop it.

No model providers are enabled. Run: python -m scripts.smoke_offline
"""
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
from urllib.error import URLError
from urllib.request import Request, urlopen


def main():
    root = Path(__file__).resolve().parents[1]
    environment = dict(os.environ, PYTHONPATH=str(root), EMBEDDING_PROVIDER="hash",
                       RERANK_PROVIDER="lexical", LLM_PROVIDER="none", PYTHON_DOTENV_DISABLED="1",
                       POD_B_ENV_FILE="nonexistent.env", HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1")
    # Ensure inherited developer configuration cannot invoke a provider or source corpus.
    for key in ("OPENAI_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY", "GROQ_API_KEY",
                "REPLICATE_API_KEY", "REPLICATE_API_TOKEN", "POD_B_CORPUS", "POD_B_GRAPH",
                "POD_B_CACHE_DIR", "POD_B_SOURCES_DIR"):
        environment.pop(key, None)
    with socket.socket() as reservation:
        reservation.bind(("127.0.0.1", 0))
        port = reservation.getsockname()[1]
    with tempfile.TemporaryDirectory(prefix="saarthi-smoke-") as directory:
        with open(Path(directory) / "server.log", "w+") as log:
            process = subprocess.Popen([sys.executable, "-m", "uvicorn", "src.api.service:app",
                                        "--host", "127.0.0.1", "--port", str(port)],
                                       cwd=directory, env=environment, stdout=log, stderr=log)
            try:
                base = f"http://127.0.0.1:{port}"
                for _ in range(100):
                    try:
                        with urlopen(base + "/health", timeout=1) as response:
                            health = json.load(response)
                        break
                    except (URLError, TimeoutError):
                        if process.poll() is not None:
                            raise RuntimeError("Offline server exited during startup")
                        time.sleep(0.1)
                else:
                    raise RuntimeError("Offline server did not become ready")
                assert health["status"] == "healthy"
                request = Request(base + "/quiz", data=b'{"student_id":"smoke","size":3}',
                                  headers={"Content-Type": "application/json"})
                with urlopen(request, timeout=5) as response:
                    quiz = json.load(response)
                assert len(quiz["questions"]) == 3
                assert all("answer" not in item for item in quiz["questions"])
                def post_json(path, body):
                    request = Request(base + path, data=json.dumps(body).encode(),
                                      headers={"Content-Type": "application/json"})
                    with urlopen(request, timeout=5) as response:
                        return json.load(response)

                item = quiz["questions"][0]
                submission = {"student_id": "smoke", "q_id": item["q_id"],
                              "attempt_id": item["attempt_id"], "answer": "smoke response"}
                first = post_json("/answer", submission)
                retry = post_json("/answer", submission)
                assert retry["replayed"] is True
                assert first["new_mastery"] == retry["new_mastery"]
                with urlopen(base + "/report/smoke", timeout=5) as response:
                    assert "report" in json.load(response)
                session = post_json("/sessions", {"student_id": "smoke"})["id"]
                answer = post_json(f"/sessions/{session}/chat", {
                    "student_id": "smoke", "question": "What is the chain rule?"})
                assert answer["verification"] == "extractive"
                with urlopen(base + f"/sessions/{session}", timeout=5) as response:
                    saved = json.load(response)["messages"][-1]
                assert saved["confidence_kind"] == answer["confidence_kind"]
                boundary = "saarthi-smoke-boundary"
                content = (f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; "
                           "filename=\"smoke-notes.txt\"\r\nContent-Type: text/plain\r\n\r\n"
                           "Impulse equals force multiplied by time. Momentum changes when an impulse acts.\r\n"
                           f"--{boundary}--\r\n").encode()
                upload = Request(base + "/ingest/upload", data=content, headers={
                    "Content-Type": f"multipart/form-data; boundary={boundary}"})
                with urlopen(upload, timeout=10) as response:
                    assert response.status == 200
                with urlopen(base + "/sources/smoke-notes.txt", timeout=5) as response:
                    assert b"Impulse equals force" in response.read()
                with urlopen(base + "/eval/ragas", timeout=5) as response:
                    assert json.load(response)["status"] == "not_measured"
                print("PASS: real offline server startup, health, quiz, idempotent grading, report, "
                      "chat/reload, upload/source view, and evaluation status")
            finally:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)


if __name__ == "__main__":
    main()
