"""Sandbox guard: exploration and trials run only in an attested environment.

Two attestation kinds exist:
  SYNTHETIC      issued only for the in-process MockPlatformBridge, whose simulated UI
                 cannot touch the host. Results are SYNTHETIC_FIXTURE evidence.
  DISPOSABLE_VM  would be issued for a verified disposable macOS VM (image digest,
                 isolation probe, VM identity evidence). BLOCKED_VM_STORAGE today.
Any other bridge (including a real-platform bridge pointed at the host) is refused.
"""

from __future__ import annotations

from enum import StrEnum

from ghost._model import StrictModel
from ghost.evidence import BlockedVMStorageError, EvidenceLevel
from ghost.platform.mock import MockPlatformBridge
from ghost.platform.protocol import PlatformBridge, RequestContext
from ghost.platform.types import EnvironmentKind


class AttestationKind(StrEnum):
    SYNTHETIC = "synthetic"
    DISPOSABLE_VM = "disposable_vm"


class SandboxAttestation(StrictModel):
    kind: AttestationKind
    environment_id: str
    evidence_level: EvidenceLevel
    checks: tuple[str, ...]


class SandboxRefusedError(RuntimeError):
    """The environment is not an attested sandbox; nothing may be explored or trialled."""


def attest(bridge: PlatformBridge, ctx: RequestContext, environment_id: str) -> SandboxAttestation:
    health = bridge.health(ctx)
    environment = health.readiness.environment
    if environment is EnvironmentKind.DISPOSABLE_VM:
        raise BlockedVMStorageError("disposable-VM sandbox attestation")
    if environment is EnvironmentKind.SYNTHETIC and isinstance(bridge, MockPlatformBridge):
        if not health.ready:
            raise SandboxRefusedError("synthetic bridge is not ready")
        return SandboxAttestation(
            kind=AttestationKind.SYNTHETIC,
            environment_id=environment_id,
            evidence_level=EvidenceLevel.SYNTHETIC_FIXTURE,
            checks=("in-process MockPlatformBridge", "health ready"),
        )
    raise SandboxRefusedError(
        f"refusing {type(bridge).__name__}: environment {environment.value} is not attestable"
    )
