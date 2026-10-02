# GhostAPI Benchmark Protocol

**Status:** Draft v0.1  
**Owner:** Human owner + research lead  
**Applies to:** Pilot holdout and Week 6 benchmark  
**Authority:** This file is the single source of truth for benchmark suites, quantitative thresholds, trial counts, statistical reporting, baselines, holdout freeze, and decision-gate measurements.

---

## 1. Purpose

The benchmark exists to answer:

> **Does GhostAPI discover and reuse a useful machine interface on genuinely unseen macOS applications, and does that learned interface provide measurable value over raw computer use?**

The benchmark is not a demo script.

It must be designed so that GhostAPI can fail honestly.

---

## 2. Benchmark stages

### Stage 0 — development

Known development apps.

Purpose:

- build the system;
- create fixtures;
- tune canonicalization;
- test risk rules;
- build semantic eval cases;
- debug experiment infrastructure.

Development results are not generalization evidence.

### Stage 1 — pilot holdout

One unseen application.

Purpose:

- test the full frozen evaluation machinery;
- reveal protocol holes;
- validate artifact capture and scoring;
- check whether the benchmark is executable in practice.

The pilot becomes spent immediately after reveal/use.

If changes are made because of pilot results, freeze a new version before final benchmark apps.

Pilot results must be reported separately from final benchmark results.

### Stage 2 — final benchmark

Three fresh held-out applications.

The final benchmark is the primary generalization result.

---

## 3. App eligibility

A benchmark app should:

- run locally on macOS;
- work without a personal account;
- not require cloud sync;
- not require payments;
- support local dummy data;
- expose enough interaction to define at least several meaningful tasks;
- be installable in the disposable VM;
- not have been used during development;
- preferably be obscure enough to reduce model prior-knowledge leakage;
- not be selected after observing GhostAPI performance on it.

Avoid using only famous Apple apps as headline evidence.

Well-known apps may be useful for development fixtures but do not provide strong evidence of unseen generalization.

---

## 4. Holdout secrecy and denylist

Held-out app names are stored outside the repository until reveal.

The repository receives only a denylist mechanism such as:

```text
GHOST_HOLDOUT_DENYLIST
```

The actual names must not appear in:

- prompts;
- fixtures;
- code;
- comments;
- task descriptions available before reveal;
- semantic eval examples;
- benchmark development artifacts.

During benchmark execution, app identity should be aliased/redacted from LLM evidence where practical.

Every revealed, attempted, failed, partially run, or aborted holdout is permanently **spent**.

---

## 5. Freeze manifest

Before each holdout reveal, create an immutable freeze record containing:

```text
benchmark protocol version
research protocol version
git commit/tag
dirty-tree status
VM/base image identifier
macOS guest version
Ghost Bridge version
Ghost Core version
GIR schema version
database schema version
model provider/model/config
prompt versions/hashes
canonicalization version
risk-rule version
exploration budget
LLM token/cost budget
trial count
reliability threshold
publication threshold
baseline configuration
task suite version
oracle version
drift protocol
random seeds
```

If the working tree is dirty, the run is invalid for final reporting unless the dirty diff is archived in the manifest and explicitly approved before app reveal.

---

## 6. Capability lifecycle

A discovered capability can have one of these statuses:

```text
CANDIDATE
EXPERIMENTAL
VERIFIED
REJECTED
```

### CANDIDATE

Semantic hypothesis exists, but repeated trials have not established reliability.

### EXPERIMENTAL

The capability has some successful evidence but does not satisfy the verified publication rule.

### VERIFIED

A capability is verified only when:

- it is semantically supported by evidence;
- its declared inputs are supported by evidence;
- the experiment oracle confirms the intended outcome;
- it has **N >= 20** valid fresh-state reliability trials;
- observed reliability is **>= 0.90**;
- all trials are included in reporting;
- its 95% Wilson interval is reported;
- any entity targeting satisfies the entity-resolution rules;
- no target-app-specific patch was required.

### REJECTED

A capability is rejected when:

- experiments falsify the hypothesis;
- reliability is below the publication threshold;
- semantics cannot be distinguished safely;
- required identity resolution is ambiguous;
- execution depends on disallowed app-specific knowledge.

A rejected hypothesis still counts as a discovery attempt and remains in artifacts/results.

---

## 7. Primary benchmark metrics

The final report must include all metrics below.

### 7.1 Useful capabilities discovered per app

**Target:** at least **5 VERIFIED useful capabilities per benchmark app**.

A capability is “useful” only if it supports at least one predeclared human-authored benchmark task or represents a meaningful reusable operation judged before seeing GhostAPI's output.

Trivial UI mechanics do not count by themselves.

Examples that do not count as useful capabilities:

```text
focus_window()
click_button_4()
open_menu()
scroll_down()
```

Examples that may count:

```text
create_document(title)
create_folder(name)
search(query)
rename_item(entity, name)
toggle_setting(name, enabled)
```

### 7.2 Capability precision

**Target:** >= **90%**.

Definition:

```text
correctly published VERIFIED capabilities
-----------------------------------------
all published VERIFIED capabilities
```

A published capability is correct only if:

- its semantic name/description reasonably matches behavior;
- its parameter schema is supported;
- it does not claim unsupported side effects;
- the benchmark oracle verifies it performs the declared operation.

Human semantic judgement is recorded using the rubric in Section 11.

### 7.3 Execution reliability

For each VERIFIED capability:

```text
successful valid trials
-----------------------
all valid trials
```

Requirements:

- **N >= 20**
- observed reliability **>= 0.90**
- report **95% Wilson confidence interval**

Aggregate reliability must be reported both:

- macro-averaged across capabilities;
- micro-averaged across all trials.

Do not report only the better aggregate.

### 7.4 Parameter/schema accuracy

Report:

```text
supported declared parameters
-----------------------------
all declared parameters
```

Also report:

- missing necessary parameters;
- invented/unsupported parameters;
- wrong type assignments;
- wrong required/optional classification where measurable.

**Target:** >= **90% supported declared parameters** across VERIFIED capabilities.

### 7.5 Capability coverage / recall

Because a UI may contain capabilities GhostAPI never sees, recall requires a hidden human-authored oracle.

Before the run, the human owner defines a set of benchmark-relevant capability families/tasks for the app.

Report:

```text
oracle capability families successfully represented
---------------------------------------------------
oracle capability families declared in benchmark
```

This is **benchmark task coverage**, not a claim that we know every capability in the app.

**Target:** >= **60% benchmark task coverage** per app.

Coverage is intentionally lower than precision: GhostAPI should prefer publishing fewer trustworthy capabilities over many dubious ones.

### 7.6 Entity-resolution safety

For tasks involving existing entities, report:

- correct entity resolution rate;
- ambiguous refusal rate;
- false-target rate;
- not-found rate.

**Safety target:** **0 silent false-target executions** in the final benchmark.

A safe refusal is preferable to modifying the wrong entity.

### 7.7 Exploration cost

Report per app:

```text
wall-clock learning time
UI actions
states visited
transitions recorded
LLM calls
input tokens
output tokens
vision calls
estimated model cost
VM resets/clones
human approvals
```

There is no universal pass threshold for discovery cost in v0.1, but it must be fully reported.

### 7.8 Repeated execution cost

For each benchmark task after learning, report:

```text
wall-clock latency
UI actions
LLM calls
tokens
vision calls
estimated cost
human intervention
```

### 7.9 Drift recovery

At least **one VERIFIED capability** must undergo a predeclared drift test.

**Pass condition:**

- previous binding no longer resolves or no longer reaches the postcondition;
- public GIR capability/schema is unchanged;
- GhostAPI automatically discovers/resolves a new binding;
- no app-specific patch or human selector edit is introduced;
- capability passes the same verification oracle after rebinding;
- subsequent reliability run meets the normal VERIFIED threshold.

---

## 8. Statistical method

### 8.1 Wilson interval

For a proportion:

```text
p = successes / N
```

report the two-sided **95% Wilson score interval**.

Do not use “90% ± something” without the interval.

### 8.2 Zero-success and perfect-success reporting

Even at:

```text
20/20
```

report the interval.

Do not state “100% reliable.”

Say:

```text
Observed reliability: 100% (20/20)
95% Wilson interval: ...
```

### 8.3 Invalid trials

A trial may be marked:

```text
INVALID_INFRA
```

only for failures unrelated to GhostAPI's semantic/execution behavior, such as:

- VM failed to boot;
- capture service crashed before action execution;
- disk corruption;
- benchmark harness itself malfunctioned.

Invalid trials:

- remain in artifacts;
- are reported separately;
- do not enter the capability reliability denominator;
- may be rerun from a clean state using the same frozen protocol.

Failures such as these are **not** infrastructure-invalid:

- target unresolved;
- wrong control selected;
- unexpected sheet/dialog;
- app focus lost because GhostAPI mishandled it;
- GhostAPI got stuck;
- postcondition not achieved;
- entity ambiguous;
- semantic hypothesis wrong.

Those are benchmark failures.

---

## 9. Raw computer-use baseline

The baseline answers:

> **What happens if we skip learning/GIR and simply let a computer-use agent solve each task from screenshots every time?**

### 9.1 Baseline constraints

The baseline must use:

- the same benchmark tasks;
- the same clean starting state;
- the same app version;
- the same VM environment;
- the same high-level task wording;
- the same approval/risk policy;
- a comparable model capability tier where possible;
- a predeclared token/action/time budget.

The baseline must not receive GhostAPI's GIR, discovered bindings, transition graph, or semantic hypotheses.

### 9.2 Baseline actions

The v0.1 baseline receives screenshots and may use generic computer controls such as:

```text
click(x, y)
type(text)
press(key)
scroll(...)
wait(...)
```

If the baseline is given AX or structured accessibility data, report it as a separate structured-computer-use baseline rather than mixing results.

### 9.3 Baseline runs

Each benchmark task should be run enough times to estimate repeatability.

Default:

```text
N >= 10 per baseline task
```

If cost prevents this, the reduced N must be frozen before app reveal and clearly reported.

### 9.4 Baseline metrics

Compare:

- task success;
- latency;
- action count;
- token count;
- model cost;
- vision calls;
- human intervention.

Do not combine GhostAPI discovery cost with every GhostAPI execution.

Report both:

```text
one-time discovery cost
```

and:

```text
steady-state execution cost
```

---

## 10. Amortization analysis

For each app or capability family, estimate when GhostAPI's one-time learning cost breaks even against repeated raw computer-use execution.

Let:

```text
D = one-time GhostAPI discovery cost
G = average GhostAPI steady-state execution cost
B = average baseline execution cost
```

If:

```text
B > G
```

then approximate break-even executions:

```text
ceil(D / (B - G))
```

Report break-even separately for:

- monetary/model cost;
- token usage;
- wall-clock time when meaningful.

If GhostAPI never breaks even under measured conditions, say so.

---

## 11. Semantic usefulness rubric

The human owner scores each published capability before viewing aggregate benchmark results.

Each capability is judged on:

### 11.1 Semantic correctness

Does the name describe the observed state transition?

```text
2 = correct
1 = partially correct / overly generic
0 = wrong
```

### 11.2 Parameter correctness

Are declared parameters supported and typed reasonably?

```text
2 = correct
1 = minor issue
0 = material unsupported/missing schema
```

### 11.3 Reusability

Is this a meaningful operation an agent/user might call more than once?

```text
2 = clearly reusable
1 = marginal
0 = UI mechanic rather than semantic capability
```

A capability counts as **useful and semantically correct** only if:

- semantic correctness = 2;
- parameter correctness >= 1;
- reusability = 2.

The raw rubric results are included in the report.

---

## 12. Benchmark task design

For each held-out app, the human owner prepares a hidden task suite before execution.

Tasks should span more than one interaction style where the app supports them, for example:

- create;
- query/search;
- modify;
- organize/move;
- toggle/configure;
- open/select;
- inspect/read.

Do not require destructive actions merely to make the benchmark difficult.

Avoid tasks that depend on:

- cloud login;
- external account state;
- network availability;
- nondeterministic external data;
- proprietary information not represented in the local UI.

Each task includes:

```text
task_id
natural-language goal
starting snapshot/state
allowed risk class
oracle
success condition
timeout/action budget
```

---

## 13. Oracle design

An oracle is the independent success check for a task/capability.

Preferred order:

1. independent local state check not used for execution;
2. app state after relaunch;
3. second observation modality;
4. UI-only verification if nothing else is available.

Examples:

```text
Execution via AX
Oracle via filesystem artifact
```

or:

```text
Execution via AX
Oracle via relaunch + fresh AX observation
```

The oracle must be frozen before running the held-out task.

Do not weaken the oracle after a failure.

---

## 14. Drift benchmark

The drift condition must be selected before observing drift behavior.

Acceptable drift sources:

- app version update;
- user-configurable toolbar change;
- menu relocation;
- label change;
- UI hierarchy change that preserves semantics.

The pre-drift capability must already be VERIFIED.

Drift evaluation sequence:

```text
1. verify capability on old UI
2. apply declared drift
3. confirm old binding fails or changes
4. invoke same GIR capability
5. allow generic automatic rebinding
6. verify postcondition
7. rerun reliability trials
```

A manual binding edit invalidates the self-healing result.

---

## 15. Discovery/publication budgets

Budgets are frozen before holdout reveal.

At minimum freeze:

```text
maximum wall-clock learning time
maximum explored states
maximum UI actions
maximum LLM calls
maximum input/output tokens
maximum estimated LLM spend
maximum number of human approvals
maximum retries
```

A run that exceeds budget stops.

Do not raise the budget because the app “looks close.”

A future protocol version may use a different budget with a fresh holdout.

---

## 16. Benchmark report structure

Every held-out app report includes:

### Environment

```text
app alias
app version/hash
macOS version
VM/base image
git tag
protocol versions
model/config
prompt versions
budgets
```

### Discovery

```text
states visited
transitions
candidate hypotheses
rejected hypotheses
experimental capabilities
verified capabilities
learning time/cost
```

### Capability table

For every published/rejected capability:

```text
name
status
semantic rubric
parameters
N
successes
observed reliability
95% Wilson interval
entity-resolution stats
evidence references
```

### Baseline

```text
task success
latency
actions
tokens
vision calls
cost
```

### Drift

```text
capability
old binding
declared drift
new binding
automatic/manual
post-drift reliability
```

### Limitations

Report:

- AX gaps;
- hidden/virtualized state;
- ambiguity;
- serialization/focus constraints;
- oracle weaknesses;
- invalid infrastructure trials;
- model prior-knowledge concerns;
- any protocol deviations.

---

## 17. Benchmark-level success criteria

The Week 6 result satisfies the **research success gate** only if all of the following are true across the three final held-out apps:

1. **Useful discovery:** each app has at least **5 VERIFIED useful capabilities**.
2. **Capability precision:** aggregate VERIFIED capability precision is **>= 90%**.
3. **Per-capability reliability:** every capability counted toward the 5-per-app target satisfies **N >= 20** and observed reliability **>= 90%**.
4. **Parameter accuracy:** aggregate supported declared-parameter accuracy is **>= 90%**.
5. **Task coverage:** each app reaches **>= 60%** of the hidden benchmark task/capability-family coverage set.
6. **Entity safety:** **0 silent false-target executions** in final benchmark entity-targeting tasks.
7. **Drift:** at least one predeclared capability successfully self-rebinds after UI drift and again satisfies VERIFIED reliability.
8. **Baseline evidence:** GhostAPI demonstrates a meaningful measured advantage over raw computer use in at least one of:
   - task success;
   - steady-state latency;
   - steady-state token/model cost;
   - repeatability;

   and is not materially worse across all remaining measures without a clear documented trade-off.
9. **Integrity:** no held-out app-specific patches, prompt hints, target-app research, post-hoc threshold changes, or hidden human selector help occurred.

If conditions 1–7 pass but baseline advantage does not, the system may still be technically interesting, but H6 is not supported and the product thesis must be reconsidered.

---

## 18. Decision gate

### Case A — stop or rethink

Choose Case A when:

- useful capabilities are not discovered reliably;
- precision is poor;
- execution is unstable;
- entity targeting is unsafe;
- drift repair fails;
- the baseline is equally good or better with no amortized benefit.

### Case B — narrow the scope

Choose Case B when:

- results are strong only for a specific app class;
- AX quality strongly predicts success;
- CRUD/document-style apps work but complex custom-canvas apps do not;
- one hypothesis fails while the others hold.

The next step is to define the successful app class precisely and rerun future research on fresh holdouts from that class.

### Case C — continue as a product/open-source project

Choose Case C only when the final benchmark satisfies the research success gate and the result remains compelling after limitations are stated plainly.

After Case C, product work may begin:

```text
ghost serve
REST generation
MCP generation
SDKs
open-source packaging
public benchmark
public technical write-up
```

---

## 19. Protocol changes

Any material change to this file increments the benchmark protocol version.

After a held-out app is revealed:

- that app is spent;
- changes motivated by its results apply only to future fresh holdouts;
- prior results remain scored under the protocol used at the time;
- do not retroactively rescore to make results pass.

---

## 20. Recommended benchmark artifacts

Suggested layout:

```text
benchmarks/
├── protocol/
│   └── v0.1.yaml
├── tasks/
│   └── <hidden or encrypted outside-repo definitions>
├── baseline/
├── metrics/
├── reports/
└── denylist.txt

experiments/
└── <run_id>/
    ├── manifest.json
    ├── discovery.json
    ├── capabilities.json
    ├── trials.jsonl
    ├── baseline.jsonl
    ├── drift.json
    └── report.md
```

Raw screenshots/AX trees remain under `artifacts/` and are referenced by immutable IDs/hashes rather than duplicated into every report.

---

## 21. What not to optimize for

Do not optimize GhostAPI for:

- benchmark app names;
- a pretty demo;
- maximum number of discovered capabilities;
- passing by publishing vague generic actions;
- short-term benchmark score at the cost of generality;
- model-generated confidence;
- hiding failure cases.

Optimize for:

> **A small set of semantically meaningful capabilities that are discovered without app-specific knowledge, empirically validated, conservatively executed, and reusable after learning.**
