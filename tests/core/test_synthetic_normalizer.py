"""The synthetic platform normalizer: raw capture -> PlatformObservation (UNIT evidence)."""

from __future__ import annotations

from typing import Any

import pytest

from ghost.platform.simulated import NormalizationError, normalize_synthetic
from ghost.platform.types import (
    ActionKind,
    ApplicationRef,
    ElementState,
    Role,
    StringValue,
    TruncationReason,
)

APP = ApplicationRef(ref="app_1")
SHA = "sha256:" + "c" * 64


def doc(*kids: dict[str, Any], focus: str | None = None) -> dict[str, Any]:
    return {
        "format": "synthetic-raw/1",
        "windows": [
            {"wid": "w", "title": "T", "root": {"id": "r", "kind": "panel", "kids": list(kids)}}
        ],
        "focus": focus,
        "noise": {"blink": 3},
    }


def norm(document: dict[str, Any], **limits: int) -> Any:
    return normalize_synthetic(
        document,
        application=APP,
        generation=4,
        observation_id="obs_9",
        raw_capture_id=SHA,
        max_depth=limits.get("max_depth", 40),
        max_nodes=limits.get("max_nodes", 5000),
    )


def test_maps_vocabulary_to_neutral_types() -> None:
    obs, handles = norm(
        doc(
            {
                "id": "f",
                "kind": "text_input",
                "text": "Title",
                "content": {"type": "string", "value": "v"},
                "flags": ["focused", "editable", "sparkly"],
                "acts": ["assign", "teleport"],
                "uid": "title-field",
            },
            {"id": "x", "kind": "hologram"},
            focus="f",
        )
    )
    field = obs.windows[0].root.children[0]
    assert field.role is Role.TEXT_FIELD
    assert field.value == StringValue(value="v")
    assert field.states == (ElementState.EDITABLE, ElementState.FOCUSED)
    assert field.actions == (ActionKind.SET_VALUE,)  # unknown verbs are not exposed
    assert field.stable_id_hint == "title-field"
    assert obs.windows[0].root.children[1].role is Role.UNKNOWN  # kept, never dropped
    assert obs.focused == field.ref
    assert handles == {0: "r", 1: "f", 2: "x"}
    assert field.ref.generation == 4


def test_is_deterministic() -> None:
    document = doc({"id": "a", "kind": "label", "text": "x"})
    assert norm(document)[0] == norm(document)[0]


def test_depth_and_node_limits_mark_unknown_not_absent() -> None:
    nested = {"id": "a", "kind": "panel", "kids": [{"id": "b", "kind": "label"}]}
    obs, _ = norm(doc(nested), max_depth=1)
    assert obs.windows[0].root.children[0].truncated
    assert obs.truncation.reasons == (TruncationReason.MAX_DEPTH,)
    many = [{"id": f"n{i}", "kind": "label"} for i in range(10)]
    obs, handles = norm(doc(*many), max_nodes=4)
    assert len(handles) == 4
    assert TruncationReason.MAX_NODES in obs.truncation.reasons


def test_partial_raw_nodes_are_virtualized() -> None:
    obs, _ = norm(doc({"id": "l", "kind": "list_view", "partial": True}))
    assert obs.windows[0].root.children[0].truncated
    assert obs.truncation.reasons == (TruncationReason.VIRTUALIZED,)


@pytest.mark.parametrize(
    "document",
    [
        {"format": "synthetic-raw/1", "windows": "nope"},
        {"format": "other/9", "windows": []},
        doc({"id": "a", "kind": "label", "content": {"type": "bool", "value": "yes"}}),
        doc({"id": "a", "kind": "label"}, {"id": "a", "kind": "label"}),
        doc({"id": "a", "kind": "label"}, focus="missing"),
        doc({"id": "a", "kind": "label", "frame": [1.0, 2.0]}),
    ],
)
def test_malformed_raw_capture_is_rejected(document: dict[str, Any]) -> None:
    with pytest.raises(NormalizationError):
        norm(document)
