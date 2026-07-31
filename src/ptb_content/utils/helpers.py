"""Utility functions for the content factory."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any


def project_root() -> Path:
    """Return the project root directory (4 levels up from this file)."""
    return Path(__file__).resolve().parent.parent.parent.parent


def ensure_dir(path: str | Path) -> Path:
    """Ensure directory exists and return it."""
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def read_json(path: str | Path) -> Any:
    """Read a JSON file."""
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def write_json(data: Any, path: str | Path, indent: int = 2) -> None:
    """Write data to a JSON file."""
    ensure_dir(Path(path).parent)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=indent)


def write_jsonl(records: list[dict], path: str | Path) -> None:
    """Write records as JSONL (one JSON object per line)."""
    ensure_dir(Path(path).parent)
    with open(path, "w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")


def read_jsonl(path: str | Path) -> list[dict]:
    """Read JSONL file."""
    records = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def file_hash(path: str | Path) -> str:
    """Compute SHA-256 hash of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def load_config(name: str) -> dict:
    """Load a YAML config from the config/ directory."""
    import yaml

    config_path = project_root() / "config" / f"{name}.yaml"
    with open(config_path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def env_or(key: str, default: str = "") -> str:
    """Get environment variable or return default."""
    return os.environ.get(key, default)
