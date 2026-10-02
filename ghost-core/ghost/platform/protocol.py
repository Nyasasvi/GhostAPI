"""The PlatformBridge contract: the only way Ghost Core reaches a platform.

``Ghost Core -> PlatformBridge -> MacOSBridge`` (MacOSBridge is the only real implementation
planned for the research phase and is BLOCKED_VM_STORAGE). ``MockPlatformBridge`` implements
the same contract for deterministic host-side development and contract tests.

The contract deliberately exposes no shell, no filesystem, no coordinate clicks, and no
generic keyboard input. Element handles are observation-scoped (``ElementRef.generation``).

Wire decoding (the future HTTP client) must use ``Model.model_validate_json``: the strict
models deliberately reject Python-mode coercions such as lists for tuples.
"""

from __future__ import annotations

import hashlib
import time
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
# The complete contract surface. A contract test freezes it: adding shell, filesystem,
# coordinate-click, or generic keyboard operations must fail review loudly.
CONTRACT_OPERATIONS: frozenset[str] = MUTATING_OPERATIONS | READ_OPERATIONS


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

    @classmethod
    def derived(cls, correlation_id: str, sequence: int, deadline_ms: int) -> RequestContext:
        """Deterministic request id for reproducible runs (unique per correlation+sequence)."""
        digest = hashlib.sha256(f"{correlation_id}#{sequence}".encode()).hexdigest()[:32]
        return cls(request_id=digest, correlation_id=correlation_id, deadline_ms=deadline_ms)


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


class RetryingReader:
    """Read-only view of a PlatformBridge that retries retryable read failures.

    It exposes *only* read operations, so no mutation can be retried through it. Every
    attempt reuses the caller's request id; the deadline shrinks by the time already
    spent; backoff is deterministic (``backoff_ms * 2**attempt``).
    """

    def __init__(
        self,
        bridge: PlatformBridge,
        *,
        max_retries: int = 2,
        backoff_ms: int = 50,
        clock_ms: Callable[[], int] | None = None,
        sleep_ms: Callable[[int], None] | None = None,
    ) -> None:
        if not 0 <= max_retries <= 2:
            raise ValueError("max_retries must be between 0 and 2")
        self._bridge = bridge
        self._max_retries = max_retries
        self._backoff_ms = backoff_ms
        self._clock_ms = clock_ms or (lambda: time.monotonic_ns() // 1_000_000)
        self._sleep_ms = sleep_ms or (lambda ms: time.sleep(ms / 1000))

    def health(self, ctx: RequestContext) -> Health:
        return self._retry(ctx, lambda c: self._bridge.health(c))

    def list_applications(self, ctx: RequestContext) -> tuple[ApplicationInfo, ...]:
        return self._retry(ctx, lambda c: self._bridge.list_applications(c))

    def list_windows(
        self, ctx: RequestContext, application: ApplicationRef
    ) -> tuple[WindowInfo, ...]:
        return self._retry(ctx, lambda c: self._bridge.list_windows(c, application))

    def observe(self, ctx: RequestContext, request: ObserveRequest) -> ObservationBundle:
        return self._retry(ctx, lambda c: self._bridge.observe(c, request))

    def capture(self, ctx: RequestContext, request: CaptureRequest) -> CaptureResult:
        return self._retry(ctx, lambda c: self._bridge.capture(c, request))

    def get_artifact(self, ctx: RequestContext, artifact_id: str) -> bytes:
        return self._retry(ctx, lambda c: self._bridge.get_artifact(c, artifact_id))

    def _retry[T](self, ctx: RequestContext, call: Callable[[RequestContext], T]) -> T:
        started = self._clock_ms()
        attempt = 0
        current = ctx
        while True:
            try:
                return call(current)
            except BridgeError as error:
                if not error.retryable_for(mutating=False) or attempt >= self._max_retries:
                    raise
                wait = self._backoff_ms * 2**attempt
                remaining = ctx.deadline_ms - (self._clock_ms() - started) - wait
                if remaining <= 0:
                    raise
                self._sleep_ms(wait)
                attempt += 1
                current = ctx.model_copy(update={"deadline_ms": remaining})
