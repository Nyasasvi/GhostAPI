"""Canonicalizer v1: determinism, noise invariance, meaningful-change sensitivity (UNIT)."""

from __future__ import annotations

from dataclasses import replace

import pytest

from ghost.observation.canonical import (
    MaskedField,
    MaskEntry,
    VolatilityMask,
    calibrate_mask,
    canonicalize,
    locate_all,
)
from ghost.platform.types import (
    ActionKind,
    BoolValue,
    ElementState,
    PlatformObservation,
    Rect,
    Role,
    StringValue,
)
from tests.support.obs import E, W, build, canon

INV = (ActionKind.INVOKE,)


def ui(
    rows: tuple[str, ...] = ("Alpha", "Beta"),
    field_value: str = "",
    clock: str = "10:00",
    check: bool = False,
) -> list[W]:
    toolbar = E(
        Role.TOOLBAR,
        kids=(
            E(Role.BUTTON, "Add", actions=INV, bounds=Rect(x=1, y=1, w=10, h=10)),
            E(Role.BUTTON, "Remove", actions=INV),
        ),
    )
    form = E(
        Role.GROUP,
        kids=(
            E(
                Role.TEXT_FIELD,
                "Title",
                value=StringValue(value=field_value),
                states=(ElementState.EDITABLE,),
                actions=(ActionKind.SET_VALUE,),
            ),
            E(Role.CHECKBOX, "Pinned", value=BoolValue(value=check), actions=INV),
            E(Role.STATIC_TEXT, clock),
        ),
    )
    listing = E(Role.LIST, kids=tuple(E(Role.ROW, r, actions=INV) for r in rows))
    root = E(Role.GROUP, kids=(toolbar, form, listing))
    return [W("Items", root, bounds=Rect(x=0, y=0, w=500, h=400))]


def test_is_deterministic_and_round_trip_stable() -> None:
    obs = build(ui())
    again = PlatformObservation.model_validate_json(obs.model_dump_json())
    assert canonicalize(obs) == canonicalize(again)
    assert canonicalize(obs).fingerprint == canon(ui()).fingerprint


def test_handles_ids_generation_geometry_and_focus_are_noise() -> None:
    base = canon(ui()).fingerprint
    moved = ui()
    moved[0] = replace(moved[0], bounds=Rect(x=300, y=90, w=640, h=480), focused=True)
    assert canon(moved, generation=17, observation_id="obs_99").fingerprint == base
    focused = ui()
    form = focused[0].root.kids[1]
    title = replace(form.kids[0], focused=True)
    focused[0] = replace(
        focused[0],
        root=replace(
            focused[0].root,
            kids=(
                focused[0].root.kids[0],
                replace(form, kids=(title, *form.kids[1:])),
                focused[0].root.kids[2],
            ),
        ),
    )
    state = canon(focused)
    assert state.fingerprint == base
    assert state.volatile.focused_path is not None
    assert "text_field[Title]" in state.volatile.focused_path


@pytest.mark.parametrize("seed", range(25))
def test_window_and_set_order_never_changes_identity(seed: int) -> None:
    windows = [*ui(), W("Inspector", E(Role.GROUP, kids=(E(Role.BUTTON, "Close", actions=INV),)))]
    windows[0] = replace(
        windows[0],
        root=replace(
            windows[0].root,
            kids=(
                *windows[0].root.kids,
                E(
                    Role.ROW,
                    "multi",
                    states=(ElementState.SELECTED, ElementState.EXPANDED, ElementState.CHECKED),
                    actions=(ActionKind.INVOKE, ActionKind.SET_VALUE),
                ),
            ),
        ),
    )
    assert canon(windows, shuffle_seed=seed).fingerprint == canon(windows).fingerprint


@pytest.mark.parametrize(
    "changed",
    [
        ui(rows=("Alpha", "Beta", "Gamma")),  # element added
        ui(rows=("Alpha",)),  # element removed
        ui(rows=("Beta", "Alpha")),  # meaningful order (rule R3)
        ui(field_value="probe"),  # value
        ui(check=True),  # checked setting
        ui(rows=("Alpha", "Beta-renamed")),  # label
        ui(clock="10:01"),  # unmasked text is identity
    ],
)
def test_meaningful_changes_change_identity(changed: list[W]) -> None:
    assert canon(changed).fingerprint != canon(ui()).fingerprint


def test_states_actions_modal_and_truncation_are_identity() -> None:
    base = canon(ui()).fingerprint
    disabled = ui()
    toolbar = disabled[0].root.kids[0]
    add_off = replace(toolbar.kids[0], states=(ElementState.DISABLED,), actions=())
    disabled[0] = replace(
        disabled[0],
        root=replace(
            disabled[0].root,
            kids=(replace(toolbar, kids=(add_off, toolbar.kids[1])), *disabled[0].root.kids[1:]),
        ),
    )
    assert canon(disabled).fingerprint != base
    assert canon([replace(ui()[0], modal=True)]).fingerprint != base
    partial = ui()
    listing = replace(partial[0].root.kids[2], truncated=True)
    partial[0] = replace(
        partial[0], root=replace(partial[0].root, kids=(*partial[0].root.kids[:2], listing))
    )
    state = canon(partial)
    assert not state.complete  # unknown stays unknown (rule R6)
    assert state.fingerprint != base


def test_duplicate_siblings_get_ordinals_and_paths_survive_reobservation() -> None:
    first = build(ui(rows=("Dup", "Dup")), generation=1)
    second = build(ui(rows=("Dup", "Dup")), generation=2)
    paths1 = sorted(loc.path for loc in locate_all(first).values())
    paths2 = sorted(loc.path for loc in locate_all(second).values())
    assert paths1 == paths2
    assert any(p.endswith("row[Dup]#1") for p in paths1)


def test_idle_calibration_masks_churn_and_only_churn() -> None:
    idle = [build(ui(clock=t), observation_id=f"obs_{i}") for i, t in enumerate(["1", "2", "3"])]
    mask = calibrate_mask(idle)
    assert len(mask.entries) == 1
    (entry,) = mask.entries
    assert entry.field is MaskedField.LABEL
    assert entry.structural_path.endswith("static_text#0")
    assert entry.structural_path.startswith("Items|")  # window-relative, not ordinal-based
    masked_a = canonicalize(build(ui(clock="09:59")), mask)
    masked_b = canonicalize(build(ui(clock="23:12")), mask)
    assert masked_a.fingerprint == masked_b.fingerprint
    assert masked_a.volatile.masked_values != masked_b.volatile.masked_values
    assert canonicalize(build(ui(field_value="x")), mask).fingerprint != masked_a.fingerprint


def test_mask_identity_is_part_of_the_fingerprint() -> None:
    obs = build(ui())
    other = VolatilityMask(
        entries=(
            MaskEntry(structural_path="nowhere", field=MaskedField.VALUE, sibling_signature="s"),
        )
    )
    assert canonicalize(obs).fingerprint != canonicalize(obs, other).fingerprint


def test_single_idle_observation_gives_empty_mask() -> None:
    assert calibrate_mask([build(ui())]).entries == ()
