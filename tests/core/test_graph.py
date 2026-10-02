"""StateGraph: revisits, provenance, divergence, deterministic traversal and serialization."""

from __future__ import annotations

import pytest

from ghost.evidence import EvidenceLevel
from ghost.exploration.graph import (
    ActionDescriptor,
    StateGraph,
    TransitionEvidence,
    TransitionRecord,
)
from ghost.exploration.risk import RiskClass
from ghost.observation.canonical import CANONICALIZER, CanonicalState, ElementLocator
from ghost.observation.diff import diff_states
from ghost.platform.types import ActionKind, ActionResult, Role
from tests.support.obs import E, W, canon

SHA_A = "sha256:" + "a" * 64
SHA_B = "sha256:" + "b" * 64


def state(rows: tuple[str, ...]) -> CanonicalState:
    return canon([W("Items", E(Role.LIST, kids=tuple(E(Role.ROW, r) for r in rows)))])


def action(label: str = "Add") -> ActionDescriptor:
    locator = ElementLocator(
        window_key="window[Items]#0",
        path=f"window[Items]#0/button[{label}]#0",
        structural_path="window[Items]#0/button#0",
        role=Role.BUTTON,
        label=label,
        stable_id_hint=None,
        ancestor_roles=(Role.WINDOW,),
    )
    return ActionDescriptor(kind=ActionKind.INVOKE, locator=locator)


def record(
    seq: int, a: CanonicalState, b: CanonicalState, act: ActionDescriptor
) -> TransitionRecord:
    evidence = TransitionEvidence(
        pre_observation_id=f"obs_{seq}a",
        post_observation_id=f"obs_{seq}b",
        pre_raw_capture_id=SHA_A,
        post_raw_capture_id=SHA_B,
        executor_claim=ActionResult(
            action_id=f"act_{seq}",
            request_id="r",
            executed=True,
            platform_status="ok",
            elapsed_ms=1,
        ),
    )
    return TransitionRecord(
        transition_id=TransitionRecord.make_id(seq, a.fingerprint, b.fingerprint, act, "x", "y"),
        sequence=seq,
        from_fingerprint=a.fingerprint,
        to_fingerprint=b.fingerprint,
        action=act,
        diff=diff_states(a, b),
        risk_class=RiskClass.REVERSIBLE_WRITE,
        evidence=evidence,
        evidence_level=EvidenceLevel.SYNTHETIC_FIXTURE,
    )


@pytest.fixture
def graph() -> StateGraph:
    s0, s1, s2 = state(()), state(("x",)), state(("x", "y"))
    g = StateGraph(CANONICALIZER, s0.mask_id)
    for i, s in enumerate((s0, s1, s2)):
        g.add_state(s, f"obs_{i}")
    g.add_transition(record(0, s0, s1, action()))
    g.add_transition(record(1, s1, s2, action()))
    return g


def test_revisits_are_detected_and_counted(graph: StateGraph) -> None:
    s1 = state(("x",))
    assert not graph.add_state(s1, "obs_again")
    assert graph.visit_count(s1.fingerprint) == 2
    assert graph.root == state(()).fingerprint


def test_transitions_require_known_states_ordered_sequence_and_matching_diff(
    graph: StateGraph,
) -> None:
    unknown = state(("q",))
    with pytest.raises(ValueError, match="endpoint"):
        graph.add_transition(record(2, state(()), unknown, action()))
    with pytest.raises(ValueError, match="sequence"):
        graph.add_transition(record(7, state(()), state(("x",)), action()))
    bad = record(2, state(()), state(("x",)), action())
    swapped = bad.model_copy(update={"diff": diff_states(state(("x",)), state(()))})
    with pytest.raises(ValueError, match="diff"):
        graph.add_transition(swapped)


def test_shortest_path_is_deterministic(graph: StateGraph) -> None:
    path = graph.shortest_path(state(("x", "y")).fingerprint)
    assert [t.sequence for t in path] == [0, 1]
    assert graph.shortest_path(graph.root or "") == ()
    graph.add_state(state(("lonely",)), "obs_9")
    with pytest.raises(KeyError):
        graph.shortest_path(state(("lonely",)).fingerprint)


def test_divergent_outcomes_flag_hidden_state(graph: StateGraph) -> None:
    s1, other = state(("x",)), state(("x", "z"))
    graph.add_state(other, "obs_7")
    graph.add_transition(record(2, s1, other, action()))
    ((origin, _key, outcomes),) = graph.divergent()
    assert origin == s1.fingerprint
    assert len(outcomes) == 2


def test_json_round_trip_is_exact(graph: StateGraph) -> None:
    text = graph.to_json()
    again = StateGraph.from_json(text)
    assert again.to_json() == text
    assert again.transitions == graph.transitions


def test_states_from_another_mask_are_rejected(graph: StateGraph) -> None:
    alien = state(("x",)).model_copy(update={"mask_id": "other"})
    with pytest.raises(ValueError, match="mask"):
        graph.add_state(alien, "obs_x")
