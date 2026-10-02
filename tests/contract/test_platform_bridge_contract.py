"""PlatformBridge contract tests.

Every PlatformBridge implementation must pass this suite. Today only MockPlatformBridge can
run it (UNIT / CONTRACT evidence). MacOSBridge will be added to ``BRIDGES`` once a real
disposable macOS VM exists; until then that entry is BLOCKED_VM_STORAGE.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from functools import partial

import pytest

from ghost._model import sha256_hex
from ghost.evidence import BLOCKED_VM_STORAGE
from ghost.platform.errors import BridgeError, BridgeErrorCode
from ghost.platform.mock import MockFaults, MockPlatformBridge
from ghost.platform.protocol import (
    CONTRACT_OPERATIONS,
    PlatformBridge,
    RequestContext,
    RetryingReader,
)
from ghost.platform.simulated import SYNTHETIC_CAPTURE_MEDIA_TYPE, normalize_synthetic
from ghost.platform.types import (
    ActionKind,
    ApplicationRef,
    CaptureRequest,
    ElementRef,
    LaunchRef,
    ObservationBundle,
    ObserveRequest,
    PermissionState,
    Rect,
    Role,
    StringValue,
    TruncationReason,
    UIElement,
    WindowRef,
)
from tests.support.toy_app import ToyApp

LAUNCH = LaunchRef(ref="seed:toy")


def ctx(deadline_ms: int = 1000) -> RequestContext:
    return RequestContext.new("contract-test", deadline_ms)


def make_mock(
    faults: MockFaults | None = None, rows: int = 2, session_id: str | None = None
) -> MockPlatformBridge:
    return MockPlatformBridge(
        {"seed:toy": partial(ToyApp, rows=rows)}, faults=faults, session_id=session_id
    )


BRIDGES: dict[str, Callable[[], PlatformBridge]] = {"mock": make_mock}


@pytest.fixture(params=sorted(BRIDGES))
def bridge(request: pytest.FixtureRequest) -> PlatformBridge:
    factory = BRIDGES[request.param]
    return factory()


@pytest.mark.vm
def test_macos_bridge_contract_is_blocked() -> None:
    # Fails (never skips) so that a VM test run cannot report green while blocked.
    pytest.fail(f"{BLOCKED_VM_STORAGE}: MacOSBridge contract run needs a disposable macOS VM")


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


def test_contract_surface_is_frozen() -> None:
    # Adding shell/filesystem/coordinate/keyboard operations must fail loudly here.
    declared = {
        name
        for name in vars(PlatformBridge)
        if not name.startswith("_") and callable(getattr(PlatformBridge, name))
    }
    assert declared == set(CONTRACT_OPERATIONS)


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
    neutral = first.platform.model_dump_json()
    for raw_word in ('"kids"', "push_button", '"acts"', '"flags"'):
        assert raw_word not in neutral  # platform vocabulary never crosses the boundary


def test_normalization_is_replayable_from_stored_raw_bytes(bridge: PlatformBridge) -> None:
    app = launch(bridge)
    bundle = observe(bridge, app)
    raw = bridge.get_artifact(ctx(), bundle.raw.raw_capture.artifact_id)
    replayed, _ = normalize_synthetic(
        json.loads(raw),
        application=app,
        generation=bundle.platform.generation,
        observation_id=bundle.platform.observation_id,
        raw_capture_id=bundle.raw.raw_capture.artifact_id,
    )
    assert replayed == bundle.platform


def test_evidence_records_request_lineage(bridge: PlatformBridge) -> None:
    app = launch(bridge)
    call = RequestContext.new("run-7/trial-3", 1000)
    raw = bridge.observe(call, ObserveRequest(application=app)).raw
    assert raw.request_id == call.request_id
    assert raw.correlation_id == "run-7/trial-3"
    assert raw.environment.value == "synthetic"


def test_list_applications_and_windows(bridge: PlatformBridge) -> None:
    app = launch(bridge)
    (info,) = bridge.list_applications(ctx())
    assert info.application == app
    (window,) = bridge.list_windows(ctx(), app)
    assert window.title == "Toy"
    with pytest.raises(BridgeError) as missing:
        bridge.list_windows(ctx(), ApplicationRef(ref="app_nope"))
    assert missing.value.code is BridgeErrorCode.APP_NOT_FOUND


def test_handles_from_another_bridge_session_are_rejected() -> None:
    first, second = make_mock(), make_mock()
    stale_elsewhere = by_label(observe(first, launch(first)), "Increment").ref
    launch(second)
    with pytest.raises(BridgeError) as info:
        second.invoke(ctx(), stale_elsewhere)
    assert info.value.code is BridgeErrorCode.APP_NOT_FOUND


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


def test_reader_retries_reads_with_same_request_and_shrinking_deadline() -> None:
    seen: list[RequestContext] = []
    bridge = make_mock(MockFaults(busy_once={"health"}))
    inner_health = bridge.health

    def spy(call: RequestContext) -> object:
        seen.append(call)
        return inner_health(call)

    bridge.health = spy  # type: ignore[method-assign,assignment]
    waits: list[int] = []
    reader = RetryingReader(bridge, clock_ms=lambda: 0, sleep_ms=waits.append)
    call = ctx(deadline_ms=1000)
    assert reader.health(call).live
    assert [c.request_id for c in seen] == [call.request_id] * 2
    assert seen[1].deadline_ms == 1000 - 50
    assert waits == [50]


def test_reader_has_no_mutating_operations_and_passes_through_fatal_errors() -> None:
    reader = RetryingReader(make_mock())
    assert not any(hasattr(reader, op) for op in ("launch", "invoke", "set_value"))
    with pytest.raises(BridgeError) as info:
        reader.list_windows(ctx(), ApplicationRef(ref="app_nope"))
    assert info.value.code is BridgeErrorCode.APP_NOT_FOUND


def test_reader_gives_up_after_budgeted_retries() -> None:
    bridge = make_mock(MockFaults(latency_ms={"health": 5000}))
    reader = RetryingReader(bridge, clock_ms=lambda: 0, sleep_ms=lambda _ms: None)
    with pytest.raises(BridgeError) as info:
        reader.health(ctx(deadline_ms=1000))
    assert info.value.code is BridgeErrorCode.TIMEOUT


def test_mutation_errors_are_never_retryable_on_the_wire() -> None:
    error = BridgeError(BridgeErrorCode.TIMEOUT, "late")
    assert error.body(mutating=False).retryable
    assert not error.body(mutating=True).retryable


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
    with pytest.raises(BridgeError) as info:
        bridge.capture(ctx(), CaptureRequest(application=app, window=WindowRef(ref="win_nope")))
    assert info.value.code is BridgeErrorCode.WINDOW_NOT_FOUND


def test_denied_capture_is_recorded_not_silent() -> None:
    bridge = make_mock(MockFaults(capture=PermissionState.DENIED))
    raw = observe(bridge, launch(bridge)).raw
    assert raw.screenshot is None
    assert raw.screenshot_unavailable_reason == "capture permission denied"


def test_focus_beyond_node_limit_is_unknown_not_an_error() -> None:
    bridge = make_mock()
    app = launch(bridge)
    field = by_label(observe(bridge, app), "Name")
    bridge.set_value(ctx(), field.ref, StringValue(value="x"))  # moves focus to the field
    small = observe(bridge, app, max_nodes=3)
    assert small.platform.focused is None
    assert TruncationReason.MAX_NODES in small.platform.truncation.reasons


def test_unserializable_raw_capture_is_a_typed_error() -> None:
    bridge = make_mock()
    app = launch(bridge)
    toy = next(iter(bridge._running.values())).app
    assert isinstance(toy, ToyApp)
    toy.text = "ok"
    toy.raw_capture = lambda: {"format": "synthetic-raw/1", "windows": [], "bad": float("nan")}  # type: ignore[method-assign]
    with pytest.raises(BridgeError) as info:
        observe(bridge, app)
    assert info.value.code is BridgeErrorCode.PLATFORM_ERROR


def test_unknown_artifact_is_not_found(bridge: PlatformBridge) -> None:
    with pytest.raises(BridgeError) as info:
        bridge.get_artifact(ctx(), "sha256:" + "0" * 64)
    assert info.value.code is BridgeErrorCode.ARTIFACT_NOT_FOUND


def test_same_operations_give_identical_evidence() -> None:
    def run() -> list[str]:
        bridge = make_mock(session_id="fixed")
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


def test_quit_then_launch_relaunches_with_persisted_state(bridge: PlatformBridge) -> None:
    app = launch(bridge)
    bridge.invoke(ctx(), by_label(observe(bridge, app), "Increment").ref)
    call = ctx()
    assert bridge.quit(call, app).quit
    assert bridge.quit(call, app).quit  # same request id: deduped, not re-executed
    with pytest.raises(BridgeError) as gone:
        observe(bridge, app)
    assert gone.value.code is BridgeErrorCode.APP_NOT_FOUND
    relaunched = launch(bridge)
    assert relaunched != app
    assert by_label(observe(bridge, relaunched), "count 1")  # the toy app persists its count


def test_arrange_window_changes_only_geometry(bridge: PlatformBridge) -> None:
    app = launch(bridge)
    (window,) = bridge.list_windows(ctx(), app)
    before = observe(bridge, app).platform
    bounds = Rect(x=100.0, y=50.0, w=640.0, h=480.0)
    bridge.arrange_window(ctx(), app, window.ref, bounds)
    after = observe(bridge, app).platform
    assert after.windows[0].info.bounds == bounds
    assert after.windows[0].root.model_dump(exclude={"ref"}) != {}  # still observable
    assert [e.label for _, e, _ in after.walk()] == [e.label for _, e, _ in before.walk()]
    with pytest.raises(BridgeError) as missing:
        bridge.arrange_window(ctx(), app, WindowRef(ref="win_nope"), bounds)
    assert missing.value.code is BridgeErrorCode.WINDOW_NOT_FOUND
