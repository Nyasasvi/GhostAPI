"""PlatformObservation -> CanonicalState: deterministic, versioned canonicalization.

Canonicalizer v1 rules (each covered by tests):

R1  Excluded from state identity, kept as volatile facts: element handles and generations,
    observation ids and timestamps, all geometry (element and window bounds), keyboard focus,
    window focused/main flags.
R2  Order-insensitive: windows (sorted by title, then content hash), element states and
    action sets (sorted). Raw attribute order never matters.
R3  Child order is preserved (presentation order may be meaningful, e.g. list rows).
R4  Included in identity: role, label, value, states except ``focused``, actions,
    stable_id_hint, truncation flag, window title / modal / minimized.
R5  A field is masked (removed from identity, recorded as volatile) only when the explicit
    VolatilityMask says so. Masks are derived from evidence (idle re-observation), never
    from app knowledge, and the mask id is part of the fingerprint.
R6  Truncated (unobservable) content stays unknown: ``complete=False`` when anything was
    truncated; nothing is invented to fill it.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Sequence
from enum import StrEnum
from typing import Annotated

from pydantic import Field

from ghost._model import SHA256_PATTERN, StrictModel, canonical_json, content_hash, model_hash
from ghost.platform.types import (
    ActionKind,
    ElementRef,
    ElementState,
    GeneratorInfo,
    PlatformObservation,
    Rect,
    Role,
    TypedValue,
    UIElement,
    WindowObservation,
)

CANONICALIZER = GeneratorInfo(name="canonicalizer", version="1")


class MaskedField(StrEnum):
    LABEL = "label"
    VALUE = "value"


class VolatilityMask(StrictModel):
    """(structural path, field) pairs excluded from identity because evidence showed churn."""

    entries: tuple[tuple[str, MaskedField], ...] = ()

    @property
    def mask_id(self) -> str:
        return content_hash([[path, field.value] for path, field in self.entries])

    def masks(self, structural_path: str, field: MaskedField) -> bool:
        return (structural_path, field) in self.entries


EMPTY_MASK = VolatilityMask()


class ElementLocator(StrictModel):
    """Neutral, persistable description of where an element was observed.

    Unlike ``ElementRef`` it survives re-observation, so transitions and bindings use it.
    It is evidence about one UI layout, not entity identity.
    """

    window_key: str
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
    title: str | None
    modal: bool
    minimized: bool
    root: CanonicalNode


class VolatileFacts(StrictModel):
    """Observed facts deliberately excluded from identity (rules R1 and R5)."""

    focused_path: str | None = None
    window_bounds: tuple[tuple[str, Rect | None], ...] = ()
    masked_values: tuple[tuple[str, str, str], ...] = ()


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


def _sorted_windows(obs: PlatformObservation) -> list[tuple[str, WindowObservation]]:
    """Windows ordered by title, then content (rule R2), keyed with per-title ordinals."""

    def content(window: WindowObservation) -> str:
        return content_hash(_identity_json(window.root))

    ordered = sorted(obs.windows, key=lambda w: (w.info.title or "", content(w)))
    keys = with_ordinals(f"window[{w.info.title or ''}]" for w in ordered)
    return list(zip(keys, ordered, strict=True))


def _identity_json(element: UIElement) -> object:
    """Order key for windows: identity fields only, so handles/geometry never reorder them."""
    return {
        "r": element.role.value,
        "l": element.label,
        "v": element.value.model_dump(mode="json") if element.value else None,
        "c": [_identity_json(c) for c in element.children],
    }


class _Builder:
    def __init__(self, mask: VolatilityMask) -> None:
        self.mask = mask
        self.locators: dict[ElementRef, ElementLocator] = {}
        self.masked_values: list[tuple[str, str, str]] = []
        self.complete = True

    def label_of(self, element: UIElement, structural: str) -> str | None:
        return None if self.mask.masks(structural, MaskedField.LABEL) else element.label

    def node(
        self,
        element: UIElement,
        window_key: str,
        path: str,
        structural: str,
        ancestors: tuple[Role, ...],
    ) -> CanonicalNode:
        label_masked = self.mask.masks(structural, MaskedField.LABEL)
        value_masked = self.mask.masks(structural, MaskedField.VALUE)
        if label_masked:
            self.masked_values.append((structural, "label", canonical_json(element.label)))
        if value_masked:
            dumped = element.value.model_dump(mode="json") if element.value else None
            self.masked_values.append((structural, "value", canonical_json(dumped)))
        self.complete = self.complete and not element.truncated
        self.locators[element.ref] = ElementLocator(
            window_key=window_key,
            path=path,
            structural_path=structural,
            role=element.role,
            label=element.label,
            stable_id_hint=element.stable_id_hint,
            ancestor_roles=ancestors,
        )
        kids = element.children
        kid_structural = [
            f"{structural}/{s}" for s in with_ordinals(child.role.value for child in kids)
        ]
        kid_steps = [
            element_step(child.role, self.label_of(child, sp), child.stable_id_hint)
            for child, sp in zip(kids, kid_structural, strict=True)
        ]
        kid_paths = [f"{path}/{step}" for step in with_ordinals(kid_steps)]
        lineage = (*ancestors, element.role)
        children = tuple(
            self.node(child, window_key, p, sp, lineage)
            for child, p, sp in zip(kids, kid_paths, kid_structural, strict=True)
        )
        masked = [MaskedField.LABEL] if label_masked else []
        masked += [MaskedField.VALUE] if value_masked else []
        return CanonicalNode(
            role=element.role,
            label=None if label_masked else element.label,
            value=None if value_masked else element.value,
            states=tuple(sorted({s for s in element.states if s is not ElementState.FOCUSED})),
            actions=tuple(sorted(set(element.actions))),
            stable_id_hint=element.stable_id_hint,
            truncated=element.truncated,
            masked=tuple(masked),
            children=children,
        )

    def window(self, key: str, window: WindowObservation) -> CanonicalWindow:
        root = window.root
        structural = f"{key}/{root.role.value}#0"
        step = element_step(root.role, self.label_of(root, structural), root.stable_id_hint)
        path = f"{key}/{step}#0"
        return CanonicalWindow(
            key=key,
            title=window.info.title,
            modal=window.info.modal,
            minimized=window.info.minimized,
            root=self.node(root, key, path, structural, (Role.WINDOW,)),
        )


def _build(obs: PlatformObservation, mask: VolatilityMask) -> tuple[_Builder, CanonicalState]:
    builder = _Builder(mask)
    keyed = _sorted_windows(obs)
    windows = tuple(builder.window(key, window) for key, window in keyed)
    complete = builder.complete and not obs.truncation.truncated
    identity = {
        "canonicalizer": CANONICALIZER.model_dump(mode="json"),
        "mask_id": mask.mask_id,
        "complete": complete,
        "windows": [w.model_dump(mode="json") for w in windows],
    }
    focused = builder.locators.get(obs.focused) if obs.focused else None
    volatile = VolatileFacts(
        focused_path=focused.path if focused else None,
        window_bounds=tuple((key, window.info.bounds) for key, window in keyed),
        masked_values=tuple(sorted(builder.masked_values)),
    )
    state = CanonicalState(
        canonicalizer=CANONICALIZER,
        mask_id=mask.mask_id,
        fingerprint=content_hash(identity),
        complete=complete,
        windows=windows,
        volatile=volatile,
        source_observation_id=obs.observation_id,
        source_hash=model_hash(obs),
    )
    return builder, state


def canonicalize(obs: PlatformObservation, mask: VolatilityMask = EMPTY_MASK) -> CanonicalState:
    """Pure and deterministic: equal inputs always produce equal CanonicalStates."""
    return _build(obs, mask)[1]


def locate_all(
    obs: PlatformObservation, mask: VolatilityMask = EMPTY_MASK
) -> dict[ElementRef, ElementLocator]:
    """Locator for every element of an observation, consistent with ``canonicalize``."""
    return _build(obs, mask)[0].locators


def calibrate_mask(idle_observations: Sequence[PlatformObservation]) -> VolatilityMask:
    """Derive a VolatilityMask from observations taken with no action in between.

    Any label/value that differs at the same structural path across idle observations is
    churn the app produces by itself (clocks, counters, animations). The mask is evidence-
    derived and recorded; it never encodes knowledge about a specific app.
    """
    if len(idle_observations) < 2:
        return EMPTY_MASK
    seen: dict[tuple[str, MaskedField], set[str]] = {}
    for obs in idle_observations:
        builder, _ = _build(obs, EMPTY_MASK)
        by_ref = {e.ref: e for _, e, _ in obs.walk()}
        for ref, locator in builder.locators.items():
            element = by_ref[ref]
            value = element.value.model_dump(mode="json") if element.value else None
            for field, payload in ((MaskedField.LABEL, element.label), (MaskedField.VALUE, value)):
                key = (locator.structural_path, field)
                seen.setdefault(key, set()).add(canonical_json(payload))
    churn = sorted(key for key, values in seen.items() if len(values) > 1)
    return VolatilityMask(entries=tuple(churn))
