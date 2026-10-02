# GhostAPI: Engineering Constitution

These rules apply to every coding agent working in this repo (Claude Code, Codex, or anything else) and to humans. Project context lives in `docs/`; the build brief is `KICKOFF_PROMPT.md`.

## Source-of-truth documents (`docs/`)

| File | Owns | Rule |
|---|---|---|
| `PRODUCT.md` | Problem, user, pain, MVP, non-goals, success metric | Human-owned. Agents may critique it, never edit it silently. |
| `ARCHITECTURE.md` | Components, stack, boundaries | Architecture changes update this file in the same commit. |
| `DECISIONS.md` | ADR log | Every significant decision gets an ADR. Don't re-litigate an accepted ADR without a new one. |
| `API.md` | Ghost Bridge RPC contract and the `ghost` CLI | Change the doc and the contract tests together. |
| `DATA_MODEL.md` | SQLite schema, artifacts layout, GIR schema | Schema changes need a migration and a doc update. |
| `SECURITY.md` | Sandbox threat model, risk classes, approval gates, secrets | Anything touching safety updates this file. |
| `RESEARCH.md` | Core thesis, falsification criteria, research questions, phase gates | Do not weaken a falsification criterion after seeing results without a new ADR and explicit human approval. |
| `BENCHMARKS.md` | Holdout protocol, baselines, metrics, trial counts, drift tests | Freeze before held-out evaluation. Results never rewrite the benchmark. |

## Engineering rules

1. Never change the architecture without updating `docs/ARCHITECTURE.md` and adding an ADR.
2. Never add a dependency without stating why, and the alternative considered, in the PR/commit and, if it's significant, an ADR.
3. Prefer existing abstractions before creating new ones.
4. Never commit secrets. API keys come from env; `gitleaks` runs in CI.
5. Every feature requires tests.
6. Every bug fix requires a regression test that failed before the fix.
7. Keep source files under 500 lines. Split by responsibility, not arbitrarily. (Documentation in `docs/` is exempt.)
8. Strict typing: `mypy --strict` for Python, and no force-unwraps or `try!` in Swift outside tests.
9. SQLite migrations are versioned and reversible where possible.
10. Never silently swallow exceptions. Catch narrowly, and log or re-raise with context. Bridge AX errors are always surfaced.
11. Every external call (LLM provider, bridge RPC, VM CLI) has a timeout and an explicit retry policy. Retry only idempotent operations unless an ADR defines a safe compensation strategy.
12. Trials, experiments, and learn runs are idempotent and resumable: re-running with the same id never double-counts.
13. Validate all external input: bridge responses, LLM output (schema-validated), GIR files, CLI args, suite files.
14. Don't implement anything the brief and the current task don't ask for. Ideas go to `IDEAS.md`.
15. Before coding, read the relevant existing implementation and the docs the task lists.
16. Raw evidence is append-only. Never mutate original AX trees, screenshots, bridge responses, or trial logs after capture. Derived artifacts may be regenerated from raw evidence.
17. Every experiment writes a manifest containing at minimum: git SHA, dirty-tree flag, prompt versions, model/provider identifiers, configuration hash, random seed, VM base image identifier, app version, benchmark/suite version, trial count, budget, and start/end timestamps.
18. Randomness is explicit and seeded where possible. If a provider or OS component is nondeterministic, record that fact in the manifest.
19. Structured logs use stable event names and correlation ids for learn run, experiment, trial, VM, observation, action, hypothesis, capability, and binding.
20. Performance claims must come from benchmark artifacts, never from ad-hoc local runs or hand-written examples.

## Architecture boundaries (non-negotiable)

- **Ghost Bridge is the only code that touches macOS AX, input, or capture.** Ghost Lab talks to it only through the RPC client.
- **Ghost Core is platform-neutral** (`Ghost Core -> PlatformBridge -> MacOSBridge`, ADR-007). It consumes only neutral DTOs (`RawObservation` references, `PlatformObservation`, `CanonicalState`, and so on) and never names macOS framework concepts. `MacOSBridge` is the only platform implementation during the research phase.
- **All VM operations go through the `ghost-vm` adapter.** No shelling out to `tart` elsewhere.
- **All LLM calls go through `LLMProvider`** (`ghost/llm/`). Business logic never imports a vendor SDK. `MockProvider` exists for tests.
- **Prompts live in `prompts/`**, versioned by filename (`hypothesis_v1.md`), never inline in Python.
- **No LLM in `exploration/`, `observation/`, `experiments/`, or `gir/runtime`.** If normal code can reliably do it, don't ask an LLM. The LLM is used for ambiguity (naming, hypothesizing), code for certainty (hashing, diffing, risk rules, statistics, verification).
- **Rebinding boundary (ADR-011).** `gir/runtime` stays deterministic. It may detect binding failure, search deterministic candidates, request rebinding, and consume an already validated binding version. Semantic reasoning for rebinding lives only in `semantics/` and may only *propose* candidates. A candidate becomes active only after deterministic experimental verification.
- **Evaluation harness is outside the discovery pipeline (ADR-010).** Baseline arms, the natural-language router, and adjudication live in the benchmark harness. They may call LLMs through `LLMProvider`. Discovery code never imports them, and never reads their outputs or the sealed adjudication store.
- **The LLM never supplies confidence.** Reliability comes from repeated trials and measured outcomes.
- **The LLM proposes hypotheses; deterministic code designs/runs experiments.** Never hand the LLM unrestricted control of exploration.
- **CLI commands are thin.** Logic lives in modules; `cli.py` parses args and calls them.
- **No multi-agent orchestration.** One deterministic pipeline, with an LLM call at defined points. Add orchestration only when a concrete, logged failure requires it (ADR first).
- **GIR describes semantics, not selectors.** Runtime bindings are replaceable implementation details beneath a semantic capability.
- **Executor and verifier are separate components.** A verifier may consume the declared postcondition but must never treat the executor's success return as evidence.

## Project invariants

1. No app-specific code: no app names, bundle IDs, window titles, or control labels from any specific app in `ghost-core/`, `ghost-bridge/`, or `prompts/`. CI greps against `benchmarks/denylist.txt` and `$GHOST_HOLDOUT_DENYLIST`.
2. VM only: exploration and trials refuse to run unless the sandbox guard passes.
3. Clean-start trials: every empirical trial begins from the benchmark-defined clean snapshot/state. Cleanup actions inside the target app are never relied on to restore state.
4. Default-deny: DESTRUCTIVE and UNKNOWN_HIGH_RISK actions never execute without a recorded human approval.
5. Independent verification: trial outcomes are judged from fresh observations, never executor return values. Prefer a verification channel different from the execution channel when available.
6. AX is an observation surface, not the app's data model. Never claim hidden counts, identities, persistence, or entity state unless evidence supports them.
7. Handles ≠ identities: GIR stores semantic targets and binding candidates, never ephemeral AX handles or raw tree paths as persistent identity.
8. Entity resolution is conservative: ambiguous resolution returns `ENTITY_AMBIGUOUS`; GhostAPI never guesses which real entity the caller meant.
9. Semantic capabilities and runtime bindings are separate. A binding may change without changing the GIR capability contract.
10. No hardcoded model names; they come from config.
11. Scope gate: no REST, MCP, SDKs, web UI, or Postgres before the human approves it (see ADR-005). Visual inference by GhostAPI follows the escalation gate in ADR-009 and `RESEARCH.md` §17. The screenshot baseline is exempt, and that exemption never extends to GhostAPI.
12. Freeze: after tag `ghostapi-discovery-v0.1`, no changes motivated by a held-out app.
13. No benchmark contamination: held-out app names, docs, tutorials, screenshots, source code, automation scripts, accessibility maps, or web search results may not be added to prompts, fixtures, code, or retrieval context.
14. No personal data in research VMs: no personal Apple ID, iCloud, email, payment methods, browser profiles, credentials, synced folders, contacts, calendars, or production accounts.
15. Network is denied by default in exploration/trial VMs. Enable it only when the benchmark explicitly requires it and the target endpoints are allowlisted.
16. Published capability reliability is empirical. An LLM confidence score, one successful execution, or a visually plausible outcome is never enough.
17. A failed postcondition invalidates the trial even if the expected click/type sequence completed.
18. Runtime execution is GUI-bound unless a future ADR says otherwise: assume one active writer per app/session, possible foreground/focus requirements, and UI-scale latency. Never market or design it as equivalent to a native high-throughput REST API.

## Research and benchmark protocol

### Core thesis

GhostAPI must demonstrate that it can infer a reusable semantic capability from black-box interaction with previously unseen software, validate that capability experimentally, and execute it later more reliably or efficiently than a raw computer-use baseline.

### Development apps vs evidence apps

- **Development fixtures** may be well-known apps and exist only to debug the system. Results on them are not evidence of generalization.
- **Evaluation apps** must not have application-specific code, prompts, selectors, or fixtures.
- **At least one headline holdout should be obscure enough that prior model knowledge is unlikely to explain the result.** Prefer an app/version released after the selected model's documented knowledge cutoff when practical.
- When practical, a human who did not implement the discovery logic selects the final holdout after the discovery pipeline is frozen.

### Holdout rules

Before revealing a holdout app:

1. Freeze discovery code, prompts, risk policy, benchmark tasks, trial count, reliability threshold, metrics, and oracles.
2. Tag the repository (`ghostapi-discovery-v0.1` or later benchmark-specific tag).
3. Record the tag and benchmark manifest.
4. After reveal, do not browse for the app, read its documentation/tutorials, inspect source code, add app-specific prompts, or patch the system based on what the app looks like.
5. If a generic bug is discovered during holdout, record the failure first. Any fix requires human approval and the affected app no longer counts as a pristine holdout for that benchmark run.

### Trial protocol

- Each capability is evaluated over the benchmark-defined `N` independent trials; the default target is `N >= 20` unless `BENCHMARKS.md` specifies otherwise.
- Every trial starts from a clean VM snapshot or an independently verified equivalent clean state, then applies its preregistered state-stratum setup (`BENCHMARKS.md` §6.1).
- A trial is a statistical slot; a trial attempt is one execution of it. Infrastructure-invalid attempts are replaced only under `BENCHMARKS.md` §8.3 and are never double-counted.
- Probe values are unique per trial so stale state cannot create false positives.
- Verification occurs after the action from a fresh observation. Where persistence matters, relaunch/reopen before judging persistence.
- Record every trial, including failures, timeouts, ambiguity, crashes, and refused actions. Never discard an inconvenient run.
- Reliability thresholds are defined before evaluation. Do not lower them because an interesting capability almost passed.
- Prefer confidence intervals or other uncertainty estimates in reports; do not present a small-sample point estimate as certainty.

### Required benchmark metrics

At minimum report:

- capability recall: useful benchmark capabilities discovered / useful benchmark capabilities defined by the suite
- capability precision: verified published capabilities / published capabilities
- parameter/schema accuracy (precision and necessary-parameter recall)
- empirical execution success rate across fresh trials, per state stratum
- entity-resolution success, coverage, and ambiguity rate where entities are involved
- false-positive postcondition rate (internal verification passed, hidden adjudication failed)
- exploration actions, wall-clock time, LLM tokens, model calls, vision calls, and monetary cost
- post-learning execution latency, tokens/calls, and monetary cost
- crash/refusal/destructive-action rate
- drift recovery success rate and repair cost

Report failures and unsupported capabilities alongside successes.

### Baseline fairness

Every baseline arm (`BENCHMARKS.md` §9) and GhostAPI receive the same task intent, same starting VM/app state, same allowed credentials/data, and comparable execution budget unless the benchmark explicitly measures amortized cost. A human never translates benchmark tasks into GhostAPI calls; routing uses the frozen router (`BENCHMARKS.md` §9.5).

Report separately:

- **discovery/learning cost** for GhostAPI
- **amortized execution cost** after learning
- **per-task cost** for each baseline arm

Do not hide GhostAPI's upfront learning cost when comparing it with a zero-shot baseline.

### Drift test

A benchmark is incomplete without at least one binding-drift test once the relevant milestone is reached:

1. Learn and verify a semantic capability.
2. Change the app version, toolbar/menu layout, preference, or other UI binding without changing the intended semantic operation.
3. Show the old binding fail or become invalid.
4. Permit generic rebinding logic to search for a new implementation.
5. The GIR semantic capability and caller contract must remain unchanged.
6. Re-run clean-state trials and report reliability before and after drift.

A manual selector edit is not self-healing and does not count.

## Entity identity rules

- Prefer stable identifiers exposed by the OS/app only when they are observable without app-specific integration code.
- Otherwise use a documented composite/probabilistic identity strategy based on observed invariants (for example semantic properties, parent context, content fingerprint, visual/structural context).
- Every persistent Ghost entity handle must be resolvable against current state before mutation.
- If the best candidate is below the configured threshold, or multiple candidates are too close, fail closed with `ENTITY_AMBIGUOUS`.
- Renames, duplicates, reordering, virtualization, scrolling, and partial visibility must be included in entity-resolution tests before claiming stable update/delete semantics.
- Never expose a fabricated native `id` in GIR when the underlying interface did not reveal one. Ghost-generated handles must be clearly namespaced as Ghost handles.

## Observation and state-model rules

- Preserve the raw AX tree and screenshot before normalization.
- Canonicalization must be deterministic, versioned, and tested against fixtures so changing noise filters cannot silently change benchmark results.
- State hashes identify GhostAPI's observation of state, not ground-truth application state.
- Virtualized/off-screen UI must be treated as unknown, not absent.
- A visible row count is not an entity count unless the benchmark oracle proves equivalence.
- State diffs report observed changes before semantic interpretation. Semantic labels are derived artifacts and must never overwrite raw diffs.

## Human approval gates (agent proposes → human approves → system executes)

- Executing any DESTRUCTIVE or UNKNOWN_HIGH_RISK action in a VM
- Modifying `ghost-base`
- Enabling VM network access or expanding its endpoint allowlist
- Installing or revealing held-out apps
- Changing holdout selection after the benchmark has been frozen
- `git push --force`, rewriting history, deleting branches or tags
- Deleting `artifacts/` or `experiments/` data
- Changing the reliability threshold, suite, metrics, trial count, baseline budget, or oracles after the freeze
- Changing the entity-resolution ambiguity threshold after seeing holdout results
- Any spend beyond the configured LLM budget
- Adding a dependency that brings in a network service
- Promoting vision, REST, MCP, SDKs, web UI, Postgres, or another scope-gated component into the active milestone

## Checks are the source of truth

An agent saying "everything looks correct" means nothing. These do:

```bash
make check    # ruff check, ruff format --check, mypy --strict, pytest (unit),
              # swift build, swift test, swiftlint, gitleaks, make invariants
make test-vm  # integration tests in a fresh VM clone
```

Nothing is "done" until `make check` passes, and for VM-facing work, `make test-vm` too. Paste the summary lines.

Benchmark/research changes are not done until the experiment manifest and raw artifacts are written and the benchmark report can be regenerated from them.

## Keep context clean

Each task names the files and docs to read. Read those, plus what they import. Don't load the whole repo. When the context gets noisy, summarize the state to `docs/` or the task notes and start fresh.

For held-out evaluation, context hygiene is also an experimental control: do not load unrelated app documentation, prior runs against the same holdout, or external descriptions that could leak the app's semantics into the model.
