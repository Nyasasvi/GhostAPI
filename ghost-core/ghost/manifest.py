"""Run manifests (AGENTS rule 17; RESEARCH.md §18).

Every run writes one. A run without a manifest is not evidence. Fields that do not apply
yet say so explicitly (for example the VM base image of a synthetic run) instead of
being left blank.
"""

from __future__ import annotations

import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Literal

from pydantic import AwareDatetime, Field

from ghost._model import StrictModel, content_hash
from ghost.evidence import EvidenceLevel
from ghost.platform.types import GeneratorInfo

GHOST_VERSION = "0.1.0"
BENCHMARK_PROTOCOL = "docs/BENCHMARKS.md v0.1 (draft; v0.2 proposal pending approval)"
RESEARCH_PROTOCOL = "docs/RESEARCH.md v0.1 (draft; v0.2 proposal pending approval)"
SYNTHETIC_BASE_IMAGE = "not applicable: synthetic in-process environment"
SYNTHETIC_NETWORK = "not applicable: in-process simulated app, no network"


class RunManifest(StrictModel):
    run_id: Annotated[str, Field(pattern=r"^[A-Za-z0-9_-]{1,64}$")]
    kind: Literal["exploration", "experiment", "demo"]
    created_at: AwareDatetime
    git_sha: str | None
    git_dirty: bool | None
    ghost_version: str = GHOST_VERSION
    database_schema_version: Annotated[int, Field(ge=0)]
    gir_schema_version: str | None = None
    generators: tuple[GeneratorInfo, ...]
    prompt_versions: tuple[tuple[str, str], ...] = ()
    model: tuple[str, str] | None = None
    config_hash: str
    seed: Annotated[int, Field(ge=0)]
    evidence_level: EvidenceLevel
    environment_kind: str
    vm_base_image: str
    app_alias: str
    app_version: str | None = None
    budget_json: str
    benchmark_protocol: str = BENCHMARK_PROTOCOL
    research_protocol: str = RESEARCH_PROTOCOL
    network_policy: str
    nondeterminism: tuple[str, ...] = ()


def git_state(root: Path) -> tuple[str | None, bool | None]:
    """(HEAD sha, dirty flag), or (None, None) when git is unavailable. Never raises."""
    try:
        sha = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True,
            check=True, timeout=10,
        ).stdout.strip()  # fmt: skip
        status = subprocess.run(
            ["git", "status", "--porcelain"], cwd=root, capture_output=True, text=True,
            check=True, timeout=10,
        ).stdout  # fmt: skip
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return None, None
    return sha, bool(status.strip())


def config_hash(config: object) -> str:
    return content_hash(config)


def now() -> datetime:
    return datetime.now(UTC)
