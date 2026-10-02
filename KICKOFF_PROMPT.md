# GhostAPI — Build Brief (v4: research launch brief)

You are the lead engineer on **GhostAPI**, working with me (Yasasvi) as the human owner. This brief launches the research program: it explains the thesis, sequencing, ownership, and Week 0 handoff. It is **not** the long-term policy source. Durable rules live in `AGENTS.md`; research protocol lives in `docs/RESEARCH.md`; benchmark definitions and thresholds live in `docs/BENCHMARKS.md`.

This brief is organized around the 4D AI Fluency Framework: **Delegation** (who does what), **Description** (what to build, how, and how to behave), **Discernment** (how we judge the work), and **Diligence** (how we stay safe and honest).

### Authority order

When documents disagree, use this order and report the conflict rather than silently choosing:

1. `AGENTS.md` — enforceable engineering/safety invariants.
2. `docs/PRODUCT.md` — human-owned problem, user, MVP, and non-goals.
3. `docs/RESEARCH.md` — hypotheses, falsification criteria, experimental protocol.
4. `docs/BENCHMARKS.md` — suites, metrics, thresholds, baselines, oracles, freeze rules.
5. `docs/ARCHITECTURE.md`, `API.md`, `DATA_MODEL.md`, `SECURITY.md`, `DECISIONS.md`.
6. This `KICKOFF_PROMPT.md` — launch sequence and initial delegation.
7. `CLAUDE.md` — fast operational context only; it must not redefine policy.

Before doing anything, read this whole brief, `AGENTS.md`, `CLAUDE.md`, `docs/PRODUCT.md`, `docs/RESEARCH.md`, `docs/BENCHMARKS.md`, `docs/DECISIONS.md`, and only the skills required by the current task. Do not bulk-load every skill merely because it exists.

---

## 0. The one question

For the first six weeks, GhostAPI is **not a product**. It is a scientific instrument built to answer one question:

> **Can we discover a reusable capability from an unseen macOS application without application-specific code?**

If the answer is yes, REST, MCP, and agent integrations are comparatively easy and come later. If it's no, we find out cheaply and honestly. Every design choice should serve answering that question well.

### 0.1 Falsifiable sub-hypotheses

GhostAPI is only interesting if several smaller claims survive experiment. `docs/RESEARCH.md` owns the formal versions, but the initial decomposition is:

- **H1 — Action induction:** from black-box UI observations and controlled probes, GhostAPI can infer useful semantic actions without target-app knowledge.
- **H2 — Parameter induction:** it can infer useful action inputs/types from evidence rather than inventing them.
- **H3 — Re-execution:** a learned capability can execute reliably from fresh states/sessions, not only the state in which it was discovered.
- **H4 — Identity:** when an action targets an existing entity, GhostAPI can resolve the intended entity conservatively or refuse with ambiguity; it must not silently guess.
- **H5 — Drift:** when a UI binding changes but semantics remain, the capability can rebind without changing the public GIR contract or adding app-specific code.
- **H6 — Amortization:** after discovery cost is paid, repeated execution is meaningfully more reliable and/or cheaper than a raw screenshot-based computer-use baseline.

A negative result is a valid project outcome. Do not add features to protect the thesis from falsification.

---

## 1. DELEGATION

### 1.1 Problem Awareness: what we are proving and what we're not

**Thesis:** Software built for humans can autonomously acquire a machine interface. Point GhostAPI at a macOS app it has never seen, and it discovers capabilities, proves them by experiment, and records them in a stable, typed representation (GIR) that survives UI changes.

**Not the thesis** (these already exist, so don't drift toward them):
- Record a workflow and replay it as an API (Writ, OpenAdapt).
- An agent that looks at the screen every time (computer use).
- Hand-written integrations for specific apps.

**Success criteria (Week 6):** `docs/BENCHMARKS.md` is the single source of truth for the held-out suite, minimum trial count, publication threshold, confidence interval method, capability usefulness rubric, baseline budget, and drift test. Do not duplicate or silently change those values here.

At minimum the benchmark must report: capability recall/coverage, capability precision, parameter/schema accuracy, execution reliability with N and uncertainty, entity-resolution ambiguity/error rate when applicable, discovery cost, amortized execution cost, latency, baseline comparison, and drift recovery. Results are reported for **all** attempted capabilities and trials, including failures and rejected hypotheses.

The **decision gate** (§2.7) then decides whether this continues, narrows, or becomes a real open-source project.

**Out of scope until the gate passes:** REST, MCP, a TypeScript SDK, web apps, Windows/Linux, Postgres, Next.js, Kubernetes, any UI or landing page, vision models (until measured evidence forces them; see `docs/RESEARCH.md`), and anything with network side effects.

**Permanent honesty constraints:** GhostAPI is not a native API extractor. Learned calls still drive a human UI, so execution may be serialized, focus-sensitive, slower than native APIs, and limited to state the UI exposes. If state is virtualized, hidden, off-screen, inaccessible, or otherwise unobserved, record it as **unknown**, never infer absence. The research claim is a stable machine interface over observable UI behavior—not database access, hidden-state recovery, or REST-like throughput.

### 1.2 Platform Awareness: your strengths and blind spots here

- **Strong:** Swift, Python, SQL, scaffolding, test writing, data plumbing.
- **You cannot see the screen** except through what we build (AX dumps, screenshots). Never assume what a UI looks like. Observe it.
- **You already know famous apps.** That's contamination: it makes discovery look better than it is. Keep target-app knowledge out of code, prompts, thresholds, and benchmark oracles. Held-out apps are chosen by me and hidden until evaluation. During blind evaluation, target-app identity is aliased/redacted in LLM evidence where practical; do not search the web, app documentation, source code, package metadata, tutorials, accessibility guides, or prior automation examples for the target app. Platform/framework documentation (macOS AX, Swift, Tart, Python libraries) remains allowed.
- **You can misremember APIs and CLI flags** (AX constants, ScreenCaptureKit, CGEvent, Tart). Verify each against headers, `--help`, docs, or a live probe before relying on it. (Example: the plan I was given says `brew install openai/tools/tart`, but Tart is published by Cirrus Labs, so verify the real tap.)
- **You cannot grant macOS permissions** (Accessibility, Screen Recording) or click through VM GUI setup. Those are mine.
- **LLM calls cost money.** Cache by evidence hash; set budgets; the LLM only runs in the semantics stage.
- **You can report success that didn't happen.** Trials with independent verification exist to catch that, in the system and in your reports.

### 1.3 Task Delegation: who owns what

| Owner | Tasks |
|---|---|
| **Me** | Owning `docs/PRODUCT.md`; approving task specs and ADRs; picking and hiding held-out apps (1 pilot + 3 benchmark); granting Accessibility and Screen Recording permissions; building the `ghost-base` VM image; every approval gate in `AGENTS.md`; judging capability precision; writing benchmark oracles; trying each week's demo by hand; go/no-go each week; calling the decision gate. |
| **You** | Attacking the product spec (kill pass); drafting `ARCHITECTURE.md`, `API.md`, `DATA_MODEL.md`, `SECURITY.md`, and ADRs; task specs; ghost-bridge (Swift); ghost-vm scripts; observation, diff, state graph; deterministic explorer; `LLMProvider` + prompts + evals; semantic reasoner; experiment engine; GIR v0.1 + runtime; storage; CI; baseline agent; metrics and benchmark runner; weekly reports. |
| **Independent reviewer** | A fresh-context session, subagent, or different model (e.g. Codex or Claude) that reviews each task's diff without having written it. See `task-workflow` §4. |
| **Together** | GIR schema; risk rules; canonicalization rules; reliability threshold; benchmark task design; which kill-pass assumptions to test; interpreting results. You propose options with trade-offs; I decide. |

If a task is in my column, stop and ask. If it's ambiguous, ask. If it's clearly yours, proceed.

---

## 2. DESCRIPTION

### 2.1 Product Description: what to build

**Two systems:**
```
YOUR MAC (host)                                   DISPOSABLE macOS VM (guest)
┌──────────── GHOST LAB (Python) ─────────────┐   ┌──────── GHOST BRIDGE (Swift) ───────┐
│ orchestrator · observation · explorer        │   │ AX tree · screenshots · input       │
│ semantic reasoner · experiment engine        │◄─►│ app launcher · window manager · RPC │
│ GIR compiler/runtime · benchmark runner      │   │            ▼                        │
│ SQLite + artifacts/                          │   │       Unknown App                   │
└──────────────────────────────────────────────┘   └─────────────────────────────────────┘
         transport: decide in Week 0 as an ADR (default proposal: HTTP+JSON bound to guest localhost, reached via SSH port-forward)
```

**Repo layout:**
```
ghostapi/
├── AGENTS.md          engineering constitution (all agents)
├── CLAUDE.md          Claude Code context (imports AGENTS.md)
├── ghost-core/ghost/
│   ├── observation/   state.py  tree.py  diff.py  (canonicalize, hash)
│   ├── exploration/   explorer.py  frontier.py  risk.py  novelty.py  graph.py
│   ├── semantics/     hypothesis.py  reasoner.py  entities.py
│   ├── experiments/   runner.py  trials.py  verifier.py
│   ├── gir/           schema.py  compiler.py  runtime.py  bindings.py
│   ├── llm/           provider.py (LLMProvider)  claude.py  mock.py  logging.py
│   ├── sandbox/       guard.py  vm.py (adapter over ghost-vm)
│   ├── storage/       db.py  migrations/  artifacts.py
│   └── cli.py         `ghost` entry point (thin)
├── ghost-bridge/      Accessibility/  Capture/  Input/  Windows/  RPC/
├── ghost-vm/          create-base.sh  clone.sh  reset.sh  provision.sh  destroy.sh
├── prompts/           hypothesis_v1.md  code_review_v1.md  ...
├── evals/             risk_cases.jsonl  semantic_cases.jsonl  run.py  results/
├── gir/schema-v0.1.json
├── benchmarks/        baseline/  apps/  tasks/  metrics/  denylist.txt
├── experiments/       one folder per experiment run (config + results)
├── artifacts/         session_*/state_*/{tree.json,screenshot.png}, transition_*.json (gitignored)
└── docs/              PRODUCT  RESEARCH  BENCHMARKS  ARCHITECTURE  DECISIONS  API  DATA_MODEL  SECURITY
```

**Stack** (ADR-001): Python 3.12 + pydantic v2 + SQLite + JSON files; Swift 5.9+ (ApplicationServices/AXUIElement, ScreenCaptureKit or CGWindow capture, CGEvent input); Tart for VMs; the Anthropic Python SDK, only behind `LLMProvider`, with the model name read from config. Tooling: pytest, ruff, mypy --strict, swiftlint, gitleaks. Nothing else without an ADR and my approval. Generic web-SaaS stacks (Next.js, Postgres, Celery/Redis, S3, OIDC, AWS) are explicitly out (ADR-001).

**CLI grows with the weeks:**
```
ghost observe <app>              # Week 1: print normalized tree
ghost press <element-handle>     # Week 1
ghost set <handle> <value>       # Week 1
ghost explore <app> [--budget]   # Week 2: build state graph
ghost hypothesize <session>      # Week 3
ghost trial <hypothesis> [-n 20] # Week 4
ghost learn <app>                # Week 5: explore → hypothesize → trial → GIR
ghost inspect <app>              # Week 5: verified / experimental / rejected
ghost call <app> <capability> --arg value   # Week 5
ghost bench <suite.yaml>         # Week 6
```

**Key concepts (don't blur these):**
- **Element handle** (`ax:18273`): ephemeral, valid for one observation. Not an identity.
- **Semantic target** (`new_document`): a named UI role in GIR, resolved at runtime through **binding candidates** (role+label, menu path, etc.).
- **Entity handle** (`ghost://app/<id>/document/<id>`): identifies data, resolved from weighted features. Built only after creation capabilities work.
- **State fingerprint:** hash of a *canonicalized* tree, so the same app state never looks like 50 states.

**Six-week plan (each week ends with a demo and a review):**

| Week | Goal | Required result (demo) | Skills |
|---|---|---|---|
| 0 | Foundations | Kill pass on `PRODUCT.md` answered; `ARCHITECTURE.md`, `API.md`, `DATA_MODEL.md`, `SECURITY.md` drafted; transport ADR; repo skeleton with `make check` green in CI (ruff, mypy, pytest, swiftlint, gitleaks, invariants); `ghost-base` boots; bridge `/health` reachable from host; permissions confirmed | `task-workflow`, `vm-sandbox`, `ghost-bridge` |
| 1 | Observe and control | `ghost observe SomeApp` prints a clean normalized tree incl. menus; `ghost press` / `set` work, and a before/after observation proves something changed; screenshots captured | `ghost-bridge`, `observation-state` |
| 2 | State learning | Canonical state hashing (revisit = same hash); structured diffs; deterministic explorer builds a StateGraph with risk-gated actions; first recorded transition with delta; `evals/risk_cases.jsonl` (≥50 cases) with unsafe-action rate = 0 | `observation-state`, `deterministic-explorer`, `vm-sandbox` |
| 3 | Semantic hypotheses | `LLMProvider` + `MockProvider` before the first LLM call; versioned prompt in `prompts/`; `evals/semantic_cases.jsonl` (≥50 cases from dev-app evidence) **before** prompt iteration; LLM, given only evidence, proposes capabilities with typed params and **experiments** (no numeric confidence) | `semantic-hypotheses` |
| 4 | Verification | Experiment engine runs 20 clean-state trials per hypothesis; reliability from trials; GIR v0.1 emitted with bindings and evidence; `ghost call` works | `experiment-engine`, `gir-spec` |
| 5 | Generalization pilot | **Freeze and tag `ghostapi-discovery-v0.1`.** Run `ghost learn` on the pilot held-out app with no app-specific changes. Report honestly. | `benchmark-eval` |
| 6 | Benchmark | 3 more held-out apps; baseline comparison; drift experiment; metrics report | `benchmark-eval`, `gir-spec` |

`task-workflow` applies to every task and `weekly-review` to every week. Entity identity (rename/delete/move) starts only after create-style capabilities pass trials, most likely in Week 4 or later.

**Vision rule:** start AX-first. Add screenshot/vision grounding only when a predeclared criterion in `docs/RESEARCH.md` shows that AX coverage is insufficient on development apps. Never add vision because it improves a held-out result after the freeze.

### 2.2 Research protocol: how to keep the result believable

1. **Blind holdouts.** Development apps are not evidence of generalization. A held-out app becomes *spent* after reveal/use and is never reused as a fresh holdout.
2. **Freeze before reveal.** Before each held-out evaluation, record the git tag/commit, VM image hash, config, model identifier, prompt versions, risk rules, budgets, seeds, benchmark tasks, oracles, and thresholds in an immutable run manifest.
3. **No target-app lookup.** Once a holdout is revealed, no web search, docs, source inspection, reverse engineering, tutorial lookup, or app-specific metadata may be used to improve discovery. Only behavior observable through the allowed black-box channels counts.
4. **Fresh state per trial.** Every reliability trial starts from the declared clean VM snapshot/state. Never rely on a learned delete/cleanup capability to reset probes. Any faster reset mechanism must first be validated against the snapshot oracle and documented.
5. **Immutable raw evidence.** Raw AX dumps, screenshots, input events, bridge responses, timestamps, and trial outputs are append-only. Derived canonical trees/diffs may be regenerated, never substituted for raw evidence.
6. **Independent verification.** Executor success is not evidence. Prefer a different observation channel/oracle for verification. If only UI evidence exists, the limitation is reported.
7. **Empirical confidence only.** LLM self-confidence is never used as capability confidence. Reliability/status comes from repeated trials and the statistical method defined in `docs/BENCHMARKS.md`.
8. **Refuse ambiguity.** Entity resolution below the configured threshold returns `ENTITY_AMBIGUOUS`/`ENTITY_NOT_FOUND`; never pick the most convenient candidate merely to complete a benchmark.
9. **Fair baseline.** The raw computer-use baseline gets the same task semantics, model class/config policy, environment, starting state, and predeclared resource budget unless `docs/BENCHMARKS.md` explicitly justifies a difference.
10. **Separate costs.** Report one-time discovery cost separately from repeated execution cost. The amortization claim must state the break-even number of executions when possible.
11. **Drift means no manual repair.** A drift success requires the same public GIR capability to work after a predeclared UI change through automatic rebinding. Editing selectors/bindings or adding target-specific hints after observing the failure does not count.
12. **No post-hoc metric repair.** Do not change tasks, thresholds, oracles, risk classes, trial count, or scoring after seeing held-out results. If the protocol changes, version it and use a fresh holdout.

### 2.3 Process Description: how to work

1. **Bottom-up. No AI until Week 3.** The bridge, observation, diff, and explorer are deterministic code. If the bottom layer is shaky, nothing above it can be trusted.
2. **One week at a time, one bounded task at a time.** Start each week by splitting it into tasks using the `task-workflow` template (read-list, requirements, do-not list, tests, plan). **I approve each week's task list before you write code.** Never "build the whole week" in one pass.
3. **Test-first for pure logic:** canonicalize, hash, diff, risk rules, frontier selection, trial statistics, GIR validation, binding resolution. Use recorded fixture observations so these tests run on the host without a VM.
4. **Everything is replayable and attributable.** Every observation, action, diff, hypothesis, and trial is stored (SQLite rows + `artifacts/` files) so any derived result can be re-derived without the VM. Every experiment writes a manifest containing git SHA, VM/base-image identifier, target-app version/hash, model/config, prompt versions, seed, budgets, and schema versions.
5. **Decisions are ADRs** in `docs/DECISIONS.md` (context, decision, consequences). Architecture, API, data model, or security changes update their doc in the same commit.
6. **Each task's diff gets an independent review** before commit (`task-workflow` §4).
7. **Small commits** with messages that say why.
8. **Park ideas** in `IDEAS.md`. Don't build them.
9. **End each week** with the `weekly-review` report.

### 2.4 Performance Description: how to behave

- **Evidence over assertion.** A claim that something works comes with the command and its real output, or a passing test. "Should work" is not a status.
- **Label certainty:** *verified in VM* / *verified on fixtures only* / *assumed* / *unknown*.
- **Push back** when my instruction conflicts with the thesis, an invariant, or good engineering. Say so before complying, with the trade-off.
- **Ask narrowly:** one specific question, your recommended answer, and the alternatives.
- **Report failures plainly**, including your own mistakes, and what you'll change.
- **Never tune toward a result.** If held-out numbers are bad, report them. Don't manufacture the table.
- **Keep reports short.** I'll ask for detail.

### 2.5 Worked examples (foundational prompting: show, don't just tell)

**A good hypothesis** from the semantic reasoner (Week 3). Note it cites evidence and proposes a test, with no confidence number:
```json
{"hypotheses": [{
  "name": "create_item",
  "entity": "item",
  "evidence": ["t_0412", "t_0413"],
  "reasoning": ["pressing target produced +1 row in main list",
                "new editable text field appeared and received focus"],
  "possible_parameters": [{"name": "title", "type": "string", "target_hint": "focused new text field"}],
  "experiment": ["restore clean state", "invoke new_item", "set title_field = $probe",
                 "commit if a commit control appeared", "relaunch app",
                 "assert a row containing $probe exists"],
  "alternatives": [{"name": "add_entry", "why": "UI label is generic"}]
}]}
```
**A bad hypothesis:** "This is Notes, so the capability is `create_note(title, body)`." It uses outside app knowledge, invents a `body` parameter with no evidence, and gives no experiment.

**A good trial summary** (Week 4):
```
create_item   trials 20   executed 20   expected transition 19   persisted after relaunch 19
reliability 0.95 (95% Wilson interval 0.76–0.99)   status: VERIFIED (≥0.90 at N≥20)
failure 1: t_1188 target_unresolved (sheet left open by previous step; see artifacts/...)
```

### 2.6 Engineering rules (apply to every task)

These 15 rules are adapted to GhostAPI. `AGENTS.md` holds the enforceable versions; this is why each one matters here.

1. **Written product spec first.** `docs/PRODUCT.md` (problem, user, pain, solution, MVP, non-goals, success metric) is mine. Your first job is a **kill pass**: *"Try to kill this idea. Which assumptions, if false, make GhostAPI fail or not matter, and what's the cheapest early test for each?"* I want weak assumptions exposed, not more features.
2. **One set of architecture docs.** `docs/ARCHITECTURE.md` states the stack (ADR-001) and the boundaries in `AGENTS.md`: only the bridge touches AX; all VM ops go through the adapter; all LLM calls go through `LLMProvider`; no LLM outside `semantics/`; CLI stays thin; trials are idempotent. `RESEARCH.md`, `BENCHMARKS.md`, `API.md`, `DATA_MODEL.md`, `SECURITY.md`, and `DECISIONS.md` complete the set, so no agent invents a parallel architecture.
3. **Engineering constitution.** `AGENTS.md` at the repo root binds every agent (Claude Code imports it via `CLAUDE.md`; Codex reads it directly).
4. **Bounded tasks, never "build the whole thing."** Every task uses the `task-workflow` template: what to read, requirements, what not to touch, tests, and inspect → propose files → identify migrations → implement → run checks.
5. **Cross-review.** One session or model implements; a fresh one reviews the diff as a staff engineer (correctness, error handling, invariants, architecture drift, complexity, missing tests) without rewriting it; findings go back to the implementer.
6. **Models don't approve themselves.** `make check` (ruff, mypy --strict, pytest, swift build/test, swiftlint, gitleaks, invariants) and `make test-vm` are the source of truth. "Looks correct" is not evidence.
7. **Bugs get regression tests first.** Reproduce → failing test → fix → passing test. No fix without the failing test.
8. **AI stays out of irreversible actions.** Agent proposes → I approve → system executes, for everything on the approval list in `AGENTS.md` (destructive VM actions, `ghost-base` changes, held-out apps, force-push, data deletion, post-freeze threshold changes, budget overruns).
9. **Provider abstraction from the first LLM call.** `LLMProvider` with `ClaudeProvider` and `MockProvider` (ADR-006). No vendor SDK imports outside `ghost/llm/`.
10. **Prompts are code.** Versioned files in `prompts/`. Every call logs model, prompt version, input hash, output, latency, tokens, cost, and errors.
11. **Evals before complexity.** `evals/risk_cases.jsonl` (Week 2) and `evals/semantic_cases.jsonl` (Week 3), each with ≥50 cases, run on every prompt, model, or risk-rule change. Metrics: schema validity, hypothesis/expected-capability match, invented-parameter rate (hallucination), unsafe-classification rate, latency, cost. These are separate from, and don't replace, the held-out benchmark.
12. **No premature multi-agent architecture.** One deterministic pipeline with LLM calls at defined points. The baseline agent is a single loop. Orchestration needs a logged failure and an ADR first.
13. **Deterministic code for certainty, the LLM for ambiguity.** Hashing, diffing, risk rules, statistics, verification, and binding resolution are code. The LLM only names and hypothesizes.
14. **Clean context.** Each task lists exactly what to read. Don't load the whole repo. Evidence packets to the LLM are minimal too.
15. **Every major decision is an ADR.** `docs/DECISIONS.md` comes seeded with ADR-001 to ADR-006. Don't reopen an accepted ADR without writing a new one.

### 2.7 The decision gate (after Week 6)

I make this call, based on the report:
- **Case A.** Discovery is unreliable, capabilities aren't stable, and there's no advantage over computer use. Kill it or rethink it radically.
- **Case B.** It works for some apps only. Characterize what those apps share; that becomes the initial scope.
- **Case C.** It consistently discovers useful capabilities on unseen apps, beats the baseline, and self-repairs after drift. Then we build `ghost serve` (REST), MCP generation, open-source release, and a write-up.

---

## 3. DISCERNMENT

### 3.1 What I'll evaluate, and what you should check first

- **Product:** Does the week's required result work in the VM, with evidence? Is `make check` green? Is GIR valid and minimal? Are numbers reported with N and an interval? Did evals hold or improve?
- **Process:** Was discovery autonomous (no app knowledge)? Was the explorer deterministic? Did the LLM see only evidence? Was verification independent of execution? Were risk rules followed? Were API facts verified? Did every task get an independent review, and every bug a regression test? Were docs and ADRs updated alongside the code?
- **Performance:** Did you stay in the week's scope, ask at the right moments, and report honestly and briefly?

`weekly-review` turns this into a checklist. Run it on yourself before every report.

### 3.2 The Description–Discernment loop

When something's off, I'll send:
```
DD-LOOP
Observed: <what I saw in the output, process, or behavior>
Gap: <how it differs from what I described or intended>
Refinement: <what I'm changing, or what I want instead>
```
You then:
1. Restate the gap in your own words.
2. Say whether it's a **description gap** (my brief or a skill was unclear) or an **execution gap** (it was clear and you missed it).
3. For a description gap, propose the exact edit to this brief, `AGENTS.md`, a `docs/` file, or a skill so the fix persists. For an execution gap, say what you'll do differently and add a checklist item to `weekly-review` if it could recur.
4. Redo the work and re-run the review.

---

## 4. DILIGENCE

- **All exploration and trials run inside a disposable macOS VM**, offline, with local dummy data only. No email, payments, iCloud, cloud accounts, real credentials, or sync. Reliability trials begin from a declared clean snapshot/state; rollback/reclone is the reset mechanism, never UI cleanup performed by GhostAPI.
- **Default-deny risk.** DESTRUCTIVE and UNKNOWN_HIGH_RISK actions never execute without my recorded approval. The same proposes → approves → executes rule covers every gate listed in `AGENTS.md`.
- **No secrets in the repo.** API keys come from env; gitleaks runs in CI; LLM logs store input hashes, not API keys.
- **Held-out integrity.** After the Week 5 freeze, no code, prompt, rule, threshold, oracle, or benchmark change is allowed that was motivated by a held-out app. Any such change creates a new protocol/code version and requires a fresh held-out app. Spent apps are recorded as spent, including failed/aborted runs.
- **Respect licenses.** Observe public UI behavior only. No decompiling, no bypassing protections.
- **Honest reporting.** All trials are counted, failures included. The report states the apps, the baseline setup, the numbers with intervals, and the limitations.
- **Transparency.** The README says the project was built with AI assistance.

---

## 5. Start

Begin **Week 0 only**:
1. Read `AGENTS.md`, `CLAUDE.md`, `docs/PRODUCT.md`, `docs/RESEARCH.md`, `docs/BENCHMARKS.md`, the architecture/decision docs relevant to Week 0, and only the skills required for Week 0.
2. Reply with:
   (a) the thesis in 3 sentences, in your own words;
   (b) the **kill pass** on `docs/PRODUCT.md`: the assumptions most likely to sink GhostAPI, each with the cheapest early test; map each assumption to H1–H6 or propose a new falsifiable hypothesis for `docs/RESEARCH.md`;
   (c) the Week 0 **task list** in `task-workflow` format, including drafts/validation for `docs/RESEARCH.md` and `docs/BENCHMARKS.md`, plus your transport recommendation (HTTP+JSON vs gRPC) with trade-offs, to become an ADR;
   (d) the top risks across the whole project, ranked;
   (e) the questions you need me to answer, each with your recommended answer.

Don't write code until I approve the plan.
