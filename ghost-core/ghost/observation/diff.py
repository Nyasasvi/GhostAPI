"""Structured state diff between two CanonicalStates.

The diff reports *observations* (elements added/removed, properties changed, focus moved,
windows changed). It never reports meanings such as "document created".

Matching is explicit about its own certainty (``Change.match``):
  key         unique labelled step (role, stable id, label) present on both sides
  ordinal     same labelled step, but the number of such siblings differs, so which
              duplicate corresponds to which is ambiguous
  positional  leftover same-role siblings (or same-root-role windows) paired by position;
              could equally be "one removed, another added"
  none        unmatched
Content under a truncated (unobserved) parent is reported as unobserved, never as removed
or added, because unknown is not absent (RESEARCH.md §7.2).
"""

from __future__ import annotations

from collections import Counter
from enum import StrEnum
from typing import Literal

from ghost._model import StrictModel, canonical_json, content_hash
from ghost.observation.canonical import (
    CanonicalNode,
    CanonicalState,
    CanonicalWindow,
    element_step,
    with_ordinals,
)
from ghost.platform.types import GeneratorInfo, Role

DIFFER = GeneratorInfo(name="state-diff", version="2")
Match = Literal["key", "ordinal", "positional", "none"]


class ChangeKind(StrEnum):
    ELEMENT_ADDED = "element_added"
    ELEMENT_REMOVED = "element_removed"
    ELEMENT_UNOBSERVED = "element_unobserved"
    ELEMENT_NEWLY_OBSERVED = "element_newly_observed"
    LABEL_CHANGED = "label_changed"
    VALUE_CHANGED = "value_changed"
    STATES_CHANGED = "states_changed"
    ACTIONS_CHANGED = "actions_changed"
    STABLE_ID_CHANGED = "stable_id_changed"
    TRUNCATION_CHANGED = "truncation_changed"
    MASK_CHANGED = "mask_changed"
    WINDOW_ADDED = "window_added"
    WINDOW_REMOVED = "window_removed"
    WINDOW_CHANGED = "window_changed"
    COMPLETENESS_CHANGED = "completeness_changed"
    FOCUS_CHANGED = "focus_changed"
    WINDOW_GEOMETRY_CHANGED = "window_geometry_changed"
    VOLATILE_VALUE_CHANGED = "volatile_value_changed"


class Change(StrictModel):
    kind: ChangeKind
    path: str
    role: Role | None = None
    before: str | None = None
    after: str | None = None
    match: Match = "key"
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


def _base(node: CanonicalNode) -> str:
    return element_step(node.role, node.label, node.stable_id_hint)


def _keyed(children: tuple[CanonicalNode, ...]) -> list[tuple[str, CanonicalNode]]:
    keys = with_ordinals(_base(child) for child in children)
    return list(zip(keys, children, strict=True))


def _vjson(node: CanonicalNode) -> object:
    return node.value.model_dump(mode="json") if node.value else None


class _Differ:
    def __init__(self) -> None:
        self.changes: list[Change] = []

    def add(self, kind: ChangeKind, path: str, **fields: object) -> None:
        self.changes.append(
            Change.model_validate({"kind": kind, "path": path, **fields}, strict=False)
        )

    def fields(self, a: CanonicalNode, b: CanonicalNode, path: str, match: Match) -> None:
        pairs: list[tuple[ChangeKind, object, object]] = [
            (ChangeKind.LABEL_CHANGED, a.label, b.label),
            (ChangeKind.VALUE_CHANGED, _vjson(a), _vjson(b)),
            (ChangeKind.STATES_CHANGED, [s.value for s in a.states], [s.value for s in b.states]),
            (
                ChangeKind.ACTIONS_CHANGED,
                [x.value for x in a.actions],
                [x.value for x in b.actions],
            ),
            (ChangeKind.STABLE_ID_CHANGED, a.stable_id_hint, b.stable_id_hint),
            (ChangeKind.TRUNCATION_CHANGED, a.truncated, b.truncated),
            (ChangeKind.MASK_CHANGED, [m.value for m in a.masked], [m.value for m in b.masked]),
        ]
        for kind, before, after in pairs:
            if before != after:
                self.add(kind, path, role=b.role, before=_j(before), after=_j(after), match=match)

    def node(
        self, a: CanonicalNode, b: CanonicalNode, path_a: str, path_b: str, match: Match
    ) -> None:
        self.fields(a, b, path_b, match)
        left, right = _keyed(a.children), _keyed(b.children)
        right_map = dict(right)
        left_keys = {k for k, _ in left}
        counts_a = Counter(_base(c) for c in a.children)
        counts_b = Counter(_base(c) for c in b.children)
        for key, child in left:
            if key in right_map:
                base = _base(child)
                child_match: Match = match if counts_a[base] == counts_b[base] else "ordinal"
                if match in ("positional", "ordinal"):
                    child_match = match
                self.node(child, right_map[key], f"{path_a}/{key}", f"{path_b}/{key}", child_match)
        lost = [(k, c) for k, c in left if k not in right_map]
        new = [(k, c) for k, c in right if k not in left_keys]
        for role in sorted({c.role for _, c in lost} & {c.role for _, c in new}):
            olds = [(k, c) for k, c in lost if c.role is role]
            news = [(k, c) for k, c in new if c.role is role]
            for (old_key, old), (new_key, fresh) in zip(olds, news, strict=False):
                self.node(old, fresh, f"{path_a}/{old_key}", f"{path_b}/{new_key}", "positional")
                lost.remove((old_key, old))
                new.remove((new_key, fresh))
        gone = ChangeKind.ELEMENT_UNOBSERVED if b.truncated else ChangeKind.ELEMENT_REMOVED
        came = ChangeKind.ELEMENT_NEWLY_OBSERVED if a.truncated else ChangeKind.ELEMENT_ADDED
        for key, child in lost:
            self.add(
                gone, f"{path_a}/{key}", role=child.role, match="none", subtree_size=_size(child)
            )
        for key, child in new:
            self.add(
                came, f"{path_b}/{key}", role=child.role, match="none", subtree_size=_size(child)
            )

    def window(self, a: CanonicalWindow, b: CanonicalWindow, match: Match) -> None:
        if (a.title, a.modal, a.minimized) != (b.title, b.modal, b.minimized):
            self.add(
                ChangeKind.WINDOW_CHANGED,
                b.key,
                role=Role.WINDOW,
                before=_j([a.title, a.modal, a.minimized]),
                after=_j([b.title, b.modal, b.minimized]),
                match=match,
            )
        root_match: Match = match if _base(a.root) == _base(b.root) else "positional"
        self.node(
            a.root,
            b.root,
            f"{a.key}/{_base(a.root)}#0",
            f"{b.key}/{_base(b.root)}#0",
            root_match,
        )


def _window_digest(window: CanonicalWindow) -> str:
    return content_hash(window.model_dump(mode="json", exclude={"key", "ambiguous"}))


WindowPairs = tuple[
    list[tuple[CanonicalWindow, CanonicalWindow, Match]],
    list[CanonicalWindow],
    list[CanonicalWindow],
]


def _pair_windows(
    before: tuple[CanonicalWindow, ...], after: tuple[CanonicalWindow, ...]
) -> WindowPairs:
    """Pair windows: unique titles by key; same-title windows identical-content first, then
    by sorted order (ambiguous); leftover same-root-role windows positionally (title change)."""
    left, right = list(before), list(after)
    pairs: list[tuple[CanonicalWindow, CanonicalWindow, Match]] = []

    def take(old: CanonicalWindow, fresh: CanonicalWindow, match: Match) -> None:
        pairs.append((old, fresh, match))
        left.remove(old)
        right.remove(fresh)

    for title in sorted({w.title or "" for w in left} & {w.title or "" for w in right}):
        olds = [w for w in left if (w.title or "") == title]
        news = [w for w in right if (w.title or "") == title]
        unique = len(olds) == 1 and len(news) == 1
        for old in list(olds):
            twin = next((n for n in news if _window_digest(n) == _window_digest(old)), None)
            if twin is not None:
                take(old, twin, "key" if unique else "ordinal")
                olds.remove(old)
                news.remove(twin)
        for old, fresh in zip(olds, news, strict=False):
            take(old, fresh, "key" if unique else "positional")
    for role in sorted({w.root.role for w in left} & {w.root.role for w in right}):
        olds = [w for w in left if w.root.role is role]
        news = [w for w in right if w.root.role is role]
        for old, fresh in zip(olds, news, strict=False):
            take(old, fresh, "positional")
    return pairs, left, right


def diff_states(before: CanonicalState, after: CanonicalState) -> StateDiff:
    """Deterministic structured diff. Both states must come from the same canonicalizer."""
    if before.canonicalizer != after.canonicalizer or before.mask_id != after.mask_id:
        raise ValueError("cannot diff states from different canonicalizers or masks")
    differ = _Differ()
    pairs, removed, added = _pair_windows(before.windows, after.windows)
    for old, fresh, match in pairs:
        differ.window(old, fresh, match)
    for window in removed:
        differ.add(ChangeKind.WINDOW_REMOVED, window.key, role=Role.WINDOW, match="none",
                   subtree_size=_size(window.root))  # fmt: skip
    for window in added:
        differ.add(ChangeKind.WINDOW_ADDED, window.key, role=Role.WINDOW, match="none",
                   subtree_size=_size(window.root))  # fmt: skip
    if before.complete != after.complete:
        differ.add(ChangeKind.COMPLETENESS_CHANGED, "", before=_j(before.complete),
                   after=_j(after.complete), match="none")  # fmt: skip
    vb, va = before.volatile, after.volatile
    if vb.focused_path != va.focused_path:
        differ.add(ChangeKind.FOCUS_CHANGED, va.focused_path or "", before=_j(vb.focused_path),
                   after=_j(va.focused_path), match="none", affects_identity=False)  # fmt: skip
    old_bounds, new_bounds = dict(vb.window_bounds), dict(va.window_bounds)
    for key in sorted(old_bounds.keys() & new_bounds.keys()):
        was, now = old_bounds[key], new_bounds[key]
        if was != now:
            differ.add(ChangeKind.WINDOW_GEOMETRY_CHANGED, key, role=Role.WINDOW, match="key",
                       before=_j(was.model_dump(mode="json") if was else None),
                       after=_j(now.model_dump(mode="json") if now else None),
                       affects_identity=False)  # fmt: skip
    old_masked = {(p, f): v for p, f, v in vb.masked_values}
    new_masked = {(p, f): v for p, f, v in va.masked_values}
    for path, fld in sorted(old_masked.keys() | new_masked.keys()):
        if old_masked.get((path, fld)) != new_masked.get((path, fld)):
            # Paths here are window-relative structural paths (the mask namespace).
            differ.add(ChangeKind.VOLATILE_VALUE_CHANGED, f"{path}#{fld}",
                       before=old_masked.get((path, fld)), after=new_masked.get((path, fld)),
                       match="none", affects_identity=False)  # fmt: skip
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
