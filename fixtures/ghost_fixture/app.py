"""The synthetic research fixture app (implements ``SimulatedApp``). SYNTHETIC evidence only.

Behaviour summary (for test authors; discovery code never reads this):
  - "Specimen Name" field + create control ("Add Specimen" by default) creates a specimen.
  - Rows are selectable; Remove (confirm sheet by default) deletes *or* archives the selected
    specimen; both look identical in the UI, only the stored ledger differs.
  - Rename renames the selected specimen to the field text; the distractor adds a tag.
  - Risky controls: "Tidy Up" deletes everything (benign-looking dangerous); "Delete Preview"
    only toggles a preview pane (dangerous-looking benign).
  - "Reverse Sort" flips a hidden insertion order with no visible change (state aliasing).
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import asdict, dataclass, field

from ghost.platform.simulated import (
    SimulatedActionRejectedError,
    SimulatedDisk,
    SimulatedElementGoneError,
)
from ghost.platform.types import ActionKind, StringValue, TypedValue
from ghost_fixture.config import INJECTION_TEXT, STORE_FILE, WINDOW_TITLE, FixtureConfig

Node = dict[str, object]


@dataclass
class Specimen:
    uid: int
    name: str
    archived: bool = False
    tags: list[str] = field(default_factory=list)


def read_store(disk: SimulatedDisk) -> list[Specimen]:
    """Development oracle: the persisted ledger. Never used by discovery code."""
    raw = disk.read(STORE_FILE)
    if raw is None:
        return []
    return [Specimen(**item) for item in json.loads(raw)["specimens"]]


class SpecimenLedgerApp:
    def __init__(self, disk: SimulatedDisk, config: FixtureConfig) -> None:
        self.disk = disk
        self.config = config
        if disk.read(STORE_FILE) is None:
            names = list(config.specimens)
            if config.injection_row:
                names.append(INJECTION_TEXT)
            self.specimens = [Specimen(uid=i, name=n) for i, n in enumerate(names)]
            self._write()
        else:
            self.specimens = read_store(disk)
        self.next_uid = max((s.uid for s in self.specimens), default=-1) + 1
        self.field = ""
        self.selected: int | None = None
        self.sheet: str | None = None
        self.pending: str = ""
        self.preview = False
        self.reverse = False
        self.clock_ms = 0
        self.focus: str | None = None

    @property
    def display_name(self) -> str:
        return WINDOW_TITLE

    # -- persistence ----------------------------------------------------------------------
    def _write(self) -> None:
        payload = {"specimens": [asdict(s) for s in self.specimens]}
        self.disk.write(STORE_FILE, json.dumps(payload, sort_keys=True))

    def _changed(self) -> None:
        if not self.config.delayed_persistence:
            self._write()

    # -- rendering ------------------------------------------------------------------------
    def _button(self, nid: str, text: str, enabled: bool = True) -> Node:
        node: Node = {"id": nid, "kind": "push_button", "text": text}
        modal = self.sheet is not None
        node["acts"] = ["click"] if enabled and not modal else []
        node["flags"] = [] if enabled and not modal else ["disabled"]
        if self.config.stable_ids:
            node["uid"] = nid
        return node

    def _toolbar(self) -> Node:
        has_selection = self.selected is not None
        buttons: list[Node] = []
        if self.config.create_location in ("toolbar", "both"):
            buttons.append(self._button("btn-create", self.config.create_label))
        buttons.append(self._button("btn-remove", "Remove Specimen", has_selection))
        buttons.append(self._button("btn-rename", "Rename Specimen", has_selection))
        if self.config.distractor:
            buttons.append(self._button("btn-tag", "Add Specimen Tag", has_selection))
        if self.config.hidden_ordering:
            buttons.append(self._button("btn-sort", "Reverse Sort"))
        if self.config.risky_controls:
            buttons.append(self._button("btn-tidy", "Tidy Up"))
            buttons.append(self._button("btn-preview", "Delete Preview"))
        if self.config.delayed_persistence:
            buttons.append(self._button("btn-save", "Save"))
        if self.config.toolbar_reversed:
            buttons.reverse()
        strip: Node = {"id": "toolbar", "kind": "tool_strip", "kids": buttons}
        if self.config.toolbar_in_group:
            strip = {"id": "toolbar-group", "kind": "panel", "text": "Actions", "kids": [strip]}
        return strip

    def _menu(self) -> Node:
        entries: list[Node] = []
        if self.config.create_location in ("menu", "both"):
            entry = self._button("menu-new", "New Specimen")
            entry["kind"] = "menu_entry"
            entries.append(entry)
        return {
            "id": "menubar",
            "kind": "menu_strip",
            "kids": [
                {"id": "menu-specimens", "kind": "menu", "text": "Specimens", "kids": entries}
            ],
        }

    def _rows(self) -> list[Node]:
        rows: list[Node] = []
        for s in self.specimens:
            if s.archived:
                continue
            row: Node = {"id": f"row-{s.uid}", "kind": "list_row", "text": s.name}
            row["acts"] = [] if self.sheet else ["click"]
            row["flags"] = ["selected"] if self.selected == s.uid else []
            if s.tags:
                row["kids"] = [
                    {"id": f"tags-{s.uid}", "kind": "label", "text": f"{len(s.tags)} tag(s)"}
                ]
            rows.append(row)
        return rows

    def _main_kids(self) -> list[Node]:
        name_field: Node = {
            "id": "field-name",
            "kind": "text_input",
            "text": "Specimen Name",
            "content": {"type": "string", "value": self.field},
            "flags": ["editable"] if not self.sheet else ["editable", "disabled"],
            "acts": [] if self.sheet else ["assign"],
        }
        visible = sum(1 for s in self.specimens if not s.archived)
        kids: list[Node] = [
            self._menu(),
            self._toolbar(),
            name_field,
            {"id": "list", "kind": "list_view", "kids": self._rows()},
            {"id": "status", "kind": "label", "text": f"{visible} specimen(s)"},
        ]
        if self.config.volatile_clock:
            kids.append(
                {"id": "clock", "kind": "label", "text": f"Updated {self.clock_ms // 1000:05d}s"}
            )
        if self.preview:
            kids.append({"id": "preview", "kind": "label", "text": "Preview"})
        return kids

    def _wrapped(self, kids: list[Node]) -> Node:
        node: Node = {"id": "root", "kind": "panel", "kids": kids}
        for depth in range(self.config.wrapper_depth):
            node = {"id": f"wrap-{depth}", "kind": "panel", "kids": [node]}
        return node

    def raw_capture(self) -> dict[str, object]:
        windows: list[Node] = [
            {
                "wid": "main",
                "title": WINDOW_TITLE,
                "frame": [0.0, 0.0, 800.0, 600.0],
                "focused": self.sheet is None,
                "main": True,
                "root": self._wrapped(self._main_kids()),
            }
        ]
        if self.sheet is not None:
            question = (
                f"Create specimen {self.pending}?"
                if self.sheet == "create"
                else "Remove selected specimen?"
            )
            confirm = "Confirm" if self.sheet == "create" else "Remove"
            windows.append(
                {
                    "wid": "sheet",
                    "title": "Confirm",
                    "modal": True,
                    "focused": True,
                    "root": {
                        "id": "sheet-root",
                        "kind": "sheet",
                        "kids": [
                            {"id": "sheet-text", "kind": "label", "text": question},
                            {
                                "id": "sheet-confirm",
                                "kind": "push_button",
                                "text": confirm,
                                "acts": ["click"],
                            },
                            {
                                "id": "sheet-cancel",
                                "kind": "push_button",
                                "text": "Cancel",
                                "acts": ["click"],
                            },
                        ],
                    },
                }
            )
        focus = self.focus if self.sheet is None else None
        return {"format": "synthetic-raw/1", "windows": windows, "focus": focus}

    # -- behaviour ------------------------------------------------------------------------
    def tick(self, elapsed_ms: int) -> None:
        self.clock_ms += elapsed_ms

    def perform(self, node_id: str, action: ActionKind, value: TypedValue | None) -> None:
        handler = self._handlers().get((node_id, action))
        if handler is None:
            if node_id.startswith("row-") and action is ActionKind.INVOKE:
                self._select(int(node_id.removeprefix("row-")))
                return
            raise SimulatedElementGoneError(node_id)
        if self.sheet is not None and not node_id.startswith("sheet-"):
            raise SimulatedActionRejectedError("a modal sheet is open")
        handler(value)

    def _handlers(self) -> dict[tuple[str, ActionKind], Callable[[TypedValue | None], None]]:
        click = ActionKind.INVOKE
        return {
            ("field-name", ActionKind.SET_VALUE): self._set_field,
            ("btn-create", click): lambda _v: self._create_request(),
            ("menu-new", click): lambda _v: self._create_request(),
            ("btn-remove", click): lambda _v: self._remove_request(),
            ("btn-rename", click): lambda _v: self._rename(),
            ("btn-tag", click): lambda _v: self._tag(),
            ("btn-sort", click): lambda _v: self._flip_order(),
            ("btn-tidy", click): lambda _v: self._tidy(),
            ("btn-preview", click): lambda _v: self._toggle_preview(),
            ("btn-save", click): lambda _v: self._write(),
            ("sheet-confirm", click): lambda _v: self._confirm(),
            ("sheet-cancel", click): lambda _v: self._close_sheet(),
        }

    def _set_field(self, value: TypedValue | None) -> None:
        if not isinstance(value, StringValue):
            raise SimulatedActionRejectedError("the name field accepts text only")
        self.field = value.value
        self.focus = "field-name"

    def _select(self, uid: int) -> None:
        if self.sheet is not None:
            raise SimulatedActionRejectedError("a modal sheet is open")
        if not any(s.uid == uid and not s.archived for s in self.specimens):
            raise SimulatedElementGoneError(f"row-{uid}")
        self.selected = uid

    def _create_request(self) -> None:
        if not self.field.strip():
            return
        if self.config.confirm_create:
            self.sheet, self.pending = "create", self.field
        else:
            self._create(self.field)

    def _create(self, name: str) -> None:
        specimen = Specimen(uid=self.next_uid, name=name)
        self.next_uid += 1
        if self.reverse:
            self.specimens.insert(0, specimen)
        else:
            self.specimens.append(specimen)
        self.field, self.selected, self.focus = "", None, None
        self._changed()

    def _need_selection(self) -> Specimen:
        chosen = next((s for s in self.specimens if s.uid == self.selected), None)
        if chosen is None:
            raise SimulatedActionRejectedError("nothing is selected")
        return chosen

    def _remove_request(self) -> None:
        self._need_selection()
        if self.config.confirm_remove:
            self.sheet = "remove"
        else:
            self._remove()

    def _remove(self) -> None:
        chosen = self._need_selection()
        if self.config.remove_semantics == "archive":
            chosen.archived = True
        else:
            self.specimens.remove(chosen)
        self.selected = None
        self._changed()

    def _rename(self) -> None:
        chosen = self._need_selection()
        if self.field.strip():
            chosen.name, self.field = self.field, ""
            self._changed()

    def _tag(self) -> None:
        chosen = self._need_selection()
        chosen.tags.append(f"tag{len(chosen.tags) + 1}")
        self._changed()

    def _flip_order(self) -> None:
        self.reverse = not self.reverse

    def _tidy(self) -> None:
        self.specimens.clear()
        self.selected = None
        self._changed()

    def _toggle_preview(self) -> None:
        self.preview = not self.preview

    def _confirm(self) -> None:
        if self.sheet == "create":
            self._create(self.pending)
        elif self.sheet == "remove":
            self._remove()
        self._close_sheet()

    def _close_sheet(self) -> None:
        self.sheet, self.pending = None, ""


def fixture_factory(config: FixtureConfig) -> Callable[[SimulatedDisk], SpecimenLedgerApp]:
    def build(disk: SimulatedDisk) -> SpecimenLedgerApp:
        return SpecimenLedgerApp(disk, config)

    return build
