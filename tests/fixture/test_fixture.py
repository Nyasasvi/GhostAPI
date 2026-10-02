"""The synthetic research fixture behaves as its scenarios claim (SYNTHETIC FIXTURE)."""

from __future__ import annotations

import pytest

from ghost.evidence import BlockedVMStorageError, EvidenceLevel
from ghost.exploration.graph import (
    ActionDescriptor,
    StateGraph,
    TransitionEvidence,
    TransitionRecord,
)
from ghost.exploration.risk import RiskClass
from ghost.observation.canonical import CANONICALIZER, CanonicalState, canonicalize, locate_all
from ghost.observation.diff import diff_states
from ghost.platform.mock import MockPlatformBridge
from ghost.platform.protocol import RequestContext
from ghost.platform.types import (
    ActionKind,
    ActionResult,
    Health,
    ObservationBundle,
    ObserveRequest,
    StringValue,
    UIElement,
)
from ghost.sandbox.environment import DisposableVMEnvironmentProvider, Environment
from ghost.sandbox.guard import SandboxRefusedError, attest
from ghost_fixture.app import read_store
from ghost_fixture.config import FixtureConfig
from tests.support.fixture_env import RecordingDisks, provider


def ctx() -> RequestContext:
    return RequestContext.new("fixture-test", 2000)


def observe(env: Environment) -> ObservationBundle:
    return env.bridge.observe(ctx(), ObserveRequest(application=env.application))


def find(bundle: ObservationBundle, label: str) -> UIElement:
    found = [e for _, e, _ in bundle.platform.walk() if e.label == label]
    assert len(found) == 1, label
    return found[0]


def create(env: Environment, name: str, button: str = "Add Specimen") -> None:
    env.bridge.set_value(ctx(), find(observe(env), "Specimen Name").ref, StringValue(value=name))
    env.bridge.invoke(ctx(), find(observe(env), button).ref)


def remove(env: Environment, name: str) -> None:
    env.bridge.invoke(ctx(), find(observe(env), name).ref)
    env.bridge.invoke(ctx(), find(observe(env), "Remove Specimen").ref)
    env.bridge.invoke(ctx(), find(observe(env), "Remove").ref)  # confirm sheet


def test_archive_and_delete_look_identical_but_differ_in_the_store() -> None:
    fingerprints, stores = [], []
    for semantics in ("delete", "archive"):
        disks = RecordingDisks()
        env = provider(FixtureConfig(remove_semantics=semantics), disks=disks).start()
        remove(env, "Alpha")
        fingerprints.append(canonicalize(observe(env).platform).fingerprint)
        stores.append([(s.name, s.archived) for s in read_store(disks.disks[0])])
    assert fingerprints[0] == fingerprints[1]  # observationally equivalent
    assert stores[0] != stores[1]  # only the oracle can tell them apart


def test_modal_sheet_disables_the_main_window() -> None:
    env = provider().start()
    env.bridge.invoke(ctx(), find(observe(env), "Alpha").ref)
    env.bridge.invoke(ctx(), find(observe(env), "Remove Specimen").ref)
    bundle = observe(env)
    sheet = [w for w in bundle.platform.windows if w.info.modal]
    assert len(sheet) == 1
    assert find(bundle, "Add Specimen").actions == ()


def test_delayed_persistence_is_lost_on_relaunch_without_save() -> None:
    disks = RecordingDisks()
    env = provider(FixtureConfig(delayed_persistence=True), disks=disks).start()
    create(env, "Unsaved")
    env.bridge.quit(ctx(), env.application)
    assert "Unsaved" not in {s.name for s in read_store(disks.disks[0])}


@pytest.mark.parametrize(
    ("drift", "button"),
    [
        (FixtureConfig(create_label="Create Entry"), "Create Entry"),  # D1 label
        (FixtureConfig(toolbar_in_group=True), "Add Specimen"),  # D2 hierarchy
        (FixtureConfig(toolbar_reversed=True), "Add Specimen"),  # D3 reorder
        (FixtureConfig(create_location="menu"), "New Specimen"),  # D4 relocation
        (FixtureConfig(distractor=True), "Add Specimen"),  # D5 distractor
        (FixtureConfig(wrapper_depth=2), "Add Specimen"),  # D6 wrapper
    ],
)
def test_drift_changes_the_binding_but_not_the_operation(drift: FixtureConfig, button: str) -> None:
    base_env, drift_env = provider().start(), provider(drift).start()
    # Labelled paths are robust to pure reordering (D3); structural positions are not.
    base = {
        (loc.path, loc.structural_path) for loc in locate_all(observe(base_env).platform).values()
    }
    drifted = {
        (loc.path, loc.structural_path) for loc in locate_all(observe(drift_env).platform).values()
    }
    assert base != drifted
    create(drift_env, "Drifted", button=button)
    assert find(observe(drift_env), "Drifted")


def test_workflow_step_drift_adds_a_confirmation() -> None:  # D7
    env = provider(FixtureConfig(confirm_create=True)).start()
    create(env, "Gated")
    with pytest.raises(AssertionError):
        find(observe(env), "Gated")
    env.bridge.invoke(ctx(), find(observe(env), "Confirm").ref)
    assert find(observe(env), "Gated")


def test_hidden_state_aliasing_is_detected_as_divergence() -> None:
    """Same fingerprint + same action -> different outcomes reveals hidden state."""
    env = provider(FixtureConfig(hidden_ordering=True, specimens=("A",))).start()
    graph: StateGraph | None = None
    for flip in (False, True):
        if flip:
            env.bridge.invoke(ctx(), find(observe(env), "Reverse Sort").ref)  # no visible change
        env.bridge.set_value(ctx(), find(observe(env), "Specimen Name").ref, StringValue(value="Z"))
        before = observe(env)
        s0 = canonicalize(before.platform)
        graph = graph or StateGraph(CANONICALIZER, s0.mask_id)
        graph.add_state(s0, before.raw.observation_id)
        claim = env.bridge.invoke(ctx(), find(before, "Add Specimen").ref)
        after = observe(env)
        s1 = canonicalize(after.platform)
        graph.add_state(s1, after.raw.observation_id)
        add_button = find(before, "Add Specimen")
        descriptor = ActionDescriptor(
            kind=ActionKind.INVOKE, locator=locate_all(before.platform)[add_button.ref]
        )
        graph.add_transition(_record(graph, s0, s1, descriptor, before, after, claim))
        remove(env, "Z")  # back to the same visible state for the second round
    assert graph is not None
    assert len(graph.divergent()) == 1


def _record(
    graph: StateGraph,
    s0: CanonicalState,
    s1: CanonicalState,
    descriptor: ActionDescriptor,
    before: ObservationBundle,
    after: ObservationBundle,
    claim: ActionResult,
) -> TransitionRecord:
    seq = len(graph.transitions)
    return TransitionRecord(
        transition_id=f"tr_{seq}",
        sequence=seq,
        from_fingerprint=s0.fingerprint,
        to_fingerprint=s1.fingerprint,
        action=descriptor,
        diff=diff_states(s0, s1),
        risk_class=RiskClass.REVERSIBLE_WRITE,
        evidence=TransitionEvidence(
            pre_observation_id=before.raw.observation_id,
            post_observation_id=after.raw.observation_id,
            pre_raw_capture_id=before.raw.raw_capture.artifact_id,
            post_raw_capture_id=after.raw.raw_capture.artifact_id,
            executor_claim=claim,
        ),
        evidence_level=EvidenceLevel.SYNTHETIC_FIXTURE,
    )


class _ClaimsSynthetic:
    """A bridge that is NOT the in-process mock but reports a synthetic environment."""

    def __init__(self) -> None:
        self._inner = MockPlatformBridge({})

    def health(self, c: RequestContext) -> Health:
        return self._inner.health(c)


def test_sandbox_guard_refuses_impostors_and_blocks_vms() -> None:
    assert provider().start().attestation.kind.value == "synthetic"
    with pytest.raises(SandboxRefusedError):
        attest(_ClaimsSynthetic(), ctx(), "x")  # type: ignore[arg-type]
    with pytest.raises(BlockedVMStorageError):
        DisposableVMEnvironmentProvider().start()
