"""PlatformBridge contract tests.

Every PlatformBridge implementation must pass this suite. Today only MockPlatformBridge can
run it (UNIT / CONTRACT evidence). MacOSBridge will be added to ``BRIDGES`` once a real
disposable macOS VM exists; until then that entry is BLOCKED_VM_STORAGE.
"""

from __future__ import annotations

from collections.abc import Callable
from functools import partial

import pytest

from ghost._model import sha256_hex
from ghost.evidence import BLOCKED_VM_STORAGE
from ghost.platform.errors import BridgeError, BridgeErrorCode
from ghost.platform.mock import MockFaults, MockPlatformBridge
from ghost.platform.protocol import PlatformBridge, RequestContext, retry_read
from ghost.platform.simulated import SYNTHETIC_CAPTURE_MEDIA_TYPE
from ghost.platform.types import (
    ActionKind,
    ApplicationRef,
    CaptureRequest,
    ElementRef,
    LaunchRef,
    ObservationBundle,
    ObserveRequest,
    PermissionState,
    Role,
    StringValue,
    TruncationReason,
    UIElement,
)
from tests.support.toy_app import ToyApp

LAUNCH = LaunchRef(ref="seed:toy")


def ctx(deadline_ms: int = 1000) -> RequestContext:
    return RequestContext.new("contract-test", deadline_ms)


def make_mock(faults: MockFaults | None = None, rows: int = 2) -> MockPlatformBridge:
    return MockPlatformBridge({"seed:toy": partial(ToyApp, rows=rows)}, faults=faults)


BRIDGES: dict[str, Callable[[], PlatformBridge]] = {"mock": make_mock}


@pytest.fixture(params=sorted(BRIDGES))
def bridge(request: pytest.FixtureRequest) -> PlatformBridge:
    factory = BRIDGES[request.param]
    return factory()


@pytest.mark.vm
def test_macos_bridge_contract_is_blocked() -> None:
    pytest.skip(f"{BLOCKED_VM_STORAGE}: MacOSBridge contract run needs a disposable macOS VM")


def launch(bridge: PlatformBridge) -> ApplicationRef:
    return bridge.launch(ctx(), LAUNCH).application


def observe(
    bridge: PlatformBridge, app: ApplicationRef, max_nodes: int = 5000
) -> ObservationBundle:
    return bridge.observe(ctx(), ObserveRequest(application=app, max_nodes=max_nodes))


def by_label(bundle: ObservationBundle, label: str) -> UIElement:
    matches = [e for _, e, _ in bundle.platform.walk() if e.label == label]
    assert len(matches) == 1, f"expected exactly one {label!r}"
    return matches[0]


def test_implements_protocol(bridge: PlatformBridge) -> None:
    assert isinstance(bridge, PlatformBridge)


def test_health_reports_synthetic_ready(bridge: PlatformBridge) -> None:
    health = bridge.health(ctx())
    assert health.live
    assert health.ready
    assert health.protocol_version == "1"
    assert health.readiness.environment.value == "synthetic"


def test_launch_is_idempotent_per_launch_ref(bridge: PlatformBridge) -> None:
    first = bridge.launch(ctx(), LAUNCH)
    second = bridge.launch(ctx(), LAUNCH)
    assert first.launched
    assert not first.already_running
    assert second.already_running
    assert second.application == first.application


def test_launch_unknown_ref_is_app_not_found(bridge: PlatformBridge) -> None:
    with pytest.raises(BridgeError) as info:
        bridge.launch(ctx(), LaunchRef(ref="seed:missing"))
    assert info.value.code is BridgeErrorCode.APP_NOT_FOUND


def test_observe_links_raw_and_platform_evidence(bridge: PlatformBridge) -> None:
    app = launch(bridge)
    first, second = observe(bridge, app), observe(bridge, app)
    assert second.platform.generation == first.platform.generation + 1
    raw = bridge.get_artifact(ctx(), first.raw.raw_capture.artifact_id)
    assert "sha256:" + sha256_hex(raw) == first.raw.raw_capture.artifact_id
    assert first.platform.raw_capture_id == first.raw.raw_capture.artifact_id
    roles = {e.role for _, e, _ in first.platform.walk()}
    assert roles <= set(Role)


def test_invoke_is_a_claim_and_effect_shows_in_fresh_observation(bridge: PlatformBridge) -> None:
    app = launch(bridge)
    before = observe(bridge, app)
    result = bridge.invoke(ctx(), by_label(before, "Increment").ref)
    assert result.executed  # executor claim only
    after = observe(bridge, app)
    assert by_label(after, "count 1").role is Role.STATIC_TEXT


def test_stale_handle_is_rejected_without_effect(bridge: PlatformBridge) -> None:
    app = launch(bridge)
    old = observe(bridge, app)
    observe(bridge, app)
    with pytest.raises(BridgeError) as info:
        bridge.invoke(ctx(), by_label(old, "Increment").ref)
    assert info.value.code is BridgeErrorCode.STALE_HANDLE
    assert by_label(observe(bridge, app), "count 0")


def test_unknown_index_is_element_not_found(bridge: PlatformBridge) -> None:
    app = launch(bridge)
    current = observe(bridge, app)
    ghost_ref = ElementRef(application=app, generation=current.platform.generation, index=999)
    with pytest.raises(BridgeError) as info:
        bridge.invoke(ctx(), ghost_ref)
    assert info.value.code is BridgeErrorCode.ELEMENT_NOT_FOUND


def test_unadvertised_action_is_unsupported(bridge: PlatformBridge) -> None:
    app = launch(bridge)
    current = observe(bridge, app)
    label = by_label(current, "count 0")
    assert ActionKind.INVOKE not in label.actions
    with pytest.raises(BridgeError) as info:
        bridge.invoke(ctx(), label.ref)
    assert info.value.code is BridgeErrorCode.ACTION_UNSUPPORTED


def test_set_value_effect_is_observable(bridge: PlatformBridge) -> None:
    app = launch(bridge)
    field = by_label(observe(bridge, app), "Name")
    bridge.set_value(ctx(), field.ref, StringValue(value="probe-1"))
    after = by_label(observe(bridge, app), "Name")
    assert after.value == StringValue(value="probe-1")


def test_mutation_request_id_dedupes_and_rejects_reuse(bridge: PlatformBridge) -> None:
    app = launch(bridge)
    current = observe(bridge, app)
    call = ctx()
    first = bridge.invoke(call, by_label(current, "Increment").ref)
    again = bridge.invoke(call, by_label(current, "Increment").ref)
    assert again == first
    with pytest.raises(BridgeError) as info:
        bridge.set_value(call, by_label(current, "Name").ref, StringValue(value="x"))
    assert info.value.code is BridgeErrorCode.INVALID_REQUEST
    assert by_label(observe(bridge, app), "count 1")


def test_timeout_after_effect_retry_returns_first_result_once() -> None:
    bridge = make_mock(MockFaults(timeout_after_effect_once={"invoke"}))
    app = launch(bridge)
    current = observe(bridge, app)
    call = ctx()
    with pytest.raises(BridgeError) as info:
        bridge.invoke(call, by_label(current, "Increment").ref)
    assert info.value.code is BridgeErrorCode.TIMEOUT
    result = bridge.invoke(call, by_label(current, "Increment").ref)
    assert result.executed
    assert by_label(observe(bridge, app), "count 1")


def test_deadline_shorter_than_latency_times_out_without_effect() -> None:
    bridge = make_mock(MockFaults(latency_ms={"invoke": 50}))
    app = launch(bridge)
    current = observe(bridge, app)
    with pytest.raises(BridgeError) as info:
        bridge.invoke(ctx(deadline_ms=10), by_label(current, "Increment").ref)
    assert info.value.code is BridgeErrorCode.TIMEOUT
    assert by_label(observe(bridge, app), "count 0")


def test_retry_read_retries_reads_and_refuses_mutations() -> None:
    bridge = make_mock(MockFaults(busy_once={"health"}))
    call = ctx()
    assert retry_read("health", lambda: bridge.health(call)).live
    with pytest.raises(ValueError, match="mutating"):
        retry_read("invoke", lambda: bridge.health(call))


def test_permission_denied_blocks_observation_and_readiness() -> None:
    bridge = make_mock(MockFaults(accessibility=PermissionState.DENIED))
    app = launch(bridge)
    assert not bridge.health(ctx()).ready
    with pytest.raises(BridgeError) as info:
        observe(bridge, app)
    assert info.value.code is BridgeErrorCode.PERMISSION_DENIED


def test_malformed_capture_keeps_raw_evidence_and_invalidates_handles() -> None:
    bridge = make_mock(MockFaults())
    app = launch(bridge)
    good = observe(bridge, app)
    bridge.faults.malformed_next_capture = True
    with pytest.raises(BridgeError) as info:
        observe(bridge, app)
    assert info.value.code is BridgeErrorCode.PLATFORM_ERROR
    assert bridge.get_artifact(ctx(), info.value.detail["raw_capture_id"])
    with pytest.raises(BridgeError) as stale:
        bridge.invoke(ctx(), by_label(good, "Increment").ref)
    assert stale.value.code is BridgeErrorCode.STALE_HANDLE


def test_truncation_is_explicit_unknown_not_absent() -> None:
    bridge = make_mock(rows=50)
    app = launch(bridge)
    bundle = observe(bridge, app, max_nodes=10)
    assert bundle.platform.truncation.truncated
    assert TruncationReason.MAX_NODES in bundle.platform.truncation.reasons
    assert any(e.truncated for _, e, _ in bundle.platform.walk())


def test_capture_is_an_explicit_synthetic_artifact(bridge: PlatformBridge) -> None:
    app = launch(bridge)
    result = bridge.capture(ctx(), CaptureRequest(application=app))
    assert result.artifact.media_type == SYNTHETIC_CAPTURE_MEDIA_TYPE


def test_unknown_artifact_is_not_found(bridge: PlatformBridge) -> None:
    with pytest.raises(BridgeError) as info:
        bridge.get_artifact(ctx(), "sha256:" + "0" * 64)
    assert info.value.code is BridgeErrorCode.ARTIFACT_NOT_FOUND


def test_same_operations_give_identical_evidence() -> None:
    def run() -> list[str]:
        bridge = make_mock()
        app = launch(bridge)
        first = observe(bridge, app)
        bridge.invoke(ctx(), by_label(first, "Increment").ref)
        second = observe(bridge, app)
        return [
            first.platform.model_dump_json(),
            second.raw.raw_capture.artifact_id,
            second.platform.model_dump_json(),
        ]

    assert run() == run()
