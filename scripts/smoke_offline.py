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
                with urlopen(base + "/eval/ragas", timeout=5) as response:
                    assert json.load(response)["status"] == "not_measured"
                print("PASS: real offline server startup, health, quiz, and evaluation status")
            finally:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)


if __name__ == "__main__":
    main()
