"""Strict typing and validation rules of the platform-neutral DTOs (UNIT evidence)."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from ghost.platform.types import (
    ActionKind,
    ApplicationRef,
    ElementRef,
    ElementState,
    EnvironmentKind,
    GeneratorInfo,
    Health,
    ObservationBundle,
    PermissionState,
    PlatformObservation,
    PrimitiveAction,
    RawArtifactRef,
    RawObservation,
    Readiness,
    Role,
    StringValue,
    Truncation,
    TruncationReason,
    UIElement,
    WindowInfo,
    WindowObservation,
    WindowRef,
)

APP = ApplicationRef(ref="app_1")
SHA = "sha256:" + "a" * 64


def ref(index: int = 0, generation: int = 0) -> ElementRef:
    return ElementRef(application=APP, generation=generation, index=index)


def test_refs_reject_malformed_and_coerced_values() -> None:
    with pytest.raises(ValidationError):
        ApplicationRef(ref="com.example.app")  # opaque refs only
    with pytest.raises(ValidationError):
        ElementRef(application=APP, generation=-1, index=0)
    with pytest.raises(ValidationError):
        ElementRef.model_validate({"application": {"ref": "app_1"}, "generation": "1", "index": 0})


def test_unknown_fields_are_rejected() -> None:
    with pytest.raises(ValidationError):
        WindowRef.model_validate({"ref": "win_a", "native_id": 42})


def test_primitive_action_value_must_match_kind() -> None:
    with pytest.raises(ValidationError):
        PrimitiveAction(kind=ActionKind.SET_VALUE, target=ref())
    with pytest.raises(ValidationError):
        PrimitiveAction(kind=ActionKind.INVOKE, target=ref(), value=StringValue(value="x"))
    PrimitiveAction(kind=ActionKind.SET_VALUE, target=ref(), value=StringValue(value="x"))


def test_element_states_and_actions_are_sets() -> None:
    with pytest.raises(ValidationError):
        UIElement(ref=ref(), role=Role.BUTTON, states=(ElementState.FOCUSED, ElementState.FOCUSED))
    with pytest.raises(ValidationError):
        UIElement(ref=ref(), role=Role.BUTTON, actions=(ActionKind.INVOKE, ActionKind.INVOKE))


def test_truncation_flag_requires_reasons() -> None:
    with pytest.raises(ValidationError):
        Truncation(truncated=True)
    with pytest.raises(ValidationError):
        Truncation(truncated=False, reasons=(TruncationReason.MAX_NODES,))


def test_health_cannot_claim_ready_without_permissions() -> None:
    readiness = Readiness(
        accessibility=PermissionState.DENIED,
        capture=PermissionState.GRANTED,
        input_ready=True,
        gui_session=True,
        environment=EnvironmentKind.SYNTHETIC,
    )
    with pytest.raises(ValidationError):
        Health(
            live=True,
            ready=True,
            uptime_ms=0,
            readiness=readiness,
            normalizer=GeneratorInfo(name="n", version="1"),
            protocol_version="1",
            bridge_version="b",
        )


def _platform(observation_id: str = "obs_1", raw_id: str = SHA) -> PlatformObservation:
    root = UIElement(
        ref=ref(), role=Role.GROUP, children=(UIElement(ref=ref(1), role=Role.BUTTON),)
    )
    window = WindowObservation(info=WindowInfo(ref=WindowRef(ref="win_a")), root=root)
    return PlatformObservation(
        observation_id=observation_id,
        raw_capture_id=raw_id,
        application=APP,
        generation=0,
        platform="synthetic",
        normalizer=GeneratorInfo(name="n", version="1"),
        windows=(window,),
    )


def _raw() -> RawObservation:
    return RawObservation(
        observation_id="obs_1",
        application=APP,
        generation=0,
        captured_at=datetime(2026, 1, 1, tzinfo=UTC),
        platform="synthetic",
        raw_capture=RawArtifactRef(artifact_id=SHA, media_type="application/json", size_bytes=1),
        bridge_version="b",
    )


def test_bundle_requires_platform_observation_derived_from_its_raw() -> None:
    ObservationBundle(raw=_raw(), platform=_platform())
    with pytest.raises(ValidationError):
        ObservationBundle(raw=_raw(), platform=_platform(raw_id="sha256:" + "b" * 64))
    with pytest.raises(ValidationError):
        ObservationBundle(raw=_raw(), platform=_platform(observation_id="obs_2"))


def test_raw_observation_requires_timezone_aware_timestamp() -> None:
    with pytest.raises(ValidationError):
        RawObservation(
            observation_id="obs_1",
            application=APP,
            generation=0,
            captured_at=datetime(2026, 1, 1),
            platform="synthetic",
            raw_capture=RawArtifactRef(artifact_id=SHA, media_type="x/y", size_bytes=0),
            bridge_version="b",
        )


def test_platform_observation_json_round_trip_and_walk_order() -> None:
    obs = _platform()
    assert PlatformObservation.model_validate_json(obs.model_dump_json()) == obs
    assert [e.role for _, e, _ in obs.walk()] == [Role.GROUP, Role.BUTTON]
    assert obs.find(ref(1)) is not None
    assert obs.find(ref(7)) is None
