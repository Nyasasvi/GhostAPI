"""Observable postconditions: a small neutral language evaluated on PlatformObservations.

Clauses are behavioural (what is observable), never semantic (what it means). ``absent``
over a truncated observation is UNKNOWN, not true: unknown is not absent.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Annotated, Literal

from pydantic import Field

from ghost._model import StrictModel
from ghost.platform.types import PlatformObservation, Role, StringValue, UIElement


class ProbeRef(StrictModel):
    """Refers to the trial's generated probe value for one parameter."""

    probe: Annotated[str, Field(pattern=r"^[a-z][a-z0-9_]{0,63}$")]


Text = str | ProbeRef


class ElementMatch(StrictModel):
    role: Role | None = None
    label: Text | None = None
    label_contains: Text | None = None
    window_title: str | None = None


class Exists(StrictModel):
    kind: Literal["exists"] = "exists"
    match: ElementMatch


class Absent(StrictModel):
    kind: Literal["absent"] = "absent"
    match: ElementMatch


class ValueIs(StrictModel):
    kind: Literal["value_is"] = "value_is"
    match: ElementMatch
    value: Text


Clause = Annotated[Exists | Absent | ValueIs, Field(discriminator="kind")]


class Postcondition(StrictModel):
    all_of: Annotated[tuple[Clause, ...], Field(min_length=1)]
    after_relaunch: bool = False

    def probes_referenced(self) -> set[str]:
        names: set[str] = set()
        for clause in self.all_of:
            texts: list[Text | None] = [clause.match.label, clause.match.label_contains]
            if isinstance(clause, ValueIs):
                texts.append(clause.value)
            names.update(t.probe for t in texts if isinstance(t, ProbeRef))
        return names


def _resolve(text: Text | None, probes: Mapping[str, str]) -> str | None:
    if isinstance(text, ProbeRef):
        if text.probe not in probes:
            raise KeyError(f"postcondition references unknown probe {text.probe!r}")
        return probes[text.probe]
    return text


def _matches(
    element: UIElement, window_title: str | None, m: ElementMatch, probes: Mapping[str, str]
) -> bool:
    if m.role is not None and element.role is not m.role:
        return False
    if m.window_title is not None and window_title != m.window_title:
        return False
    label = _resolve(m.label, probes)
    if label is not None and element.label != label:
        return False
    contains = _resolve(m.label_contains, probes)
    return contains is None or (element.label is not None and contains in element.label)


def _found(obs: PlatformObservation, m: ElementMatch, probes: Mapping[str, str]) -> list[UIElement]:
    return [e for w, e, _ in obs.walk() if _matches(e, w.info.title, m, probes)]


def evaluate_clause(
    clause: Clause, obs: PlatformObservation, probes: Mapping[str, str]
) -> bool | None:
    """True / False, or None when the observation cannot decide (truncated content)."""
    found = _found(obs, clause.match, probes)
    if isinstance(clause, Exists):
        return True if found else (None if obs.truncation.truncated else False)
    if isinstance(clause, Absent):
        return False if found else (None if obs.truncation.truncated else True)
    expected = _resolve(clause.value, probes)
    if any(isinstance(e.value, StringValue) and e.value.value == expected for e in found):
        return True
    return None if obs.truncation.truncated and not found else False


def evaluate(
    post: Postcondition, obs: PlatformObservation, probes: Mapping[str, str]
) -> tuple[bool | None, tuple[bool | None, ...]]:
    results = tuple(evaluate_clause(c, obs, probes) for c in post.all_of)
    if any(r is False for r in results):
        return False, results
    if any(r is None for r in results):
        return None, results
    return True, results
