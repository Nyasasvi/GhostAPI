"""Content-addressed, write-once artifact store for raw and large evidence.

Write protocol: stream to ``.partial/`` -> hash -> fsync -> atomic rename into
``objects/sha256/ab/cd/<hex>`` -> chmod 0444. Reads re-verify the hash. Nothing in this
module updates or deletes an object (AGENTS rule 16; deletion is a human gate).
"""

from __future__ import annotations

import hashlib
import os
import uuid
from pathlib import Path

from ghost.platform.types import RawArtifactRef

MAX_ARTIFACT_BYTES = 64 * 1024 * 1024


class ArtifactIntegrityError(RuntimeError):
    """A stored artifact no longer matches its content address."""


class ArtifactStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self._objects = root / "objects" / "sha256"
        self._partial = root / ".partial"
        self._objects.mkdir(parents=True, exist_ok=True)
        self._partial.mkdir(parents=True, exist_ok=True)

    def _path(self, hex_digest: str) -> Path:
        return self._objects / hex_digest[:2] / hex_digest[2:4] / hex_digest

    def put(self, data: bytes, media_type: str) -> RawArtifactRef:
        if len(data) > MAX_ARTIFACT_BYTES:
            raise ValueError(f"artifact of {len(data)} bytes exceeds the store limit")
        digest = hashlib.sha256(data).hexdigest()
        final = self._path(digest)
        if not final.exists():
            final.parent.mkdir(parents=True, exist_ok=True)
            staging = self._partial / f"{uuid.uuid4().hex}.partial"
            with staging.open("xb") as handle:
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(staging, final)
            final.chmod(0o444)
        return RawArtifactRef(
            artifact_id=f"sha256:{digest}", media_type=media_type, size_bytes=len(data)
        )

    def get(self, artifact_id: str) -> bytes:
        digest = artifact_id.removeprefix("sha256:")
        path = self._path(digest)
        if not path.exists():
            raise FileNotFoundError(artifact_id)
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != digest:
            raise ArtifactIntegrityError(f"{artifact_id} does not match its content")
        return data

    def contains(self, artifact_id: str) -> bool:
        return self._path(artifact_id.removeprefix("sha256:")).exists()
