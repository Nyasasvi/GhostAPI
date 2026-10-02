"""Evidence repository: SQLite metadata + content-addressed artifacts, with lineage.

Raw bytes are verified against their declared content address before anything is
recorded. Derived records reference their parents and generator versions. Recording the
same observation/state twice is a no-op, so resumed runs never double-count.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime

from ghost._model import canonical_json, sha256_hex
from ghost.exploration.graph import TransitionRecord
from ghost.manifest import RunManifest
from ghost.observation.canonical import CanonicalState
from ghost.platform.types import ObservationBundle, RawArtifactRef
from ghost.sandbox.environment import Environment
from ghost.storage.artifacts import ArtifactStore
from ghost.storage.db import Database

JSON = "application/json"


class EvidenceIntegrityError(RuntimeError):
    """Evidence did not match its declared content address or lineage."""


def _now() -> str:
    return datetime.now(UTC).isoformat()


class EvidenceRepository:
    def __init__(self, db: Database, artifacts: ArtifactStore) -> None:
        self.db = db
        self.artifacts = artifacts

    # -- artifacts --------------------------------------------------------------------
    def put(self, data: bytes, media_type: str, source: str) -> RawArtifactRef:
        ref = self.artifacts.put(data, media_type)
        self.db.connection.execute(
            "INSERT OR IGNORE INTO raw_artifact VALUES (?, ?, ?, ?, ?)",
            (ref.artifact_id, media_type, ref.size_bytes, source, _now()),
        )
        return ref

    def put_json(self, payload: object, source: str) -> RawArtifactRef:
        return self.put(canonical_json(payload).encode("utf-8"), JSON, source)

    # -- runs and sessions ------------------------------------------------------------
    def start_run(self, manifest: RunManifest) -> None:
        with self.db.transaction():
            ref = self.put_json(manifest.model_dump(mode="json"), "manifest")
            self.db.connection.execute(
                "INSERT INTO run_manifest VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, 'running')",
                (
                    manifest.run_id,
                    manifest.kind,
                    ref.artifact_id,
                    manifest.git_sha,
                    None if manifest.git_dirty is None else int(manifest.git_dirty),
                    manifest.config_hash,
                    manifest.seed,
                    manifest.evidence_level.value,
                    manifest.created_at.isoformat(),
                ),
            )

    def finish_run(self, run_id: str, status: str) -> None:
        self.db.connection.execute(
            "UPDATE run_manifest SET status = ?, ended_at = ? WHERE run_id = ?",
            (status, _now(), run_id),
        )

    def start_session(self, run_id: str, env: Environment, seed: str, app_alias: str) -> str:
        session_id = f"{run_id}:{env.attestation.environment_id}"
        self.db.connection.execute(
            "INSERT OR IGNORE INTO session VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                session_id,
                run_id,
                env.attestation.environment_id,
                env.attestation.kind.value,
                seed,
                app_alias,
                _now(),
            ),
        )
        return session_id

    # -- observations and states ------------------------------------------------------
    def record_observation(
        self,
        session_id: str,
        bundle: ObservationBundle,
        raw: bytes,
        screenshot_bytes: bytes | None = None,
    ) -> str:
        """Store raw bytes (hash-verified), the raw observation record, and the derived
        PlatformObservation. Returns the platform observation id. Idempotent."""
        declared = bundle.raw.raw_capture
        if "sha256:" + sha256_hex(raw) != declared.artifact_id:
            raise EvidenceIntegrityError("raw capture bytes do not match their content address")
        shot = bundle.raw.screenshot
        if (shot is None) != (screenshot_bytes is None):
            raise EvidenceIntegrityError("screenshot reference and bytes must come together")
        if (
            shot is not None
            and screenshot_bytes is not None
            and "sha256:" + sha256_hex(screenshot_bytes) != shot.artifact_id
        ):
            raise EvidenceIntegrityError("screenshot bytes do not match their address")
        obs = bundle.raw
        derived_id = f"{session_id}/{obs.observation_id}/{bundle.platform.normalizer.version}"
        with self.db.transaction():
            self.put(raw, declared.media_type, "bridge")
            record = self.put_json(obs.model_dump(mode="json"), "bridge")
            screenshot = None
            if shot is not None and screenshot_bytes is not None:
                screenshot = self.put(screenshot_bytes, shot.media_type, "bridge").artifact_id
            self.db.connection.execute(
                "INSERT OR IGNORE INTO raw_observation VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (
                    session_id,
                    obs.observation_id,
                    record.artifact_id,
                    declared.artifact_id,
                    screenshot,
                    obs.generation,
                    obs.platform,
                    obs.environment.value,
                    obs.request_id,
                    obs.correlation_id,
                    obs.captured_at.isoformat(),
                ),
            )
            platform = self.put_json(bundle.platform.model_dump(mode="json"), "normalizer")
            self.db.connection.execute(
                "INSERT OR IGNORE INTO platform_observation VALUES (?,?,?,?,?,?,?)",
                (
                    derived_id,
                    session_id,
                    obs.observation_id,
                    platform.artifact_id,
                    declared.artifact_id,
                    bundle.platform.normalizer.name,
                    bundle.platform.normalizer.version,
                ),
            )
        return derived_id

    def record_state(self, state: CanonicalState, platform_observation_id: str) -> None:
        with self.db.transaction():
            ref = self.put_json(state.model_dump(mode="json"), "canonicalizer")
            self.db.connection.execute(
                "INSERT OR IGNORE INTO canonical_state VALUES (?,?,?,?,?,?)",
                (
                    state.fingerprint,
                    ref.artifact_id,
                    state.canonicalizer.name,
                    state.canonicalizer.version,
                    state.mask_id,
                    int(state.complete),
                ),
            )
            self.db.connection.execute(
                "INSERT OR IGNORE INTO canonical_state_observation VALUES (?, ?)",
                (platform_observation_id, state.fingerprint),
            )

    def record_transition(self, run_id: str, session_id: str, record: TransitionRecord) -> None:
        claim = record.evidence.executor_claim
        action_id = f"{session_id}/{claim.action_id}"
        value = record.action.value.model_dump(mode="json") if record.action.value else None
        with self.db.transaction():
            artifact = self.put_json(record.model_dump(mode="json"), "explorer")
            self.db.connection.execute(
                "INSERT OR IGNORE INTO primitive_action VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (
                    action_id,
                    session_id,
                    claim.request_id,
                    record.evidence.pre_observation_id,
                    record.action.kind.value,
                    record.action.locator.path,
                    None if value is None else canonical_json(value),
                    int(record.action.value_is_probe),
                    record.risk_class.value,
                    record.approval_id,
                    claim.model_dump_json(),
                ),
            )
            self.db.connection.execute(
                "INSERT OR IGNORE INTO transition VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (
                    record.transition_id,
                    run_id,
                    record.sequence,
                    session_id,
                    record.from_fingerprint,
                    record.to_fingerprint,
                    record.evidence.pre_observation_id,
                    record.evidence.post_observation_id,
                    action_id,
                    artifact.artifact_id,
                    record.evidence_level.value,
                ),
            )

    # -- queries ----------------------------------------------------------------------
    def count(self, table: str) -> int:
        if not table.isidentifier():
            raise ValueError("invalid table name")
        row = self.db.connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
        return int(row[0])

    def rows(self, sql: str, params: tuple[object, ...] = ()) -> list[sqlite3.Row]:
        return list(self.db.connection.execute(sql, params))

    def load_json(self, artifact_id: str) -> object:
        return json.loads(self.artifacts.get(artifact_id))


class RepositorySink:
    """EvidenceSink that persists everything the explorer observes and records."""

    def __init__(self, repo: EvidenceRepository, run_id: str, app_alias: str) -> None:
        self.repo = repo
        self.run_id = run_id
        self.app_alias = app_alias
        self.session_id: str | None = None
        self._platform_ids: dict[str, str] = {}

    def session_started(self, env: Environment, seed: str) -> None:
        self.session_id = self.repo.start_session(self.run_id, env, seed, self.app_alias)

    def observation(
        self, bundle: ObservationBundle, raw_bytes: bytes, screenshot_bytes: bytes | None
    ) -> None:
        session = self._session()
        derived = self.repo.record_observation(session, bundle, raw_bytes, screenshot_bytes)
        self._platform_ids[bundle.raw.observation_id] = derived

    def state(self, state: CanonicalState, observation_id: str) -> None:
        self.repo.record_state(state, self._platform_ids[observation_id])

    def transition(self, record: TransitionRecord) -> None:
        self.repo.record_transition(self.run_id, self._session(), record)

    def _session(self) -> str:
        if self.session_id is None:
            raise RuntimeError("no session started")
        return self.session_id
