# 1. Canonical repository initialization and reconciliation plan

**Status:** proposal. Nothing below has been executed. `/Users/yasasvi/Desktop/GhostAPI` is not a Git repository yet.
**Canonical repository:** `/Users/yasasvi/Desktop/GhostAPI` only. `/Users/yasasvi/Documents/ChatGPT/GhostAPI` is not created, copied, moved, or used.

## 1.1 Current state (observed 2026-09-29)

| Path | State |
|---|---|
| `AGENTS.md`, `CLAUDE.md`, `KICKOFF_PROMPT.md` (v4), `README.md` (says v4) | build kit as received |
| `docs/PRODUCT.md`, `RESEARCH.md`, `BENCHMARKS.md`, `DECISIONS.md` | build kit as received |
| `.DS_Store` | Finder metadata; to be gitignored, not deleted |
| `.claude/settings.local.json` | local Claude Code permission cache created by tool approvals in this session; to be gitignored, not committed |
| `docs/proposals/week0/` | this proposal package (new; written in Week 0) |

Provenance hashes of the build kit as received (SHA-256, recorded before any change). They are re-checked unchanged after the proposal package was written:

```text
ead6b78386945a00a53f67192046e742c5bc3a0733fa056065c36e90c610f456  AGENTS.md
f0e720f851bf7b62bf3430b411271e2a7b12c15485fd2894eda584340b06b5a1  CLAUDE.md
c1897aa6ea90daf15441635ca4ec18c10effa1ce390a994c19398677cad0a10c  KICKOFF_PROMPT.md   (v4)
8a6124fdbae6da9680f4bc1f3c9cc08597b44c26f510f496099b4b1fa848ea53  README.md
813b519f2dba7c806dc7c5aea6731727abf9f7e978f8b76c8557e04956810b81  docs/BENCHMARKS.md
2ad4c4cde42c89e58c409ec745750496d532b66ed3130497eb9d4736f862089c  docs/DECISIONS.md
74dea8da04fbab97c8f55f02815454ccaa1cb1a61780a02df2f9a9b7d9ffa0ed  docs/PRODUCT.md
a949ca9b04a7ed7db17995fc34c82923e41ba9c2a43dc8d2b6d586896a154305  docs/RESEARCH.md
```

Git identity (`user.name`, `user.email`) is configured globally. `init.defaultBranch` is unset, so the branch is named explicitly.

## 1.2 Steps (run only after you approve this plan)

1. **Verify provenance.** Re-hash the eight files and abort if any differs from §1.1.
2. **Initialize.** Run `git init -b main` in `/Users/yasasvi/Desktop/GhostAPI`. No remote, no push.
3. **Add `.gitignore`**, covering:
   - OS/editor: `.DS_Store`
   - research data: `artifacts/`, `adjudication/`, `*.sqlite`, `*.sqlite-*`
   - Python: `.venv/`, `__pycache__/`, `.mypy_cache/`, `.ruff_cache/`, `.pytest_cache/`
   - Swift: `.build/`, `*.xcodeproj/xcuserdata/`
   - local config: `.claude/settings.local.json`, `.env*`
4. **Commit 1: "Import GhostAPI build kit as received (v4)".** Contents: the eight provenance files plus `.gitignore`, byte-identical to §1.1. This keeps the v4 history.
5. **Commit 2: "Add Week 0 proposal package (not authoritative)".** Contents: `docs/proposals/week0/**`. It records exactly what you reviewed.
6. **After your approval of each item (§1.3), one commit per approved group**, each applying only the approved files from `docs/proposals/week0/proposed/`:
   - 6a. Kickoff v5 (+ Week 4/5 `ghost call` patch) and README → v5.
   - 6b. `RESEARCH.md` v0.2 + `BENCHMARKS.md` v0.2 + ADR-004 amendment + ADR-014.
   - 6c. `PRODUCT.md` (vision wording, success metric, kill-pass rows). This file is human-owned: apply only exactly what you approve.
   - 6d. `AGENTS.md` + `CLAUDE.md` terminology and boundary lines.
   - 6e. New `ARCHITECTURE.md`, `API.md`, `DATA_MODEL.md`, `SECURITY.md` + ADR-007 … ADR-013.
   - 6f. `.claude/skills/task-workflow/SKILL.md` + empty `IDEAS.md`.

   Each commit message states why, ends with the attribution line, and changes nothing outside its group. Items you reject or amend stay in `docs/proposals/` and are revised there first.
7. **No tags** in Week 0. Tags are reserved for freezes (`ghostapi-discovery-v0.1`), and deleting a tag is a human gate.

## 1.3 Version reconciliation

| Item | Resolution |
|---|---|
| Kickoff | v5 (as you supplied it) becomes `KICKOFF_PROMPT.md`. v4 stays in Git history (commit 1). The only proposed edit to v5 is the Week 4/5 `ghost call` clarification (`diffs/KICKOFF_PROMPT.md.v5-patch.diff`). |
| v5 transcription check | v5 was transcribed from your message into `reference/KICKOFF_v5_as_supplied.md` (SHA-256 `0323055ed23c0788d7e1a9ecf90189b2858e7ac52f082d997519103247343427`). `proposed/KICKOFF_PROMPT.md` is that file plus the patch. Please diff the reference copy against your source before approving 6a. |
| README | "(v4)" → "(v5)"; "copy this kit into an empty repository" → "this directory is the canonical repository". |
| Future writes | All code, docs, commits, tags, experiments, manifests, and benchmark evidence go only to this repository (artifacts gitignored but local). |
