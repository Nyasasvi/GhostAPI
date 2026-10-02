"""Shared strict model base and canonical hashing helpers."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from pydantic import BaseModel, ConfigDict

SHA256_PATTERN = r"^sha256:[0-9a-f]{64}$"


class StrictModel(BaseModel):
    """Immutable, strictly typed base for every Ghost Core record.

    ``extra="forbid"`` rejects unknown fields (AGENTS rule 13: validate external input);
    ``frozen=True`` keeps evidence records immutable once constructed.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)


def canonical_json(data: Any) -> str:
    """Deterministic JSON: sorted keys, no insignificant whitespace, no NaN/Infinity."""
    return json.dumps(
        data, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    )


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def content_hash(data: Any) -> str:
    """``sha256:<hex>`` of the canonical JSON encoding of ``data``."""
    return "sha256:" + sha256_hex(canonical_json(data).encode("utf-8"))


def model_hash(model: BaseModel) -> str:
    return content_hash(model.model_dump(mode="json"))
