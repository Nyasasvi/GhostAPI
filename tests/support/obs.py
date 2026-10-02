"""Compact builders for PlatformObservations used by unit tests."""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from ghost.observation.canonical import CanonicalState, canonicalize
from ghost.platform.types import (
    ActionKind,
    ApplicationRef,
    ElementRef,
    ElementState,
    GeneratorInfo,
    PlatformObservation,
    Rect,
    Role,
    TypedValue,
    UIElement,
    WindowInfo,
    WindowObservation,
    WindowRef,
)

APP = ApplicationRef(ref="app_1")
SHA = "sha256:" + "d" * 64


@dataclass(frozen=True)
class E:
    role: Role
    label: str | None = None
    kids: tuple[E, ...] = ()
    value: TypedValue | None = None
    states: tuple[ElementState, ...] = ()
    actions: tuple[ActionKind, ...] = ()
    sid: str | None = None
    truncated: bool = False
    bounds: Rect | None = None
    focused: bool = False


@dataclass(frozen=True)
class W:
    title: str | None
    root: E
    modal: bool = False
    bounds: Rect | None = None
    focused: bool = False


@dataclass
class _Numbering:
    generation: int
    next_index: int = 0
    focus: ElementRef | None = None
    rng: random.Random | None = None
    order: list[int] = field(default_factory=list)


def _element(spec: E, numbering: _Numbering) -> UIElement:
    ref = ElementRef(application=APP, generation=numbering.generation, index=numbering.next_index)
    numbering.next_index += 1
    if spec.focused:
        numbering.focus = ref
    states = list(spec.states)
    actions = list(spec.actions)
    if numbering.rng is not None:
        numbering.rng.shuffle(states)
        numbering.rng.shuffle(actions)
    return UIElement(
        ref=ref,
        role=spec.role,
        label=spec.label,
        value=spec.value,
        states=tuple(states),
        actions=tuple(actions),
        bounds=spec.bounds,
        stable_id_hint=spec.sid,
        children=tuple(_element(kid, numbering) for kid in spec.kids),
        truncated=spec.truncated,
    )


def build(
    windows: list[W],
    *,
    generation: int = 0,
    observation_id: str = "obs_1",
    shuffle_seed: int | None = None,
) -> PlatformObservation:
    """Build an observation. ``shuffle_seed`` permutes window order and set orderings only."""
    numbering = _Numbering(generation=generation)
    ordered = list(windows)
    if shuffle_seed is not None:
        numbering.rng = random.Random(shuffle_seed)
        numbering.rng.shuffle(ordered)
    observed = tuple(
        WindowObservation(
            info=WindowInfo(
                ref=WindowRef(ref=f"win_{i}"),
                title=w.title,
                modal=w.modal,
                bounds=w.bounds,
                focused=w.focused,
            ),
            root=_element(w.root, numbering),
        )
        for i, w in enumerate(ordered)
    )
    return PlatformObservation(
        observation_id=observation_id,
        raw_capture_id=SHA,
        application=APP,
        generation=generation,
        platform="synthetic",
        normalizer=GeneratorInfo(name="test", version="1"),
        windows=observed,
        focused=numbering.focus,
    )


def canon(
    windows: list[W],
    *,
    generation: int = 0,
    observation_id: str = "obs_1",
    shuffle_seed: int | None = None,
) -> CanonicalState:
    return canonicalize(
        build(
            windows,
            generation=generation,
            observation_id=observation_id,
            shuffle_seed=shuffle_seed,
        )
    )
