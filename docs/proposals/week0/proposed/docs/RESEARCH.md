# GhostAPI Research Protocol

**Status:** Draft v0.2 (Week 0 protocol repair; see ADR-014)  
**Owner:** Human owner + research lead  
**Applies to:** GhostAPI research phase through the Week 6 decision gate  
**Authority:** This file owns the research hypotheses, falsification criteria, allowed experimental methods, contamination controls, and interpretation rules. `AGENTS.md` remains authoritative for engineering/safety invariants. `docs/BENCHMARKS.md` owns quantitative thresholds, benchmark suites, statistical methods, and baseline scoring.

---

## 1. Research question

GhostAPI exists to test one claim:

> **Can an unseen macOS application autonomously acquire a reusable machine interface without application-specific code?**

The project is not trying to prove that an LLM can click through a GUI, record a workflow, or wrap a hand-authored automation in an API. Those already exist.

The research contribution, if it exists, is that GhostAPI can:

1. observe an application as a black box;
2. infer useful semantic capabilities from behavior;
3. validate those capabilities experimentally;
4. encode them in a persistent machine-readable representation (GIR);
5. re-execute them reliably from fresh state;
6. preserve the semantic interface even when UI bindings change;
7. do this on applications that were not used to build or tune the system.

A negative result is acceptable. GhostAPI must be allowed to fail this thesis.

---

## 2. Research scope

### 2.1 In scope

During the research phase, GhostAPI may use:

- macOS Accessibility (AX) observations;
- app/window metadata exposed through approved macOS APIs;
- screenshots captured inside the disposable VM as immutable raw evidence (visual inference over them is governed by §17);
- deterministic keyboard/mouse/AX actions;
- controlled black-box experiments;
- local dummy data;
- a semantic LLM used only to propose names, schemas, hypotheses, and experiments from observed evidence;
- deterministic code for canonicalization, hashing, diffing, risk classification, experiment execution, statistics, verification, and binding resolution.

### 2.2 Out of scope

Until the research gate passes:

- native app reverse engineering;
- decompilation;
- source-code inspection of target apps;
- reading private application databases to discover capabilities;
- target-app-specific plugins or adapters;
- record-and-replay as the main discovery method;
- manually authored selectors for held-out apps;
- REST, MCP, SDK, public web UI, or product polish;
- Windows/Linux/mobile support;
- cloud-connected or account-dependent benchmark apps;
- actions with real-world network side effects;
- tuning the system after seeing held-out results and then continuing to treat that same app as unseen.

---

## 3. Core falsifiable hypotheses

The research program is organized around six hypotheses.

### H1 — Action induction

**Claim:** From black-box UI observations and controlled probes, GhostAPI can infer useful semantic actions without target-app knowledge.

Examples:

- `create_document(title, body)`
- `create_folder(name)`
- `search(query)`
- `toggle_setting(name, enabled)`

The claim is falsified if useful action discovery consistently depends on app-specific code, target-app documentation, prior model knowledge of the app, or human-authored workflow hints.

The claim is also not supported if a published capability is only a recorded action sequence with a semantic name. A capability must be one public contract that works across unseen parameter values and the predeclared state strata (H3) without per-state or per-path variants. If GhostAPI needs a separate capability for each start state or UI path, or if a resilient trace-replay baseline (`BENCHMARKS.md` §9) does equally well, report that GIR adds no semantic generalization over replay.

**Semantic identifiability.** Some operations produce the same observable transition (for example delete, archive, hide, remove-from-view). When no allowed experiment can tell the alternatives apart, the hypothesis must stay at the level the evidence supports (a generic name, or `UNKNOWN` semantics). It must not pick the familiar interpretation. Hidden benchmark adjudication (§13.2) scores what GhostAPI claimed. It never supplies the discriminating fact to discovery.

### H2 — Parameter induction

**Claim:** GhostAPI can infer useful action parameters and types from evidence rather than inventing them.

A valid parameter must be supported by observed controls, state transitions, or repeated experiments.

Examples:

```text
create_item(title: string)
```

is supported if a newly created item exposes a text input whose value persists into the resulting entity.

This claim is weakened when the semantic model invents unsupported parameters such as `body`, `folder`, or `priority` because those fields are common in similar apps.

This claim is equally weakened by **under-declaration**. If the operation needs `create_event(title, date, time, location)` to do what the benchmark task asks, and GhostAPI publishes `create_event(title)`, that is not a correct schema just because `title` is right. H2 is therefore measured as both:

- **precision:** declared parameters that the evidence supports;
- **recall:** necessary parameters (defined by the hidden adjudication oracle, §13.2) that GhostAPI declared.

Where observable, H2 also reports type correctness, required/optional classification, enum values, defaults, and basic constraints. Parameters whose existence or constraints cannot be observed through the allowed channels are reported as `UNKNOWN`, not as absent. Metric definitions and targets live in `BENCHMARKS.md` §7.4.

### H3 — Re-execution

**Claim:** A learned capability can be executed reliably from fresh application state and across new sessions, not only from the exact discovery state.

A capability that works once directly after discovery but fails after app relaunch, VM reset, focus changes, or benign state changes has not demonstrated reusable machine-interface behavior.

H3 is **not** "the same operation succeeds 20 times from one identical snapshot". Reliability trials are spread across **predeclared state strata**. Every trial still starts from a clean, externally reset state. Each stratum then applies a declared, generic setup before the call, for example:

- app relaunch;
- changed focus;
- changed window placement;
- reordered entities;
- additional benign entities, different entity counts, or different list sizes;
- benign preference or presentation variation;
- modal and no-modal starts where the app has them.

The same public capability must pass across strata without state-specific patches. The stratum list, how trials are allocated to strata, and per-stratum reporting are preregistered in `BENCHMARKS.md` §6.1. Stratification spreads the existing trial count across conditions; it does not multiply it.

### H4 — Entity identity

**Claim:** When a capability targets an existing entity, GhostAPI can conservatively resolve the intended entity or refuse when identity is ambiguous.

GhostAPI must not pretend that UI elements expose stable application-native IDs when they do not.

Entity resolution may use observable invariants such as:

- title/text;
- parent container;
- content fingerprint;
- creation evidence;
- neighboring relationships;
- structural location;
- visual features;
- other stable observable properties.

If confidence is insufficient or multiple candidates are plausible, the correct result is:

```text
ENTITY_AMBIGUOUS
```

or:

```text
ENTITY_NOT_FOUND
```

not a guess.

H4 has two sides, and both are measured:

- **Safety:** zero silent false-target executions. Executing on a request the adjudication oracle declared genuinely ambiguous counts as an unsafe resolution, even if the chosen entity happens to be the intended one.
- **Usefulness:** on requests the oracle declared resolvable, GhostAPI must actually resolve and act. A resolver that answers `ENTITY_AMBIGUOUS` to everything is safe but useless, and does not support H4.

Required metrics are the correct-resolution rate, false-target rate, ambiguous-refusal rate, not-found rate, and entity-resolution coverage. Targets live in `BENCHMARKS.md` §7.6. If no entity-targeting capability is discovered for an app, H4 is reported as **not tested** for that app, not as passed.

### H5 — Drift resilience

**Claim:** A stable GIR capability can survive a UI binding change through automatic rebinding without changing the public semantic contract or adding app-specific patches.

A valid drift result requires:

1. the public capability remains the same;
2. the previous binding fails or becomes unavailable;
3. GhostAPI discovers/resolves a new binding automatically;
4. the capability succeeds under the same benchmark oracle;
5. no human edits selectors, menu paths, labels, prompts, or app-specific hints after seeing the failure.

Rebinding is **not** "run discovery again and call it rebinding". A drift result must also:

6. keep the same public capability, the same inputs, and the same semantic postcondition;
7. search only for the failed semantic target, within a preregistered rebinding budget;
8. report rebinding cost next to the cost of full rediscovery. If rebinding costs about as much as rediscovery, H5's practical value is not supported, even when rebinding succeeds;
9. meet the normal VERIFIED reliability rule after drift.

The drift taxonomy, the rebinding budget, and the cost comparison are defined in §16 and `BENCHMARKS.md` §7.9 and §14.

### H6 — Amortized advantage

**Claim:** After paying one-time discovery cost, repeated GhostAPI execution is meaningfully more reliable and/or less expensive than the strongest applicable baseline for the same tasks (`BENCHMARKS.md` §9). "Meaningfully" is defined in `BENCHMARKS.md` §7.10 and is fixed before evaluation.

Only **reliability** and **success-adjusted total cost** can support H6. Latency, action count, or token count alone cannot, although all are reported. The comparison must show that any advantage comes from GIR and semantic compilation. An advantage that comes only from better sensors (AX metadata), memory, caching, or persistent selectors is not enough, which is why the diagnostic baselines exist. If GhostAPI beats only the screenshot-only stateless baseline, report H6 as supported against that baseline only.

Economic value is judged over a predeclared usage horizon and includes discovery, failed discovery attempts, trials, VM/reset overhead, retries, verification, rebinding after drift, maintenance, and human-approval overhead (`BENCHMARKS.md` §10). Do not claim an economic advantage when break-even needs unrealistic usage.

The comparison must separate:

- discovery cost;
- per-execution cost after learning;
- latency;
- token usage;
- vision usage;
- success rate;
- human intervention.

The important comparison is not “GhostAPI is always cheaper.” It is whether learning creates an interface whose repeated use amortizes the original discovery cost.

---

## 4. What counts as an unseen application?

An application is **unseen** only if it has not influenced the frozen system.

An app is not unseen if any of the following affected implementation, prompts, thresholds, risk rules, GIR design, canonicalization, binding logic, or benchmark logic:

- its name or bundle ID;
- documentation;
- tutorials;
- screenshots;
- source code;
- automation examples;
- prior manual testing;
- app-specific bugs encountered during development;
- model prompts containing the app identity;
- hand-authored labels or selectors derived from the app.

### 4.1 Development apps

Development apps may be known and repeatedly used while building GhostAPI.

Results on development apps are engineering evidence only. They are not evidence of generalization.

### 4.2 Pilot holdout

The pilot holdout is the first frozen generalization test.

Once revealed or attempted, it is permanently **spent**.

Its purpose is to test whether the research protocol itself is workable before the final benchmark.

It does not remain a fresh holdout after the first run.

### 4.3 Benchmark holdouts

Final benchmark apps are:

- privately chosen by the human owner;
- hidden until the frozen evaluation;
- absent from repository prompts/code/fixtures;
- preferably obscure enough that model prior knowledge is unlikely to dominate;
- local/offline;
- suitable for dummy data;
- accessible enough to provide a meaningful UI interaction surface;
- not chosen because GhostAPI is already known to work on them.

Every revealed, failed, aborted, or partially tested holdout becomes spent.

### 4.4 Synthetic research fixture

The project may build **one** configurable synthetic research fixture app, and a second only if logged evidence justifies it. The fixture exists for mechanics testing, adversarial testing, and falsification tests: duplicate entities, archive/delete ambiguity, drift toggles, prompt-injection text, and dangerous-looking controls.

Results on the fixture are **never** evidence of generalization. The fixture is written by the implementer and encodes the implementer's assumptions about UIs. The fixture's name, labels, and scenarios are development material and follow the same no-app-specific-code rule as any development app.

### 4.5 Eligible population and claim scope

Three held-out apps cannot show that GhostAPI works for "software built for humans". Before holdout selection, the human owner records:

1. the **eligible population** the benchmark samples from (initial proposal: local macOS applications that work offline, can be used with dummy data, need no personal or cloud account, and expose enough observable accessibility surface to allow meaningful interaction);
2. the **screening procedure** used to decide eligibility;
3. an **exclusion log** of candidate apps that were screened out, each with a reason code.

The exclusion log stays private until the benchmark report, so it cannot leak holdouts. Claims are limited to the eligible population. If GhostAPI works only for a narrower class (for example AX-rich CRUD or document apps), report that class precisely as a Case B result (§21).

---

## 5. Blind evaluation protocol

Blind evaluation exists to prevent pretrained app knowledge from masquerading as discovery.

During a held-out run:

- do not search the web for the target app;
- do not read its documentation;
- do not inspect source code;
- do not decompile it;
- do not inspect package contents for capability discovery beyond what the approved sandbox/launcher requires;
- do not use tutorials, screenshots, automation examples, forum posts, or previous agents' traces;
- do not ask another model what the app can do;
- do not add the app name or known semantics to prompts.

Where practical, evidence sent to the semantic model should replace app identity with an alias, e.g.:

```text
APP_7F3A
```

instead of the product name.

OS/platform information required for execution is allowed, such as:

- AX role semantics;
- macOS API documentation;
- Swift/Python library documentation;
- Tart/Virtualization behavior;
- generic UI role definitions.

The line is simple:

> **We may learn how macOS works. We may not learn what the held-out app is supposed to do from outside sources.**

---

## 6. Experimental environment

### 6.1 Disposable VM requirement

All exploration and reliability trials run inside a disposable macOS VM environment approved by the sandbox guard.

No personal accounts are allowed:

- no Apple ID;
- no iCloud;
- no Gmail;
- no Slack;
- no payment accounts;
- no cloud sync;
- no personal files;
- no production credentials.

Network is disabled by default.

If a development experiment requires network access, it must be explicitly approved and documented. Held-out benchmark apps must not require network side effects.

### 6.2 Clean-state trials

Every reliability trial begins from the clean state defined by `docs/BENCHMARKS.md`.

Preferred reset methods are:

1. VM snapshot rollback;
2. disposable clone from a frozen base;
3. another validated external reset mechanism documented before the benchmark.

GhostAPI must not depend on its own newly learned `delete`, `undo`, or cleanup capability to restore benchmark state. That would make reset validity circular.

---

## 7. Observation model

Observation has three levels. The same names are used across all documents and code:

```text
RawObservation  ->  PlatformObservation  ->  CanonicalState
```

**RawObservation**: immutable original evidence captured at one point in time. It may include:

```text
timestamp
app/process identity
window list
raw AX capture (verbatim attributes)
focused element
screenshot reference
input/action history
capture metadata
raw bridge response
```

**PlatformObservation**: a normalized, platform-neutral UI representation derived from one RawObservation. It contains no macOS framework objects and no semantic interpretation. It still represents observed UI evidence (neutral roles, labels, values, states, bounds, supported actions, truncation markers). It carries the version of the normalizer that produced it.

**CanonicalState**: a deterministic representation derived from a PlatformObservation. It removes noise and is used for state hashing (the **state fingerprint**), structured diffs, and StateGraph identity. Canonicalization rules are deterministic, versioned, tested against fixtures, and reproducible.

### 7.1 Raw vs derived evidence

RawObservations are immutable.

Derived structures may include:

- PlatformObservation;
- CanonicalState and its state fingerprint;
- structural diff;
- semantic UI annotations;
- transition records;
- entity candidates.

Derived structures must be reproducible from raw evidence plus versioned code/config. Every derived record carries its parent hashes and the name and version of the code that generated it.

### 7.2 Unknown does not mean absent

UI observation is incomplete.

The following may exist without being observable:

- off-screen rows;
- virtualized list entries;
- collapsed branches;
- hidden panels;
- inaccessible custom controls;
- application-internal objects;
- cached/background state.

If GhostAPI cannot observe something, it records **unknown**, not “does not exist.”

---

## 8. State and transition model

GhostAPI models an application as an observed transition system:

```text
S0 --A0--> S1
S1 --A1--> S2
```

A transition records:

```text
from_state
action
action inputs
to_state
raw evidence references
structured diff
risk classification
verification result
```

State fingerprints are hashes of `CanonicalState` (§7). `from_state` and `to_state` refer to CanonicalState fingerprints, and every transition also references the RawObservations it was derived from.

Canonicalization may remove volatile UI noise, but it must not erase evidence required to distinguish semantically different states.

All canonicalization rules are versioned and testable.

---

## 9. Exploration model

Exploration is deterministic where possible.

The explorer owns:

- frontier selection;
- state revisit detection;
- novelty scoring;
- action budgets;
- risk gating;
- traversal order;
- experiment scheduling.

The semantic model must not be told:

> “Explore the app and tell us what it can do.”

Instead:

1. deterministic code gathers evidence;
2. deterministic code identifies candidate transitions/controls;
3. the LLM proposes semantic hypotheses;
4. deterministic code turns those hypotheses into bounded experiments;
5. experiments produce evidence;
6. publication decisions come from empirical results.

The LLM acts as a hypothesis generator, not the controller of the scientific process.

---

## 10. Risk model

Every possible action is assigned one of the approved risk classes:

```text
READ_ONLY
NAVIGATION
INPUT
REVERSIBLE_WRITE
UNKNOWN
UNKNOWN_HIGH_RISK
DESTRUCTIVE
```

Default behavior:

- `READ_ONLY`: allowed.
- `NAVIGATION`: allowed.
- `INPUT`: allowed only with dummy probe values.
- `REVERSIBLE_WRITE`: allowed in disposable VM under the approved research policy.
- `UNKNOWN`: allowed only under conservative rules defined in `SECURITY.md`. Until the human owner approves those rules, any `UNKNOWN` action that may mutate state fails closed: it is not executed, and the refusal is recorded.
- `UNKNOWN_HIGH_RISK`: human approval required.
- `DESTRUCTIVE`: human approval required.

During final held-out evaluation, human approval must not reveal target semantics to the agent. Approval should refer to the observed action/evidence, not “yes, that is the Delete button.”

---

## 11. Semantic hypothesis protocol

A semantic hypothesis must contain:

- candidate capability name;
- entity type, if any;
- evidence references;
- proposed parameters and types;
- reasoning grounded in observed changes;
- alternative interpretations when plausible;
- a falsifiable experiment;
- expected postcondition(s).

Example:

```json
{
  "name": "create_item",
  "entity": "item",
  "evidence": ["transition_0412", "transition_0413"],
  "parameters": [
    {"name": "title", "type": "string"}
  ],
  "experiment": {
    "probe": "unique random title",
    "expected_postcondition": "a persisted item matching the probe exists"
  }
}
```

The semantic model must not return a numeric confidence score used for publication.

Model self-confidence is not evidence.

When the evidence fits several interpretations, the hypothesis must list them as alternatives and propose an experiment that would tell them apart using only allowed channels. If no such experiment exists, the capability is named at the level the evidence supports, or its semantics are marked `UNKNOWN` (see H1, semantic identifiability).

The semantic model never receives hidden benchmark tasks, oracles, adjudication results, or baseline outputs.

---

## 12. Experiment design

Every experiment must define, before execution:

- hypothesis being tested;
- starting state;
- probe inputs;
- allowed actions;
- action budget;
- expected transition;
- verification oracle;
- failure conditions;
- reset method;
- number of trials or stopping rule;
- artifact locations.

Experiments must be idempotent/resumable at the orchestration level.

A rerun with the same trial ID must not double-count a result.

---

## 13. Independent verification and adjudication

Two different questions are answered by two separate components. Neither may stand in for the other.

### 13.1 Internal behavioral verification

This asks: **did the expected observable state transition happen?** It is part of GhostAPI. It decides trial outcomes and capability status (CANDIDATE / EXPERIMENTAL / VERIFIED / REJECTED).

Executor return values do not determine success.

For example:

```text
AXPress returned success
```

does **not** prove:

```text
document was created
```

Verification should prefer a channel independent from the action executor.

Examples:

```text
Execution: AX action
Verification: fresh observation of persisted UI after relaunch
```

or:

```text
Execution: keyboard/AX
Verification: approved local filesystem oracle
```

If the only available oracle is the same UI channel, record the limitation.

The verifier must evaluate the declared postcondition, not merely whether the action sequence completed without error. Postconditions must depend on the unique probe, and must be shown to be false in the pre-action observation. A postcondition that was already true before the action cannot verify anything.

Internal verification establishes **behavior**, not **meaning**. If GhostAPI believes `delete_document()` and observes "the document disappears from the current list", that supports a behavioral postcondition. It does not show that the operation is a delete.

### 13.2 Hidden benchmark adjudication

This asks: **did GhostAPI correctly understand what the operation actually does?** It belongs to the benchmark, not to GhostAPI. The benchmark oracle may know that the operation above is really `archive_document()`.

Rules:

- Internal behavioral success does not equal semantic correctness. Both are reported, and so is the difference between them (the false-positive postcondition rate).
- The adjudication oracle, benchmark tasks, necessary-parameter definitions, and adjudication results are never available to discovery, hypothesis generation, experiment design, internal verification, or rebinding, before or after reveal of the app under evaluation.
- GhostAPI's published capability set is snapshotted and hashed before any adjudication runs. Adjudication cannot change what was published.
- GhostAPI must not invent a semantic interpretation, invent its own oracle, satisfy that oracle, and then report the interpretation as proven. The internal oracle proves only the declared behavioral postcondition.

`BENCHMARKS.md` §13 defines how adjudication evidence is captured and kept sealed during trials.

---

## 14. Entity identity protocol

GhostAPI distinguishes:

### Element handle

An ephemeral reference to a UI element observed at one moment.

Example:

```text
el:obs_000412:17
```

It is opaque, scoped to one observation generation, and invalid once stale. It is not stored as semantic identity.

### Semantic target

A role used by GIR execution.

Example:

```text
new_document
save
title_field
```

Semantic targets are resolved to current bindings at runtime.

### Ghost entity handle

A GhostAPI-level reference to a persistent data entity.

Example:

```text
ghost://APP_7F3A/document/82df...
```

A Ghost entity handle is not claimed to be a native application ID.

It resolves from observed evidence.

If resolution is ambiguous, GhostAPI refuses.

---

## 15. GIR research requirements

GIR must separate:

```text
WHAT the application can do
```

from:

```text
HOW the current UI exposes that capability
```

A GIR capability should include:

- semantic name;
- typed inputs;
- entity relationship;
- preconditions;
- semantic execution steps;
- expected transition;
- verification method;
- evidence references;
- empirical reliability;
- current binding candidates;
- schema/protocol version.

GIR must not persist:

- raw ephemeral element handles (or any platform-native element reference) as identity;
- fragile absolute coordinates as the only binding;
- app-specific code paths inside generic runtime logic.

---

## 16. Drift protocol

A drift test is designed before the held-out drift result is observed.

### 16.1 Drift taxonomy

Each drift condition belongs to exactly one class. The semantic operation, its inputs, and its postcondition must stay the same.

| Class | Example |
|---|---|
| D1 label change | "New" becomes "Add" or an icon-only button |
| D2 hierarchy change | a control moves into or out of a group/container |
| D3 control reorder | toolbar or list order changes |
| D4 relocation | menu command moves to toolbar, or the reverse |
| D5 added distractor | a new, similar-looking control appears nearby |
| D6 wrapper/container change | non-semantic wrapper layers are added or removed |
| D7 minor workflow-step change | an extra confirm step, or a sheet replaced by an inline field, with the same semantics |

### 16.2 Where drift comes from

- **Development drift** uses the configurable synthetic research fixture (§4.4). Each class above can be toggled there, so rebinding mechanics can be tested cheaply and repeatably. Fixture drift results are development evidence only.
- **Real-app drift** is tested only through a legitimate, predeclared, reproducible mechanism in the app itself: configurable toolbar or layout, a UI preference, presentation customization, or a genuine version change with equivalent semantics. Nobody may edit app binaries, reverse engineer the app, or modify its internals to manufacture drift. If a held-out app has no such mechanism, report "no safe drift mechanism" for that app. Do not invent one.

Before the Week 5 freeze, the research lead proposes and the human owner decides whether H5 is validated through (1) the fixture, (2) a dedicated real-app drift test, or (3) both. That decision is frozen and not revisited after seeing results.

### 16.3 Rebinding versus rediscovery

Automatic rebinding follows the boundary in ADR-011 and `ARCHITECTURE.md`. The deterministic GIR runtime detects the failure and requests rebinding. Semantic reasoning, if needed, happens only in `semantics/` and may only *propose* candidate bindings. A candidate becomes active only after deterministic experiments verify the unchanged semantic postcondition.

Rebinding searches only for the failed semantic target, within a preregistered rebinding budget (`BENCHMARKS.md` §7.9). Rebinding cost is reported beside the cost of full rediscovery. If rebinding needs about as much search as rediscovery, report that.

### 16.4 What does not count

A drift test does **not** count if:

- the public semantic behavior changed;
- a human edits the binding after failure;
- target-specific hints are added;
- the prompt is modified based on the failed held-out app;
- the benchmark oracle is weakened;
- the public capability's inputs or postcondition changed to fit the new UI;
- "rebinding" was an unscoped rerun of full discovery.

A passing drift result demonstrates:

```text
same GIR capability
+
different binding
+
automatic re-resolution/rebinding
+
same verified postcondition
```

---

## 17. Vision escalation rule

GhostAPI begins AX-first. Two things are kept apart:

- **Screenshot capture** is allowed from the start. Screenshots are immutable raw evidence (part of a RawObservation).
- **Visual inference**, meaning any model reasoning over images (multimodal semantic reasoning or visual grounding), is **disabled for GhostAPI by default**.

Visual inference may be enabled for GhostAPI only when all four conditions hold:

1. a measurable, development-only AX-insufficiency criterion is preregistered in this section or in an ADR **before** the measurement it relies on;
2. development evidence (development apps, not the synthetic fixture alone, and never a held-out app) meets that criterion;
3. the human owner explicitly approves the escalation;
4. the escalation happens before any affected held-out freeze.

**Proposed preregistered criterion (AXI-1; status: proposed, needs approval).** AX is insufficient when, on at least 2 development apps, at least 30% of the capability families the human owner declared useful in advance are *blocked*. Blocked means the required control, input, or postcondition state is visible on screen (confirmed by human annotation of a captured screenshot) but absent or unlabeled in the AX capture, after the generic AX-enablement steps documented in `API.md`.

Examples of acceptable evidence:

- repeated inability to identify interactive controls represented visually but absent from AX;
- inability to verify postconditions because relevant state is only rendered graphically;
- benchmark-independent development evidence showing a systematic accessibility gap.

Vision must not be added after a held-out result merely because it would improve that result.

**Baseline exemption (ADR-009).** The screenshot-only computer-use baseline and its variants (`BENCHMARKS.md` §9) use visual inference by design, because screenshots are the baseline's intended sensor. The exemption covers only the baseline harness. It does not allow GhostAPI to use visual inference. Baseline outputs, trajectories, and anything learned from them must never flow into GhostAPI discovery, prompts, bindings, or evals.

If vision is introduced:

- record model/provider/version;
- version prompts;
- include vision calls in cost metrics;
- preserve screenshots used as evidence;
- keep structured AX evidence available when present.

---

## 18. Reproducibility manifest

Every experiment run writes a manifest containing at least:

```text
run_id
timestamp
git commit/tag
dirty-tree status
GhostAPI version
GIR schema version
SQLite schema version
VM/base-image identifier
guest macOS version
target app alias
target app version/hash where available
model provider/model/config
prompt versions/hashes
random seed(s)
risk-rule version
platform-normalizer version
canonicalization version
state-strata allocation version
exploration budget
trial budget
LLM spend limits in force
benchmark/protocol version
oracle version (hash of the sealed oracle bundle)
network policy
```

A result without a reproducibility manifest is development evidence only and cannot be included in the final benchmark.

---

## 19. Evidence integrity

Raw research artifacts are append-only.

Never rewrite a failed trial into a successful one.

Never discard a failed run because:

- the UI was awkward;
- the app opened in an unexpected state;
- the model misunderstood something;
- the VM was slower than expected;
- the result hurts the average.

If a trial is invalid due to infrastructure failure, mark it:

```text
INVALID_INFRA
```

and retain the evidence.

`INVALID_INFRA` covers only faults outside GhostAPI's behavior that the harness itself detected and logged. Examples: the VM failed before GhostAPI's first action, the capture subsystem was unavailable, disk corruption, or a test-harness failure unrelated to GhostAPI. These are **GhostAPI failures, never** `INVALID_INFRA`: target unresolved, wrong control chosen, GhostAPI focus failure, an unexpected modal, a semantic error, entity ambiguity, a postcondition failure, a GhostAPI timeout, or an incorrect binding.

A **trial** is a canonical statistical slot. A **trial attempt** is one execution of that slot. An infrastructure-invalid attempt may be replaced by another attempt of the *same* slot (same probe, same stratum). Every attempt is retained, and no slot is counted twice. Classification rules and replacement limits are defined in `BENCHMARKS.md` §8.3.

---

## 20. Research anti-patterns

The following invalidate the intended claim:

### App-specific branching

```python
if bundle_id == "com.example.foo":
    click_toolbar_plus()
```

### Prompt leakage

```text
You are controlling Bear. The plus button creates a note.
```

### Model memory as evidence

```text
The model knows this is a note-taking app, therefore "+" means new note.
```

### Self-verification

```text
executor returned OK, therefore trial passed
```

### Cleanup circularity

```text
create probe → use newly learned delete capability → assume clean state
```

### Post-hoc threshold changes

```text
90% failed, so redefine verified as 80%
```

### Holdout tuning

```text
test app → observe failure → patch generic code specifically for that app → keep reporting app as unseen
```

### Hidden manual support

```text
human tells agent which control corresponds to the intended capability
```

---

## 21. Interpretation of outcomes

The project should distinguish at least three outcomes.

### Case A — thesis fails

Examples:

- semantics cannot be induced reliably;
- parameters are mostly hallucinated;
- learned capabilities fail outside discovery state;
- entity identity is too ambiguous, or safe only because nearly everything is refused;
- raw computer use is as good or better after amortization;
- GIR does no better than resilient trace replay (record-and-replay with better names);
- drift repair does not work, or costs about as much as rediscovery.

The correct response is to stop or materially rethink the thesis.

### Case B — thesis holds for a narrower class

Examples:

- works well only for document-style apps;
- works only when AX quality is high;
- works only for CRUD-like workflows;
- works only where semantic state is exposed through structured accessibility;
- beats only the screenshot-only baseline, not the AX-enabled, cached, or replay baselines.

The research contribution becomes identifying that class precisely, within the eligible population recorded under §4.5.

That boundary can become the initial product scope.

### Case C — thesis survives

GhostAPI demonstrates on blind held-out apps that it can:

- discover useful semantic capabilities;
- infer supported parameters;
- re-execute them reliably;
- resolve entity identity usefully while safely rejecting ambiguous cases;
- compare favorably with the strongest applicable baseline after discovery, by the H6 definition in `BENCHMARKS.md` §7.10;
- survive at least one predeclared UI drift condition through automatic rebinding at a cost clearly below rediscovery.

Even in Case C, claims stay limited to the eligible population (§4.5).

Only then should the project expand into a developer product.

---

## 22. Changes to this protocol

Changes are allowed during development.

However:

- all changes are versioned;
- material changes require an ADR when they affect architecture or research validity;
- a protocol change after seeing a held-out result cannot retroactively change that result;
- once a held-out app has influenced a protocol change, that app is spent;
- final benchmark runs must use a protocol frozen before app reveal.

Version history:

| Version | Change | ADR |
|---|---|---|
| v0.1 | Initial draft | none |
| v0.2 | Week 0 protocol repair: observation terminology; H1 construct validity and identifiability; H2 recall; H3 state strata; H4 usefulness; H5 rebinding vs rediscovery and drift taxonomy; H6 definition; verification/adjudication split; INVALID_INFRA and trial/attempt; fixture and population scope; vision gate and baseline exemption | ADR-009, ADR-011, ADR-014 |

---

## 23. Open research questions

These are intentionally unresolved until evidence answers them:

1. What canonical representation best preserves semantic state while suppressing AX noise?
2. How much exploration is required before useful capability discovery saturates?
3. How should semantic hypotheses be clustered when multiple UI transitions appear to represent the same action?
4. What evidence is sufficient to infer parameter types?
5. Which observable features produce stable entity handles?
6. When should GhostAPI refuse to bind a semantic target?
7. When is vision justified over structured accessibility?
8. Which app classes provide enough observable state for reliable discovery?
9. What is the practical break-even point where discovery cost is amortized?
10. Does GIR remain stable across realistic application updates?

These questions are research outputs, not excuses to expand scope prematurely.
