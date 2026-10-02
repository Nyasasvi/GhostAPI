"""Helpers wiring the synthetic research fixture into a SyntheticEnvironmentProvider."""

from __future__ import annotations

from ghost.platform.simulated import SimulatedDisk
from ghost.sandbox.environment import SyntheticEnvironmentProvider
from ghost_fixture.app import fixture_factory
from ghost_fixture.config import FixtureConfig

LAUNCH = "seed:ledger"


class RecordingDisks:
    """Seed-disk factory that keeps every disk it creates (development oracle access)."""

    def __init__(self) -> None:
        self.disks: list[SimulatedDisk] = []

    def __call__(self) -> SimulatedDisk:
        disk = SimulatedDisk()
        self.disks.append(disk)
        return disk


def provider(
    config: FixtureConfig | None = None,
    *,
    seeds: dict[str, FixtureConfig] | None = None,
    disks: RecordingDisks | None = None,
) -> SyntheticEnvironmentProvider:
    base = {"base": fixture_factory(config or FixtureConfig())}
    extra = {name: fixture_factory(cfg) for name, cfg in (seeds or {}).items()}
    return SyntheticEnvironmentProvider(LAUNCH, {**base, **extra}, seed_disk=disks)
