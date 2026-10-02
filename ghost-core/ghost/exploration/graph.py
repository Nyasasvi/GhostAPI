"""StateGraph: observed CanonicalStates as nodes, observed transitions as edges.

A research artifact, not a debug log: every edge carries its raw evidence references,
its structured diff, its risk class, and its evidence level. No LLM logic lives here.
"""

from __future__ import annotations

from collections import Counter, deque
from typing import Annotated

from pydantic import Field

from ghost._model import SHA256_PATTERN, StrictModel, canonical_json, content_hash
from ghost.evidence import EvidenceLevel
from ghost.exploration.risk import RiskClass
from ghost.observation.canonical import CanonicalState, ElementLocator, identity_hash
from ghost.observation.diff import StateDiff
from ghost.platform.types import ActionKind, ActionResult, GeneratorInfo, TypedValue


class ActionDescriptor(StrictModel):
    """A primitive action described by a persistable locator (never by an ephemeral handle)."""

    kind: ActionKind
    locator: ElementLocator
    value: TypedValue | None = None
    value_is_probe: bool = False

    @property
    def key(self) -> str:
        value = self.value.model_dump(mode="json") if self.value else None
        return canonical_json([self.kind.value, self.locator.path, value])


class TransitionEvidence(StrictModel):
    pre_observation_id: str
    post_observation_id: str
    pre_raw_capture_id: Annotated[str, Field(pattern=SHA256_PATTERN)]
    post_raw_capture_id: Annotated[str, Field(pattern=SHA256_PATTERN)]
    executor_claim: ActionResult


class TransitionRecord(StrictModel):
    transition_id: str
    sequence: Annotated[int, Field(ge=0)]
    from_fingerprint: Annotated[str, Field(pattern=SHA256_PATTERN)]
    to_fingerprint: Annotated[str, Field(pattern=SHA256_PATTERN)]
    action: ActionDescriptor
    diff: StateDiff
    risk_class: RiskClass
    approval_id: str | None = None
    """The human approval that allowed this action, when its risk class required one."""
    evidence: TransitionEvidence
    evidence_level: EvidenceLevel

    @staticmethod
    def make_id(
        sequence: int,
        from_fp: str,
        to_fp: str,
        action: ActionDescriptor,
        pre_obs: str,
        post_obs: str,
    ) -> str:
        digest = content_hash([sequence, from_fp, to_fp, action.key, pre_obs, post_obs])
        return "tr_" + digest.removeprefix("sha256:")[:24]


class GraphSnapshot(StrictModel):
    canonicalizer: GeneratorInfo
    mask_id: str
    root: str | None
    states: tuple[CanonicalState, ...]
    visits: tuple[tuple[str, tuple[str, ...]], ...]
    transitions: tuple[TransitionRecord, ...]


class StateGraph:
    """Deterministic in-memory graph with revisit detection and divergence tracking."""

    def __init__(self, canonicalizer: GeneratorInfo, mask_id: str) -> None:
        self.canonicalizer = canonicalizer
        self.mask_id = mask_id
        self.root: str | None = None
        self._states: dict[str, CanonicalState] = {}
        self._visits: dict[str, list[str]] = {}
        self._seen_observations: set[str] = set()
        self._transitions: list[TransitionRecord] = []
        self._outgoing: dict[str, list[TransitionRecord]] = {}

    # -- mutation -----------------------------------------------------------------------
    def add_state(self, state: CanonicalState, observation_id: str | None) -> bool:
        """Record a visit; returns True when this fingerprint is new (not a revisit).

        Idempotent per observation id: re-recording the same observation never double-counts.
        ``observation_id=None`` inserts the state without a visit (snapshot loading).
        """
        if state.canonicalizer != self.canonicalizer or state.mask_id != self.mask_id:
            raise ValueError("state was canonicalized under a different canonicalizer or mask")
        if identity_hash(state) != state.fingerprint:
            raise ValueError("state fingerprint does not match its identity fields")
        is_new = state.fingerprint not in self._states
        if is_new:
            self._states[state.fingerprint] = state
            self._visits[state.fingerprint] = []
            if self.root is None:
                self.root = state.fingerprint
        if observation_id is not None and observation_id not in self._seen_observations:
            self._seen_observations.add(observation_id)
            self._visits[state.fingerprint].append(observation_id)
        return is_new

    def add_transition(self, record: TransitionRecord) -> None:
        if record.from_fingerprint not in self._states or record.to_fingerprint not in self._states:
            raise ValueError("both endpoint states must be recorded before the transition")
        if record.sequence != len(self._transitions):
            raise ValueError(f"expected sequence {len(self._transitions)}, got {record.sequence}")
        if record.diff.from_fingerprint != record.from_fingerprint or (
            record.diff.to_fingerprint != record.to_fingerprint
        ):
            raise ValueError("transition diff does not connect the transition's states")
        self._transitions.append(record)
        self._outgoing.setdefault(record.from_fingerprint, []).append(record)

    # -- queries ------------------------------------------------------------------------
    def has_state(self, fingerprint: str) -> bool:
        return fingerprint in self._states

    def state(self, fingerprint: str) -> CanonicalState:
        return self._states[fingerprint]

    def visit_count(self, fingerprint: str) -> int:
        return len(self._visits.get(fingerprint, ()))

    @property
    def fingerprints(self) -> tuple[str, ...]:
        return tuple(self._states)

    @property
    def transitions(self) -> tuple[TransitionRecord, ...]:
        return tuple(self._transitions)

    def outgoing(self, fingerprint: str) -> tuple[TransitionRecord, ...]:
        return tuple(self._outgoing.get(fingerprint, ()))

    def outcomes(self, fingerprint: str, action_key: str) -> Counter[str]:
        return Counter(
            t.to_fingerprint for t in self.outgoing(fingerprint) if t.action.key == action_key
        )

    def divergent(self) -> list[tuple[str, str, tuple[str, ...]]]:
        """(state, action, outcomes) where the same action from the same state led to
        different states: evidence that the fingerprint aliases hidden state."""
        found = []
        for fingerprint in self._states:
            keys = sorted({t.action.key for t in self.outgoing(fingerprint)})
            for key in keys:
                outcomes = self.outcomes(fingerprint, key)
                if len(outcomes) > 1:
                    found.append((fingerprint, key, tuple(sorted(outcomes))))
        return found

    def shortest_path(self, target: str, start: str | None = None) -> tuple[TransitionRecord, ...]:
        """Fewest-transitions path from ``start`` (default: root) to ``target``.

        Raises KeyError if unreachable. Ties break on recording order, so it is deterministic.
        """
        origin = start if start is not None else self.root
        if origin is None or target not in self._states:
            raise KeyError(target)
        if origin == target:
            return ()
        previous: dict[str, TransitionRecord] = {}
        queue = deque([origin])
        seen = {origin}
        while queue:
            node = queue.popleft()
            for edge in self.outgoing(node):
                nxt = edge.to_fingerprint
                if nxt in seen:
                    continue
                seen.add(nxt)
                previous[nxt] = edge
                if nxt == target:
                    path = [edge]
                    while path[-1].from_fingerprint != origin:
                        path.append(previous[path[-1].from_fingerprint])
                    return tuple(reversed(path))
                queue.append(nxt)
        raise KeyError(target)

    # -- serialization ------------------------------------------------------------------
    def snapshot(self) -> GraphSnapshot:
        """Insertion order is preserved, so a reloaded graph iterates identically."""
        return GraphSnapshot(
            canonicalizer=self.canonicalizer,
            mask_id=self.mask_id,
            root=self.root,
            states=tuple(self._states.values()),
            visits=tuple((f, tuple(v)) for f, v in self._visits.items()),
            transitions=tuple(self._transitions),
        )

    def to_json(self) -> str:
        return canonical_json(self.snapshot().model_dump(mode="json"))

    @classmethod
    def from_snapshot(cls, snapshot: GraphSnapshot) -> StateGraph:
        """Rebuild and validate: fingerprints recomputed, visits must reference known states,
        and the root must be the first recorded state."""
        graph = cls(snapshot.canonicalizer, snapshot.mask_id)
        known = [s.fingerprint for s in snapshot.states]
        if len(set(known)) != len(known):
            raise ValueError("snapshot repeats a state")
        if known and snapshot.root != known[0]:
            raise ValueError("snapshot root must be the first recorded state")
        if [f for f, _ in snapshot.visits] != known:
            raise ValueError("snapshot visits do not match its states")
        for state, (_, observations) in zip(snapshot.states, snapshot.visits, strict=True):
            graph.add_state(state, None)
            for observation_id in observations:
                graph.add_state(state, observation_id)
        for record in snapshot.transitions:
            graph.add_transition(record)
        return graph

    @classmethod
    def from_json(cls, text: str) -> StateGraph:
        return cls.from_snapshot(GraphSnapshot.model_validate_json(text))
