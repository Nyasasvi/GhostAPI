"""GhostAPI invariant checks (``make invariants``).

Each check returns explicit violations with file and line. Any violation fails the run.
These checks enforce AGENTS.md boundaries mechanically; they complement, and never replace,
review. Patterns are assembled from fragments so this file does not match itself.
"""

from __future__ import annotations

import ast
import os
import re
import subprocess
import sys
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE_ROOTS = {
    "ghost-core": "ghost",
    "benchmarks": "ghost_bench",
    "fixtures": "ghost_fixture",
}
CODE_DIRS = ("ghost-core", "benchmarks", "fixtures", "tools", "tests")
SKIP_DIRS = {".git", ".venv", "__pycache__", ".mypy_cache", ".ruff_cache", ".pytest_cache"}
MAX_SOURCE_LINES = 500


@dataclass
class Result:
    name: str
    violations: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


def iter_files(root: Path, rel: str, suffix: str) -> Iterator[Path]:
    base = root / rel
    if not base.exists():
        return
    for dirpath, dirnames, filenames in os.walk(base):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
        for name in sorted(filenames):
            if name.endswith(suffix):
                yield Path(dirpath) / name


def code_files(root: Path) -> Iterator[Path]:
    for rel in CODE_DIRS:
        yield from iter_files(root, rel, ".py")


def module_of(path: Path, root: Path) -> str | None:
    for src, package in SOURCE_ROOTS.items():
        base = root / src
        if path.is_relative_to(base / package):
            parts = path.relative_to(base).with_suffix("").parts
            return ".".join(p for p in parts if p != "__init__")
    return None


def imported_modules(path: Path) -> list[tuple[int, str]]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    found: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.extend((node.lineno, alias.name) for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            found.append((node.lineno, node.module))
    return found


def rel(path: Path, root: Path) -> str:
    return str(path.relative_to(root))


# -- checks -------------------------------------------------------------------------------
_PLATFORM = re.compile(
    "|".join(
        [
            r"\b" + "A" + r"X[A-Z][A-Za-z]+",
            r"\bk" + "A" + r"X\w+",
            r"\bC" + r"GEvent\w*",
            r"\bC" + r"GWindowID\b",
            "Screen" + "CaptureKit",
            r"\bS" + r"CStream\w*",
            r"\bN" + r"SWorkspace\b",
            r"\bN" + r"SRunningApplication\b",
            r"\bApplication" + r"Services\b",
            r"\bApp" + r"Kit\b",
            r"\bQuar" + r"tz\b",
            r"\bpy" + r"objc\b",
            r"\bbundle" + r"_?[iI]d(entifier)?\b",
        ]
    )
)


def check_platform_neutral_core(root: Path) -> Result:
    result = Result("platform-neutral Ghost Core (no platform framework vocabulary)")
    for path in iter_files(root, "ghost-core/ghost", ".py"):
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            match = _PLATFORM.search(line)
            if match:
                result.violations.append(f"{rel(path, root)}:{number}: {match.group(0)!r}")
    return result


_VENDOR_SDKS = ("anthropic", "openai", "google.generativeai", "google.genai", "mistralai", "cohere")
_LLM_FREE = (
    "ghost.platform",
    "ghost.observation",
    "ghost.exploration",
    "ghost.experiments",
    "ghost.gir",
    "ghost.storage",
)


def _within(module: str, package: str) -> bool:
    return module == package or module.startswith(package + ".")


def check_import_boundaries(root: Path) -> Result:
    result = Result("import boundaries (LLM, vendor SDK, harness, fixture)")
    for path in code_files(root):
        module = module_of(path, root) or ""
        for line, imported in imported_modules(path):
            where = f"{rel(path, root)}:{line}: imports {imported}"
            if any(_within(imported, sdk) for sdk in _VENDOR_SDKS) and not _within(
                module, "ghost.llm"
            ):
                result.violations.append(f"{where} (vendor SDK outside ghost.llm)")
            if any(_within(module, p) for p in _LLM_FREE) and (
                _within(imported, "ghost.llm") or _within(imported, "ghost.semantics")
            ):
                result.violations.append(f"{where} (LLM-free package reaches LLM/semantics)")
            if _within(module, "ghost") and imported.split(".")[0] in {
                "ghost_bench",
                "ghost_fixture",
                "tests",
            }:
                result.violations.append(f"{where} (Ghost Core must not import harness/fixture)")
            if _within(module, "ghost_fixture") and _within(imported, "ghost_bench"):
                result.violations.append(f"{where} (fixture must not import the harness)")
    return result


_MODEL_ID = re.compile(
    r"\b("
    + "clau"
    + r"de-[a-z0-9][a-z0-9.-]*|"
    + "gp"
    + r"t-[0-9][\w.-]*|"
    + "gem"
    + r"ini-[\w.-]+)"
)


def check_model_names(root: Path) -> Result:
    result = Result("no hardcoded model identifiers in code (config only)")
    for path in code_files(root):
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            match = _MODEL_ID.search(line)
            if match:
                result.violations.append(f"{rel(path, root)}:{number}: {match.group(0)!r}")
    return result


_FUTURE_ADAPTER = re.compile(r"^(Web|Windows|Android|IOS|Ios)Bridge$")
_FUTURE_ADAPTER_FILE = re.compile(r"(web|windows|android|ios)_?bridge", re.IGNORECASE)


def check_no_future_adapters(root: Path) -> Result:
    result = Result("no premature future platform adapters")
    for path in code_files(root):
        if _FUTURE_ADAPTER_FILE.search(path.name):
            result.violations.append(f"{rel(path, root)}: future adapter module")
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and _FUTURE_ADAPTER.match(node.name):
                result.violations.append(f"{rel(path, root)}:{node.lineno}: class {node.name}")
    return result


def _denylist_terms(root: Path) -> tuple[list[str], list[str]]:
    terms: list[str] = []
    notes: list[str] = []
    listed = root / "benchmarks" / "denylist.txt"
    if listed.exists():
        for raw in listed.read_text(encoding="utf-8").splitlines():
            term = raw.split("#", 1)[0].strip()
            if term:
                terms.append(term)
    holdout = os.environ.get("GHOST_HOLDOUT_DENYLIST", "")
    held = [t.strip() for t in re.split(r"[\n,]", holdout) if t.strip()]
    notes.append(
        f"holdout denylist: {len(held)} term(s) from $GHOST_HOLDOUT_DENYLIST"
        if held
        else "holdout denylist: $GHOST_HOLDOUT_DENYLIST not set (local-only check)"
    )
    return terms + held, notes


def check_denylist(root: Path) -> Result:
    terms, notes = _denylist_terms(root)
    result = Result("denylist (no app-specific names/labels in core or prompts)", notes=notes)
    patterns = [
        (term, re.compile(r"(?<!\w)" + re.escape(term) + r"(?!\w)", re.IGNORECASE))
        for term in terms
    ]
    targets = list(iter_files(root, "ghost-core/ghost", ".py")) + list(
        iter_files(root, "prompts", ".md")
    )
    for path in targets:
        text = path.read_text(encoding="utf-8")
        for term, pattern in patterns:
            for match in pattern.finditer(text):
                line = text.count("\n", 0, match.start()) + 1
                result.violations.append(f"{rel(path, root)}:{line}: denylisted term {term!r}")
    return result


def check_file_length(root: Path) -> Result:
    result = Result(f"source files under {MAX_SOURCE_LINES} lines")
    for path in code_files(root):
        count = len(path.read_text(encoding="utf-8").splitlines())
        if count >= MAX_SOURCE_LINES:
            result.violations.append(f"{rel(path, root)}: {count} lines")
    return result


_SECRET = re.compile(
    "|".join(
        [
            "sk-" + r"ant-[A-Za-z0-9_-]{20,}",
            "AK" + r"IA[0-9A-Z]{16}",
            "-----BEGIN " + r"(RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----",
            "gh" + r"p_[A-Za-z0-9]{36}",
            "xo" + r"x[baprs]-[A-Za-z0-9-]{10,}",
        ]
    )
)


def _candidate_files(root: Path) -> list[Path]:
    try:
        listed = subprocess.run(
            ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
            cwd=root,
            capture_output=True,
            text=True,
            check=True,
            timeout=30,
        ).stdout.splitlines()
        return [root / name for name in listed if (root / name).is_file()]
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        files: list[Path] = []
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
            files.extend(Path(dirpath) / n for n in filenames)
        return files


def check_secret_patterns(root: Path) -> Result:
    result = Result("no credential-shaped strings in repository files")
    for path in _candidate_files(root):
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for number, line in enumerate(text.splitlines(), 1):
            if _SECRET.search(line):
                result.violations.append(f"{rel(path, root)}:{number}: credential-shaped string")
    return result


_TART = re.compile(r"""["']ta""" + r"""rt["']""")
_TART_ALLOWED = ("ghost-core/ghost/sandbox/vm.py",)


def check_vm_cli_confined(root: Path) -> Result:
    result = Result("VM CLI invoked only from the VM adapter")
    for path in code_files(root):
        if rel(path, root) in _TART_ALLOWED:
            continue
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if _TART.search(line):
                result.violations.append(f"{rel(path, root)}:{number}: VM CLI invocation")
    return result


_PROMPT_PACKAGES = ("ghost-core/ghost/semantics", "ghost-core/ghost/llm")
_MAX_INLINE_TEXT = 300


def check_no_inline_prompts(root: Path) -> Result:
    result = Result("prompts live in prompts/, not inline in Python")
    for package in _PROMPT_PACKAGES:
        for path in iter_files(root, package, ".py"):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            docstrings = {
                id(node.body[0].value)
                for node in ast.walk(tree)
                if isinstance(node, ast.Module | ast.ClassDef | ast.FunctionDef)
                and node.body
                and isinstance(node.body[0], ast.Expr)
                and isinstance(node.body[0].value, ast.Constant)
            }
            for node in ast.walk(tree):
                if (
                    isinstance(node, ast.Constant)
                    and isinstance(node.value, str)
                    and len(node.value) > _MAX_INLINE_TEXT
                    and id(node) not in docstrings
                ):
                    result.violations.append(f"{rel(path, root)}:{node.lineno}: long inline text")
    return result


CHECKS: list[Callable[[Path], Result]] = [
    check_platform_neutral_core,
    check_import_boundaries,
    check_model_names,
    check_no_future_adapters,
    check_denylist,
    check_file_length,
    check_secret_patterns,
    check_vm_cli_confined,
    check_no_inline_prompts,
]


def run(root: Path, checks: list[Callable[[Path], Result]] | None = None) -> list[Result]:
    return [check(root) for check in (checks or CHECKS)]


def main() -> int:
    results = run(ROOT)
    failed = False
    for result in results:
        status = "FAIL" if result.violations else "PASS"
        failed = failed or bool(result.violations)
        print(f"[{status}] {result.name}")
        for note in result.notes:
            print(f"       note: {note}")
        for violation in result.violations:
            print(f"       {violation}")
    print("invariants: FAILED" if failed else f"invariants: {len(results)} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
