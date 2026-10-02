# GhostAPI Research Protocol

**Status:** Draft v0.1  
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
- screenshots captured inside the disposable VM;
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

### H2 — Parameter induction

**Claim:** GhostAPI can infer useful action parameters and types from evidence rather than inventing them.

A valid parameter must be supported by observed controls, state transitions, or repeated experiments.

Examples:

```text
create_item(title: string)
```

is supported if a newly created item exposes a text input whose value persists into the resulting entity.

This claim is weakened when the semantic model invents unsupported parameters such as `body`, `folder`, or `priority` because those fields are common in similar apps.

### H3 — Re-execution

**Claim:** A learned capability can be executed reliably from fresh application state and across new sessions, not only from the exact discovery state.

A capability that works once directly after discovery but fails after app relaunch, VM reset, focus changes, or benign state changes has not demonstrated reusable machine-interface behavior.

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

### H5 — Drift resilience

**Claim:** A stable GIR capability can survive a UI binding change through automatic rebinding without changing the public semantic contract or adding app-specific patches.

A valid drift result requires:

1. the public capability remains the same;
2. the previous binding fails or becomes unavailable;
3. GhostAPI discovers/resolves a new binding automatically;
4. the capability succeeds under the same benchmark oracle;
5. no human edits selectors, menu paths, labels, prompts, or app-specific hints after seeing the failure.

### H6 — Amortized advantage

**Claim:** After paying one-time discovery cost, repeated GhostAPI execution is meaningfully more reliable and/or less expensive than a raw screenshot-based computer-use baseline for the same tasks.

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

An `Observation` is the raw evidence available at a point in time.

It may include:

```text
timestamp
app/process identity
window list
AX tree
focused element
visible text
screenshot path
input/action history
capture metadata
```

### 7.1 Raw vs derived evidence

Raw observations are immutable.

Derived structures may include:

- canonical tree;
- state fingerprint;
- structural diff;
- semantic UI annotations;
- transition records;
- entity candidates.

Derived structures must be reproducible from raw evidence plus versioned code/config.

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

State fingerprints are derived from canonicalized observations.

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
- `UNKNOWN`: allowed only under conservative rules defined in `SECURITY.md`.
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

## 13. Independent verification

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
Verification: visual state + persisted UI after relaunch
```

or:

```text
Execution: keyboard/AX
Verification: approved local filesystem oracle
```

If the only available oracle is the same UI channel, record the limitation.

The verifier must evaluate the declared postcondition, not merely whether the action sequence completed without error.

---

## 14. Entity identity protocol

GhostAPI distinguishes:

### Element handle

An ephemeral reference to a UI element observed at one moment.

Example:

```text
ax:18273
```

It is not stored as semantic identity.

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

- raw ephemeral AX handles as identity;
- fragile absolute coordinates as the only binding;
- app-specific code paths inside generic runtime logic.

---

## 16. Drift protocol

A drift test is designed before the held-out drift result is observed.

Examples of drift:

- menu item moves to toolbar;
- control label changes;
- toolbar layout changes;
- a button becomes a menu command;
- non-semantic wrapper hierarchy changes.

A drift test does **not** count if:

- the public semantic behavior changed;
- a human edits the binding after failure;
- target-specific hints are added;
- the prompt is modified based on the failed held-out app;
- the benchmark oracle is weakened.

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

GhostAPI begins AX-first.

Vision may be added only after a measured development-app failure mode demonstrates that AX alone does not expose enough information to continue fairly.

The criterion for adding vision must be defined in this file or an ADR before it is used.

Examples of acceptable evidence:

- repeated inability to identify interactive controls represented visually but absent from AX;
- inability to verify postconditions because relevant state is only rendered graphically;
- benchmark-independent development evidence showing a systematic accessibility gap.

Vision must not be added after a held-out result merely because it would improve that result.

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
canonicalization version
exploration budget
trial budget
benchmark/protocol version
oracle version
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

The benchmark protocol defines whether and how invalid infrastructure trials are rerun.

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
- entity identity is too ambiguous;
- raw computer use is as good or better after amortization;
- drift repair does not work.

The correct response is to stop or materially rethink the thesis.

### Case B — thesis holds for a narrower class

Examples:

- works well only for document-style apps;
- works only when AX quality is high;
- works only for CRUD-like workflows;
- works only where semantic state is exposed through structured accessibility.

The research contribution becomes identifying that class precisely.

That boundary can become the initial product scope.

### Case C — thesis survives

GhostAPI demonstrates on blind held-out apps that it can:

- discover useful semantic capabilities;
- infer supported parameters;
- re-execute them reliably;
- resolve or safely reject entity identity;
- compare favorably with the baseline after discovery;
- survive at least one predeclared UI drift condition through automatic rebinding.

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
