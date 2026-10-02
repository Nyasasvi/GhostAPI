# GhostAPI: Claude Code context

@AGENTS.md

GhostAPI is a research instrument that tests whether an unseen macOS app can autonomously acquire a machine interface. **Ghost Lab** (Python, on the host) observes, explores, hypothesizes, and runs trials against **Ghost Bridge** (Swift, inside a disposable macOS VM). Proven capabilities are recorded in GIR.

## Start here

- Build brief: `KICKOFF_PROMPT.md`
- Rules and non-negotiable boundaries: `AGENTS.md` (imported above; authoritative)
- Product scope: `docs/PRODUCT.md`
- Architecture and component boundaries: `docs/ARCHITECTURE.md`
- Research thesis and falsification criteria: `docs/RESEARCH.md`
- Benchmark protocol, thresholds, baselines, and holdout rules: `docs/BENCHMARKS.md`
- Decisions / ADRs: `docs/DECISIONS.md`
- Ghost Bridge RPC + CLI contract: `docs/API.md`
- SQLite, artifacts, and GIR schemas: `docs/DATA_MODEL.md`
- Sandbox / threat model / risk policy: `docs/SECURITY.md`
- How to run a single task: the `task-workflow` skill

Do not duplicate policy, thresholds, benchmark rules, or architecture decisions in this file. If this file conflicts with `AGENTS.md` or a source-of-truth doc, the source-of-truth wins.

## Before changing code

1. Read `AGENTS.md` plus only the source-of-truth docs relevant to the task.
2. Inspect `git status` and preserve unrelated user/agent changes; never reset or overwrite work you did not create.
3. Read the implementation you are changing and its direct imports/callers before editing.
4. Confirm the task does not cross a human approval gate or scope gate.
5. If the task touches a held-out evaluation, follow `docs/BENCHMARKS.md` before inspecting the target app or external material about it.

## Layout

```
ghost-core/ghost/   platform/ observation/ exploration/ semantics/ experiments/ gir/ llm/ storage/ sandbox/ cli.py
ghost-bridge/       Accessibility/ Capture/ Input/ Windows/ Normalize/ RPC/   (MacOSBridge; the only platform implementation)
ghost-vm/           create-base.sh clone.sh reset.sh provision.sh destroy.sh
prompts/            versioned prompt files (hypothesis_v1.md, ...)
evals/              semantic_cases.jsonl, risk_cases.jsonl, runner + results
gir/                schema-v0.1.json, learned/<app>.gir.yaml
benchmarks/         baseline/ apps/ tasks/ metrics/ denylist.txt
experiments/        per-run manifests + results
artifacts/          immutable raw observations, screenshots, transitions (gitignored)
docs/               PRODUCT ARCHITECTURE RESEARCH BENCHMARKS DECISIONS API DATA_MODEL SECURITY
```

## Commands

```bash
make bridge        # build ghost-bridge
make check         # static checks + unit tests + invariants; source of truth for normal work
make test-vm       # integration tests in a fresh VM clone
make evals         # run prompt/risk evals and write versioned results
make invariants    # denylist, LLM-boundary, model-config, sandbox and architecture invariants
```

For VM-facing work, `make check` alone is not enough: run `make test-vm` too. For research/benchmark changes, the run is not complete until its manifest and raw artifacts are written and the report is reproducible.

## Mental model

GhostAPI is **not** record-and-replay and **not** an LLM clicking around until something works.

The pipeline is:

```text
unseen app
  -> RawObservation
  -> PlatformObservation
  -> CanonicalState
  -> deterministic exploration
  -> observed transition
  -> LLM semantic hypothesis
  -> deterministic experiment
  -> internal behavioral verification
  -> repeated clean-state trials across state strata
  -> empirical reliability
  -> GIR semantic capability
  -> replaceable runtime binding
```

Hidden benchmark adjudication (was the *meaning* right?) happens outside this pipeline, after publication, and never feeds back into it.

The LLM proposes semantics; measured behavior decides whether a capability exists.

## Glossary

- **RawObservation:** immutable original evidence (raw bridge output, raw AX capture, screenshot reference, focus/window info, capture metadata). Defined in `docs/RESEARCH.md` §7.
- **PlatformObservation:** normalized, platform-neutral UI representation derived from a RawObservation; no macOS framework objects and no semantic interpretation.
- **CanonicalState:** deterministic, versioned, noise-reduced representation derived from a PlatformObservation; its hash is a **state fingerprint**, not ground-truth app state.
- **Transition:** `(from_state, action, inputs, to_state, diff)` based on observed evidence.
- **StateGraph:** observed states as nodes and observed transitions as edges.
- **Hypothesis:** an LLM-proposed semantic capability plus parameters and a testable experiment.
- **Experiment:** deterministic procedure used to test a hypothesis.
- **Trial:** one canonical statistical slot of an experiment (fixed stratum and probe), judged by internal behavioral verification. Counted once.
- **Trial attempt:** one execution of a trial slot; infrastructure-invalid attempts may be replaced under `docs/BENCHMARKS.md` §8.3, and all attempts are kept.
- **Internal verification vs adjudication:** internal verification checks the observed behavioral postcondition; hidden benchmark adjudication checks semantic correctness and is never visible to discovery.
- **Capability:** a semantic operation admitted to GIR only according to the current benchmark/reliability policy in `docs/BENCHMARKS.md`.
- **Binding:** current UI-level implementation of a semantic target; bindings may change without changing the GIR contract.
- **Ghost entity handle:** GhostAPI-owned reference resolved from observed identity evidence; never pretend it is an app-native ID.
- **Ambiguous entity:** resolution is not strong enough to mutate safely; return `ENTITY_AMBIGUOUS` rather than guessing.
- **Risk classes:** READ_ONLY · NAVIGATION · INPUT · REVERSIBLE_WRITE · UNKNOWN · UNKNOWN_HIGH_RISK · DESTRUCTIVE.

## Research discipline

- Famous/well-known apps are development fixtures, not evidence of generalization.
- Holdout apps must not leak into prompts, fixtures, code, web research, or implementation decisions before evaluation.
- Every empirical trial starts from the benchmark-defined clean VM state; never depend on in-app cleanup.
- Raw evidence is append-only. Derived interpretations may be regenerated; original evidence may not be rewritten.
- Never infer hidden app data (entity counts, IDs, persistence, off-screen items) from visible UI unless an oracle independently supports it.
- Capability confidence is empirical, never an LLM self-rating.
- Failures, timeouts, crashes, refusals, and ambiguous results count and remain in the dataset.
- Discovery/learning cost and post-learning execution cost are reported separately.
- Baselines must receive the same task intent and comparable starting state/budget.
- A drift claim requires the same semantic API contract to survive a changed UI binding through generic rebinding; a manual selector edit does not count.

## Held-out evaluation mode

When a benchmark holdout has been revealed:

- Do not browse the web for the app.
- Do not read its documentation, tutorials, source, automation examples, AppleScript dictionary, accessibility maps, or prior semantic descriptions unless the benchmark explicitly permits it.
- Do not add the app's names, labels, bundle ids, selectors, screenshots, or behaviors to generic prompts or code.
- Do not patch discovery logic because of a holdout-specific failure. Record the failure first and follow the benchmark contamination policy.
- Treat context hygiene as part of the experiment.

## Spent held-out apps

Record an app here only after it has been used in a held-out evaluation. Once spent, it is no longer a pristine holdout for future headline claims.

| App (recorded after use) | Used in | Code tag | Notes |
|---|---|---|---|

## When finishing a task

Report, briefly:

- what changed and why;
- source-of-truth docs/ADRs updated, if any;
- tests/checks actually run and their summary result;
- VM/benchmark artifacts produced, when applicable;
- unresolved risks or known failures;
- whether any human approval gate is still pending.

Never say a benchmark, capability, or test passed unless the corresponding check/artifact exists.

## Open questions for the human

-
