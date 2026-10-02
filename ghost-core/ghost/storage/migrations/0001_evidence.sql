-- 0001: raw evidence and derived observation/state lineage.
-- Raw rows are append-only (triggers below). Derived rows are immutable too: a new
-- generator version produces new rows, never an overwrite.

CREATE TABLE raw_artifact (
    artifact_id TEXT PRIMARY KEY CHECK (artifact_id GLOB 'sha256:*'),
    media_type TEXT NOT NULL,
    size_bytes INTEGER NOT NULL CHECK (size_bytes >= 0),
    source TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE run_manifest (
    run_id TEXT PRIMARY KEY,
    kind TEXT NOT NULL,
    manifest_artifact_id TEXT NOT NULL REFERENCES raw_artifact(artifact_id),
    git_sha TEXT,
    git_dirty INTEGER,
    config_hash TEXT NOT NULL,
    seed INTEGER NOT NULL,
    evidence_level TEXT NOT NULL
        CHECK (evidence_level IN ('UNIT_CONTRACT', 'SYNTHETIC_FIXTURE', 'REAL_VM')),
    started_at TEXT NOT NULL,
    ended_at TEXT,
    status TEXT NOT NULL CHECK (status IN ('running', 'completed', 'failed', 'stopped'))
);

CREATE TABLE session (
    session_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES run_manifest(run_id),
    environment_id TEXT NOT NULL,
    environment_kind TEXT NOT NULL,
    seed_name TEXT NOT NULL,
    app_alias TEXT NOT NULL,
    started_at TEXT NOT NULL
);

CREATE TABLE raw_observation (
    session_id TEXT NOT NULL REFERENCES session(session_id),
    observation_id TEXT NOT NULL,
    record_artifact_id TEXT NOT NULL REFERENCES raw_artifact(artifact_id),
    raw_capture_id TEXT NOT NULL REFERENCES raw_artifact(artifact_id),
    screenshot_id TEXT REFERENCES raw_artifact(artifact_id),
    generation INTEGER NOT NULL,
    platform TEXT NOT NULL,
    environment TEXT NOT NULL,
    request_id TEXT NOT NULL,
    correlation_id TEXT NOT NULL,
    captured_at TEXT NOT NULL,
    PRIMARY KEY (session_id, observation_id)
);

CREATE TABLE platform_observation (
    platform_observation_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    observation_id TEXT NOT NULL,
    artifact_id TEXT NOT NULL REFERENCES raw_artifact(artifact_id),
    parent_raw_capture_id TEXT NOT NULL REFERENCES raw_artifact(artifact_id),
    generator_name TEXT NOT NULL,
    generator_version TEXT NOT NULL,
    FOREIGN KEY (session_id, observation_id)
        REFERENCES raw_observation(session_id, observation_id),
    UNIQUE (session_id, observation_id, generator_name, generator_version)
);

CREATE TABLE canonical_state (
    fingerprint TEXT PRIMARY KEY CHECK (fingerprint GLOB 'sha256:*'),
    artifact_id TEXT NOT NULL REFERENCES raw_artifact(artifact_id),
    generator_name TEXT NOT NULL,
    generator_version TEXT NOT NULL,
    mask_id TEXT NOT NULL,
    complete INTEGER NOT NULL CHECK (complete IN (0, 1))
);

CREATE TABLE canonical_state_observation (
    platform_observation_id TEXT NOT NULL
        REFERENCES platform_observation(platform_observation_id),
    fingerprint TEXT NOT NULL REFERENCES canonical_state(fingerprint),
    PRIMARY KEY (platform_observation_id, fingerprint)
);

CREATE TABLE primitive_action (
    action_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES session(session_id),
    request_id TEXT NOT NULL,
    pre_observation_id TEXT NOT NULL,
    kind TEXT NOT NULL,
    locator_path TEXT NOT NULL,
    value_json TEXT,
    value_is_probe INTEGER NOT NULL CHECK (value_is_probe IN (0, 1)),
    risk_class TEXT NOT NULL,
    approval_id TEXT,
    executor_claim_json TEXT NOT NULL,
    FOREIGN KEY (session_id, pre_observation_id)
        REFERENCES raw_observation(session_id, observation_id),
    UNIQUE (session_id, request_id)
);

CREATE TABLE transition (
    transition_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES run_manifest(run_id),
    sequence INTEGER NOT NULL CHECK (sequence >= 0),
    session_id TEXT NOT NULL,
    from_fingerprint TEXT NOT NULL REFERENCES canonical_state(fingerprint),
    to_fingerprint TEXT NOT NULL REFERENCES canonical_state(fingerprint),
    pre_observation_id TEXT NOT NULL,
    post_observation_id TEXT NOT NULL,
    action_id TEXT NOT NULL REFERENCES primitive_action(action_id),
    record_artifact_id TEXT NOT NULL REFERENCES raw_artifact(artifact_id),
    evidence_level TEXT NOT NULL,
    FOREIGN KEY (session_id, pre_observation_id)
        REFERENCES raw_observation(session_id, observation_id),
    FOREIGN KEY (session_id, post_observation_id)
        REFERENCES raw_observation(session_id, observation_id),
    UNIQUE (run_id, sequence)
);

CREATE TRIGGER raw_artifact_append_only_u BEFORE UPDATE ON raw_artifact
BEGIN SELECT RAISE(ABORT, 'raw_artifact is append-only'); END;
CREATE TRIGGER raw_artifact_append_only_d BEFORE DELETE ON raw_artifact
BEGIN SELECT RAISE(ABORT, 'raw_artifact is append-only'); END;

CREATE TRIGGER session_append_only_u BEFORE UPDATE ON session
BEGIN SELECT RAISE(ABORT, 'session is append-only'); END;
CREATE TRIGGER session_append_only_d BEFORE DELETE ON session
BEGIN SELECT RAISE(ABORT, 'session is append-only'); END;

CREATE TRIGGER raw_observation_append_only_u BEFORE UPDATE ON raw_observation
BEGIN SELECT RAISE(ABORT, 'raw_observation is append-only'); END;
CREATE TRIGGER raw_observation_append_only_d BEFORE DELETE ON raw_observation
BEGIN SELECT RAISE(ABORT, 'raw_observation is append-only'); END;

CREATE TRIGGER platform_observation_immutable_u BEFORE UPDATE ON platform_observation
BEGIN SELECT RAISE(ABORT, 'platform_observation is immutable'); END;
CREATE TRIGGER platform_observation_immutable_d BEFORE DELETE ON platform_observation
BEGIN SELECT RAISE(ABORT, 'platform_observation is immutable'); END;

CREATE TRIGGER canonical_state_immutable_u BEFORE UPDATE ON canonical_state
BEGIN SELECT RAISE(ABORT, 'canonical_state is immutable'); END;
CREATE TRIGGER canonical_state_immutable_d BEFORE DELETE ON canonical_state
BEGIN SELECT RAISE(ABORT, 'canonical_state is immutable'); END;

CREATE TRIGGER canonical_state_observation_immutable_u
BEFORE UPDATE ON canonical_state_observation
BEGIN SELECT RAISE(ABORT, 'canonical_state_observation is immutable'); END;
CREATE TRIGGER canonical_state_observation_immutable_d
BEFORE DELETE ON canonical_state_observation
BEGIN SELECT RAISE(ABORT, 'canonical_state_observation is immutable'); END;

CREATE TRIGGER primitive_action_append_only_u BEFORE UPDATE ON primitive_action
BEGIN SELECT RAISE(ABORT, 'primitive_action is append-only'); END;
CREATE TRIGGER primitive_action_append_only_d BEFORE DELETE ON primitive_action
BEGIN SELECT RAISE(ABORT, 'primitive_action is append-only'); END;

CREATE TRIGGER transition_immutable_u BEFORE UPDATE ON transition
BEGIN SELECT RAISE(ABORT, 'transition is immutable'); END;
CREATE TRIGGER transition_immutable_d BEFORE DELETE ON transition
BEGIN SELECT RAISE(ABORT, 'transition is immutable'); END;

-- A run manifest may only be closed once: status running -> final, setting ended_at.
CREATE TRIGGER run_manifest_close_once BEFORE UPDATE ON run_manifest
WHEN OLD.status != 'running'
    OR NEW.run_id != OLD.run_id
    OR NEW.manifest_artifact_id != OLD.manifest_artifact_id
    OR NEW.config_hash != OLD.config_hash
    OR NEW.started_at != OLD.started_at
    OR NEW.status = 'running'
BEGIN SELECT RAISE(ABORT, 'run_manifest can only be closed once'); END;
CREATE TRIGGER run_manifest_no_delete BEFORE DELETE ON run_manifest
BEGIN SELECT RAISE(ABORT, 'run_manifest is append-only'); END;
