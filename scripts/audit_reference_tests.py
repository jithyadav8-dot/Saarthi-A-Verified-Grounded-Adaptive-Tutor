"""Run reviewed reference tests with no inherited secrets, .env or network.

Use an isolated venv; existing system packages can be shared read-only. No packages
or model assets are installed by this script. Reference code is not imported until
the guards are active. This is a test guard, not an OS security boundary.
"""
import os
from pathlib import Path
import socket
import sys


def main():
    reference = Path(sys.argv[1]).resolve()
    if (reference / ".env").exists():
        raise RuntimeError("Refusing a reference checkout with a .env file")
    allowed = {k: v for k, v in os.environ.items() if k.upper() in
               {"SYSTEMROOT", "WINDIR", "PATH", "TEMP", "TMP", "COMSPEC", "PATHEXT"}}
    os.environ.clear()
    os.environ.update(allowed, PRAMANA_LLM_MODE="replay", HF_HUB_OFFLINE="1",
                      TRANSFORMERS_OFFLINE="1", PYTEST_DISABLE_PLUGIN_AUTOLOAD="1",
                      PRAMANA_DATA=str(reference / ".audit-data"))
    def blocked(*args, **kwargs):
        raise RuntimeError("Network disabled for reference audit")
    socket.socket.connect = blocked
    socket.create_connection = blocked
    socket.getaddrinfo = blocked
    os.chdir(reference)
    sys.path.insert(0, str(reference))
    import pytest
    raise SystemExit(pytest.main([*sys.argv[2:], "-q", "--basetemp", str(reference / ".audit-test-tmp")]))


if __name__ == "__main__":
    main()
