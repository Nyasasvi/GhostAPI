"""Risk classes (the deterministic classifier is added in Checkpoint 3)."""

from __future__ import annotations

from enum import StrEnum


class RiskClass(StrEnum):
    READ_ONLY = "READ_ONLY"
    NAVIGATION = "NAVIGATION"
    INPUT = "INPUT"
    REVERSIBLE_WRITE = "REVERSIBLE_WRITE"
    UNKNOWN = "UNKNOWN"
    UNKNOWN_HIGH_RISK = "UNKNOWN_HIGH_RISK"
    DESTRUCTIVE = "DESTRUCTIVE"
