# GhostAPI build kit (v4)

This kit bootstraps the **research phase** of GhostAPI.

For the first six weeks, GhostAPI is not being built as a polished product. The goal is to test one falsifiable claim:

> **Can an unseen macOS application autonomously acquire a reusable machine interface without application-specific code?**

If that claim survives the benchmark, product surfaces such as REST, MCP, SDKs, and a public UI come later.

## Start here

Copy this kit into the root of an empty `ghostapi` repository, open Claude Code (or another coding agent) there, and say:

> Read `KICKOFF_PROMPT.md` and follow it.

The agent should **not write code immediately**. It should first return the Week 0 planning output requested by the kickoff brief: thesis restatement, kill pass, task list, risks, and questions. You approve the plan before implementation begins.

## Source-of-truth map

Do not treat this README as policy. When documents disagree, follow the authority order defined in `KICKOFF_PROMPT.md`.

| File | Owns |
|---|---|
| `AGENTS.md` | Enforceable engineering and safety constitution for humans and coding agents |
| `docs/PRODUCT.md` | Human-owned problem, user, pain, MVP, non-goals, and product success criteria |
| `docs/RESEARCH.md` | Research hypotheses, falsification criteria, experimental protocol, allowed observation channels |
| `docs/BENCHMARKS.md` | Held-out suites, metrics, thresholds, trial counts, statistical method, baseline rules, oracles, freeze protocol |
| `docs/ARCHITECTURE.md` | Components, stack, boundaries, and system shape |
| `docs/API.md` | Ghost Bridge RPC and `ghost` CLI contracts |
| `docs/DATA_MODEL.md` | SQLite schema, artifact layout, GIR persistence, migrations |
| `docs/SECURITY.md` | VM threat model, risk classes, approval gates, secrets, network policy |
| `docs/DECISIONS.md` | Architecture Decision Records (ADRs) |
| `KICKOFF_PROMPT.md` | One-time research launch brief: thesis, ownership, sequence, Week 0 handoff |
| `CLAUDE.md` | Fast operational context for Claude Code; imports/references the authoritative files above |

The important separation is:

```text
PRODUCT       → what problem are we trying to solve?
RESEARCH      → what claims are we trying to falsify?
BENCHMARKS    → how will we measure whether those claims survived?
ARCHITECTURE  → how is the instrument built?
AGENTS        → what rules may never be bypassed?
KICKOFF       → how do we start the project?
CLAUDE        → what does an agent need to orient itself quickly?
```

## Repository shape

The intended repository eventually contains:

```text
ghostapi/
├── AGENTS.md
├── CLAUDE.md
├── KICKOFF_PROMPT.md
│
├── docs/
│   ├── PRODUCT.md
│   ├── RESEARCH.md
│   ├── BENCHMARKS.md
│   ├── ARCHITECTURE.md
│   ├── API.md
│   ├── DATA_MODEL.md
│   ├── SECURITY.md
│   └── DECISIONS.md
│
├── ghost-core/
├── ghost-bridge/
├── ghost-vm/
├── prompts/
├── evals/
├── gir/
├── benchmarks/
├── experiments/
├── artifacts/
└── .claude/skills/
```

Not every directory needs to exist on day one. Week 0 establishes the approved skeleton.

## Skills (`.claude/skills/`)

Skills are task-specific operating guides. Agents should load only the skills required for the current task rather than reading all of them into context.

| Skill | Covers |
|---|---|
| `task-workflow` | Bounded task template, inspect-before-coding, checks as truth, regression procedure, independent diff review, definition of done |
| `vm-sandbox` | Base VM, disposable trial environments, offline policy, permissions, sandbox guard |
| `ghost-bridge` | Swift bridge API, AX observation/control, normalized elements, capture/input robustness |
| `observation-state` | Raw observations, canonicalization, state fingerprints, structured diffs |
| `deterministic-explorer` | Risk-aware frontier traversal, novelty, StateGraph construction |
| `semantic-hypotheses` | Evidence-only LLM hypotheses, typed parameter proposals, experiment proposals, semantic evals |
| `experiment-engine` | Clean-state trials, independent verification, reproducibility manifests, empirical reliability |
| `gir-spec` | GIR schema, semantic targets, bindings, runtime execution, entity handles, drift rebinding |
| `benchmark-eval` | Freeze protocol, blind holdouts, fair baseline, metrics, drift evaluation, reporting |
| `weekly-review` | End-of-week self-review, evidence summary, DD-LOOP handling |

Exact thresholds, trial counts, confidence-interval methods, and benchmark budgets belong in `docs/BENCHMARKS.md`, not in skill summaries or this README.

## Your part as the human owner

Before allowing benchmark work to begin:

- **Own `docs/PRODUCT.md`.** Edit it until the problem, user, non-goals, and post-gate product goal say what you actually believe.
- **Approve `docs/RESEARCH.md`.** The falsifiable hypotheses and experiment protocol must be fixed before the project can claim evidence for or against the thesis.
- **Approve `docs/BENCHMARKS.md`.** Lock metrics, thresholds, baseline conditions, trial protocol, usefulness rubric, oracles, and drift criteria before held-out evaluation.
- **Choose development apps** that the agent is allowed to know and use while building the system.
- **Choose held-out apps privately.** Use obscure, offline/local-data applications where possible. Do not reveal names until the applicable frozen evaluation run.
- Keep the held-out names outside the repo and expose the denylist only through the mechanism defined by `AGENTS.md` / `docs/BENCHMARKS.md`.
- Treat every revealed, attempted, failed, or aborted held-out app as **spent**.
- **Do not let the agent research held-out apps.** No app-specific documentation, tutorials, source inspection, web search, prior automation examples, or prompt hints during blind evaluation.
- **Build/approve `ghost-base`.** Grant only the macOS permissions required by the approved architecture. Do not sign into personal Apple IDs, iCloud, email, payment, or cloud accounts.
- **Approve all human gates** in `AGENTS.md`, including destructive/unknown-risk actions, base-image changes, held-out reveal, benchmark/protocol changes, and budget overruns.
- **Try each week's required demo by hand** and compare the claim with the actual evidence.
- **Keep evaluation honest.** Bad held-out results are useful results. Do not permit post-hoc threshold, oracle, prompt, or task changes to rescue a benchmark.
- **Optional cross-model review:** one model/session may implement and a fresh one may review, but the reviewer must follow the same constitution and must not rewrite the benchmark after seeing results.

## Holdout discipline

Generalization is only meaningful if the evaluation is blind.

A valid held-out run should have, before reveal/execution:

```text
frozen git commit/tag
frozen prompts
frozen model/config
frozen VM/base-image identifier
frozen GIR/schema version
frozen risk rules
frozen exploration/trial budgets
frozen benchmark tasks
frozen oracles
frozen scoring thresholds
```

The run must also write a reproducibility manifest containing the actual versions/hashes used.

Where practical, evidence passed to the semantic model should alias or redact the target application's identity. The model should reason from observed behavior, not from pretrained knowledge of the application's brand.

## Evidence discipline

A GhostAPI claim is supported by recorded evidence, not by an agent saying it worked.

Keep raw evidence append-only:

```text
AX observations
screenshots
input/action events
bridge responses
state snapshots
transition records
hypotheses
trial outcomes
verification evidence
experiment manifests
```

Derived state fingerprints, canonical trees, diffs, metrics, and GIR can be regenerated from that evidence.

Reliability comes from repeated fresh-state trials and the statistical method in `docs/BENCHMARKS.md`. LLM self-reported confidence is never capability confidence.

## A few things GhostAPI must say honestly

GhostAPI does **not** magically reveal an application's hidden data model.

It learns a machine interface over behavior it can observe and reproduce through the human-facing UI. Therefore:

- UI execution may be slower than a native API.
- An app may need focus and may serialize calls.
- AX may expose only part of application state.
- Virtualized, off-screen, hidden, or inaccessible state is **unknown**, not absent.
- A Ghost entity handle is a probabilistic semantic identity, not necessarily an application's native database ID.
- Ambiguous identity resolution must fail safely rather than guess.
- A capability is not proven merely because a control was clicked; the intended state transition must be independently verified.
- A drift result only counts when GhostAPI repairs/rebinds automatically without target-specific manual selector changes.

These are constraints of the research problem, not things to hide in a limitations section later.

## What happens after Week 6?

The benchmark should lead to one of three outcomes:

**A — Thesis fails.**  
Discovery is unreliable, capabilities are unstable, or learned execution provides no meaningful advantage over raw computer use. Stop or rethink the thesis.

**B — Thesis holds for a narrower class.**  
Characterize exactly what those applications have in common. That becomes the initial technical/product boundary.

**C — Thesis survives.**  
GhostAPI reliably discovers useful capabilities on unseen apps, reuses them from fresh state, compares favorably with the frozen baseline, and can recover from UI drift without app-specific patches.

Only after Case C should the project seriously expand toward:

```text
ghost serve
REST generation
MCP generation
SDKs
open-source launch
public benchmark/write-up
product UI
```

## Feedback format

When something is off, use:

```text
DD-LOOP
Observed: <what actually happened>
Gap: <how it differs from the intended behavior/process>
Refinement: <what should change>
```

The goal is to fix the underlying instruction, test, or process when possible—not just patch the current output.

---

### Note for later

This file is a **build-kit README**, not the eventual public GhostAPI README.

If GhostAPI reaches the post-benchmark open-source stage, replace the repository's public README with a user/developer-facing document explaining what GhostAPI is, showing the benchmark honestly, providing installation/examples, and linking to the research methodology. Keep this build-kit README under `docs/` or another internal project-history location if it remains useful.
