"""Deterministic, fail-closed risk classification of primitive actions.

Inputs are neutral observation facts only (role, label, action kind, enclosing dialog text,
whether a value is a generated probe). There is no override parameter: neither an LLM nor
any caller can change a decision. Approvals are a separate, explicit human record.

Rules v1 (generic English UI vocabulary; non-English or unlabelled controls fall to UNKNOWN,
which blocks mutation):
 1. Command vocabulary is read only from command-like elements (buttons, menu items,
    checkboxes, radios, popups, unknown actionable elements, and *field labels*). Data
    elements (rows, cells, static text) are never interpreted as commands: a row titled
    "Delete me" is data.
 2. DESTRUCTIVE beats UNKNOWN_HIGH_RISK beats everything else (conservative precedence).
 3. Confirmation buttons (ok/yes/confirm/continue/proceed/done/apply) inside a dialog or
    modal window inherit the strongest class found in that dialog's text.
 4. SET_VALUE on an editable field is INPUT, allowed only with a generated probe value;
    credential-like or high-risk field labels escalate.
 5. Anything unmatched is UNKNOWN. UNKNOWN mutations are blocked until a policy for them
    is approved (RESEARCH.md §10).
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from enum import StrEnum

from ghost._model import StrictModel
from ghost.platform.types import ActionKind, GeneratorInfo, Role

RISK_RULES = GeneratorInfo(name="risk-rules", version="1")
MINUS_SIGN = "\u2212"  # the typographic minus used on some "remove" buttons


class RiskClass(StrEnum):
    READ_ONLY = "READ_ONLY"
    NAVIGATION = "NAVIGATION"
    INPUT = "INPUT"
    REVERSIBLE_WRITE = "REVERSIBLE_WRITE"
    UNKNOWN = "UNKNOWN"
    UNKNOWN_HIGH_RISK = "UNKNOWN_HIGH_RISK"
    DESTRUCTIVE = "DESTRUCTIVE"


_DESTRUCTIVE = {
    "delete", "remove", "erase", "discard", "clear", "reset", "trash", "purge", "wipe",
    "destroy", "overwrite", "replace", "empty", "uninstall", "format", "revoke", "drop",
    "forget", "kill", "terminate", "-", MINUS_SIGN,
}  # fmt: skip
_DESTRUCTIVE_PHRASES = ("don't save", "do not save", "dont save")
_HIGH_RISK = {
    "send", "submit", "publish", "post", "share", "upload", "export", "purchase", "buy",
    "pay", "order", "checkout", "subscribe", "sync", "login", "logout", "signin", "signout",
    "invite", "email", "mail", "print", "call", "transfer", "install", "download",
    "authorize", "connect", "upgrade", "update", "password", "passcode", "card", "cvv",
    "ssn", "iban", "token", "secret",
}  # fmt: skip
_HIGH_RISK_PHRASES = ("sign in", "sign out", "log in", "log out", "api key", "credit card")
_WRITE = {
    "add", "new", "create", "insert", "save", "rename", "edit", "duplicate", "copy", "paste",
    "apply", "move", "pin", "unpin", "star", "favorite", "mark", "tag", "set", "enable",
    "disable", "+",
}  # fmt: skip
_NAVIGATION = {
    "open", "show", "view", "back", "forward", "next", "previous", "cancel", "close",
    "expand", "collapse", "more", "details", "settings", "preferences", "help", "about",
    "search", "find", "filter", "sort", "refresh", "reload", "hide", "select", "go",
}  # fmt: skip
_CONFIRM = {"ok", "yes", "confirm", "continue", "proceed", "done", "apply"}

_COMMAND_ROLES = {
    Role.BUTTON, Role.MENU_ITEM, Role.CHECKBOX, Role.RADIO, Role.POPUP, Role.UNKNOWN,
    Role.IMAGE, Role.TAB, Role.MENU,
}  # fmt: skip
_DATA_ROLES = {Role.ROW, Role.CELL, Role.STATIC_TEXT, Role.LIST, Role.TABLE}
_EDITABLE_ROLES = {Role.TEXT_FIELD, Role.TEXT_AREA}
_STRENGTH = {
    RiskClass.READ_ONLY: 0,
    RiskClass.NAVIGATION: 1,
    RiskClass.INPUT: 2,
    RiskClass.REVERSIBLE_WRITE: 3,
    RiskClass.UNKNOWN: 4,
    RiskClass.UNKNOWN_HIGH_RISK: 5,
    RiskClass.DESTRUCTIVE: 6,
}


class RiskInput(StrictModel):
    """Neutral facts about one candidate action. Built by deterministic code only."""

    action: ActionKind
    role: Role
    label: str | None
    in_dialog: bool = False
    dialog_text: tuple[str, ...] = ()
    value_is_probe: bool = False


class RiskDecision(StrictModel):
    risk_class: RiskClass
    rule_id: str
    reasons: tuple[str, ...]
    rules: GeneratorInfo = RISK_RULES


def _tokens(text: str | None) -> tuple[set[str], str]:
    lowered = (text or "").lower().strip()
    words = set(re.findall(r"[a-z]+|[+\-" + MINUS_SIGN + "]", lowered))
    return words, lowered


def _lexical_class(text: str | None) -> tuple[RiskClass | None, str]:
    words, lowered = _tokens(text)
    if words & _DESTRUCTIVE or any(p in lowered for p in _DESTRUCTIVE_PHRASES):
        return RiskClass.DESTRUCTIVE, "lexicon:destructive"
    if words & _HIGH_RISK or any(p in lowered for p in _HIGH_RISK_PHRASES):
        return RiskClass.UNKNOWN_HIGH_RISK, "lexicon:high-risk"
    if words & _WRITE:
        return RiskClass.REVERSIBLE_WRITE, "lexicon:write"
    if words & _NAVIGATION:
        return RiskClass.NAVIGATION, "lexicon:navigation"
    return None, "lexicon:none"


def _strongest(texts: Iterable[str]) -> RiskClass | None:
    found = [c for c, _ in (_lexical_class(t) for t in texts) if c is not None]
    return max(found, key=_STRENGTH.__getitem__) if found else None


def classify(fact: RiskInput) -> RiskDecision:
    """Deterministic classification. Pure function of ``fact``; no overrides."""
    label = fact.label
    if fact.action is ActionKind.SET_VALUE:
        if fact.role not in _EDITABLE_ROLES and fact.role is not Role.POPUP:
            return RiskDecision(
                risk_class=RiskClass.UNKNOWN, rule_id="set-value:non-editable", reasons=()
            )
        lexical, rule = _lexical_class(label)
        if lexical in (RiskClass.DESTRUCTIVE, RiskClass.UNKNOWN_HIGH_RISK):
            return RiskDecision(
                risk_class=lexical, rule_id=f"field-label:{rule}", reasons=(label or "",)
            )
        return RiskDecision(risk_class=RiskClass.INPUT, rule_id="set-value:field", reasons=())
    if fact.role in _DATA_ROLES:
        # Invoking a data element selects or opens it; its text is data, never a command.
        return RiskDecision(
            risk_class=RiskClass.NAVIGATION, rule_id="invoke:data-element", reasons=()
        )
    if fact.role is Role.TAB:
        return RiskDecision(risk_class=RiskClass.NAVIGATION, rule_id="invoke:tab", reasons=())
    if fact.role not in _COMMAND_ROLES or not (label and label.strip()):
        return RiskDecision(
            risk_class=RiskClass.UNKNOWN, rule_id="invoke:unlabelled-or-unknown-role", reasons=()
        )
    words, _ = _tokens(label)
    if fact.in_dialog and words & _CONFIRM:
        inherited = _strongest(fact.dialog_text)
        if inherited is not None:
            return RiskDecision(
                risk_class=inherited, rule_id="confirm:inherits-dialog", reasons=fact.dialog_text
            )
        return RiskDecision(
            risk_class=RiskClass.UNKNOWN, rule_id="confirm:unexplained-dialog", reasons=()
        )
    lexical, rule = _lexical_class(label)
    if lexical is None and fact.role in (Role.CHECKBOX, Role.RADIO):
        return RiskDecision(
            risk_class=RiskClass.REVERSIBLE_WRITE, rule_id="invoke:toggle", reasons=()
        )
    if lexical is None and fact.role in (Role.POPUP, Role.MENU):
        return RiskDecision(
            risk_class=RiskClass.NAVIGATION, rule_id="invoke:open-chooser", reasons=()
        )
    if lexical is None:
        return RiskDecision(risk_class=RiskClass.UNKNOWN, rule_id=rule, reasons=(label,))
    return RiskDecision(risk_class=lexical, rule_id=rule, reasons=(label,))
