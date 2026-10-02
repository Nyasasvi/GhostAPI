"""The PlatformBridge contract: the only way Ghost Core reaches a platform.

``Ghost Core -> PlatformBridge -> MacOSBridge`` (MacOSBridge is the only real implementation
planned for the research phase and is BLOCKED_VM_STORAGE). ``MockPlatformBridge`` implements
the same contract for deterministic host-side development and contract tests.

The contract deliberately exposes no shell, no filesystem, no coordinate clicks, and no
generic keyboard input. Element handles are observation-scoped (``ElementRef.generation``).
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from typing import Annotated, Protocol, runtime_checkable

from pydantic import Field

from ghost._model import StrictModel
from ghost.platform.errors import BridgeError
from ghost.platform.types import (
    ActionResult,
    ApplicationInfo,
    ApplicationRef,
    CaptureRequest,
    CaptureResult,
    ElementRef,
    Health,
    LaunchRef,
    LaunchResult,
    ObservationBundle,
    ObserveRequest,
    TypedValue,
    WindowInfo,
)

PROTOCOL_VERSION = "1"
MAX_DEADLINE_MS = 120_000

MUTATING_OPERATIONS: frozenset[str] = frozenset({"launch", "invoke", "set_value"})
READ_OPERATIONS: frozenset[str] = frozenset(
    {"health", "list_applications", "list_windows", "observe", "capture", "get_artifact"}
)


class RequestContext(StrictModel):
    """Per-call envelope: request id (dedupe key), correlation id (lineage), deadline."""

    request_id: Annotated[str, Field(pattern=r"^[0-9a-f]{32}$")]
    correlation_id: Annotated[str, Field(min_length=1, max_length=200)]
    deadline_ms: Annotated[int, Field(gt=0, le=MAX_DEADLINE_MS)]

    @classmethod
    def new(cls, correlation_id: str, deadline_ms: int) -> RequestContext:
        return cls(
            request_id=uuid.uuid4().hex, correlation_id=correlation_id, deadline_ms=deadline_ms
        )


@runtime_checkable
class PlatformBridge(Protocol):
    """Neutral platform contract. Implementations raise ``BridgeError`` on every failure."""

    @property
    def platform(self) -> str:
        """Short platform identifier recorded in evidence (e.g. ``synthetic``, ``macos``)."""
        ...

    def health(self, ctx: RequestContext) -> Health: ...

    def list_applications(self, ctx: RequestContext) -> tuple[ApplicationInfo, ...]: ...

    def list_windows(
        self, ctx: RequestContext, application: ApplicationRef
    ) -> tuple[WindowInfo, ...]: ...

    def launch(self, ctx: RequestContext, launch_ref: LaunchRef) -> LaunchResult:
        """Mutation. Never retried automatically; a repeated request id returns the first result."""
        ...

    def observe(self, ctx: RequestContext, request: ObserveRequest) -> ObservationBundle:
        """Capture a RawObservation (stored as an artifact first) and its PlatformObservation.

        Each call starts a new observation generation; all older element handles go stale.
        """
        ...

    def capture(self, ctx: RequestContext, request: CaptureRequest) -> CaptureResult: ...

    def get_artifact(self, ctx: RequestContext, artifact_id: str) -> bytes:
        """Bounded raw bytes of a captured artifact. Callers must verify the hash."""
        ...

    def invoke(self, ctx: RequestContext, element: ElementRef) -> ActionResult:
        """Mutation (executor claim only). Stale handles raise ``STALE_HANDLE``."""
        ...

    def set_value(
        self, ctx: RequestContext, element: ElementRef, value: TypedValue
    ) -> ActionResult:
        """Mutation (executor claim only). Stale handles raise ``STALE_HANDLE``."""
        ...


def retry_read[T](operation: str, call: Callable[[], T], *, max_retries: int = 2) -> T:
    """Retry a *read* operation on retryable bridge errors, reusing the same request.

    Mutations are refused outright: an automatic retry could execute an action twice.
    """
    if operation in MUTATING_OPERATIONS:
        raise ValueError(f"refusing to retry mutating operation {operation!r}")
    if operation not in READ_OPERATIONS:
        raise ValueError(f"unknown bridge operation {operation!r}")
    if not 0 <= max_retries <= 2:
        raise ValueError("max_retries must be between 0 and 2")
    attempt = 0
    while True:
        try:
            return call()
        except BridgeError as error:
            if not error.retryable_for_reads or attempt >= max_retries:
                raise
            attempt += 1
