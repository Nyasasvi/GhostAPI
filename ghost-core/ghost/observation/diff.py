"""Structured state diff between two CanonicalStates.

The diff reports *observations* (elements added/removed, properties changed, focus moved,
windows changed). It never reports meanings such as "document created".

Children are matched first by their labelled step (role, stable id, label, ordinal). Any
remaining same-role children are then paired by position, and those changes are marked
``match="positional"``. That keeps the ambiguity visible: a positional label change could
equally be "one element removed, another added". Nothing here decides which.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

from ghost._model import StrictModel, canonical_json
from ghost.observation.canonical import (
    CanonicalNode,
    CanonicalState,
    CanonicalWindow,
    element_step,
    with_ordinals,
)
from ghost.platform.types import GeneratorInfo, Role

DIFFER = GeneratorInfo(name="state-diff", version="1")


class ChangeKind(StrEnum):
    ELEMENT_ADDED = "element_added"
    ELEMENT_REMOVED = "element_removed"
    LABEL_CHANGED = "label_changed"
    VALUE_CHANGED = "value_changed"
    STATES_CHANGED = "states_changed"
    ACTIONS_CHANGED = "actions_changed"
    STABLE_ID_CHANGED = "stable_id_changed"
    TRUNCATION_CHANGED = "truncation_changed"
    WINDOW_ADDED = "window_added"
    WINDOW_REMOVED = "window_removed"
    WINDOW_CHANGED = "window_changed"
    FOCUS_CHANGED = "focus_changed"
    WINDOW_GEOMETRY_CHANGED = "window_geometry_changed"
    VOLATILE_VALUE_CHANGED = "volatile_value_changed"


class Change(StrictModel):
    kind: ChangeKind
    path: str
    role: Role | None = None
    before: str | None = None
    after: str | None = None
    match: Literal["key", "positional", "none"] = "key"
    subtree_size: int = 1
    affects_identity: bool = True


class StateDiff(StrictModel):
    differ: GeneratorInfo
    from_fingerprint: str
    to_fingerprint: str
    same_identity: bool
    changes: tuple[Change, ...]

    def of_kind(self, kind: ChangeKind) -> tuple[Change, ...]:
        return tuple(c for c in self.changes if c.kind is kind)


def _j(value: object) -> str:
    return canonical_json(value)


def _size(node: CanonicalNode) -> int:
    return 1 + sum(_size(c) for c in node.children)


def _child_key(node: CanonicalNode) -> str:
    return element_step(node.role, node.label, node.stable_id_hint)


def _keyed(children: tuple[CanonicalNode, ...]) -> list[tuple[str, CanonicalNode]]:
    keys = with_ordinals(_child_key(child) for child in children)
    return list(zip(keys, children, strict=True))


class _Differ:
    def __init__(self) -> None:
        self.changes: list[Change] = []

    def add(self, **kwargs: object) -> None:
        self.changes.append(Change.model_validate(kwargs, strict=False))

    def fields(self, a: CanonicalNode, b: CanonicalNode, path: str, match: str) -> None:
        role = b.role
        if a.label != b.label:
            self.add(
                kind=ChangeKind.LABEL_CHANGED,
                path=path,
                role=role,
                before=_j(a.label),
                after=_j(b.label),
                match=match,
            )
        if a.value != b.value:
            before = a.value.model_dump(mode="json") if a.value else None
            after = b.value.model_dump(mode="json") if b.value else None
            self.add(
                kind=ChangeKind.VALUE_CHANGED,
                path=path,
                role=role,
                before=_j(before),
                after=_j(after),
                match=match,
            )
        if a.states != b.states:
            self.add(
                kind=ChangeKind.STATES_CHANGED,
                path=path,
                role=role,
                before=_j([s.value for s in a.states]),
                after=_j([s.value for s in b.states]),
                match=match,
            )
        if a.actions != b.actions:
            self.add(
                kind=ChangeKind.ACTIONS_CHANGED,
                path=path,
                role=role,
                before=_j([x.value for x in a.actions]),
                after=_j([x.value for x in b.actions]),
                match=match,
            )
        if a.stable_id_hint != b.stable_id_hint:
            self.add(
                kind=ChangeKind.STABLE_ID_CHANGED,
                path=path,
                role=role,
                before=_j(a.stable_id_hint),
                after=_j(b.stable_id_hint),
                match=match,
            )
        if a.truncated != b.truncated:
            self.add(
                kind=ChangeKind.TRUNCATION_CHANGED,
                path=path,
                role=role,
                before=_j(a.truncated),
                after=_j(b.truncated),
                match=match,
            )

    def node(self, a: CanonicalNode, b: CanonicalNode, path: str, match: str) -> None:
        self.fields(a, b, path, match)
        left, right = _keyed(a.children), _keyed(b.children)
        right_keys = {k for k, _ in right}
        left_keys = {k for k, _ in left}
        for key, child in left:
            if key in right_keys:
                self.node(child, dict(right)[key], f"{path}/{key}", match)
        lost = [(k, c) for k, c in left if k not in right_keys]
        new = [(k, c) for k, c in right if k not in left_keys]
        for role in sorted({c.role for _, c in lost} & {c.role for _, c in new}):
            olds = [(k, c) for k, c in lost if c.role is role]
            news = [(k, c) for k, c in new if c.role is role]
            for (old_key, old), (new_key, fresh) in zip(olds, news, strict=False):
                self.node(old, fresh, f"{path}/{new_key}", "positional")
                lost.remove((old_key, old))
                new.remove((new_key, fresh))
        for key, child in lost:
            self.add(
                kind=ChangeKind.ELEMENT_REMOVED,
                path=f"{path}/{key}",
                role=child.role,
                match="none",
                subtree_size=_size(child),
            )
        for key, child in new:
            self.add(
                kind=ChangeKind.ELEMENT_ADDED,
                path=f"{path}/{key}",
                role=child.role,
                match="none",
                subtree_size=_size(child),
            )

    def window(self, a: CanonicalWindow, b: CanonicalWindow) -> None:
        if (a.title, a.modal, a.minimized) != (b.title, b.modal, b.minimized):
            self.add(
                kind=ChangeKind.WINDOW_CHANGED,
                path=b.key,
                role=Role.WINDOW,
                before=_j([a.title, a.modal, a.minimized]),
                after=_j([b.title, b.modal, b.minimized]),
            )
        root_key = f"{_child_key(b.root)}#0"
        if _child_key(a.root) == _child_key(b.root):
            self.node(a.root, b.root, f"{b.key}/{root_key}", "key")
        else:
            self.node(a.root, b.root, f"{b.key}/{root_key}", "positional")


def diff_states(before: CanonicalState, after: CanonicalState) -> StateDiff:
    """Deterministic structured diff. Both states must come from the same canonicalizer."""
    if before.canonicalizer != after.canonicalizer or before.mask_id != after.mask_id:
        raise ValueError("cannot diff states from different canonicalizers or masks")
    differ = _Differ()
    left = {w.key: w for w in before.windows}
    right = {w.key: w for w in after.windows}
    for key in sorted(left.keys() & right.keys()):
        differ.window(left[key], right[key])
    for key in sorted(left.keys() - right.keys()):
        differ.add(
            kind=ChangeKind.WINDOW_REMOVED,
            path=key,
            role=Role.WINDOW,
            match="none",
            subtree_size=_size(left[key].root),
        )
    for key in sorted(right.keys() - left.keys()):
        differ.add(
            kind=ChangeKind.WINDOW_ADDED,
            path=key,
            role=Role.WINDOW,
            match="none",
            subtree_size=_size(right[key].root),
        )
    vb, va = before.volatile, after.volatile
    if vb.focused_path != va.focused_path:
        differ.add(
            kind=ChangeKind.FOCUS_CHANGED,
            path=va.focused_path or "",
            before=_j(vb.focused_path),
            after=_j(va.focused_path),
            match="none",
            affects_identity=False,
        )
    old_bounds, new_bounds = dict(vb.window_bounds), dict(va.window_bounds)
    for key in sorted(old_bounds.keys() & new_bounds.keys()):
        if old_bounds[key] != new_bounds[key]:
            old, new = old_bounds[key], new_bounds[key]
            differ.add(
                kind=ChangeKind.WINDOW_GEOMETRY_CHANGED,
                path=key,
                role=Role.WINDOW,
                match="key",
                before=_j(old.model_dump(mode="json") if old else None),
                after=_j(new.model_dump(mode="json") if new else None),
                affects_identity=False,
            )
    old_masked = {(p, f): v for p, f, v in vb.masked_values}
    new_masked = {(p, f): v for p, f, v in va.masked_values}
    for path, field in sorted(old_masked.keys() | new_masked.keys()):
        if old_masked.get((path, field)) != new_masked.get((path, field)):
            differ.add(
                kind=ChangeKind.VOLATILE_VALUE_CHANGED,
                path=f"{path}#{field}",
                before=old_masked.get((path, field)),
                after=new_masked.get((path, field)),
                match="none",
                affects_identity=False,
            )
    changes = tuple(
        sorted(differ.changes, key=lambda c: (c.path, c.kind.value, c.before or "", c.after or ""))
    )
    return StateDiff(
        differ=DIFFER,
        from_fingerprint=before.fingerprint,
        to_fingerprint=after.fingerprint,
        same_identity=before.fingerprint == after.fingerprint,
        changes=changes,
    )
