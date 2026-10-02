"""Deterministic explorer over a PlatformBridge (no LLM anywhere in the loop).

Policy ``novelty-bfs/1``:
  1. In the current state, take the untried *allowed* action whose (element path, kind)
     has been tried least often anywhere (global novelty); SET_VALUE before INVOKE, then
     path order. SET_VALUE uses a generated probe value, stable per field path.
  2. When the current state has nothing left, reset to a fresh clean environment and replay
     the shortest recorded path to the shallowest state that still has untried actions
     (bounded revisit). A replay that diverges from the recorded fingerprints is recorded,
     and that target is abandoned.
  3. Stop on action/state/replay budget, or when nothing reachable is left.
Every candidate passes the deterministic risk classifier and policy gate; refusals are
recorded. Same provider + config => identical StateGraph.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from typing import Annotated, Protocol

from pydantic import Field

from ghost._model import StrictModel
from ghost.evidence import EvidenceLevel
from ghost.exploration.graph import (
    ActionDescriptor,
    GraphSnapshot,
    StateGraph,
    TransitionEvidence,
    TransitionRecord,
)
from ghost.exploration.policy import ApprovalLedger, Gate, PolicyVerdict, evaluate
from ghost.exploration.risk import RiskClass, RiskDecision, RiskInput, classify
from ghost.observation.canonical import (
    CANONICALIZER,
    CanonicalState,
    ElementLocator,
    VolatilityMask,
    calibrate_mask,
    canonicalize,
    locate_all,
)
from ghost.observation.diff import diff_states
from ghost.platform.errors import BridgeError, BridgeErrorCode
from ghost.platform.protocol import RequestContext
from ghost.platform.types import (
    ActionKind,
    ActionResult,
    ElementRef,
    ElementState,
    ObservationBundle,
    ObserveRequest,
    Role,
    StringValue,
)
from ghost.sandbox.environment import Environment, EnvironmentProvider

POLICY_NAME = "novelty-bfs/1"
_EDITABLE = {Role.TEXT_FIELD, Role.TEXT_AREA}


class ExplorationBudget(StrictModel):
    max_actions: Annotated[int, Field(ge=1)]
    max_states: Annotated[int, Field(ge=1)]
    max_replay_actions: Annotated[int, Field(ge=0)]
    max_depth: Annotated[int, Field(ge=1)]


class ExplorationConfig(StrictModel):
    run_id: Annotated[str, Field(pattern=r"^[A-Za-z0-9_-]{1,64}$")]
    budget: ExplorationBudget
    probe_seed: Annotated[int, Field(ge=0)] = 0
    calibration_observations: Annotated[int, Field(ge=1, le=10)] = 3
    calibration_idle_ms: Annotated[int, Field(ge=0)] = 1000
    deadline_ms: Annotated[int, Field(gt=0)] = 5000
    max_nodes: Annotated[int, Field(ge=1)] = 5000


class StopReason(StrEnum):
    BUDGET_ACTIONS = "budget_actions"
    BUDGET_STATES = "budget_states"
    BUDGET_REPLAY = "budget_replay"
    EXHAUSTED = "exhausted"


class Refusal(StrictModel):
    fingerprint: str
    action_key: str
    risk_class: RiskClass
    gate: Gate
    rule_id: str


class ActionFailure(StrictModel):
    fingerprint: str
    action_key: str
    error_code: str


class ExplorationCounters(StrictModel):
    actions: int
    replay_actions: int
    resets: int
    observations: int
    replay_divergences: int


class ExplorationResult(StrictModel):
    run_id: str
    policy: str
    evidence_level: EvidenceLevel
    stop_reason: StopReason
    mask: VolatilityMask
    graph: GraphSnapshot
    refusals: tuple[Refusal, ...]
    failures: tuple[ActionFailure, ...]
    divergent: tuple[tuple[str, str, tuple[str, ...]], ...]
    counters: ExplorationCounters


class EvidenceSink(Protocol):
    def observation(self, bundle: ObservationBundle, raw_bytes: bytes) -> None: ...

    def transition(self, record: TransitionRecord) -> None: ...


class NullSink:
    def observation(self, bundle: ObservationBundle, raw_bytes: bytes) -> None:
        return None

    def transition(self, record: TransitionRecord) -> None:
        return None


@dataclass(frozen=True)
class Candidate:
    descriptor: ActionDescriptor
    decision: RiskDecision
    verdict: PolicyVerdict


@dataclass(frozen=True)
class _View:
    bundle: ObservationBundle
    state: CanonicalState
    by_path: dict[str, ElementRef]


class ProbeGenerator:
    """Unique, recognisable dummy values; stable per field path within one run."""

    def __init__(self, seed: int) -> None:
        self._seed = seed
        self._by_path: dict[str, str] = {}

    def for_path(self, path: str) -> str:
        if path not in self._by_path:
            self._by_path[path] = f"GP{self._seed:04d}x{len(self._by_path):04d}"
        return self._by_path[path]


def build_candidates(
    view_bundle: ObservationBundle,
    locators: dict[ElementRef, ElementLocator],
    probes: ProbeGenerator,
    approvals: ApprovalLedger,
    disposable: bool,
) -> list[Candidate]:
    """Every primitive action the observation advertises, classified and gated."""
    obs = view_bundle.platform
    texts: dict[str, tuple[str, ...]] = {}
    for window, element, _ in obs.walk():
        if element.role is Role.STATIC_TEXT and element.label:
            key = window.info.ref.ref
            texts[key] = (*texts.get(key, ()), element.label)
    out: list[Candidate] = []
    for window, element, _ in obs.walk():
        if ElementState.DISABLED in element.states:
            continue
        locator = locators[element.ref]
        in_dialog = window.info.modal or Role.DIALOG in locator.ancestor_roles
        for kind in element.actions:
            value = None
            if kind is ActionKind.SET_VALUE:
                if element.role not in _EDITABLE:
                    continue
                value = StringValue(value=probes.for_path(locator.path))
            descriptor = ActionDescriptor(
                kind=kind, locator=locator, value=value, value_is_probe=value is not None
            )
            decision = classify(
                RiskInput(
                    action=kind,
                    role=element.role,
                    label=element.label,
                    in_dialog=in_dialog,
                    dialog_text=texts.get(window.info.ref.ref, ()) if in_dialog else (),
                    value_is_probe=value is not None,
                )
            )
            verdict = evaluate(
                decision,
                action_key=descriptor.key,
                value_is_probe=value is not None,
                disposable=disposable,
                approvals=approvals,
            )
            out.append(Candidate(descriptor=descriptor, decision=decision, verdict=verdict))
    return out


class Explorer:
    def __init__(
        self,
        provider: EnvironmentProvider,
        config: ExplorationConfig,
        *,
        approvals: ApprovalLedger | None = None,
        sink: EvidenceSink | None = None,
    ) -> None:
        self.provider = provider
        self.config = config
        self.approvals = approvals or ApprovalLedger()
        self.sink: EvidenceSink = sink or NullSink()
        self.probes = ProbeGenerator(config.probe_seed)
        self.step = 0
        self.counters = Counter[str]()
        self.refusals: dict[tuple[str, str], Refusal] = {}
        self.failures: list[ActionFailure] = []
        self.tried: set[tuple[str, str]] = set()
        self.unreachable: set[str] = set()
        self.novelty = Counter[tuple[str, ActionKind]]()
        self.candidates: dict[str, list[Candidate]] = {}
        self.depth: dict[str, int] = {}

    # -- plumbing -----------------------------------------------------------------------
    def _ctx(self) -> RequestContext:
        self.step += 1
        return RequestContext.derived(self.config.run_id, self.step, self.config.deadline_ms)

    def _observe(self, env: Environment, mask: VolatilityMask) -> _View:
        bundle = env.bridge.observe(
            self._ctx(),
            ObserveRequest(application=env.application, max_nodes=self.config.max_nodes),
        )
        raw = env.bridge.get_artifact(self._ctx(), bundle.raw.raw_capture.artifact_id)
        self.sink.observation(bundle, raw)
        self.counters["observations"] += 1
        locators = locate_all(bundle.platform, mask)
        state = canonicalize(bundle.platform, mask)
        return _View(bundle, state, {loc.path: ref for ref, loc in locators.items()})

    def _start(self, mask: VolatilityMask | None) -> tuple[Environment, VolatilityMask, _View]:
        env = self.provider.start()
        self.counters["resets"] += 1
        if mask is None:
            idle = []
            for i in range(self.config.calibration_observations):
                if i:
                    env.idle(self.config.calibration_idle_ms)
                idle.append(self._observe(env, VolatilityMask()).bundle.platform)
            mask = calibrate_mask(idle)
        return env, mask, self._observe(env, mask)

    def _register(self, view: _View, env: Environment, depth: int) -> None:
        fingerprint = view.state.fingerprint
        if fingerprint in self.candidates:
            return
        locators = locate_all(view.bundle.platform, self._mask)
        disposable = env.attestation is not None
        found = build_candidates(view.bundle, locators, self.probes, self.approvals, disposable)
        self.candidates[fingerprint] = found
        self.depth[fingerprint] = depth
        for c in found:
            if not c.verdict.allowed:
                self.refusals.setdefault(
                    (fingerprint, c.descriptor.key),
                    Refusal(
                        fingerprint=fingerprint,
                        action_key=c.descriptor.key,
                        risk_class=c.decision.risk_class,
                        gate=c.verdict.gate,
                        rule_id=c.decision.rule_id,
                    ),
                )

    def _untried(self, fingerprint: str) -> list[Candidate]:
        if self.depth.get(fingerprint, 0) >= self.config.budget.max_depth:
            return []
        pending = [
            c
            for c in self.candidates.get(fingerprint, [])
            if c.verdict.allowed and (fingerprint, c.descriptor.key) not in self.tried
        ]

        def rank(c: Candidate) -> tuple[int, int, str, str]:
            d = c.descriptor
            first = 0 if d.kind is ActionKind.SET_VALUE else 1
            return (self.novelty[(d.locator.path, d.kind)], first, d.locator.path, d.kind.value)

        return sorted(pending, key=rank)

    def _act(self, env: Environment, view: _View, descriptor: ActionDescriptor) -> ActionResult:
        ref = view.by_path.get(descriptor.locator.path)
        if ref is None:
            raise BridgeError(
                BridgeErrorCode.ELEMENT_NOT_FOUND,
                f"no element at {descriptor.locator.path!r} in the current observation",
            )
        if descriptor.kind is ActionKind.INVOKE:
            return env.bridge.invoke(self._ctx(), ref)
        if descriptor.value is None:
            raise ValueError("set_value descriptor without value")
        return env.bridge.set_value(self._ctx(), ref, descriptor.value)

    def _record(
        self,
        before: _View,
        after: _View,
        candidate: Candidate,
        claim: ActionResult,
        env: Environment,
    ) -> None:
        descriptor = candidate.descriptor
        sequence = len(self._graph.transitions)
        pre, post = before.bundle.raw, after.bundle.raw
        record = TransitionRecord(
            transition_id=TransitionRecord.make_id(
                sequence,
                before.state.fingerprint,
                after.state.fingerprint,
                descriptor,
                pre.observation_id,
                post.observation_id,
            ),
            sequence=sequence,
            from_fingerprint=before.state.fingerprint,
            to_fingerprint=after.state.fingerprint,
            action=descriptor,
            diff=diff_states(before.state, after.state),
            risk_class=candidate.decision.risk_class,
            approval_id=candidate.verdict.approval_id,
            evidence=TransitionEvidence(
                pre_observation_id=pre.observation_id,
                post_observation_id=post.observation_id,
                pre_raw_capture_id=pre.raw_capture.artifact_id,
                post_raw_capture_id=post.raw_capture.artifact_id,
                executor_claim=claim,
            ),
            evidence_level=env.attestation.evidence_level,
        )
        self._graph.add_transition(record)
        self.sink.transition(record)

    # -- main loop ----------------------------------------------------------------------
    def run(self) -> ExplorationResult:
        budget = self.config.budget
        env, self._mask, view = self._start(None)
        self._graph = StateGraph(CANONICALIZER, self._mask.mask_id)
        self._graph.add_state(view.state, view.bundle.raw.observation_id)
        self._register(view, env, 0)
        stop = StopReason.EXHAUSTED
        while True:
            if self.counters["actions"] >= budget.max_actions:
                stop = StopReason.BUDGET_ACTIONS
                break
            if len(self._graph.fingerprints) >= budget.max_states:
                stop = StopReason.BUDGET_STATES
                break
            pending = self._untried(view.state.fingerprint)
            if pending:
                view = self._step(env, view, pending[0])
                continue
            target = self._next_target()
            if target is None:
                break
            path = self._graph.shortest_path(target)
            if self.counters["replay_actions"] + len(path) > budget.max_replay_actions:
                stop = StopReason.BUDGET_REPLAY
                break
            env, _, view = self._start(self._mask)
            view = self._replay(env, view, path, target)
        return ExplorationResult(
            run_id=self.config.run_id,
            policy=POLICY_NAME,
            evidence_level=env.attestation.evidence_level,
            stop_reason=stop,
            mask=self._mask,
            graph=self._graph.snapshot(),
            refusals=tuple(self.refusals[k] for k in sorted(self.refusals)),
            failures=tuple(self.failures),
            divergent=tuple(self._graph.divergent()),
            counters=ExplorationCounters(
                actions=self.counters["actions"],
                replay_actions=self.counters["replay_actions"],
                resets=self.counters["resets"],
                observations=self.counters["observations"],
                replay_divergences=self.counters["replay_divergences"],
            ),
        )

    def _step(self, env: Environment, view: _View, candidate: Candidate) -> _View:
        descriptor = candidate.descriptor
        fingerprint = view.state.fingerprint
        self.tried.add((fingerprint, descriptor.key))
        self.novelty[(descriptor.locator.path, descriptor.kind)] += 1
        try:
            claim = self._act(env, view, descriptor)
        except BridgeError as error:
            self.failures.append(
                ActionFailure(
                    fingerprint=fingerprint, action_key=descriptor.key, error_code=error.code.value
                )
            )
            return self._observe(env, self._mask)
        self.counters["actions"] += 1
        after = self._observe(env, self._mask)
        self._graph.add_state(after.state, after.bundle.raw.observation_id)
        self._register(after, env, self.depth[fingerprint] + 1)
        self._record(view, after, candidate, claim, env)
        return after

    def _next_target(self) -> str | None:
        choices = [
            (self.depth[f], f)
            for f in self._graph.fingerprints
            if f not in self.unreachable and self._untried(f)
        ]
        return min(choices)[1] if choices else None

    def _replay(
        self, env: Environment, view: _View, path: tuple[TransitionRecord, ...], target: str
    ) -> _View:
        expected_start = self._graph.root
        if view.state.fingerprint != expected_start:
            self.counters["replay_divergences"] += 1
            self.unreachable.add(target)
            return view
        for edge in path:
            try:
                claim = self._act(env, view, edge.action)
            except BridgeError:
                self.counters["replay_divergences"] += 1
                self.unreachable.add(target)
                return self._observe(env, self._mask)
            del claim  # replays re-use recorded edges; they add no new transitions
            self.counters["replay_actions"] += 1
            view = self._observe(env, self._mask)
            self._graph.add_state(view.state, view.bundle.raw.observation_id)
            if view.state.fingerprint != edge.to_fingerprint:
                self.counters["replay_divergences"] += 1
                self.unreachable.add(target)
                self._register(view, env, self.depth.get(edge.from_fingerprint, 0) + 1)
                return view
        return view


ExplorerFactory = Callable[[EnvironmentProvider, ExplorationConfig], Explorer]
