"""Risk policy gate: risk decision + environment + explicit human approval -> allow/block.

Policy (AGENTS invariant 4, RESEARCH.md §10; UNKNOWN fails closed until a policy is approved):
  READ_ONLY, NAVIGATION   allowed
  INPUT                   allowed only with a generated probe value, in a disposable env
  REVERSIBLE_WRITE        allowed only in a disposable environment
  UNKNOWN                 blocked (fail closed)
  UNKNOWN_HIGH_RISK,      blocked unless a matching APPROVED human approval record exists
  DESTRUCTIVE             (and still only in a disposable environment)
"""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated

from pydantic import Field

from ghost._model import StrictModel
from ghost.exploration.risk import RiskClass, RiskDecision


class ApprovalDecision(StrEnum):
    APPROVED = "approved"
    DENIED = "denied"


class ApprovalRecord(StrictModel):
    """A human decision about one specific action. Describes evidence, never semantics."""

    approval_id: Annotated[str, Field(pattern=r"^apr_[A-Za-z0-9_-]{1,64}$")]
    action_key: Annotated[str, Field(min_length=1)]
    risk_class: RiskClass
    decision: ApprovalDecision
    decided_by: Annotated[str, Field(min_length=1)]
    subject: Annotated[str, Field(min_length=1)]


class ApprovalLedger:
    """In-memory lookup of recorded approvals (persisted by the storage layer later)."""

    def __init__(self, records: tuple[ApprovalRecord, ...] = ()) -> None:
        self._records: dict[tuple[str, RiskClass], ApprovalRecord] = {}
        for record in records:
            self.add(record)

    def add(self, record: ApprovalRecord) -> None:
        key = (record.action_key, record.risk_class)
        if key in self._records:
            raise ValueError(f"approval already recorded for {key}")
        self._records[key] = record

    def lookup(self, action_key: str, risk_class: RiskClass) -> ApprovalRecord | None:
        return self._records.get((action_key, risk_class))


class Gate(StrEnum):
    ALLOWED = "allowed"
    BLOCKED_NEEDS_APPROVAL = "blocked_needs_approval"
    BLOCKED_UNKNOWN_MUTATION = "blocked_unknown_mutation"
    BLOCKED_INPUT_NOT_PROBE = "blocked_input_not_probe"
    BLOCKED_NOT_DISPOSABLE = "blocked_not_disposable"
    DENIED_BY_APPROVAL = "denied_by_approval"


class PolicyVerdict(StrictModel):
    allowed: bool
    gate: Gate
    approval_id: str | None = None


def evaluate(
    decision: RiskDecision,
    *,
    action_key: str,
    value_is_probe: bool,
    disposable: bool,
    approvals: ApprovalLedger,
) -> PolicyVerdict:
    risk = decision.risk_class
    if risk in (RiskClass.READ_ONLY, RiskClass.NAVIGATION):
        return PolicyVerdict(allowed=True, gate=Gate.ALLOWED)
    if not disposable:
        return PolicyVerdict(allowed=False, gate=Gate.BLOCKED_NOT_DISPOSABLE)
    if risk is RiskClass.INPUT:
        if not value_is_probe:
            return PolicyVerdict(allowed=False, gate=Gate.BLOCKED_INPUT_NOT_PROBE)
        return PolicyVerdict(allowed=True, gate=Gate.ALLOWED)
    if risk is RiskClass.REVERSIBLE_WRITE:
        return PolicyVerdict(allowed=True, gate=Gate.ALLOWED)
    if risk is RiskClass.UNKNOWN:
        return PolicyVerdict(allowed=False, gate=Gate.BLOCKED_UNKNOWN_MUTATION)
    record = approvals.lookup(action_key, risk)
    if record is None:
        return PolicyVerdict(allowed=False, gate=Gate.BLOCKED_NEEDS_APPROVAL)
    if record.decision is ApprovalDecision.DENIED:
        return PolicyVerdict(
            allowed=False, gate=Gate.DENIED_BY_APPROVAL, approval_id=record.approval_id
        )
    return PolicyVerdict(allowed=True, gate=Gate.ALLOWED, approval_id=record.approval_id)
