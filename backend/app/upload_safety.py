"""Bounded, atomic uploads with portable basename validation.

The upload directory must be trusted and application-owned. Filenames never
select a parent or subdirectory, and existing symlink destinations are rejected.
"""

import os
from pathlib import Path, PureWindowsPath
import tempfile
from typing import BinaryIO


DEFAULT_MAX_UPLOAD_BYTES = 100 * 1024 * 1024
_WINDOWS_DEVICES = {"CON", "PRN", "AUX", "NUL", "CONIN$", "CONOUT$"}
_WINDOWS_DEVICES.update(f"{prefix}{i}" for prefix in ("COM", "LPT") for i in range(1, 10))


class UploadTooLargeError(ValueError):
    """The uploaded file exceeded the configured byte limit."""


def validate_upload_filename(filename: str | None) -> str:
    if not filename or filename in {".", ".."}:
        raise ValueError("A filename is required.")
    if (any(ord(char) < 32 or char in '/\\:<>\"|?*' for char in filename)
            or filename.endswith((" ", "."))
            or PureWindowsPath(filename).is_reserved()
            or filename.split(".", 1)[0].upper() in _WINDOWS_DEVICES):
        raise ValueError("Filename must be a plain file name without path components.")
    return filename


def resolve_upload_path(root: Path, filename: str | None) -> Path:
    name = validate_upload_filename(filename)
    root = Path(root).resolve()
    destination = root / name
    if destination.is_symlink() or destination.resolve().parent != root:
        raise ValueError("Upload destination must stay within the upload directory.")
    if destination.exists() and not destination.is_file():
        raise ValueError("Upload destination must be a regular file.")
    return destination


def save_upload(file: BinaryIO, root: Path, filename: str | None,
                max_bytes: int | None = None) -> Path:
    """Save a stream without overwriting an existing file on size/read failure."""
    if max_bytes is None:
        max_bytes = int(os.getenv("SAARTHI_MAX_UPLOAD_BYTES", str(DEFAULT_MAX_UPLOAD_BYTES)))
    if max_bytes <= 0:
        raise ValueError("Upload size limit must be positive.")
    destination = resolve_upload_path(root, filename)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(mode="wb", dir=destination.parent,
                                         prefix=".upload-", suffix=".tmp", delete=False) as temporary:
            temporary_path = Path(temporary.name)
            total = 0
            while True:
                chunk = file.read(min(1024 * 1024, max_bytes - total + 1))
                if not chunk:
                    break
                total += len(chunk)
                if total > max_bytes:
                    raise UploadTooLargeError(f"File exceeds upload limit of {max_bytes} bytes.")
                temporary.write(chunk)
        resolve_upload_path(destination.parent, filename)
        os.replace(temporary_path, destination)
        return destination
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
