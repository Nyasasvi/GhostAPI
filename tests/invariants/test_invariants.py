"""The invariant checker must catch real violations, not just pass on a clean tree."""

from __future__ import annotations

from pathlib import Path

import pytest

import invariants as inv


def write(root: Path, rel: str, text: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_repository_passes_all_checks() -> None:
    failures = [r for r in inv.run(inv.ROOT) if r.violations]
    assert failures == [], [(r.name, r.violations) for r in failures]


def test_platform_vocabulary_in_core_is_caught(tmp_path: Path) -> None:
    write(tmp_path, "ghost-core/ghost/x.py", "role = 'A" + "XButton'\n")
    assert inv.check_platform_neutral_core(tmp_path).violations


def test_llm_import_from_explorer_is_caught(tmp_path: Path) -> None:
    write(tmp_path, "ghost-core/ghost/exploration/e.py", "import ghost.llm.provider\n")
    write(tmp_path, "ghost-core/ghost/gir/r.py", "from ghost.semantics import h\n")
    flagged = {v.split(":")[0] for v in inv.check_import_boundaries(tmp_path).violations}
    assert flagged == {"ghost-core/ghost/exploration/e.py", "ghost-core/ghost/gir/r.py"}


def test_vendor_sdk_outside_llm_is_caught(tmp_path: Path) -> None:
    write(tmp_path, "ghost-core/ghost/semantics/s.py", "import anth" + "ropic\n")
    write(tmp_path, "ghost-core/ghost/llm/ok.py", "import anth" + "ropic\n")
    violations = inv.check_import_boundaries(tmp_path).violations
    assert len(violations) == 1
    assert "semantics" in violations[0]


def test_core_importing_harness_or_fixture_is_caught(tmp_path: Path) -> None:
    write(
        tmp_path, "ghost-core/ghost/a.py", "import ghost_bench.adjudication\nimport ghost_fixture\n"
    )
    lines = {v.split(":")[1] for v in inv.check_import_boundaries(tmp_path).violations}
    assert lines == {"1", "2"}


def test_model_id_and_future_adapter_and_vm_cli_are_caught(tmp_path: Path) -> None:
    write(tmp_path, "tools/m.py", "MODEL = 'clau" + "de-opus-9'\n")
    write(tmp_path, "ghost-core/ghost/platform/web_bridge.py", "class We" + "bBridge: ...\n")
    write(tmp_path, "tools/vm.py", "cmd = ['ta" + "rt', 'run']\n")
    assert inv.check_model_names(tmp_path).violations
    assert len(inv.check_no_future_adapters(tmp_path).violations) == 2
    assert inv.check_vm_cli_confined(tmp_path).violations


def test_denylist_and_holdout_env_are_enforced(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    write(tmp_path, "benchmarks/denylist.txt", "# comment\nShiny Widget Pro\n")
    write(tmp_path, "ghost-core/ghost/a.py", "x = 'shiny widget pro'\ny = 'Secret Holdout'\n")
    write(tmp_path, "prompts/p_v1.md", "Nothing here.\n")
    assert len(inv.check_denylist(tmp_path).violations) == 1
    monkeypatch.setenv("GHOST_HOLDOUT_DENYLIST", "Secret Holdout")
    assert len(inv.check_denylist(tmp_path).violations) == 2


def test_long_files_secrets_and_inline_prompts_are_caught(tmp_path: Path) -> None:
    write(tmp_path, "tools/long.py", "x = 1\n" * 600)
    write(tmp_path, "notes.txt", "key = sk-" + "ant-" + "A" * 30 + "\n")
    write(tmp_path, "ghost-core/ghost/semantics/p.py", "PROMPT = '" + "word " * 100 + "'\n")
    assert inv.check_file_length(tmp_path).violations
    assert inv.check_secret_patterns(tmp_path).violations
    assert inv.check_no_inline_prompts(tmp_path).violations


def test_review_regressions_import_forms_are_caught(tmp_path: Path) -> None:
    write(tmp_path, "ghost-core/ghost/exploration/a.py", "from ghost import llm\n")
    write(tmp_path, "ghost-core/ghost/exploration/b.py", "from ..llm import provider\n")
    write(
        tmp_path,
        "ghost-core/ghost/exploration/c.py",
        "import importlib\nm = importlib.import_module('ghost.semantics.x')\n",
    )
    write(tmp_path, "ghost-core/ghost/semantics/d.py", "from goo" + "gle import genai\n")
    violations = inv.check_import_boundaries(tmp_path).violations
    assert any("exploration/a.py" in v for v in violations)
    assert any("exploration/b.py" in v for v in violations)
    assert any("exploration/c.py" in v for v in violations)
    assert any("semantics/d.py" in v and "vendor SDK" in v for v in violations)


def test_review_regressions_platform_modules_commands_prefixes(tmp_path: Path) -> None:
    write(tmp_path, "ghost-core/ghost/a.py", "import Co" + "coa\n")
    write(tmp_path, "ghost-core/ghost/b.py", "import ob" + "jc\n")
    write(tmp_path, "ghost-core/ghost/c.py", "x = 'C" + "GImage'\n")
    write(tmp_path, "ghost-core/ghost/d.py", "cmd = ['osa" + "script', '-e', 'x']\n")
    write(tmp_path, "ghost-core/ghost/e.py", "p" + "id = 4\n")
    flagged = {v.split(":")[0] for v in inv.check_platform_neutral_core(tmp_path).violations}
    assert flagged == {f"ghost-core/ghost/{n}.py" for n in "abcde"}


def test_review_regressions_vm_cli_in_strings_and_scripts(tmp_path: Path) -> None:
    write(tmp_path, "tools/a.py", "import os\nos.system('ta" + "rt run vm')\n")
    write(tmp_path, "scripts/run.sh", "ta" + "rt clone a b\n")
    write(tmp_path, "ghost-vm/clone.sh", "ta" + "rt clone a b\n")  # the adapter may
    violations = inv.check_vm_cli_confined(tmp_path).violations
    assert len(violations) == 2
    assert not any("ghost-vm" in v for v in violations)
