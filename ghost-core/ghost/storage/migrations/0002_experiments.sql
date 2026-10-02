-- 0002: hypotheses, experiments, trial slots vs trial attempts, internal verification,
-- capabilities, binding versions. Hidden benchmark adjudication is NOT here: it lives in a
-- separate database owned by the benchmark harness (ghost_bench).

CREATE TABLE hypothesis (
    hypothesis_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES run_manifest(run_id),
    artifact_id TEXT NOT NULL REFERENCES raw_artifact(artifact_id),
    source TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE experiment (
    experiment_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES run_manifest(run_id),
    hypothesis_id TEXT REFERENCES hypothesis(hypothesis_id),
    spec_artifact_id TEXT NOT NULL REFERENCES raw_artifact(artifact_id),
    target_trials INTEGER NOT NULL CHECK (target_trials >= 1),
    max_attempts_per_slot INTEGER NOT NULL CHECK (max_attempts_per_slot >= 1),
    created_at TEXT NOT NULL
);

-- One canonical statistical slot per (experiment, index). Counted once, ever.
CREATE TABLE trial (
    trial_id TEXT PRIMARY KEY,
    experiment_id TEXT NOT NULL REFERENCES experiment(experiment_id),
    slot_index INTEGER NOT NULL CHECK (slot_index >= 0),
    stratum TEXT NOT NULL,
    probes_json TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('PENDING', 'PASS', 'FAIL', 'INFRA_EXHAUSTED')),
    failure_code TEXT,
    UNIQUE (experiment_id, slot_index)
);

-- Every execution of a slot, including infrastructure-invalid ones. Append-only.
CREATE TABLE trial_attempt (
    trial_id TEXT NOT NULL REFERENCES trial(trial_id),
    attempt_no INTEGER NOT NULL CHECK (attempt_no >= 1),
    session_id TEXT REFERENCES session(session_id),
    outcome TEXT NOT NULL CHECK (outcome IN ('PASS', 'FAIL', 'INVALID_INFRA')),
    infra_fault_code TEXT,
    failure_code TEXT,
    log_artifact_id TEXT NOT NULL REFERENCES raw_artifact(artifact_id),
    started_at TEXT NOT NULL,
    ended_at TEXT NOT NULL,
    PRIMARY KEY (trial_id, attempt_no),
    CHECK ((outcome = 'INVALID_INFRA') = (infra_fault_code IS NOT NULL)),
    CHECK (outcome != 'PASS' OR failure_code IS NULL)
);

CREATE TABLE verification (
    verification_id TEXT PRIMARY KEY,
    trial_id TEXT NOT NULL,
    attempt_no INTEGER NOT NULL,
    verdict TEXT NOT NULL CHECK (verdict IN ('PASS', 'FAIL', 'INCONCLUSIVE')),
    pre_state_false INTEGER NOT NULL CHECK (pre_state_false IN (0, 1)),
    channel TEXT NOT NULL,
    artifact_id TEXT NOT NULL REFERENCES raw_artifact(artifact_id),
    verifier_version TEXT NOT NULL,
    FOREIGN KEY (trial_id, attempt_no) REFERENCES trial_attempt(trial_id, attempt_no)
);

CREATE TABLE capability (
    capability_id TEXT PRIMARY KEY,
    app_alias TEXT NOT NULL,
    name TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('CANDIDATE', 'EXPERIMENTAL', 'VERIFIED', 'REJECTED')),
    stats_json TEXT NOT NULL,
    evidence_level TEXT NOT NULL,
    policy_version TEXT NOT NULL,
    gir_artifact_id TEXT REFERENCES raw_artifact(artifact_id),
    created_at TEXT NOT NULL
);

CREATE TABLE binding_version (
    binding_version_id TEXT PRIMARY KEY,
    capability_name TEXT NOT NULL,
    semantic_target TEXT NOT NULL,
    candidates_json TEXT NOT NULL,
    source TEXT NOT NULL CHECK (source IN ('discovered', 'rebound')),
    proposed_by TEXT NOT NULL CHECK (proposed_by IN ('deterministic', 'semantic', 'evidence')),
    validated_by_experiment_id TEXT REFERENCES experiment(experiment_id),
    status TEXT NOT NULL CHECK (status IN ('CANDIDATE', 'ACTIVE', 'RETIRED', 'REJECTED')),
    created_at TEXT NOT NULL,
    CHECK (status != 'ACTIVE' OR validated_by_experiment_id IS NOT NULL)
);

CREATE TRIGGER hypothesis_append_only_u BEFORE UPDATE ON hypothesis
BEGIN SELECT RAISE(ABORT, 'hypothesis is append-only'); END;
CREATE TRIGGER hypothesis_append_only_d BEFORE DELETE ON hypothesis
BEGIN SELECT RAISE(ABORT, 'hypothesis is append-only'); END;

CREATE TRIGGER experiment_frozen_u BEFORE UPDATE ON experiment
BEGIN SELECT RAISE(ABORT, 'experiment specs are frozen'); END;
CREATE TRIGGER experiment_frozen_d BEFORE DELETE ON experiment
BEGIN SELECT RAISE(ABORT, 'experiment specs are frozen'); END;

-- A trial slot is decided exactly once: PENDING -> final status, identity unchanged.
CREATE TRIGGER trial_decided_once BEFORE UPDATE ON trial
WHEN OLD.status != 'PENDING'
    OR NEW.status = 'PENDING'
    OR NEW.trial_id != OLD.trial_id
    OR NEW.experiment_id != OLD.experiment_id
    OR NEW.slot_index != OLD.slot_index
    OR NEW.stratum != OLD.stratum
    OR NEW.probes_json != OLD.probes_json
BEGIN SELECT RAISE(ABORT, 'a trial slot is decided exactly once'); END;
CREATE TRIGGER trial_no_delete BEFORE DELETE ON trial
BEGIN SELECT RAISE(ABORT, 'trials are never deleted'); END;

CREATE TRIGGER trial_attempt_append_only_u BEFORE UPDATE ON trial_attempt
BEGIN SELECT RAISE(ABORT, 'trial_attempt is append-only'); END;
CREATE TRIGGER trial_attempt_append_only_d BEFORE DELETE ON trial_attempt
BEGIN SELECT RAISE(ABORT, 'trial_attempt is append-only'); END;

CREATE TRIGGER verification_append_only_u BEFORE UPDATE ON verification
BEGIN SELECT RAISE(ABORT, 'verification is append-only'); END;
CREATE TRIGGER verification_append_only_d BEFORE DELETE ON verification
BEGIN SELECT RAISE(ABORT, 'verification is append-only'); END;

CREATE TRIGGER capability_no_delete BEFORE DELETE ON capability
BEGIN SELECT RAISE(ABORT, 'capabilities are never deleted'); END;

-- Binding versions: identity frozen; only legal status transitions.
CREATE TRIGGER binding_version_transitions BEFORE UPDATE ON binding_version
WHEN NEW.binding_version_id != OLD.binding_version_id
    OR NEW.candidates_json != OLD.candidates_json
    OR NEW.semantic_target != OLD.semantic_target
    OR NOT (
        (OLD.status = 'CANDIDATE' AND NEW.status IN ('ACTIVE', 'REJECTED'))
        OR (OLD.status = 'ACTIVE' AND NEW.status = 'RETIRED')
    )
BEGIN SELECT RAISE(ABORT, 'illegal binding_version change'); END;
CREATE TRIGGER binding_version_no_delete BEFORE DELETE ON binding_version
BEGIN SELECT RAISE(ABORT, 'binding versions are never deleted'); END;
