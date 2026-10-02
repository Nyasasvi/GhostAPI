# GhostAPI Benchmark Protocol

**Status:** Draft v0.2 (Week 0 protocol repair; see ADR-014). Headline thresholds unchanged from v0.1.  
**Owner:** Human owner + research lead  
**Applies to:** Pilot holdout and Week 6 benchmark  
**Authority:** This file is the single source of truth for benchmark suites, quantitative thresholds, trial counts, statistical reporting, baselines, holdout freeze, and decision-gate measurements.

---

## 1. Purpose

The benchmark exists to answer:

> **Does GhostAPI discover and reuse a useful machine interface on genuinely unseen macOS applications, and does that learned interface provide measurable value over raw computer use and over the stronger diagnostic alternatives in §9?**

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

### 3.1 Eligible population, screening, and exclusions

Before any holdout is selected, the human owner freezes (see `RESEARCH.md` §4.5):

- the eligible-population definition (initial proposal: local macOS apps that work offline, can be used with dummy data, need no personal or cloud account, and expose enough observable accessibility surface for meaningful interaction);
- the screening procedure, including any generic accessibility-surface check, which the human runs privately without the agent;
- an exclusion log with one row per screened-out candidate (reason code and date), kept private until the benchmark report.

The benchmark report states the population, the screening procedure, and the number of exclusions by reason code. Results generalize only to that population.

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
platform-normalizer version
canonicalization version
risk-rule version
exploration budget
LLM token/cost budget and spend limits (ADR-013)
trial count
state-strata definitions and allocation (§6.1)
futility-stop rule (§6.2)
reliability threshold
publication threshold
necessary-parameter recall target (§7.4)
entity-resolution request sets and targets (§7.6)
baseline arms, models, budgets, and N per arm (§9)
natural-language router model/config/prompt hash, if Evaluation C runs (§9.5)
usage horizon, cost rates, and sensitivity range (§10)
rebinding budget and H5 validation route (§7.9, §14)
task suite version
oracle version (hash of the sealed oracle bundle)
eligible-population definition and exclusion-log hash (§3.1)
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
- internal behavioral verification (`RESEARCH.md` §13.1) confirms the declared postcondition;
- it has **N >= 20** valid fresh-state reliability trials, spread across the preregistered state strata (§6.1);
- observed reliability is **>= 0.90**;
- no single state stratum has more than one failed trial (§6.1);
- all trials are included in reporting;
- its 95% Wilson interval is reported;
- any entity targeting satisfies the entity-resolution rules;
- no target-app-specific patch was required.

VERIFIED is decided by internal verification only. Whether the capability means what its name claims is decided separately, by hidden adjudication (§13), after publication.

### 6.1 State strata and trial allocation

Every reliability trial starts from a clean, externally reset state (clone of a frozen seed). The harness then applies the trial's stratum setup before invoking the capability. Stratum setups are generic harness operations or human-prepared seed variants. They never use GhostAPI's learned capabilities.

| Stratum | Setup | Prepared by | Slots of N = 20 |
|---|---|---|---|
| S0 clean | frozen app seed, app launched | harness | 4 |
| S1 relaunch | app quit and relaunched before the call | harness (generic) | 4 |
| S2 window/focus | window moved and resized to a seeded position; focus given to another app first | harness (generic) | 4 |
| S3 entity population | seed variant with more, fewer, or reordered benign entities (different list size) | human, before reveal | 4 |
| S4 benign preference/modal | seed variant with a benign preference or presentation change, or a no-modal/modal start where the app has one | human, before reveal | 4 |

Rules:

- The allocation is frozen before trials. If a stratum does not apply to an app, that is declared before the run with a reason, and its slots are reassigned round-robin to S0–S2.
- Trial order is a seeded random interleaving of strata, so a time trend cannot hide inside one stratum.
- Per-stratum success counts are always reported.
- **Concentration rule:** a capability with more than one failure in any single stratum is not VERIFIED, even if its overall rate is at least 0.90. With N = 20, at most two failures are allowed in total. This rule stops both from falling in the same condition, where they would signal state-specific fragility.
- Stratification spreads N; it never multiplies it. Any proposal to raise per-stratum N must include the trial-cost impact first.

### 6.2 Futility stop

A capability's reliability run stops as soon as its failure count makes VERIFIED impossible: the third failure at N = 20, or the second failure within one stratum. Its status becomes EXPERIMENTAL or REJECTED, and the unexecuted slots are reported as `NOT_RUN_FUTILITY`. This rule can only end runs early for capabilities that are already excluded, so it cannot create a false positive. It reduces trial cost.

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
- hidden adjudication (§13) confirms it performs the declared operation.

Human semantic judgement is recorded using the rubric in Section 11. Adjudication runs only after the published capability set has been snapshotted and hashed.

Also report the **false-positive postcondition rate**: trials that passed internal verification but failed hidden adjudication, divided by trials that passed internal verification. This directly measures how far "behavior observed" differs from "meaning correct".

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

Also report success per state stratum (§6.1), per capability and pooled, with Wilson intervals. The intervals will be wide at 4 trials per stratum; they are reported to locate fragility, not to make per-stratum claims.

### 7.4 Parameter/schema accuracy

Parameter accuracy is measured as **precision and recall**, so declaring fewer parameters cannot inflate the score.

**Precision** (unchanged from v0.1):

```text
supported declared parameters
-----------------------------
all declared parameters
```

**Recall** (new in v0.2):

```text
necessary parameters declared by GhostAPI
-----------------------------------------
necessary parameters defined by the adjudication oracle
```

A parameter is **necessary** when the oracle's mapped benchmark task cannot be completed as specified without supplying that value through a UI-visible input. For each oracle capability family, the human owner lists necessary parameters in the sealed oracle bundle before reveal. Parameters that no allowed channel can observe are excluded from the denominator and listed as `UNOBSERVABLE`.

Worked example: the oracle defines `create_event(title, date, time, location)` as necessary, and GhostAPI declares `create_event(title)`. Precision is 1/1, recall is 1/4, and the schema is **not** correct.

Also report, where observable:

- missing necessary parameters (by name);
- invented/unsupported parameters;
- type correctness;
- required/optional classification;
- enum values;
- defaults;
- basic constraints (length, range, format).

Recall is computed only for VERIFIED capabilities that adjudication maps to an oracle family.

**Targets:**

- >= **90% supported declared parameters** across VERIFIED capabilities (unchanged);
- >= **80% necessary-parameter recall** across VERIFIED capabilities mapped to oracle families (**new; proposed value, requires owner approval**).

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

### 7.6 Entity-resolution safety and usefulness

For each app with at least one VERIFIED entity-targeting capability, the sealed oracle bundle predeclares two request sets:

- **resolvable requests:** the intended entity is uniquely identifiable from observable evidence (for example after a rename or reorder, or when a similar-looking entity is also present);
- **ambiguous requests:** the intended entity cannot be told apart from another by any allowed observation (for example true duplicates).

Minimum per app: **10 resolvable + 10 ambiguous** requests. Resolvable requests may be drawn from the capability's own reliability trials. Ambiguous requests are extra trials.

Report:

- correct-resolution rate (resolvable set);
- false-target rate: executed on the wrong entity (both sets);
- unsafe-resolution rate: executed at all on an ambiguous request (ambiguous set);
- ambiguous-refusal rate (both sets; appropriate only on the ambiguous set);
- not-found rate (both sets);
- **entity-resolution coverage**: resolvable requests on which GhostAPI acted, divided by all resolvable requests.

**Targets:**

- **Safety:** **0 silent false-target executions** and **0 unsafe resolutions** in the final benchmark.
- **Usefulness:** correct-resolution rate on the resolvable set **>= 0.80** (**new; proposed value, requires owner approval**). A resolver that refuses everything fails this target.

A safe refusal is preferable to modifying the wrong entity. Refusing everything is safe but does not support H4. If no entity-targeting capability is VERIFIED for an app, report H4 as **not tested** for that app.

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
VM-hours (exploration, hypothesis trials, rejected-candidate trials)
failed or aborted discovery attempts and their cost
human approvals and human minutes spent on them
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
retries (attempts per successful execution)
verification overhead, if the runtime verifies postconditions
natural-language routing cost, reported separately (§9.5)
```

Per-call cost excludes benchmark-only VM clone/reset overhead for **every** arm, because steady-state use runs against a live app. Reset overhead is included in GhostAPI discovery cost, because discovery needs it.

### 7.9 Drift recovery

At least **one VERIFIED capability** must undergo a predeclared drift test.

**Pass condition:**

- previous binding no longer resolves or no longer reaches the postcondition;
- public GIR capability/schema is unchanged;
- GhostAPI automatically discovers/resolves a new binding;
- no app-specific patch or human selector edit is introduced;
- capability passes the same verification oracle after rebinding;
- subsequent reliability run meets the normal VERIFIED threshold;
- the capability's inputs and semantic postcondition are unchanged (not only its name);
- the rebinding search stayed within the **rebinding budget** below.

**Rebinding budget** (**new; proposed value, requires owner approval**). Let `D_search` be the app's pre-drift discovery *search* cost: exploration, semantic calls, and candidate experiments, excluding the final N-trial reliability runs, which both paths need anyway. Rebinding may use at most **25% of `D_search`**, measured separately in UI actions, wall-clock time, and LLM cost. If any one is exceeded, the attempt counts as a rebinding failure and is reported as "equivalent to rediscovery".

Rationale: with the 5-capability target, one capability's share of discovery search is about 20%. Rebinding that costs more than that share is not cheaper than rediscovering that capability.

**Report for every drift test:**

- drift class (`RESEARCH.md` §16.1) and source (fixture or real-app mechanism);
- old and new binding;
- rebinding success;
- rebinding cost (actions, wall-clock, LLM calls, tokens, $);
- cost ratio `R = rebinding cost / D_search`;
- post-drift reliability (N >= 20, stratified, Wilson interval);
- whether the semantic subsystem was invoked, and how many candidates were proposed, rejected, and verified.

For fixture drift, run one actual full rediscovery on the drifted fixture, once per drift class tested, to check that `D_search` is a fair stand-in for rediscovery cost.

### 7.10 H6: what counts as a material advantage

Only **reliability** and **success-adjusted total cost** can support H6. Latency, actions, and tokens are always reported, but none alone supports H6.

All comparisons use the same tasks, starting strata, probe inputs, and approval policy for every arm. The comparison arm for each claim is the **strongest** applicable baseline arm on that metric (§9).

**Reliability advantage** (**new; proposed definition, requires owner approval**):

- pooled steady-state task success for GhostAPI minus the strongest arm's is **>= 10 percentage points**; and
- the 95% Newcombe (Wilson-score) interval for that difference excludes 0.

Both are computed per app and pooled across the final apps.

**Cost advantage** (**new; proposed definition, requires owner approval**):

- GhostAPI's success-adjusted steady-state cost per successful task (§10) is **<= 50%** of the strongest arm's; and
- GhostAPI's success rate is not more than **5 percentage points** below that arm's; and
- break-even falls within the usage horizon (§10) in the base case.

**How H6 is reported:**

- **Supported (strong):** a reliability or cost advantage over every required arm (B1, B2, B4).
- **Supported only against weaker arms:** name which arms and which not. This is a Case B signal (`RESEARCH.md` §21).
- **Not supported:** no advantage over B1, or break-even beyond the horizon with no reliability advantage.

End-to-end comparisons against computer-use arms require Evaluation C (§9.5). Without it, H6 may be claimed only at the execution level against B4, and is labeled "routing excluded".

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

### 8.3 Invalid trials, trials, and trial attempts

A **trial** is a canonical statistical slot: `(experiment_id, slot_index, stratum, probe)`, fixed before execution. A **trial attempt** is one execution of a slot. Trials are counted once. Attempts are stored append-only.

An attempt may be marked:

```text
INVALID_INFRA
```

only when a **preregistered harness fault code** was detected and logged by the harness itself, independently of the attempt's outcome. Harness fault codes (v0.2):

| Code | Condition |
|---|---|
| `VM_CLONE_FAILED` | clone could not be created |
| `VM_BOOT_FAILED` | VM did not reach bridge-ready before GhostAPI's first action |
| `BRIDGE_UNHEALTHY_PRE` | bridge health check failed before GhostAPI's first action |
| `CAPTURE_UNAVAILABLE` | capture subsystem unavailable (permission or service), detected by the harness health probe |
| `HOST_IO_ERROR` | host disk full or disk/IO corruption logged by the harness |
| `HYPERVISOR_CRASH` | VM process exited abnormally, confirmed by the VM adapter, not by an app crash |
| `HARNESS_EXCEPTION` | uncaught exception in harness (not GhostAPI) code, with stack trace |
| `ISOLATION_PROBE_FAILED` | pre-trial network-isolation probe failed; the attempt is aborted before any action |

Rules:

- A fault is classified only from the harness log written at detection time. It can never be assigned after seeing a failed postcondition.
- Any fault after GhostAPI's first mutating action is a GhostAPI failure unless it carries one of the codes above **and** the harness evidence shows GhostAPI did not cause it. A target-app crash is always a GhostAPI failure.
- A slot may have at most **2 replacement attempts** (3 attempts in total). Replacements reuse the same stratum and probe. All attempts are retained and reported.
- A slot whose attempts are all `INVALID_INFRA` is `INFRA_EXHAUSTED`. If more than 10% of a capability's slots are `INFRA_EXHAUSTED`, its reliability is *indeterminate* for that run and it cannot be VERIFIED from that run.
- Report the `INVALID_INFRA` attempt rate per run and per fault code.

Invalid attempts:

- remain in artifacts;
- are reported separately;
- do not enter the capability reliability denominator;
- may be replaced as above using the same frozen protocol.

Failures such as these are **never** infrastructure-invalid:

- target unresolved;
- wrong control selected or incorrect binding;
- unexpected sheet/dialog/modal;
- app focus lost because GhostAPI mishandled it;
- GhostAPI got stuck or timed out;
- postcondition not achieved;
- entity ambiguous;
- semantic hypothesis wrong.

Those are benchmark failures.

---

## 9. Baselines

The baselines answer two questions:

> **What happens if we skip learning and GIR and let a computer-use agent solve each task every time?**
>
> **Does any GhostAPI advantage come from GIR and semantic compilation, or only from better sensors (AX), memory, caching, or persistent selectors?**

### 9.0 Arms

| Arm | What it is | Sensor | Memory across runs | Model at call time | Role | N per task (holdout) |
|---|---|---|---|---|---|---|
| **B1** screenshot CUA | stateless computer-use loop | screenshots | none | yes | primary, required | >= 10 |
| **B2** AX-enabled CUA | same loop as B1, plus the serialized PlatformObservation and element-level actions | screenshots + AX | none | yes | diagnostic, required | >= 5 |
| **B3** stateful/cached CUA | B2 loop plus a per-task memory: replay the stored successful trajectory with probe substitution, fall back to the loop on failure, update memory | screenshots + AX | yes | only on fallback | diagnostic, can wait (§9.6) | >= 5 |
| **B4** resilient trace replay | no model at call time; replays a trace recorded from the first successful B1 run (on a separate acquisition clone) using generic resilient element matching (role + label + neutral ancestor path, then label-only, then fail) with probe substitution | AX | the recorded trace | no | diagnostic, required (directly tests "record-and-replay with better names") | >= 10 |
| **G** GhostAPI | GIR capability execution (Evaluation B), with routing through the frozen router for end-to-end comparisons (Evaluation C) | AX | GIR | router only (C) | system under test | per §6 / §9.5 |

On development apps and the fixture, every arm uses N >= 10. The holdout Ns above are the reduced diagnostic Ns that §9.3 permits. They are frozen before reveal and reported as reduced.

### 9.1 Baseline constraints

Every arm must use:

- the same benchmark tasks;
- the same clean starting state and the same state strata (§6.1) where the task allows;
- the same app version;
- the same VM environment and display size;
- the same high-level task wording and the same probe values;
- the same approval/risk policy (for B1/B2 clicks, the risk classifier is applied to the element under the click point; approvals count as human intervention);
- the same model and configuration as GhostAPI's semantic model, unless the owner approves otherwise before freeze;
- the provider's native computer-use tooling where it exists (tool version recorded). A deliberately weakened baseline is invalid;
- a predeclared per-run budget (proposed: at most 30 model steps, 10 minutes wall-clock, and $2.00 model cost per run). A run that exceeds budget is a failure.

No baseline arm may receive GhostAPI's GIR, discovered bindings, StateGraph, hypotheses, or adjudication results. **The reverse also holds:** baseline outputs, trajectories, traces, and anything learned from them must never reach GhostAPI discovery, prompts, bindings, or evals (ADR-009, ADR-010).

### 9.2 Baseline actions

B1 receives screenshots and may use generic computer controls such as:

```text
click(x, y)
type(text)
press(key)
scroll(...)
wait(...)
```

B2 and B3 additionally receive the PlatformObservation text and may act on its element handles. Structured-sensor results (B2, B3) are always reported separately from screenshot-only results (B1), never mixed.

### 9.3 Baseline runs

Each benchmark task should be run enough times to estimate repeatability.

Default:

```text
N >= 10 per baseline task
```

If cost prevents this, the reduced N must be frozen before app reveal and clearly reported. The reduced diagnostic Ns in §9.0 are such a frozen reduction.

B3/B4 trace acquisition runs (the first successful B1 run per task) are counted as one-time acquisition cost for those arms. They are not scored as B3/B4 trials.

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

### 9.5 Three separate evaluations and task routing

A human must never translate hidden benchmark tasks into `ghost call` invocations after seeing the discovered capabilities. That would be hidden manual assistance. Three evaluations are kept separate:

**A. Capability discovery.** Were the right capabilities and schemas discovered? Scored by hidden adjudication (§13) and the rubric (§11): precision, coverage, parameter precision/recall. No natural-language routing is involved.

**B. Capability execution.** Each published capability is invoked through its GIR contract, with probe inputs from the frozen, generic benchmark probe generator, across the state strata. These are the same reliability trials as §6. Each trial is judged twice: by internal verification (reliability, VERIFIED status) and afterwards by hidden adjudication, using the sealed evidence captured during the trial (§13). This adds no trials. Adjudication pairs a capability with an oracle family only for **scoring**. That pairing is never used to choose what to execute.

**C. Natural-language routing** (required for end-to-end H6 claims against computer-use arms). A generic frozen router receives the task text and the published GIR capability signatures, and returns a schema-validated call or `NO_MATCH`. Router rules:

- frozen model, configuration, and prompt (`prompts/router_v1.md`), all recorded in the freeze manifest;
- no app-specific examples;
- no human correction after capability discovery;
- routing failures and `NO_MATCH` count as task failures and are never repaired manually.

For each task, the routed call is executed end to end with N matching B1, across the same strata. Routing accuracy, routing cost, and end-to-end success are reported separately from Evaluation B.

### 9.6 Arm priority under schedule pressure

B1, B2, B4, and the Evaluation C router are required for the final benchmark. B3 runs if the frozen budget allows. If B3 is not run, the report states: "H6 not tested against memory/caching computer use". The decision to run or skip B3 is frozen before reveal and never made after seeing results.

---

## 10. Amortization analysis

For each app, and for each arm compared, estimate when GhostAPI's one-time costs break even against repeated execution by that arm. Costs are success-adjusted, and every component below is included where measurable.

Per arm `a`:

```text
c_a = mean cost per attempt  = LLM $ + r_vm × VM-hours of the call + r_h × human minutes + retry cost
s_a = steady-state task success rate
C_a = c_a / s_a              = success-adjusted cost per successful task   (s_a = 0  ->  infinite)
A_a = one-time acquisition cost (B3/B4 trace acquisition; 0 for B1/B2)
```

GhostAPI:

```text
D    = discovery: exploration + semantic calls + all candidate experiments (including rejected
       candidates, failed or aborted discovery attempts, and INVALID_INFRA attempts)
       + VM clone/reset overhead + human approval minutes × r_h
M(H) = maintenance over the horizon: expected drift events × (rebinding cost + post-drift
       reliability trials) + any periodic re-verification the runtime needs
C_G  = success-adjusted steady-state cost per successful task, including verification
       overhead, retries, and routing cost (Evaluation C)
```

Break-even against arm `a`: the smallest number of successful executions `n*` for which

```text
D + M(H) + n* × C_G  <=  A_a + n* × C_a
```

If `C_G >= C_a`, GhostAPI never breaks even against that arm.

**Usage horizon** (**new; proposed value, requires owner approval**): `H` = 1,000 successful executions per app over 90 days, with 1 drift event per app per horizon.

**Declared shadow rates** (**new; proposed values, requires owner approval**): `r_vm` = $1.00 per VM-hour (order of magnitude of a rented Apple-silicon host; declared, not measured) and `r_h` = $60 per human-hour.

Report `n*` against each arm:

- as a band: at or below 10, at or below 100, at or below 1,000, or never within the horizon;
- in dollars, and separately in VM-hours and in tokens;
- in a sensitivity analysis that moves each input to ×0.5 and ×2 one at a time, plus one combined pessimistic case.

Claim an economic advantage only if base-case `n*` is within the horizon, and always report the pessimistic case beside it. If GhostAPI never breaks even under measured conditions, say so.

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
starting snapshot/state and applicable state strata (§6.1)
probe values (or the generic probe-generator seed)
allowed risk class
oracle (capability family, necessary parameters, success condition, capture step)
entity request set, if entity-targeting (§7.6)
timeout/action budget
```

Human-prepared seed variants for strata S3/S4 and entity request sets are made before reveal, as part of the task suite.

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

### 13.1 Sealed adjudication

The benchmark oracle is the **hidden adjudication oracle** (`RESEARCH.md` §13.2). It is separate from GhostAPI's internal behavioral verification.

- The **oracle bundle** holds the capability families, necessary parameters, success conditions, capture steps, entity request sets, and task suite. It lives outside the repository until the benchmark report, and its SHA-256 goes into the freeze manifest.
- During each trial, **after** GhostAPI's internal verification finishes, the harness runs the oracle's capture step inside the same clone. It writes the result to a sealed adjudication store. Discovery, semantics, experiment, verifier, GIR, and rebinding code cannot read that store; an import/path invariant enforces this.
- The published capability set is snapshotted and hashed (`publication_snapshot`) before any adjudication runs.
- Adjudication, the rubric (§11), and the capability-to-family pairing for scoring happen after the snapshot. Results go into `benchmark_adjudication` records and never flow back.

The capture step must not change app state that GhostAPI's own verification reads, so it runs last. Capture steps may read app data files, because that is adjudication, not capability discovery (`RESEARCH.md` §2.2 forbids reading private app databases *to discover capabilities*). Their output never reaches discovery.

---

## 14. Drift benchmark

The drift condition must be selected before observing drift behavior.

Acceptable drift sources:

- app version update;
- user-configurable toolbar change;
- menu relocation;
- label change;
- UI hierarchy change that preserves semantics.

For held-out (closed-source) apps, only a **legitimate, predeclared, reproducible mechanism in the app itself** may be used: configurable toolbar or layout, UI preference, presentation customization, or a genuine version change with equivalent semantics. Editing binaries, reverse engineering, and modifying internals are forbidden. If a held-out app has no such mechanism, the report says "no safe drift mechanism" for that app.

Development drift uses the synthetic fixture's drift toggles (classes D1–D7, `RESEARCH.md` §16.1).

**H5 validation route.** Before the Week 5 freeze, the owner chooses and freezes one of: (1) fixture drift only, (2) a dedicated real-app drift test, or (3) both. Proposal: (3) both, where fixture drift establishes the mechanics across classes and at least one real-app drift runs wherever a held-out app offers a legitimate mechanism. If no held-out app offers one, H5 on real apps is reported as **not tested**. It is not replaced after the fact by fixture evidence.

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
maximum estimated LLM spend (per run, per app; ADR-013)
maximum number of human approvals
maximum retries
rebinding budget (§7.9)
baseline per-run and per-app budgets for each arm (§9.1)
router budget (§9.5)
```

A run that exceeds budget stops cleanly, and the stop is recorded. Capabilities not VERIFIED at that point count as not discovered.

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
parameters (precision, recall, missing, invented, types, required/optional)
N
successes
observed reliability
95% Wilson interval
per-stratum successes
futility stops / INFRA_EXHAUSTED slots
internal-verification vs adjudication outcome (false-positive postcondition rate)
entity-resolution stats (correct, false-target, unsafe, refusal, not-found, coverage)
evidence references
```

### Baselines

For each arm (B1, B2, B3 if run, B4) and for GhostAPI Evaluations B and C:

```text
task success (Wilson interval)
latency
actions
tokens
vision calls
cost and success-adjusted cost
acquisition cost (B3/B4)
human intervention
routing accuracy and NO_MATCH rate (Evaluation C)
```

### Amortization

```text
D, M(H), C_G, C_a per arm
break-even band per arm (<=10 / <=100 / <=1,000 / never)
sensitivity table
```

### Drift

```text
capability
drift class and source (fixture / real-app mechanism)
old binding
declared drift
new binding
automatic/manual
semantic subsystem invoked (yes/no), candidates proposed/rejected/verified
rebinding cost and ratio R to D_search
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
- eligible population, screening, and exclusion counts (§3.1);
- arms not run (for example B3) and what that leaves untested;
- any protocol deviations.

---

## 17. Benchmark-level success criteria

The Week 6 result satisfies the **research success gate** only if all of the following are true across the three final held-out apps:

1. **Useful discovery:** each app has at least **5 VERIFIED useful capabilities**.
2. **Capability precision:** aggregate VERIFIED capability precision is **>= 90%**.
3. **Per-capability reliability:** every capability counted toward the 5-per-app target satisfies **N >= 20** (stratified per §6.1, including the concentration rule) and observed reliability **>= 90%**.
4. **Parameter accuracy:** aggregate supported declared-parameter accuracy is **>= 90%**, and aggregate necessary-parameter recall is **>= 80%** (§7.4; recall target proposed).
5. **Task coverage:** each app reaches **>= 60%** of the hidden benchmark task/capability-family coverage set.
6. **Entity safety and usefulness:** **0 silent false-target executions** and **0 unsafe resolutions** in final benchmark entity-targeting requests, and correct-resolution rate **>= 0.80** on resolvable requests (§7.6; usefulness target proposed). If no app has an entity-targeting capability, H4 is "not tested", not passed.
7. **Drift:** at least one predeclared capability self-rebinds after UI drift within the rebinding budget, keeps the same contract (inputs and postcondition), and again satisfies VERIFIED reliability. Rebinding cost ratio `R` is reported.
8. **Baseline evidence (H6):** GhostAPI demonstrates a **reliability** or **cost** advantage as defined in §7.10 over every required arm (B1, B2, B4). Latency, actions, or tokens alone do not satisfy this condition. An advantage over only some arms is reported as partial support (Case B signal), not as a pass.
9. **Integrity:** no held-out app-specific patches, prompt hints, target-app research, post-hoc threshold changes, hidden human selector help, or human routing of tasks occurred, and no adjudication data reached discovery.

If conditions 1–7 pass but baseline advantage does not, the system may still be technically interesting, but H6 is not supported and the product thesis must be reconsidered.

---

## 18. Decision gate

### Case A — stop or rethink

Choose Case A when:

- useful capabilities are not discovered reliably;
- precision is poor;
- execution is unstable;
- entity targeting is unsafe, or safe only by refusing nearly everything;
- drift repair fails, or costs about as much as rediscovery;
- GhostAPI does no better than resilient trace replay (B4);
- the baseline is equally good or better with no amortized benefit.

### Case B — narrow the scope

Choose Case B when:

- results are strong only for a specific app class;
- AX quality strongly predicts success;
- CRUD/document-style apps work but complex custom-canvas apps do not;
- one hypothesis fails while the others hold;
- GhostAPI beats the screenshot-only arm but not the AX-enabled, cached, or replay arms.

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

Version history:

| Version | Change | ADR |
|---|---|---|
| v0.1 | Initial draft | none |
| v0.2 | Week 0 protocol repair. Headline thresholds unchanged (N >= 20, >= 0.90, precision >= 90%, supported-parameter >= 90%, coverage >= 60%, 0 false targets). Added: state strata, concentration rule, futility stop; parameter recall; entity usefulness; rebinding budget and cost ratio; H6 definition; INVALID_INFRA codes and trial/attempt rules; baseline arms B1–B4; evaluations A/B/C and frozen router; full amortization model and horizon; sealed adjudication; population/exclusions; H5 route. New numeric values marked "proposed" require owner approval. | ADR-009, ADR-010, ADR-014 |

---

## 20. Recommended benchmark artifacts

Suggested layout:

```text
benchmarks/
├── protocol/
│   └── v0.2.yaml
├── tasks/
│   └── <hidden or encrypted outside-repo definitions; oracle bundle hash only>
├── baseline/          evaluation harness (arms B1–B4, router); never imported by discovery code
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
    ├── publication_snapshot.json   (hashed before adjudication)
    ├── adjudication.jsonl          (written only after the snapshot)
    └── report.md
```

Raw screenshots/AX trees remain under `artifacts/` and are referenced by immutable IDs/hashes rather than duplicated into every report. Sealed adjudication captures are stored outside every path that discovery code can read (§13.1).

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
