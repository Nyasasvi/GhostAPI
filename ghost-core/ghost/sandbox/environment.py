"""Clean environments for exploration and trials.

An ``EnvironmentProvider`` hands out a *fresh, clean* environment per call. Reset is always
"start a new environment"; nothing is cleaned up inside the app (RESEARCH.md §6.2).

``SyntheticEnvironmentProvider`` builds a fresh MockPlatformBridge over simulated apps.
That is SYNTHETIC reset, which is **not** equivalent to a VM clone reset.
``DisposableVMEnvironmentProvider`` is BLOCKED_VM_STORAGE.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Protocol

from ghost.evidence import BlockedVMStorageError
from ghost.platform.mock import MockPlatformBridge
from ghost.platform.protocol import PlatformBridge, RequestContext
from ghost.platform.simulated import SimulatedAppFactory, SimulatedDisk
from ghost.platform.types import ApplicationRef, LaunchRef
from ghost.sandbox.guard import SandboxAttestation, attest


@dataclass(frozen=True)
class Environment:
    bridge: PlatformBridge
    application: ApplicationRef
    launch_ref: LaunchRef
    attestation: SandboxAttestation
    idle: Callable[[int], None]
    """Let time pass with no action (volatility calibration). Never acts on the UI."""


class EnvironmentProvider(Protocol):
    def start(self, seed: str = "base") -> Environment:
        """A fresh clean environment, built from the named frozen seed, app launched."""
        ...


class SyntheticEnvironmentProvider:
    """Fresh MockPlatformBridge per ``start``; each seed name maps to an app factory."""

    def __init__(
        self,
        launch_ref: str,
        seeds: Mapping[str, SimulatedAppFactory],
        *,
        seed_disk: Callable[[], SimulatedDisk] | None = None,
        deadline_ms: int = 5000,
    ) -> None:
        if "base" not in seeds:
            raise ValueError("the clean 'base' seed must be provided")
        self._launch = LaunchRef(ref=launch_ref)
        self._seeds = dict(seeds)
        self._seed_disk = seed_disk or SimulatedDisk
        self._deadline_ms = deadline_ms
        self.starts = 0

    def start(self, seed: str = "base") -> Environment:
        factory = self._seeds.get(seed)
        if factory is None:
            raise KeyError(f"unknown seed {seed!r}")
        self.starts += 1
        environment_id = f"syn{self.starts:05d}"
        bridge = MockPlatformBridge(
            {self._launch.ref: factory},
            session_id=environment_id,
            disks={self._launch.ref: self._seed_disk()},
        )
        ctx = RequestContext.new(f"env/{environment_id}", self._deadline_ms)
        attestation = attest(bridge, ctx, environment_id)
        application = bridge.launch(ctx, self._launch).application
        return Environment(
            bridge=bridge,
            application=application,
            launch_ref=self._launch,
            attestation=attestation,
            idle=bridge.advance,
        )


class DisposableVMEnvironmentProvider:
    """Clone-per-trial macOS VM environments (ghost-vm adapter). BLOCKED_VM_STORAGE."""

    def start(self, seed: str = "base") -> Environment:
        raise BlockedVMStorageError(f"disposable VM clone of seed {seed}")
