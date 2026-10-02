"""Platform-neutral DTOs shared by Ghost Core and every PlatformBridge implementation.

Nothing here names a platform framework concept. Platform adapters translate their native
objects into these types at the platform boundary (ADR-007, proposed).
"""

from __future__ import annotations

from collections.abc import Iterator
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import AwareDatetime, Field, model_validator

from ghost._model import SHA256_PATTERN, StrictModel


class ApplicationRef(StrictModel):
    """Opaque reference to a running application, valid for the process lifetime."""

    ref: Annotated[str, Field(pattern=r"^app_[A-Za-z0-9_-]{1,64}$")]


class WindowRef(StrictModel):
    """Opaque reference to a window, valid for the process lifetime."""

    ref: Annotated[str, Field(pattern=r"^win_[A-Za-z0-9_-]{1,64}$")]


class LaunchRef(StrictModel):
    """Operator-provided opaque launch reference declared in the environment seed.

    Ghost Core never holds application names, bundle identifiers, or install paths.
    """

    ref: Annotated[str, Field(pattern=r"^[a-z][a-z0-9_.:-]{0,127}$")]


class ElementRef(StrictModel):
    """Ephemeral, observation-scoped element handle.

    Valid only while ``generation`` is the latest observation generation of ``application``.
    It is NOT entity identity and must never be persisted in GIR (AGENTS invariant 7).
    """

    application: ApplicationRef
    generation: Annotated[int, Field(ge=0)]
    index: Annotated[int, Field(ge=0)]


class Rect(StrictModel):
    x: float
    y: float
    w: Annotated[float, Field(ge=0)]
    h: Annotated[float, Field(ge=0)]
    space: Literal["screen_points_top_left"] = "screen_points_top_left"


class Role(StrEnum):
    BUTTON = "button"
    TEXT_FIELD = "text_field"
    TEXT_AREA = "text_area"
    CHECKBOX = "checkbox"
    RADIO = "radio"
    MENU_BAR = "menu_bar"
    MENU = "menu"
    MENU_ITEM = "menu_item"
    LIST = "list"
    ROW = "row"
    CELL = "cell"
    TABLE = "table"
    TAB = "tab"
    POPUP = "popup"
    SLIDER = "slider"
    WINDOW = "window"
    DIALOG = "dialog"
    STATIC_TEXT = "static_text"
    IMAGE = "image"
    GROUP = "group"
    TOOLBAR = "toolbar"
    UNKNOWN = "unknown"


class ElementState(StrEnum):
    FOCUSED = "focused"
    SELECTED = "selected"
    DISABLED = "disabled"
    CHECKED = "checked"
    EXPANDED = "expanded"
    EDITABLE = "editable"


class ActionKind(StrEnum):
    """Primitive actions in the Week 1 contract. New kinds require an API change + ADR."""

    INVOKE = "invoke"
    SET_VALUE = "set_value"


class StringValue(StrictModel):
    type: Literal["string"] = "string"
    value: Annotated[str, Field(max_length=4096)]


class BoolValue(StrictModel):
    type: Literal["bool"] = "bool"
    value: bool


class NumberValue(StrictModel):
    type: Literal["number"] = "number"
    value: Annotated[float, Field(allow_inf_nan=False)]


TypedValue = Annotated[StringValue | BoolValue | NumberValue, Field(discriminator="type")]


class UIElement(StrictModel):
    """One observed UI element. Evidence only: no semantic interpretation."""

    ref: ElementRef
    role: Role
    label: str | None = None
    value: TypedValue | None = None
    states: tuple[ElementState, ...] = ()
    actions: tuple[ActionKind, ...] = ()
    bounds: Rect | None = None
    stable_id_hint: str | None = None
    children: tuple[UIElement, ...] = ()
    truncated: bool = False
    """True when this element's children/attributes were not fully observable (UNKNOWN)."""

    @model_validator(mode="after")
    def _unique_sets(self) -> UIElement:
        if len(set(self.states)) != len(self.states):
            raise ValueError("duplicate element states")
        if len(set(self.actions)) != len(self.actions):
            raise ValueError("duplicate element actions")
        return self


class WindowInfo(StrictModel):
    ref: WindowRef
    title: str | None = None
    bounds: Rect | None = None
    focused: bool = False
    main: bool = False
    minimized: bool = False
    modal: bool = False


class WindowObservation(StrictModel):
    info: WindowInfo
    root: UIElement


class TruncationReason(StrEnum):
    MAX_NODES = "max_nodes"
    MAX_DEPTH = "max_depth"
    ATTRIBUTE_ERROR = "attribute_error"
    VIRTUALIZED = "virtualized"


class Truncation(StrictModel):
    truncated: bool = False
    reasons: tuple[TruncationReason, ...] = ()

    @model_validator(mode="after")
    def _consistent(self) -> Truncation:
        if self.truncated != bool(self.reasons):
            raise ValueError("truncated must be true exactly when reasons are given")
        return self


class GeneratorInfo(StrictModel):
    """Identifies the code (and its version) that produced a derived record."""

    name: Annotated[str, Field(min_length=1)]
    version: Annotated[str, Field(min_length=1)]


class EnvironmentKind(StrEnum):
    """Where the bridge's target UI lives.

    DISPOSABLE_VM is the only environment in which real-platform exploration and trials may
    run (AGENTS invariant 2). SYNTHETIC is an in-process simulated UI that cannot touch the
    host; results from it are SYNTHETIC_FIXTURE evidence and never real-platform evidence.
    """

    SYNTHETIC = "synthetic"
    DISPOSABLE_VM = "disposable_vm"
    UNKNOWN = "unknown"


class RawArtifactRef(StrictModel):
    artifact_id: Annotated[str, Field(pattern=SHA256_PATTERN)]
    media_type: Annotated[str, Field(min_length=3)]
    size_bytes: Annotated[int, Field(ge=0)]


class RawObservation(StrictModel):
    """Immutable evidence bundle exactly as captured by a platform bridge."""

    observation_id: Annotated[str, Field(pattern=r"^obs_[A-Za-z0-9_-]{1,64}$")]
    application: ApplicationRef
    generation: Annotated[int, Field(ge=0)]
    captured_at: AwareDatetime
    platform: Annotated[str, Field(min_length=1)]
    environment: EnvironmentKind
    request_id: Annotated[str, Field(min_length=1)]
    correlation_id: Annotated[str, Field(min_length=1)]
    raw_capture: RawArtifactRef
    screenshot: RawArtifactRef | None = None
    screenshot_unavailable_reason: str | None = None
    bridge_version: Annotated[str, Field(min_length=1)]
    truncation: Truncation = Truncation()

    @model_validator(mode="after")
    def _screenshot_explained(self) -> RawObservation:
        if (self.screenshot is None) == (self.screenshot_unavailable_reason is None):
            raise ValueError("exactly one of screenshot / screenshot_unavailable_reason is set")
        return self


class PlatformObservation(StrictModel):
    """Platform-neutral normalized UI evidence derived from exactly one RawObservation.

    Contains no platform framework objects and no semantic interpretation.
    """

    observation_id: Annotated[str, Field(pattern=r"^obs_[A-Za-z0-9_-]{1,64}$")]
    raw_capture_id: Annotated[str, Field(pattern=SHA256_PATTERN)]
    application: ApplicationRef
    generation: Annotated[int, Field(ge=0)]
    platform: Annotated[str, Field(min_length=1)]
    normalizer: GeneratorInfo
    windows: tuple[WindowObservation, ...]
    focused: ElementRef | None = None
    truncation: Truncation = Truncation()

    @model_validator(mode="after")
    def _handles_consistent(self) -> PlatformObservation:
        seen: set[int] = set()
        for _, element, _ in self.walk():
            ref = element.ref
            if ref.application != self.application or ref.generation != self.generation:
                raise ValueError(f"element {ref.index} belongs to another application/generation")
            if ref.index in seen:
                raise ValueError(f"duplicate element index {ref.index}")
            seen.add(ref.index)
        if self.focused is not None and self.focused.index not in seen:
            raise ValueError("focused element is not part of the observation")
        if self.focused is not None and (
            self.focused.application != self.application
            or self.focused.generation != self.generation
        ):
            raise ValueError("focused element belongs to another application/generation")
        return self

    def walk(self) -> Iterator[tuple[WindowObservation, UIElement, int]]:
        """Depth-first (window, element, depth) in observed order."""
        for window in self.windows:
            stack: list[tuple[UIElement, int]] = [(window.root, 0)]
            while stack:
                element, depth = stack.pop()
                yield window, element, depth
                stack.extend((child, depth + 1) for child in reversed(element.children))

    def find(self, ref: ElementRef) -> UIElement | None:
        for _, element, _ in self.walk():
            if element.ref == ref:
                return element
        return None


class ObservationBundle(StrictModel):
    raw: RawObservation
    platform: PlatformObservation

    @model_validator(mode="after")
    def _linked(self) -> ObservationBundle:
        p, r = self.platform, self.raw
        if (p.observation_id, p.generation, p.application) != (
            r.observation_id,
            r.generation,
            r.application,
        ):
            raise ValueError("platform observation does not match its raw observation")
        if p.raw_capture_id != r.raw_capture.artifact_id:
            raise ValueError("platform observation was not derived from this raw capture")
        if p.platform != r.platform:
            raise ValueError("platform observation and raw observation name different platforms")
        return self


class PrimitiveAction(StrictModel):
    kind: ActionKind
    target: ElementRef
    value: TypedValue | None = None

    @model_validator(mode="after")
    def _value_matches_kind(self) -> PrimitiveAction:
        if self.kind is ActionKind.SET_VALUE and self.value is None:
            raise ValueError("set_value requires a value")
        if self.kind is ActionKind.INVOKE and self.value is not None:
            raise ValueError("invoke takes no value")
        return self


class ActionResult(StrictModel):
    """Executor claim only. It is never evidence that the intended effect happened."""

    action_id: Annotated[str, Field(min_length=1)]
    request_id: Annotated[str, Field(min_length=1)]
    executed: bool
    platform_status: str
    elapsed_ms: Annotated[int, Field(ge=0)]


class PermissionState(StrEnum):
    GRANTED = "granted"
    DENIED = "denied"
    UNKNOWN = "unknown"


class Readiness(StrictModel):
    accessibility: PermissionState
    capture: PermissionState
    input_ready: bool
    gui_session: bool
    environment: EnvironmentKind


class Health(StrictModel):
    live: bool
    ready: bool
    uptime_ms: Annotated[int, Field(ge=0)]
    readiness: Readiness
    normalizer: GeneratorInfo
    protocol_version: str
    bridge_version: str

    @model_validator(mode="after")
    def _ready_requires_readiness(self) -> Health:
        r = self.readiness
        fully_ready = (
            self.live
            and r.accessibility is PermissionState.GRANTED
            and r.capture is PermissionState.GRANTED
            and r.gui_session
            and r.environment is not EnvironmentKind.UNKNOWN
        )
        if self.ready and not fully_ready:
            raise ValueError(
                "ready=true requires live, granted permissions, GUI session, known env"
            )
        return self


class ApplicationInfo(StrictModel):
    application: ApplicationRef
    display_name: str
    is_active: bool
    is_hidden: bool = False
    version_hash: str | None = None


class LaunchResult(StrictModel):
    application: ApplicationRef
    launched: bool
    already_running: bool


class ObserveRequest(StrictModel):
    application: ApplicationRef
    max_depth: Annotated[int, Field(ge=1, le=200)] = 40
    max_nodes: Annotated[int, Field(ge=1, le=100_000)] = 5000
    include_capture: bool = True


class CaptureRequest(StrictModel):
    application: ApplicationRef
    window: WindowRef | None = None


class CaptureResult(StrictModel):
    capture_id: Annotated[str, Field(pattern=r"^cap_[A-Za-z0-9_-]{1,64}$")]
    artifact: RawArtifactRef
    captured_at: AwareDatetime
