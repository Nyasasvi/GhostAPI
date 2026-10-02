"""Structured state diff: observations only, explicit about positional ambiguity (UNIT)."""

from __future__ import annotations

from dataclasses import replace

import pytest

from ghost.observation.canonical import MaskedField, VolatilityMask, canonicalize
from ghost.observation.diff import ChangeKind, diff_states
from ghost.platform.types import ActionKind, ElementState, Role, StringValue
from tests.support.obs import E, W, build, canon

INV = (ActionKind.INVOKE,)


def window(rows: tuple[str, ...] = ("Alpha",), value: str = "", add_enabled: bool = True) -> W:
    add = E(
        Role.BUTTON,
        "Add",
        actions=INV if add_enabled else (),
        states=() if add_enabled else (ElementState.DISABLED,),
    )
    field = E(
        Role.TEXT_FIELD, "Title", value=StringValue(value=value), actions=(ActionKind.SET_VALUE,)
    )
    listing = E(Role.LIST, kids=tuple(E(Role.ROW, r) for r in rows))
    return W("Items", E(Role.GROUP, kids=(add, field, listing)))


def test_identical_states_have_no_changes() -> None:
    d = diff_states(canon([window()]), canon([window()], generation=5))
    assert d.same_identity
    assert d.changes == ()


def test_added_and_removed_elements() -> None:
    added = diff_states(canon([window()]), canon([window(rows=("Alpha", "Beta"))]))
    (change,) = added.changes
    assert change.kind is ChangeKind.ELEMENT_ADDED
    assert change.path.endswith("list#0/row[Beta]#0")
    assert change.role is Role.ROW
    removed = diff_states(canon([window(rows=("Alpha", "Beta"))]), canon([window()]))
    assert [c.kind for c in removed.changes] == [ChangeKind.ELEMENT_REMOVED]


def test_value_change_reports_before_and_after() -> None:
    d = diff_states(canon([window()]), canon([window(value="probe-7")]))
    (change,) = d.of_kind(ChangeKind.VALUE_CHANGED)
    assert '"probe-7"' in (change.after or "")
    assert '""' in (change.before or "")


def test_label_change_is_marked_positional_not_interpreted() -> None:
    d = diff_states(canon([window(rows=("Alpha",))]), canon([window(rows=("Omega",))]))
    (change,) = d.changes
    assert change.kind is ChangeKind.LABEL_CHANGED
    assert change.match == "positional"  # could equally be remove + add; not decided here


def test_action_availability_and_state_changes() -> None:
    d = diff_states(canon([window()]), canon([window(add_enabled=False)]))
    kinds = {c.kind for c in d.changes}
    assert kinds == {ChangeKind.ACTIONS_CHANGED, ChangeKind.STATES_CHANGED}


def test_focus_only_change_is_volatile() -> None:
    plain = window()
    focused_field = replace(plain.root.kids[1], focused=True)
    focused = replace(
        plain,
        root=replace(plain.root, kids=(plain.root.kids[0], focused_field, plain.root.kids[2])),
    )
    d = diff_states(canon([plain]), canon([focused]))
    assert d.same_identity
    (change,) = d.changes
    assert change.kind is ChangeKind.FOCUS_CHANGED
    assert not change.affects_identity


def test_window_added_and_diff_is_deterministic() -> None:
    dialog = W("Confirm", E(Role.DIALOG, kids=(E(Role.BUTTON, "OK", actions=INV),)), modal=True)
    a, b = canon([window()]), canon([window(), dialog])
    d1, d2 = diff_states(a, b), diff_states(a, b)
    assert d1 == d2
    assert [c.kind for c in d1.changes] == [ChangeKind.WINDOW_ADDED]


def test_states_from_different_masks_cannot_be_diffed() -> None:
    obs = build([window()])
    other = canonicalize(obs, VolatilityMask(entries=(("x", MaskedField.VALUE),)))
    with pytest.raises(ValueError, match="different canonicalizers or masks"):
        diff_states(canonicalize(obs), other)
