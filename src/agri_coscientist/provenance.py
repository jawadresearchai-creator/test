from __future__ import annotations
import hashlib
import json
from pathlib import Path
from typing import Iterable, Mapping, Any


def sha256_file(path: str | Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def freeze_manifest(paths: Iterable[str | Path]) -> dict[str, str]:
    return {str(Path(p)): sha256_file(p) for p in sorted(map(Path, paths), key=lambda x: str(x))}


def verify_manifest(manifest: Mapping[str, str]) -> bool:
    return all(Path(p).exists() and sha256_file(p) == expected for p, expected in manifest.items())


def canonical_hash(payload: Mapping[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def analysis_lock(specification: Mapping[str, Any], file_manifest: Mapping[str, str]) -> dict[str, Any]:
    payload = {"specification": specification, "files": dict(sorted(file_manifest.items()))}
    return {"lock_sha256": canonical_hash(payload), "payload": payload}
