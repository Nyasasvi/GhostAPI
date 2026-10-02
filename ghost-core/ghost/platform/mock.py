"""MockPlatformBridge: deterministic, in-process implementation of the PlatformBridge contract.

It drives generic ``SimulatedApp`` objects and holds no application knowledge. It exists for
contract tests, host-side development, and deterministic failure injection (stale handles,
timeouts, busy, permission denial, malformed captures, timeouts after a mutation took effect).
It never touches the host's real UI. Its environment kind is SYNTHETIC.
"""

from __future__ import annotations

import json
import uuid
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from ghost._model import canonical_json, sha256_hex
from ghost.platform.errors import BridgeError, BridgeErrorCode
from ghost.platform.protocol import PROTOCOL_VERSION, RequestContext
from ghost.platform.simulated import (
    SYNTHETIC_CAPTURE_MEDIA_TYPE,
    SYNTHETIC_NORMALIZER,
    SYNTHETIC_RAW_MEDIA_TYPE,
    NormalizationError,
    SimulatedActionRejectedError,
    SimulatedApp,
    SimulatedAppFactory,
    SimulatedDisk,
    SimulatedElementGoneError,
    normalize_synthetic,
    parse_raw_capture,
)
from ghost.platform.types import (
    ActionKind,
    ActionResult,
    ApplicationInfo,
    ApplicationRef,
    CaptureRequest,
    CaptureResult,
    ElementRef,
    EnvironmentKind,
    Health,
    LaunchRef,
    LaunchResult,
    ObservationBundle,
    ObserveRequest,
    PermissionState,
    PlatformObservation,
    RawArtifactRef,
    RawObservation,
    Readiness,
    Rect,
    TypedValue,
    WindowInfo,
    WindowRef,
)

MAX_ARTIFACT_BYTES = 32 * 1024 * 1024
DEFAULT_LATENCY_MS = 5


@dataclass
class MockFaults:
    """Deterministic failure injection. Every fault is opt-in."""

    accessibility: PermissionState = PermissionState.GRANTED
    capture: PermissionState = PermissionState.GRANTED
    unhealthy: bool = False
    latency_ms: dict[str, int] = field(default_factory=dict)
    busy_once: set[str] = field(default_factory=set)
    malformed_next_capture: bool = False
    timeout_after_effect_once: set[str] = field(default_factory=set)


@dataclass
class _RunningApp:
    ref: ApplicationRef
    launch_ref: str
    app: SimulatedApp
    generation: int = -1
    handles: dict[int, str] = field(default_factory=dict)
    last: PlatformObservation | None = None


class MockPlatformBridge:
    """PlatformBridge over simulated apps. ``apps`` maps launch refs to app factories."""

    def __init__(
        self,
        apps: Mapping[str, SimulatedAppFactory],
        *,
        faults: MockFaults | None = None,
        bridge_version: str = "mock-bridge/0.1",
        epoch: datetime = datetime(2026, 1, 1, tzinfo=UTC),
        disks: Mapping[str, SimulatedDisk] | None = None,
        session_id: str | None = None,
    ) -> None:
        if session_id is not None and not session_id.isalnum():
            raise ValueError("session_id must be alphanumeric")
        # Application refs are scoped to this bridge session, so handles minted by another
        # bridge instance can never address an element here.
        self.session_id = session_id or uuid.uuid4().hex[:8]
        self._factories = dict(apps)
        self.faults = faults or MockFaults()
        self._bridge_version = bridge_version
        self._epoch = epoch
        self.now_ms = 0
        self._disks: dict[str, SimulatedDisk] = dict(disks or {})
        self._running: dict[str, _RunningApp] = {}
        self._artifacts: dict[str, tuple[str, bytes]] = {}
        self._mutations: dict[str, tuple[str, str, ActionResult | LaunchResult]] = {}
        self._counters: dict[str, int] = {}

    # -- PlatformBridge -----------------------------------------------------------------
    @property
    def platform(self) -> str:
        return "synthetic"

    def health(self, ctx: RequestContext) -> Health:
        self._begin(ctx, "health")
        readiness = Readiness(
            accessibility=self.faults.accessibility,
            capture=self.faults.capture,
            input_ready=not self.faults.unhealthy,
            gui_session=not self.faults.unhealthy,
            environment=EnvironmentKind.SYNTHETIC,
        )
        ready = (
            not self.faults.unhealthy
            and readiness.accessibility is PermissionState.GRANTED
            and readiness.capture is PermissionState.GRANTED
        )
        return Health(
            live=True,
            ready=ready,
            uptime_ms=self.now_ms,
            readiness=readiness,
            normalizer=SYNTHETIC_NORMALIZER,
            protocol_version=PROTOCOL_VERSION,
            bridge_version=self._bridge_version,
        )

    def list_applications(self, ctx: RequestContext) -> tuple[ApplicationInfo, ...]:
        self._begin(ctx, "list_applications")
        return tuple(
            ApplicationInfo(application=r.ref, display_name=r.app.display_name, is_active=True)
            for r in sorted(self._running.values(), key=lambda r: r.ref.ref)
        )

    def list_windows(
        self, ctx: RequestContext, application: ApplicationRef
    ) -> tuple[WindowInfo, ...]:
        self._begin(ctx, "list_windows")
        return self._windows(self._app(application))

    def launch(self, ctx: RequestContext, launch_ref: LaunchRef) -> LaunchResult:
        def effect() -> LaunchResult:
            for running in self._running.values():
                if running.launch_ref == launch_ref.ref:
                    return LaunchResult(
                        application=running.ref, launched=False, already_running=True
                    )
            factory = self._factories.get(launch_ref.ref)
            if factory is None:
                raise BridgeError(
                    BridgeErrorCode.APP_NOT_FOUND, f"unknown launch ref {launch_ref.ref}"
                )
            disk = self._disks.setdefault(launch_ref.ref, SimulatedDisk())
            ref = ApplicationRef(ref=f"app_{self.session_id}_{self._next('app')}")
            self._running[ref.ref] = _RunningApp(
                ref=ref, launch_ref=launch_ref.ref, app=factory(disk)
            )
            return LaunchResult(application=ref, launched=True, already_running=False)

        result = self._mutate(ctx, "launch", f"launch:{launch_ref.ref}", effect)
        if not isinstance(result, LaunchResult):
            raise TypeError("launch dedupe returned a non-launch result")
        return result

    def observe(self, ctx: RequestContext, request: ObserveRequest) -> ObservationBundle:
        self._begin(ctx, "observe")
        running = self._app(request.application)
        if self.faults.accessibility is not PermissionState.GRANTED:
            raise BridgeError(BridgeErrorCode.PERMISSION_DENIED, "accessibility not granted")
        document: object = running.app.raw_capture()
        if self.faults.malformed_next_capture:
            self.faults.malformed_next_capture = False
            document = {"format": "synthetic-raw/1", "windows": "not-a-list"}
        try:
            raw_bytes = canonical_json(document).encode("utf-8")
        except (TypeError, ValueError) as error:
            raise BridgeError(
                BridgeErrorCode.PLATFORM_ERROR, f"raw capture is not serializable: {error}"
            ) from error
        raw_ref = self._store(SYNTHETIC_RAW_MEDIA_TYPE, raw_bytes)
        running.generation += 1
        observation_id = f"obs_{self._next('obs')}"
        screenshot, unavailable = None, None
        if not request.include_capture:
            unavailable = "not requested"
        elif self.faults.capture is not PermissionState.GRANTED:
            unavailable = f"capture permission {self.faults.capture.value}"
        else:
            screenshot = self._synthetic_capture(raw_bytes)
        raw = RawObservation(
            observation_id=observation_id,
            application=running.ref,
            generation=running.generation,
            captured_at=self._now(),
            platform=self.platform,
            environment=EnvironmentKind.SYNTHETIC,
            request_id=ctx.request_id,
            correlation_id=ctx.correlation_id,
            raw_capture=raw_ref,
            screenshot=screenshot,
            screenshot_unavailable_reason=unavailable,
            bridge_version=self._bridge_version,
        )
        try:
            # Normalize from the stored bytes, so the derivation is replayable from evidence.
            platform_obs, handles = normalize_synthetic(
                json.loads(raw_bytes),
                application=running.ref,
                generation=running.generation,
                observation_id=observation_id,
                raw_capture_id=raw_ref.artifact_id,
                max_depth=request.max_depth,
                max_nodes=request.max_nodes,
            )
        except NormalizationError as error:
            running.handles, running.last = {}, None
            raise BridgeError(
                BridgeErrorCode.PLATFORM_ERROR,
                "raw capture could not be normalized",
                detail={"raw_capture_id": raw_ref.artifact_id, "error": str(error)[:500]},
            ) from error
        running.handles, running.last = handles, platform_obs
        return ObservationBundle(raw=raw, platform=platform_obs)

    def capture(self, ctx: RequestContext, request: CaptureRequest) -> CaptureResult:
        self._begin(ctx, "capture")
        running = self._app(request.application)
        if self.faults.capture is not PermissionState.GRANTED:
            raise BridgeError(BridgeErrorCode.PERMISSION_DENIED, "capture not granted")
        if request.window is not None:
            known = {w.ref for w in self._windows(running)}
            if request.window not in known:
                raise BridgeError(BridgeErrorCode.WINDOW_NOT_FOUND, request.window.ref)
        try:
            raw_bytes = canonical_json(running.app.raw_capture()).encode("utf-8")
        except (TypeError, ValueError) as error:
            raise BridgeError(BridgeErrorCode.CAPTURE_FAILED, str(error)) from error
        artifact = self._synthetic_capture(raw_bytes)
        return CaptureResult(
            capture_id=f"cap_{self._next('cap')}", artifact=artifact, captured_at=self._now()
        )

    def get_artifact(self, ctx: RequestContext, artifact_id: str) -> bytes:
        self._begin(ctx, "get_artifact")
        stored = self._artifacts.get(artifact_id)
        if stored is None:
            raise BridgeError(BridgeErrorCode.ARTIFACT_NOT_FOUND, artifact_id)
        return stored[1]

    def invoke(self, ctx: RequestContext, element: ElementRef) -> ActionResult:
        return self._act(ctx, "invoke", ActionKind.INVOKE, element, None)

    def set_value(
        self, ctx: RequestContext, element: ElementRef, value: TypedValue
    ) -> ActionResult:
        return self._act(ctx, "set_value", ActionKind.SET_VALUE, element, value)

    # -- environment hooks (synthetic only; not part of PlatformBridge) -------------------
    def advance(self, ms: int) -> None:
        """Let simulated time pass without any action (volatility calibration, delays)."""
        self.now_ms += ms
        for running in self._running.values():
            running.app.tick(ms)

    def disk(self, launch_ref: str) -> SimulatedDisk:
        return self._disks.setdefault(launch_ref, SimulatedDisk())

    def terminate(self, application: ApplicationRef) -> None:
        """Simulated app quit (state not persisted by the app is lost)."""
        self._app(application)
        del self._running[application.ref]

    # -- internals ----------------------------------------------------------------------
    def _windows(self, running: _RunningApp) -> tuple[WindowInfo, ...]:
        try:
            capture = parse_raw_capture(running.app.raw_capture())
        except NormalizationError as error:
            raise BridgeError(BridgeErrorCode.PLATFORM_ERROR, str(error)) from error
        return tuple(
            WindowInfo(
                ref=WindowRef(ref=f"win_{w.wid}"),
                title=w.title,
                bounds=None
                if w.frame is None
                else Rect(x=w.frame[0], y=w.frame[1], w=w.frame[2], h=w.frame[3]),
                focused=w.focused,
                main=w.main,
                minimized=w.minimized,
                modal=w.modal,
            )
            for w in capture.windows
        )

    def _act(
        self,
        ctx: RequestContext,
        operation: str,
        kind: ActionKind,
        element: ElementRef,
        value: TypedValue | None,
    ) -> ActionResult:
        def effect() -> ActionResult:
            running = self._app(element.application)
            if running.last is None or element.generation != running.generation:
                raise BridgeError(
                    BridgeErrorCode.STALE_HANDLE,
                    f"handle generation {element.generation} is not current ({running.generation})",
                )
            node_id = running.handles.get(element.index)
            target = running.last.find(element)
            if node_id is None or target is None:
                raise BridgeError(BridgeErrorCode.ELEMENT_NOT_FOUND, f"index {element.index}")
            if kind not in target.actions:
                raise BridgeError(
                    BridgeErrorCode.ACTION_UNSUPPORTED, f"{kind.value} not advertised"
                )
            try:
                running.app.perform(node_id, kind, value)
            except SimulatedElementGoneError as error:
                raise BridgeError(BridgeErrorCode.ELEMENT_NOT_FOUND, str(error)) from error
            except SimulatedActionRejectedError as error:
                raise BridgeError(BridgeErrorCode.PLATFORM_ERROR, str(error)) from error
            return ActionResult(
                action_id=f"act_{self._next('act')}",
                request_id=ctx.request_id,
                executed=True,
                platform_status="ok",
                elapsed_ms=self._latency(operation),
            )

        signature = (
            f"{operation}:{element.model_dump_json()}:{value.model_dump_json() if value else ''}"
        )
        result = self._mutate(ctx, operation, signature, effect)
        if not isinstance(result, ActionResult):
            raise TypeError("action dedupe returned a non-action result")
        return result

    def _mutate(
        self,
        ctx: RequestContext,
        operation: str,
        signature: str,
        effect: Callable[[], ActionResult | LaunchResult],
    ) -> ActionResult | LaunchResult:
        previous = self._mutations.get(ctx.request_id)
        if previous is not None:
            if previous[:2] != (operation, signature):
                raise BridgeError(
                    BridgeErrorCode.INVALID_REQUEST, "request id reused for a different mutation"
                )
            return previous[2]
        self._begin(ctx, operation)
        result = effect()
        self._mutations[ctx.request_id] = (operation, signature, result)
        if operation in self.faults.timeout_after_effect_once:
            self.faults.timeout_after_effect_once.discard(operation)
            raise BridgeError(BridgeErrorCode.TIMEOUT, f"{operation} deadline passed after effect")
        return result

    def _begin(self, ctx: RequestContext, operation: str) -> None:
        latency = self._latency(operation)
        if latency > ctx.deadline_ms:
            raise BridgeError(
                BridgeErrorCode.TIMEOUT,
                f"{operation} needs {latency} ms > deadline {ctx.deadline_ms}",
            )
        if operation in self.faults.busy_once:
            self.faults.busy_once.discard(operation)
            raise BridgeError(BridgeErrorCode.BUSY, f"{operation}: another mutation in progress")
        self.advance(latency)

    def _latency(self, operation: str) -> int:
        return self.faults.latency_ms.get(operation, DEFAULT_LATENCY_MS)

    def _app(self, application: ApplicationRef) -> _RunningApp:
        running = self._running.get(application.ref)
        if running is None:
            raise BridgeError(BridgeErrorCode.APP_NOT_FOUND, application.ref)
        return running

    def _store(self, media_type: str, data: bytes) -> RawArtifactRef:
        if len(data) > MAX_ARTIFACT_BYTES:
            raise BridgeError(BridgeErrorCode.PAYLOAD_TOO_LARGE, f"{len(data)} bytes")
        artifact_id = "sha256:" + sha256_hex(data)
        self._artifacts.setdefault(artifact_id, (media_type, data))
        return RawArtifactRef(artifact_id=artifact_id, media_type=media_type, size_bytes=len(data))

    def _synthetic_capture(self, raw_bytes: bytes) -> RawArtifactRef:
        # Not an image: an explicit synthetic stand-in, so nobody mistakes it for a screenshot.
        payload = {"kind": "synthetic-capture/1", "source_raw_sha256": sha256_hex(raw_bytes)}
        return self._store(SYNTHETIC_CAPTURE_MEDIA_TYPE, canonical_json(payload).encode("utf-8"))

    def _next(self, prefix: str) -> str:
        self._counters[prefix] = self._counters.get(prefix, 0) + 1
        return f"{self._counters[prefix]:06d}"

    def _now(self) -> datetime:
        return self._epoch + timedelta(milliseconds=self.now_ms)
