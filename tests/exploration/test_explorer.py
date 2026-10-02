"""Deterministic exploration against the synthetic fixture (SYNTHETIC FIXTURE evidence)."""

from __future__ import annotations

import json

import pytest

from ghost.evidence import BlockedVMStorageError, EvidenceLevel
from ghost.exploration.explorer import (
    ExplorationBudget,
    ExplorationConfig,
    ExplorationResult,
    Explorer,
    StopReason,
)
from ghost.exploration.graph import StateGraph
from ghost.exploration.policy import ApprovalDecision, ApprovalLedger, ApprovalRecord, Gate
from ghost.exploration.risk import RiskClass
from ghost.observation.diff import ChangeKind
from ghost.sandbox.environment import DisposableVMEnvironmentProvider
from ghost_fixture.app import read_store
from ghost_fixture.config import FixtureConfig
from tests.support.fixture_env import RecordingDisks, provider

RISKY = FixtureConfig(risky_controls=True, injection_row=True, distractor=True, volatile_clock=True)


def config(run_id: str = "t1", actions: int = 60, states: int = 200) -> ExplorationConfig:
    budget = ExplorationBudget(
        max_actions=actions, max_states=states, max_replay_actions=400, max_depth=6
    )
    return ExplorationConfig(run_id=run_id, budget=budget)


def explore(
    fixture: FixtureConfig = RISKY,
    cfg: ExplorationConfig | None = None,
    approvals: ApprovalLedger | None = None,
    disks: RecordingDisks | None = None,
) -> ExplorationResult:
    explorer = Explorer(provider(fixture, disks=disks), cfg or config(), approvals=approvals)
    return explorer.run()


def label_of(action_key: str) -> str:
    return str(json.loads(action_key)[1]).rsplit("/", 1)[-1]


def test_results_are_labelled_synthetic_evidence() -> None:
    result = explore()
    assert result.evidence_level is EvidenceLevel.SYNTHETIC_FIXTURE
    assert {t.evidence_level for t in result.graph.transitions} == {EvidenceLevel.SYNTHETIC_FIXTURE}


def test_multi_step_create_chain_is_discovered_without_domain_knowledge() -> None:
    result = explore()
    graph = StateGraph.from_snapshot(result.graph)
    creations = [
        t
        for t in result.graph.transitions
        if any(c.role and c.role.value == "row" for c in t.diff.of_kind(ChangeKind.ELEMENT_ADDED))
    ]
    assert creations, "the explorer never observed a row being added"
    chain = graph.shortest_path(creations[0].to_fingerprint)
    kinds = [t.action.kind.value for t in chain]
    assert "set_value" in kinds  # a probe was typed before the row appeared
    probe = next(t.action.value for t in chain if t.action.value is not None)
    assert probe is not None
    added = creations[0].diff.of_kind(ChangeKind.ELEMENT_ADDED)[0].path
    assert f"[{probe.value}]" in added  # probe propagation: typed value became the row label


def test_dangerous_and_unknown_controls_never_execute_without_approval() -> None:
    disks = RecordingDisks()
    result = explore(disks=disks)
    executed = {t.risk_class for t in result.graph.transitions}
    assert executed.isdisjoint(
        {RiskClass.DESTRUCTIVE, RiskClass.UNKNOWN, RiskClass.UNKNOWN_HIGH_RISK}
    )
    refused = {label_of(r.action_key): r for r in result.refusals}
    assert refused["button<btn-tidy>[Tidy Up]#0"].gate is Gate.BLOCKED_UNKNOWN_MUTATION
    assert refused["button<btn-preview>[Delete Preview]#0"].gate is Gate.BLOCKED_NEEDS_APPROVAL
    assert refused["button<btn-remove>[Remove Specimen]#0"].risk_class is RiskClass.DESTRUCTIVE
    # No specimen was ever deleted or archived (renames are allowed reversible writes).
    seeded = set(range(len(RISKY.specimens) + 1))  # seeded names + the injection row
    for disk in disks.disks:
        stored = read_store(disk)
        assert seeded <= {s.uid for s in stored}
        assert not any(s.archived for s in stored)


def test_approved_destructive_actions_run_only_with_their_own_approval() -> None:
    probe = explore(FixtureConfig(), config(actions=40))
    remove_keys = sorted(
        {r.action_key for r in probe.refusals if "Remove" in label_of(r.action_key)}
    )
    ledger = ApprovalLedger(
        tuple(
            ApprovalRecord(
                approval_id=f"apr_{i}",
                action_key=key,
                risk_class=RiskClass.DESTRUCTIVE,
                decision=ApprovalDecision.APPROVED,
                decided_by="owner",
                subject=f"control {label_of(key)} (evidence from run t1)",
            )
            for i, key in enumerate(remove_keys)
        )
    )
    result = explore(FixtureConfig(), config(run_id="t2", actions=40), approvals=ledger)
    destructive = [t for t in result.graph.transitions if t.risk_class is RiskClass.DESTRUCTIVE]
    assert destructive
    assert all(t.approval_id is not None for t in destructive)


def test_budgets_are_respected() -> None:
    assert explore(cfg=config(actions=7)).counters.actions == 7
    small = explore(cfg=config(actions=500, states=5))
    assert small.stop_reason is StopReason.BUDGET_STATES
    assert len(small.graph.states) <= 5


def test_exploration_is_deterministic() -> None:
    first, second = explore(cfg=config("same")), explore(cfg=config("same"))
    assert first.graph.model_dump_json() == second.graph.model_dump_json()
    assert first.refusals == second.refusals


def test_bounded_revisit_replays_paths_without_divergence() -> None:
    result = explore(cfg=config(actions=80))
    assert result.counters.resets > 1
    assert result.counters.replay_actions > 0
    assert result.counters.replay_divergences == 0


def test_idle_calibration_keeps_a_ticking_clock_out_of_state_identity() -> None:
    ticking = explore(FixtureConfig(volatile_clock=True), config(actions=30))
    still = explore(FixtureConfig(), config(actions=30))
    assert ticking.mask.entries
    assert len(ticking.graph.states) == len(still.graph.states)


def test_disposable_vm_exploration_is_blocked_not_faked() -> None:
    with pytest.raises(BlockedVMStorageError):
        Explorer(DisposableVMEnvironmentProvider(), config()).run()
