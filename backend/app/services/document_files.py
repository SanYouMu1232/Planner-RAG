"""Resolve registered uploads, including databases moved with their project folder."""
from pathlib import Path

from ..config import UPLOAD_DIR


def resolve_document_file(storage_path: str | None) -> Path | None:
    if not storage_path:
        return None
    root = Path(UPLOAD_DIR).resolve()
    stored = Path(storage_path).resolve()
    # The generated storage filename is retained when the project is moved.
    basename = storage_path.replace('\\', '/').rsplit('/', 1)[-1]
    candidates = [stored, root / basename]
    for candidate in candidates:
        resolved = candidate.resolve()
        if resolved.is_relative_to(root) and resolved.is_file():
            return resolved
    return None
