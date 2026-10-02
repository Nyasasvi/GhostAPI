"""Evidence levels and the explicit VM-storage block.

Every result GhostAPI produces is labelled with the strongest evidence that actually
supports it. While no disposable macOS VM is available, ``REAL_VM`` evidence cannot be
produced, and code paths that need a real VM raise ``BlockedVMStorageError`` instead of
pretending.
"""

from __future__ import annotations

from enum import StrEnum

BLOCKED_VM_STORAGE = "BLOCKED_VM_STORAGE"


class EvidenceLevel(StrEnum):
    UNIT_CONTRACT = "UNIT_CONTRACT"
    SYNTHETIC_FIXTURE = "SYNTHETIC_FIXTURE"
    REAL_VM = "REAL_VM"


class BlockedVMStorageError(RuntimeError):
    """A real disposable macOS VM is required, and VM storage is currently unavailable."""

    code = BLOCKED_VM_STORAGE

    def __init__(self, what: str) -> None:
        super().__init__(f"{BLOCKED_VM_STORAGE}: {what} needs a real disposable macOS VM")
        self.what = what
