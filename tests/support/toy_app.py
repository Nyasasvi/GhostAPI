"""A minimal generic simulated app for contract tests (not the research fixture).

Window: a counter label, an increment button, a text input, a disabled button, and a list
whose length is configurable (to exercise truncation limits).
"""

from __future__ import annotations

from ghost.platform.simulated import (
    SimulatedActionRejectedError,
    SimulatedDisk,
    SimulatedElementGoneError,
)
from ghost.platform.types import ActionKind, StringValue, TypedValue


class ToyApp:
    def __init__(self, disk: SimulatedDisk, *, rows: int = 2) -> None:
        self.disk = disk
        self.count = int(disk.read("count") or "0")
        self.text = ""
        self.rows = rows
        self.focus: str | None = None

    @property
    def display_name(self) -> str:
        return "toy"

    def raw_capture(self) -> dict[str, object]:
        kids: list[dict[str, object]] = [
            {"id": "count", "kind": "label", "text": f"count {self.count}"},
            {"id": "inc", "kind": "push_button", "text": "Increment", "acts": ["click"]},
            {
                "id": "name",
                "kind": "text_input",
                "text": "Name",
                "content": {"type": "string", "value": self.text},
                "flags": ["editable"] + (["focused"] if self.focus == "name" else []),
                "acts": ["assign"],
            },
            {"id": "off", "kind": "push_button", "text": "Off", "flags": ["disabled"], "acts": []},
            {
                "id": "list",
                "kind": "list_view",
                "kids": [
                    {"id": f"row{i}", "kind": "list_row", "text": f"row {i}"}
                    for i in range(self.rows)
                ],
            },
        ]
        return {
            "format": "synthetic-raw/1",
            "windows": [
                {
                    "wid": "main",
                    "title": "Toy",
                    "frame": [0.0, 0.0, 400.0, 300.0],
                    "focused": True,
                    "main": True,
                    "root": {"id": "root", "kind": "panel", "kids": kids},
                }
            ],
            "focus": self.focus,
        }

    def perform(self, node_id: str, action: ActionKind, value: TypedValue | None) -> None:
        if node_id == "inc" and action is ActionKind.INVOKE:
            self.count += 1
            self.disk.write("count", str(self.count))
        elif node_id == "name" and action is ActionKind.SET_VALUE:
            if not isinstance(value, StringValue):
                raise SimulatedActionRejectedError("name accepts text only")
            self.text = value.value
            self.focus = "name"
        elif node_id in {"count", "off", "list", "root"} or node_id.startswith("row"):
            raise SimulatedActionRejectedError(f"{node_id} does not accept {action.value}")
        else:
            raise SimulatedElementGoneError(node_id)

    def tick(self, elapsed_ms: int) -> None:
        return None
