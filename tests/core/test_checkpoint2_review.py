"""Regression tests for the Checkpoint 2 independent review findings (UNIT)."""

from __future__ import annotations

import time
from dataclasses import replace

import pytest
from pydantic import ValidationError

from ghost.exploration.graph import StateGraph
from ghost.observation.canonical import (
    CANONICALIZER,
    calibrate_mask,
    canonicalize,
    locate_all,
)
from ghost.observation.diff import ChangeKind, diff_states
from ghost.platform.types import ActionKind, ElementState, NumberValue, Role, StringValue
from tests.support.obs import E, W, build, canon

INV = (ActionKind.INVOKE,)


def doc(rows: tuple[str, ...], disabled: bool = False, clock: str | None = None) -> W:
    button = E(Role.BUTTON, "Save", actions=() if disabled else INV,
               states=(ElementState.DISABLED,) if disabled else ())  # fmt: skip
    kids = [button, E(Role.LIST, kids=tuple(E(Role.ROW, r) for r in rows))]
    if clock is not None:
        kids.append(E(Role.STATIC_TEXT, clock))
    return W("Doc", E(Role.GROUP, kids=tuple(kids)))


def test_1_same_title_windows_are_order_invariant_even_when_only_states_differ() -> None:
    a, b = doc(("x",)), doc(("x",), disabled=True)
    assert canon([a, b]).fingerprint == canon([b, a]).fingerprint


def test_1_calibration_never_masks_same_title_windows() -> None:
    idle = [
        build([doc(("a", "b"), clock=t), doc(("Invoice 1", "Invoice 2"), clock=u)])
        for t, u in (("1", "9"), ("2", "8"), ("3", "7"))
    ]
    mask = calibrate_mask(idle)
    assert mask.entries == ()
    one = canonicalize(build([doc(("a", "b"), clock="1"), doc(("q",), clock="2")]), mask)
    two = canonicalize(
        build([doc(("Invoice 1", "Invoice 2"), clock="1"), doc(("q",), clock="2")]), mask
    )
    assert one.fingerprint != two.fingerprint


def test_2_same_title_windows_are_flagged_ambiguous_and_never_matched_as_certain() -> None:
    before = build([doc(("a",)), doc(("b",))])
    edited = build([doc(("a", "typed")), doc(("b",))])
    assert all(loc.window_ambiguous for loc in locate_all(before).values())
    changes = diff_states(canonicalize(before), canonicalize(edited)).changes
    assert changes
    assert all(c.match != "key" for c in changes)


def test_3_stale_mask_entries_are_not_applied_to_a_different_element() -> None:
    def view(texts: tuple[str, ...]) -> W:
        return W("Main", E(Role.GROUP, kids=tuple(E(Role.STATIC_TEXT, t) for t in texts)))

    mask = calibrate_mask([build([view((t,))]) for t in ("10:00", "10:01")])
    assert len(mask.entries) == 1
    disk_full = canonicalize(build([view(("Error: disk full", "10:02"))]), mask)
    saved = canonicalize(build([view(("Saved successfully", "10:02"))]), mask)
    assert disk_full.fingerprint != saved.fingerprint
    assert disk_full.volatile.mask_misses


def test_4_truncated_content_is_unobserved_not_removed() -> None:
    full = W("Main", E(Role.LIST, kids=tuple(E(Role.ROW, r) for r in ("a", "b", "c"))))
    cut = W("Main", E(Role.LIST, kids=(E(Role.ROW, "a"),), truncated=True))
    d = diff_states(canon([full]), canon([cut]))
    kinds = {c.kind for c in d.changes}
    assert ChangeKind.ELEMENT_REMOVED not in kinds
    assert len(d.of_kind(ChangeKind.ELEMENT_UNOBSERVED)) == 2
    assert d.of_kind(ChangeKind.COMPLETENESS_CHANGED)


def test_5_window_title_change_keeps_inner_detail() -> None:
    def win(title: str, value: str) -> W:
        field = E(Role.TEXT_FIELD, "Body", value=StringValue(value=value))
        return W(title, E(Role.GROUP, kids=(field,)))

    d = diff_states(canon([win("Doc", "")]), canon([win("Doc - Edited", "hello")]))
    kinds = {c.kind for c in d.changes}
    assert kinds == {ChangeKind.WINDOW_CHANGED, ChangeKind.VALUE_CHANGED}
    assert all(c.match == "positional" for c in d.changes)


def test_6_duplicate_label_matches_are_marked_ordinal() -> None:
    def rows(values: tuple[float, ...]) -> W:
        kids = tuple(E(Role.ROW, "Dup", value=NumberValue(value=v)) for v in values)
        return W("Main", E(Role.LIST, kids=kids))

    d = diff_states(canon([rows((1.0, 2.0))]), canon([rows((2.0,))]))
    assert {c.match for c in d.changes} <= {"ordinal", "none"}
    assert d.of_kind(ChangeKind.VALUE_CHANGED)[0].match == "ordinal"


def test_7_large_flat_lists_diff_in_linear_time() -> None:
    big = W("Main", E(Role.LIST, kids=tuple(E(Role.ROW, f"r{i}") for i in range(4000))))
    a, b = canon([big]), canon([big], generation=2)
    started = time.perf_counter()
    diff_states(a, b)
    assert time.perf_counter() - started < 1.5


def test_8_same_observation_is_never_counted_twice() -> None:
    state = canon([doc(("a",))])
    graph = StateGraph(CANONICALIZER, state.mask_id)
    graph.add_state(state, "obs_1")
    graph.add_state(state, "obs_1")
    assert graph.visit_count(state.fingerprint) == 1


def test_9_snapshots_keep_unvisited_states_order_and_reject_forgeries() -> None:
    s0, s1 = canon([doc(("a",))]), canon([doc(("b",))])
    graph = StateGraph(CANONICALIZER, s0.mask_id)
    graph.add_state(s1, "obs_1")
    graph.add_state(s0, None)
    again = StateGraph.from_snapshot(graph.snapshot())
    assert again.fingerprints == graph.fingerprints
    assert again.visit_count(s0.fingerprint) == 0
    forged = s0.model_copy(update={"fingerprint": s1.fingerprint})
    with pytest.raises(ValueError, match="fingerprint"):
        StateGraph(CANONICALIZER, s0.mask_id).add_state(forged, "obs_x")


def test_10_non_finite_numbers_are_rejected_and_negative_zero_is_zero() -> None:
    with pytest.raises(ValidationError):
        NumberValue.model_validate_json('{"type":"number","value":NaN}')

    def gauge(v: float) -> W:
        return W("Main", E(Role.SLIDER, "Level", value=NumberValue(value=v)))

    assert canon([gauge(-0.0)]).fingerprint == canon([gauge(0.0)]).fingerprint


def test_11_removed_children_under_positional_parent_use_the_old_path() -> None:
    before = W("Main", E(Role.GROUP, "Old", kids=(E(Role.BUTTON, "Gone", actions=INV),)))
    after = replace(before, root=replace(before.root, label="New", kids=()))
    d = diff_states(canon([before]), canon([after]))
    (removed,) = d.of_kind(ChangeKind.ELEMENT_REMOVED)
    assert "group[Old]" in removed.path
