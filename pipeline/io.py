"""JSON read/write helpers. Deterministic formatting so git diffs stay small."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any


class ImmutableFileError(Exception):
    """Raised when code tries to overwrite a write-once file."""


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    with path.open() as f:
        return json.load(f)


def _dump(obj: Any) -> str:
    return json.dumps(obj, indent=2, sort_keys=False, ensure_ascii=False) + "\n"


def write_json(path: Path, obj: Any) -> bool:
    """Atomic write. Returns True if the file content changed."""
    return _write_text(path, _dump(obj))


def write_table(path: Path, meta: dict, columns: list[str], rows: list[list[Any]]) -> bool:
    """Compact columnar JSON: one row per line. For large history files."""
    head = json.dumps({**meta, "columns": columns}, ensure_ascii=False)[:-1]
    body = ",\n".join(json.dumps(r, ensure_ascii=False, separators=(",", ":")) for r in rows)
    return _write_text(path, f'{head}, "rows": [\n{body}\n]}}\n')


def _write_text(path: Path, text: str) -> bool:
    if path.exists() and path.read_text() == text:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".tmp-", suffix=".json")
    with os.fdopen(fd, "w") as f:
        f.write(text)
    os.replace(tmp, path)
    return True


def write_once(path: Path, obj: Any) -> None:
    """Create a file that must never change. Refuses if it already exists.

    Uses O_EXCL so even a race between two processes cannot overwrite.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    except FileExistsError as e:
        raise ImmutableFileError(f"refusing to overwrite write-once file: {path}") from e
    with os.fdopen(fd, "w") as f:
        f.write(_dump(obj))


def append_jsonl(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")


def read_jsonl(path: Path) -> list[Any]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
