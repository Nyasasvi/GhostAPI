# Week 0 proposal package (not authoritative)

Everything here is a **proposal awaiting approval**. No authoritative file has been changed; the eight build-kit files still match their provenance hashes (`01-repo-init-plan.md` §1.1). Apply only what you approve, one group at a time (`approval-gates.md` §B).

## Layout

```text
docs/proposals/week0/
├── README.md                        this index
├── 01-repo-init-plan.md             repository init + version reconciliation
├── 02-authority-reconciliation.md   every conflict found and its proposed fix
├── 03-change-register.md            the nine required fields for each change (CR-01 … CR-24)
├── vm-storage-network-preflight.md  VM/storage preflight + network-isolation comparison
├── fixture-plan.md                  one configurable synthetic fixture
├── feasibility.md                   six-week estimate, costs, classification, schedule rules
├── approval-gates.md                every pending decision
├── diffs/                           exact unified diffs against the current files (NEW_* = new files)
├── proposed/                        full post-approval versions (applying = copying approved files)
└── reference/KICKOFF_v5_as_supplied.md   v5 transcription, for you to verify
```

## The 25 requested deliverables

| # | Deliverable | Where |
|---|---|---|
| 1 | Canonical repo init/reconciliation plan | `01-repo-init-plan.md` |
| 2 | Authority/version reconciliation | `02-authority-reconciliation.md` |
| 3 | Exact `RESEARCH.md` changes | `diffs/docs_RESEARCH.md.diff`; rationale CR-01…CR-18 |
| 4 | Exact `BENCHMARKS.md` changes | `diffs/docs_BENCHMARKS.md.diff`; rationale CR-03…CR-18 |
| 5 | PRODUCT/vision conflict resolution | `diffs/docs_PRODUCT.md.diff`, RESEARCH §17, ADR-009 (CR-14) |
| 6 | Baseline-vision exception | ADR-009; RESEARCH §17; BENCHMARKS §9.1; AGENTS inv. 11 |
| 7 | Observation terminology reconciliation | RESEARCH §7; `diffs/CLAUDE.md.diff`; ARCHITECTURE §3.2 (CR-01) |
| 8 | Week 4/Week 5 `ghost call` | `diffs/KICKOFF_PROMPT.md.v5-patch.diff`; API.md §7 (CR-21) |
| 9 | `ARCHITECTURE.md` draft | `proposed/docs/ARCHITECTURE.md` |
| 10 | PlatformBridge boundary table | ARCHITECTURE §3.1; ADR-007 |
| 11 | Automatic rebinding architecture | ARCHITECTURE §6; ADR-011; RESEARCH §16.3 |
| 12 | HTTP/JSON transport ADR | ADR-008 in `diffs/docs_DECISIONS.md.diff` |
| 13 | Minimal Week 1 API | `proposed/docs/API.md` |
| 14 | `DATA_MODEL.md` draft | `proposed/docs/DATA_MODEL.md` |
| 15 | `SECURITY.md` draft | `proposed/docs/SECURITY.md` |
| 16 | VM/storage preflight plan | `vm-storage-network-preflight.md` §1–6, §8–9 |
| 17 | Network-isolation comparison | `vm-storage-network-preflight.md` §7 |
| 18 | Configurable-fixture plan | `fixture-plan.md` |
| 19 | Baseline design | BENCHMARKS §9.0–§9.4, §9.6; ADR-010 |
| 20 | Benchmark task-routing design | BENCHMARKS §9.5 (Evaluations A/B/C, frozen router) |
| 21 | Drift evaluation strategy | RESEARCH §16; BENCHMARKS §7.9, §14; `fixture-plan.md` |
| 22 | LLM budget proposal | ADR-013; `approval-gates.md` §D |
| 23 | Six-week feasibility estimate | `feasibility.md` |
| 24 | Minimal `task-workflow` proposal | `proposed/.claude/skills/task-workflow/SKILL.md` |
| 25 | Remaining human approval gates | `approval-gates.md` |

## How to review quickly

1. `02-authority-reconciliation.md` (what was wrong).
2. `diffs/docs_RESEARCH.md.diff` and `diffs/docs_BENCHMARKS.md.diff` (the substance).
3. `approval-gates.md` §C (new numbers you are being asked to set).
4. `feasibility.md` §2 and §5 (what it costs and how slips are handled).
