"""PlatformObservation -> CanonicalState: deterministic, versioned canonicalization.

Canonicalizer v2 rules (each covered by tests):

R1  Excluded from state identity, kept as volatile facts: element handles and generations,
    observation ids and timestamps, all geometry, keyboard focus, window focused/main flags.
R2  Order-insensitive: windows (sorted by their full masked canonical identity), element
    state and action sets (sorted). Raw attribute order never matters.
R3  Child order is preserved (presentation order may be meaningful, e.g. list rows).
R4  Included in identity: role, label, value (with -0.0 normalized to 0.0), states except
    ``focused``, actions, stable_id_hint, truncation flag, window title / modal / minimized.
R5  A field is masked (removed from identity, recorded as volatile) only when the explicit,
    evidence-derived VolatilityMask names it *and* the element's sibling role signature still
    matches the one seen at calibration. A stale entry is not applied (recorded as a miss),
    so a mask can never silently hide a different element. Mask paths are window-relative
    (window title + structural path) and never depend on window ordering.
R6  Truncated (unobservable) content stays unknown: ``complete=False``; nothing is invented.
R7  Same-titled windows cannot be told apart by identity; their keys are ordinals over the
    sorted order and are flagged ``ambiguous``. Consumers must not treat such keys as stable.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Annotated

from pydantic import Field

from ghost._model import SHA256_PATTERN, StrictModel, canonical_json, content_hash, model_hash
from ghost.platform.types import (
    ActionKind,
    ElementRef,
    ElementState,
    GeneratorInfo,
    NumberValue,
    PlatformObservation,
    Rect,
    Role,
    TypedValue,
    UIElement,
    WindowObservation,
)

CANONICALIZER = GeneratorInfo(name="canonicalizer", version="2")
_ROOT_SIGNATURE = content_hash(["<window-root>"])


class MaskedField(StrEnum):
    LABEL = "label"
    VALUE = "value"


class MaskEntry(StrictModel):
    structural_path: str
    field: MaskedField
    sibling_signature: str


class VolatilityMask(StrictModel):
    """Fields excluded from identity because idle re-observation showed them churning."""

    entries: tuple[MaskEntry, ...] = ()

    @property
    def mask_id(self) -> str:
        return content_hash([e.model_dump(mode="json") for e in self.entries])


EMPTY_MASK = VolatilityMask()


class ElementLocator(StrictModel):
    """Neutral, persistable description of where an element was observed.

    Survives re-observation (unlike ``ElementRef``). Evidence about one UI layout, not entity
    identity. ``window_ambiguous`` is true when another window shares this window's title.
    """

    window_key: str
    window_ambiguous: bool = False
    path: str
    structural_path: str
    role: Role
    label: str | None
    stable_id_hint: str | None
    ancestor_roles: tuple[Role, ...]


class CanonicalNode(StrictModel):
    role: Role
    label: str | None
    value: TypedValue | None
    states: tuple[ElementState, ...]
    actions: tuple[ActionKind, ...]
    stable_id_hint: str | None
    truncated: bool
    masked: tuple[MaskedField, ...] = ()
    children: tuple[CanonicalNode, ...] = ()


class CanonicalWindow(StrictModel):
    key: str
    ambiguous: bool
    title: str | None
    modal: bool
    minimized: bool
    root: CanonicalNode


class VolatileFacts(StrictModel):
    """Observed facts deliberately excluded from identity (rules R1 and R5)."""

    focused_path: str | None = None
    window_bounds: tuple[tuple[str, Rect | None], ...] = ()
    masked_values: tuple[tuple[str, str, str], ...] = ()
    mask_misses: tuple[str, ...] = ()


class CanonicalState(StrictModel):
    canonicalizer: GeneratorInfo
    mask_id: str
    fingerprint: Annotated[str, Field(pattern=SHA256_PATTERN)]
    complete: bool
    windows: tuple[CanonicalWindow, ...]
    volatile: VolatileFacts
    source_observation_id: str
    source_hash: Annotated[str, Field(pattern=SHA256_PATTERN)]


def element_step(role: Role, label: str | None, stable_id: str | None) -> str:
    text = role.value
    if stable_id:
        text += f"<{stable_id}>"
    if label is not None:
        text += f"[{label}]"
    return text


def with_ordinals(keys: Iterable[str]) -> list[str]:
    seen: Counter[str] = Counter()
    out = []
    for key in keys:
        out.append(f"{key}#{seen[key]}")
        seen[key] += 1
    return out


def identity_hash(state: CanonicalState) -> str:
    """Recompute a state's fingerprint from its identity fields (detects forged states)."""
    return content_hash(
        {
            "canonicalizer": state.canonicalizer.model_dump(mode="json"),
            "mask_id": state.mask_id,
            "complete": state.complete,
            "windows": [
                w.model_dump(mode="json", exclude={"key", "ambiguous"}) for w in state.windows
            ],
        }
    )


def _normalized_value(value: TypedValue | None) -> TypedValue | None:
    if isinstance(value, NumberValue) and value.value == 0.0:
        return NumberValue(value=0.0)
    return value


@dataclass
class _Pending:
    ref: ElementRef
    rel_path: str
    structural_path: str
    role: Role
    label: str | None
    stable_id_hint: str | None
    ancestors: tuple[Role, ...]


@dataclass
class _WindowBuild:
    window: WindowObservation
    root: CanonicalNode
    pending: list[_Pending] = field(default_factory=list)


class _Builder:
    def __init__(self, mask: VolatilityMask) -> None:
        self.index = {(e.structural_path, e.field): e.sibling_signature for e in mask.entries}
        self.masked_values: list[tuple[str, str, str]] = []
        self.misses: list[str] = []
        self.complete = True

    def _masked(self, structural: str, fld: MaskedField, signature: str) -> bool:
        expected = self.index.get((structural, fld))
        if expected is None:
            return False
        if expected != signature:
            self.misses.append(f"{structural}#{fld.value}")
            return False
        return True

    def _peek_label_mask(self, structural: str, signature: str) -> bool:
        return self.index.get((structural, MaskedField.LABEL)) == signature

    def node(
        self,
        element: UIElement,
        rel_path: str,
        structural: str,
        signature: str,
        ancestors: tuple[Role, ...],
        pending: list[_Pending],
    ) -> CanonicalNode:
        label_masked = self._masked(structural, MaskedField.LABEL, signature)
        value_masked = self._masked(structural, MaskedField.VALUE, signature)
        value = _normalized_value(element.value)
        if label_masked:
            self.masked_values.append((structural, "label", canonical_json(element.label)))
        if value_masked:
            dumped = value.model_dump(mode="json") if value else None
            self.masked_values.append((structural, "value", canonical_json(dumped)))
        self.complete = self.complete and not element.truncated
        pending.append(
            _Pending(
                ref=element.ref,
                rel_path=rel_path,
                structural_path=structural,
                role=element.role,
                label=element.label,
                stable_id_hint=element.stable_id_hint,
                ancestors=ancestors,
            )
        )
        kids = element.children
        kid_signature = content_hash([child.role.value for child in kids])
        kid_structural = [f"{structural}/{s}" for s in with_ordinals(c.role.value for c in kids)]
        kid_steps = [
            element_step(
                child.role,
                None if self._peek_label_mask(sp, kid_signature) else child.label,
                child.stable_id_hint,
            )
            for child, sp in zip(kids, kid_structural, strict=True)
        ]
        kid_paths = [f"{rel_path}/{step}" for step in with_ordinals(kid_steps)]
        lineage = (*ancestors, element.role)
        children = tuple(
            self.node(child, p, sp, kid_signature, lineage, pending)
            for child, p, sp in zip(kids, kid_paths, kid_structural, strict=True)
        )
        masked = [MaskedField.LABEL] if label_masked else []
        masked += [MaskedField.VALUE] if value_masked else []
        return CanonicalNode(
            role=element.role,
            label=None if label_masked else element.label,
            value=None if value_masked else value,
            states=tuple(sorted({s for s in element.states if s is not ElementState.FOCUSED})),
            actions=tuple(sorted(set(element.actions))),
            stable_id_hint=element.stable_id_hint,
            truncated=element.truncated,
            masked=tuple(masked),
            children=children,
        )

    def window(self, window: WindowObservation) -> _WindowBuild:
        root = window.root
        structural = f"{window.info.title or ''}|{root.role.value}#0"
        label = None if self._peek_label_mask(structural, _ROOT_SIGNATURE) else root.label
        rel = f"{element_step(root.role, label, root.stable_id_hint)}#0"
        pending: list[_Pending] = []
        node = self.node(root, rel, structural, _ROOT_SIGNATURE, (Role.WINDOW,), pending)
        return _WindowBuild(window=window, root=node, pending=pending)


def _window_order(build: _WindowBuild) -> tuple[str, str]:
    info = build.window.info
    identity = [info.title, info.modal, info.minimized, build.root.model_dump(mode="json")]
    return (info.title or "", content_hash(identity))


def _build(
    obs: PlatformObservation, mask: VolatilityMask
) -> tuple[dict[ElementRef, ElementLocator], CanonicalState]:
    builder = _Builder(mask)
    built = sorted((builder.window(w) for w in obs.windows), key=_window_order)
    title_counts = Counter(b.window.info.title or "" for b in built)
    keys = with_ordinals(f"window[{b.window.info.title or ''}]" for b in built)
    locators: dict[ElementRef, ElementLocator] = {}
    windows = []
    for key, b in zip(keys, built, strict=True):
        info = b.window.info
        ambiguous = title_counts[info.title or ""] > 1
        windows.append(
            CanonicalWindow(
                key=key,
                ambiguous=ambiguous,
                title=info.title,
                modal=info.modal,
                minimized=info.minimized,
                root=b.root,
            )
        )
        for p in b.pending:
            locators[p.ref] = ElementLocator(
                window_key=key,
                window_ambiguous=ambiguous,
                path=f"{key}/{p.rel_path}",
                structural_path=p.structural_path,
                role=p.role,
                label=p.label,
                stable_id_hint=p.stable_id_hint,
                ancestor_roles=p.ancestors,
            )
    focused = locators.get(obs.focused) if obs.focused else None
    volatile = VolatileFacts(
        focused_path=focused.path if focused else None,
        window_bounds=tuple((k, b.window.info.bounds) for k, b in zip(keys, built, strict=True)),
        masked_values=tuple(sorted(builder.masked_values)),
        mask_misses=tuple(sorted(set(builder.misses))),
    )
    draft = CanonicalState(
        canonicalizer=CANONICALIZER,
        mask_id=mask.mask_id,
        fingerprint="sha256:" + "0" * 64,
        complete=builder.complete and not obs.truncation.truncated,
        windows=tuple(windows),
        volatile=volatile,
        source_observation_id=obs.observation_id,
        source_hash=model_hash(obs),
    )
    return locators, draft.model_copy(update={"fingerprint": identity_hash(draft)})


def canonicalize(obs: PlatformObservation, mask: VolatilityMask = EMPTY_MASK) -> CanonicalState:
    """Pure and deterministic: equal inputs always produce equal CanonicalStates."""
    return _build(obs, mask)[1]


def locate_all(
    obs: PlatformObservation, mask: VolatilityMask = EMPTY_MASK
) -> dict[ElementRef, ElementLocator]:
    """Locator for every element of an observation, consistent with ``canonicalize``."""
    return _build(obs, mask)[0]


def calibrate_mask(idle_observations: Sequence[PlatformObservation]) -> VolatilityMask:
    """Derive a VolatilityMask from observations taken with no action in between.

    A label/value that differs at the same window-relative structural path (with the same
    sibling role signature) across idle observations is churn the app produces by itself.
    Windows whose title is shared with another window are skipped: their elements cannot be
    aligned reliably, and over-masking would merge genuinely different states.
    """
    if len(idle_observations) < 2:
        return EMPTY_MASK
    seen: dict[tuple[str, MaskedField, str], set[str]] = {}
    for obs in idle_observations:
        titles = Counter(w.info.title or "" for w in obs.windows)
        for window in obs.windows:
            if titles[window.info.title or ""] == 1:
                _collect(window, seen)
    churn = sorted(key for key, values in seen.items() if len(values) > 1)
    entries = tuple(MaskEntry(structural_path=p, field=f, sibling_signature=s) for p, f, s in churn)
    return VolatilityMask(entries=entries)


def _collect(window: WindowObservation, seen: dict[tuple[str, MaskedField, str], set[str]]) -> None:
    root = window.root
    stack: list[tuple[UIElement, str, str]] = [
        (root, f"{window.info.title or ''}|{root.role.value}#0", _ROOT_SIGNATURE)
    ]
    while stack:
        element, structural, signature = stack.pop()
        value = _normalized_value(element.value)
        dumped = value.model_dump(mode="json") if value else None
        for fld, payload in ((MaskedField.LABEL, element.label), (MaskedField.VALUE, dumped)):
            seen.setdefault((structural, fld, signature), set()).add(canonical_json(payload))
        kid_signature = content_hash([c.role.value for c in element.children])
        ordinals = with_ordinals(c.role.value for c in element.children)
        stack.extend(
            (child, f"{structural}/{o}", kid_signature)
            for child, o in zip(element.children, ordinals, strict=True)
        )
