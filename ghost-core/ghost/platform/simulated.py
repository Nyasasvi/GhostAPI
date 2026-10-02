"""Synthetic platform: raw capture schema, its normalizer, and the simulated-app interface.

This is the platform the MockPlatformBridge speaks. Its raw capture format
(``synthetic-raw/1``) is deliberately *not* modelled on any real accessibility API: it is
its own schema with its own vocabulary, translated to neutral DTOs by a versioned
normalizer, exactly as MacOSBridge will translate its raw capture. Results produced
through it are SYNTHETIC_FIXTURE evidence at best, never REAL_VM evidence.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Annotated, Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from ghost.platform.types import (
    ActionKind,
    ApplicationRef,
    BoolValue,
    ElementRef,
    ElementState,
    GeneratorInfo,
    NumberValue,
    PlatformObservation,
    Rect,
    Role,
    StringValue,
    Truncation,
    TruncationReason,
    TypedValue,
    UIElement,
    WindowInfo,
    WindowObservation,
    WindowRef,
)

SYNTHETIC_RAW_FORMAT = "synthetic-raw/1"
SYNTHETIC_RAW_MEDIA_TYPE = "application/vnd.ghost.synthetic-raw+json"
SYNTHETIC_CAPTURE_MEDIA_TYPE = "application/vnd.ghost.synthetic-capture+json"
SYNTHETIC_NORMALIZER = GeneratorInfo(name="synthetic-normalizer", version="1")

# Versioned vocabulary of the synthetic platform (part of SYNTHETIC_NORMALIZER v1).
KIND_TO_ROLE: dict[str, Role] = {
    "panel": Role.GROUP,
    "push_button": Role.BUTTON,
    "text_input": Role.TEXT_FIELD,
    "text_block": Role.TEXT_AREA,
    "label": Role.STATIC_TEXT,
    "list_view": Role.LIST,
    "list_row": Role.ROW,
    "tool_strip": Role.TOOLBAR,
    "menu_strip": Role.MENU_BAR,
    "menu": Role.MENU,
    "menu_entry": Role.MENU_ITEM,
    "check": Role.CHECKBOX,
    "chooser": Role.POPUP,
    "sheet": Role.DIALOG,
    "tab": Role.TAB,
}
ACT_TO_ACTION: dict[str, ActionKind] = {"click": ActionKind.INVOKE, "assign": ActionKind.SET_VALUE}
FLAG_TO_STATE: dict[str, ElementState] = {
    "focused": ElementState.FOCUSED,
    "selected": ElementState.SELECTED,
    "disabled": ElementState.DISABLED,
    "checked": ElementState.CHECKED,
    "expanded": ElementState.EXPANDED,
    "editable": ElementState.EDITABLE,
}


class _RawModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class RawContent(_RawModel):
    type: Literal["string", "bool", "number"]
    value: str | bool | float

    @model_validator(mode="after")
    def _typed(self) -> RawContent:
        expected = {"string": str, "bool": bool, "number": float}[self.type]
        if type(self.value) is not expected:
            raise ValueError(f"content value does not match type {self.type}")
        return self


class RawNode(_RawModel):
    id: Annotated[str, Field(min_length=1)]
    kind: str
    text: str | None = None
    content: RawContent | None = None
    flags: list[str] = []
    acts: list[str] = []
    uid: str | None = None
    frame: Annotated[list[float], Field(min_length=4, max_length=4)] | None = None
    kids: list[RawNode] = []
    partial: bool = False


class RawWindow(_RawModel):
    wid: Annotated[str, Field(pattern=r"^[A-Za-z0-9_-]{1,64}$")]
    title: str | None = None
    frame: Annotated[list[float], Field(min_length=4, max_length=4)] | None = None
    focused: bool = False
    main: bool = False
    minimized: bool = False
    modal: bool = False
    root: RawNode


class RawCapture(_RawModel):
    format: Literal["synthetic-raw/1"]
    windows: list[RawWindow]
    focus: str | None = None
    noise: dict[str, str | int | float] = {}


class NormalizationError(Exception):
    """The raw capture could not be normalized; the raw evidence is still retained."""


class SimulatedActionRejectedError(Exception):
    """The simulated app refused an action (for example, the element is disabled)."""


class SimulatedElementGoneError(Exception):
    """The element a handle pointed at no longer exists in the simulated app."""


class SimulatedDisk:
    """Environment-owned persistence for a simulated app; survives app relaunch.

    Only the simulated app and development oracles read it. Discovery code never does.
    """

    def __init__(self) -> None:
        self._files: dict[str, str] = {}

    def read(self, name: str) -> str | None:
        return self._files.get(name)

    def write(self, name: str, text: str) -> None:
        self._files[name] = text

    def snapshot(self) -> dict[str, str]:
        return dict(self._files)


class SimulatedApp(Protocol):
    """Generic interface the MockPlatformBridge drives. It carries no app knowledge itself."""

    @property
    def display_name(self) -> str: ...

    def raw_capture(self) -> dict[str, object]:
        """A JSON-serializable ``synthetic-raw/1`` document describing the current UI."""
        ...

    def perform(self, node_id: str, action: ActionKind, value: TypedValue | None) -> None:
        """Apply an action. Raises SimulatedActionRejectedError or SimulatedElementGoneError."""
        ...

    def tick(self, elapsed_ms: int) -> None:
        """Advance simulated time (volatile UI, delayed persistence)."""
        ...


SimulatedAppFactory = Callable[[SimulatedDisk], SimulatedApp]


def parse_raw_capture(document: object) -> RawCapture:
    try:
        return RawCapture.model_validate(document)
    except ValidationError as error:
        raise NormalizationError(f"malformed {SYNTHETIC_RAW_FORMAT} capture: {error}") from error


def _rect(frame: list[float] | None) -> Rect | None:
    if frame is None:
        return None
    return Rect(x=frame[0], y=frame[1], w=frame[2], h=frame[3])


def _value(content: RawContent | None) -> TypedValue | None:
    if content is None:
        return None
    if content.type == "string" and isinstance(content.value, str):
        return StringValue(value=content.value)
    if content.type == "bool" and isinstance(content.value, bool):
        return BoolValue(value=content.value)
    if isinstance(content.value, float):
        return NumberValue(value=content.value)
    raise NormalizationError("inconsistent raw content")


class _Normalizer:
    def __init__(
        self, application: ApplicationRef, generation: int, max_depth: int, max_nodes: int
    ):
        self.application = application
        self.generation = generation
        self.max_depth = max_depth
        self.max_nodes = max_nodes
        self.handles: dict[int, str] = {}
        self.reasons: set[TruncationReason] = set()
        self.seen: set[str] = set()

    def element(self, node: RawNode, depth: int) -> UIElement:
        if node.id in self.seen:
            raise NormalizationError(f"duplicate raw node id {node.id!r}")
        self.seen.add(node.id)
        index = len(self.handles)
        self.handles[index] = node.id
        truncated = node.partial
        if node.partial:
            self.reasons.add(TruncationReason.VIRTUALIZED)
        children: list[UIElement] = []
        if node.kids and depth >= self.max_depth:
            truncated = True
            self.reasons.add(TruncationReason.MAX_DEPTH)
        else:
            for kid in node.kids:
                if len(self.handles) >= self.max_nodes:
                    truncated = True
                    self.reasons.add(TruncationReason.MAX_NODES)
                    break
                children.append(self.element(kid, depth + 1))
        states = sorted({FLAG_TO_STATE[f] for f in node.flags if f in FLAG_TO_STATE})
        actions = sorted({ACT_TO_ACTION[a] for a in node.acts if a in ACT_TO_ACTION})
        return UIElement(
            ref=ElementRef(application=self.application, generation=self.generation, index=index),
            role=KIND_TO_ROLE.get(node.kind, Role.UNKNOWN),
            label=node.text,
            value=_value(node.content),
            states=tuple(states),
            actions=tuple(actions),
            bounds=_rect(node.frame),
            stable_id_hint=node.uid,
            children=tuple(children),
            truncated=truncated,
        )


def normalize_synthetic(
    document: object,
    *,
    application: ApplicationRef,
    generation: int,
    observation_id: str,
    raw_capture_id: str,
    max_depth: int = 40,
    max_nodes: int = 5000,
) -> tuple[PlatformObservation, dict[int, str]]:
    """Translate a ``synthetic-raw/1`` capture into a PlatformObservation.

    Returns the observation and the handle table (element index -> raw node id) for this
    generation. Pure and deterministic: the same raw document always yields the same output.
    """
    capture = parse_raw_capture(document)
    norm = _Normalizer(application, generation, max_depth, max_nodes)
    windows = []
    for raw_window in capture.windows:
        root = norm.element(raw_window.root, 0)
        info = WindowInfo(
            ref=WindowRef(ref=f"win_{raw_window.wid}"),
            title=raw_window.title,
            bounds=_rect(raw_window.frame),
            focused=raw_window.focused,
            main=raw_window.main,
            minimized=raw_window.minimized,
            modal=raw_window.modal,
        )
        windows.append(WindowObservation(info=info, root=root))
    focused: ElementRef | None = None
    if capture.focus is not None:
        index = next((i for i, nid in norm.handles.items() if nid == capture.focus), None)
        if index is None:
            raise NormalizationError(f"focus refers to unknown node {capture.focus!r}")
        focused = ElementRef(application=application, generation=generation, index=index)
    reasons = tuple(sorted(norm.reasons))
    observation = PlatformObservation(
        observation_id=observation_id,
        raw_capture_id=raw_capture_id,
        application=application,
        generation=generation,
        platform="synthetic",
        normalizer=SYNTHETIC_NORMALIZER,
        windows=tuple(windows),
        focused=focused,
        truncation=Truncation(truncated=bool(reasons), reasons=reasons),
    )
    return observation, norm.handles
