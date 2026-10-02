"""Typed, stable bridge errors (neutral wire contract)."""

from __future__ import annotations

from collections.abc import Mapping
from enum import StrEnum

from ghost._model import StrictModel


class BridgeErrorCode(StrEnum):
    INVALID_REQUEST = "INVALID_REQUEST"
    UNAUTHORIZED = "UNAUTHORIZED"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    APP_NOT_FOUND = "APP_NOT_FOUND"
    WINDOW_NOT_FOUND = "WINDOW_NOT_FOUND"
    ELEMENT_NOT_FOUND = "ELEMENT_NOT_FOUND"
    ARTIFACT_NOT_FOUND = "ARTIFACT_NOT_FOUND"
    STALE_HANDLE = "STALE_HANDLE"
    BUSY = "BUSY"
    ACTION_UNSUPPORTED = "ACTION_UNSUPPORTED"
    PAYLOAD_TOO_LARGE = "PAYLOAD_TOO_LARGE"
    PLATFORM_ERROR = "PLATFORM_ERROR"
    CAPTURE_FAILED = "CAPTURE_FAILED"
    TIMEOUT = "TIMEOUT"
    NOT_IN_SANDBOX = "NOT_IN_SANDBOX"
    PROTOCOL_MISMATCH = "PROTOCOL_MISMATCH"


# Retryability for *read* operations. Mutations are never retried automatically, whatever
# the code says (AGENTS rule 11), so the wire body is computed per operation.
_RETRYABLE_READ: frozenset[BridgeErrorCode] = frozenset(
    {
        BridgeErrorCode.BUSY,
        BridgeErrorCode.PLATFORM_ERROR,
        BridgeErrorCode.CAPTURE_FAILED,
        BridgeErrorCode.TIMEOUT,
    }
)


class BridgeErrorBody(StrictModel):
    code: BridgeErrorCode
    message: str
    retryable: bool
    detail: tuple[tuple[str, str], ...] = ()


class BridgeError(Exception):
    """Raised by every PlatformBridge implementation; never swallowed silently."""

    def __init__(
        self,
        code: BridgeErrorCode,
        message: str,
        *,
        detail: Mapping[str, str] | None = None,
    ) -> None:
        super().__init__(f"{code.value}: {message}")
        self.code = code
        self.message = message
        self.detail: dict[str, str] = dict(detail or {})

    @property
    def retryable_for_reads(self) -> bool:
        return self.code in _RETRYABLE_READ

    def retryable_for(self, *, mutating: bool) -> bool:
        """Mutations are never retryable on the wire, whatever the error code."""
        return not mutating and self.retryable_for_reads

    def body(self, *, mutating: bool) -> BridgeErrorBody:
        return BridgeErrorBody(
            code=self.code,
            message=self.message,
            retryable=self.retryable_for(mutating=mutating),
            detail=tuple(sorted(self.detail.items())),
        )
