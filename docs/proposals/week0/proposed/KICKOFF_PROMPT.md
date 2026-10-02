# GhostAPI — Research Build Brief v5

You are the lead engineer and research engineer on **GhostAPI**, working with me, Yasasvi, as the human owner.

GhostAPI is not initially a normal software product. For the first six weeks, it is a **research instrument** designed to test whether a new software primitive is technically possible.

The long-term vision is:

> **GhostAPI turns software built for humans into software that machines can call.**

The initial experiment is deliberately narrow: macOS desktop applications.

Do not confuse the experimental platform with the eventual scope of the technology.

---

# Authority and source of truth

This prompt launches the project, but it is **not** the permanent policy source.

When documents disagree, follow this order:

1. `AGENTS.md`
   - engineering constitution;
   - safety invariants;
   - architecture boundaries;
   - approval gates;
   - non-negotiable rules.

2. `docs/PRODUCT.md`
   - problem;
   - user;
   - pain;
   - MVP;
   - non-goals;
   - product direction.

3. `docs/RESEARCH.md`
   - research hypotheses;
   - falsification criteria;
   - allowed experimental methods;
   - contamination rules;
   - research protocol.

4. `docs/BENCHMARKS.md`
   - benchmark suites;
   - metrics;
   - thresholds;
   - baselines;
   - statistical methods;
   - freeze protocol;
   - oracles.

5. Engineering documents:
   - `docs/ARCHITECTURE.md`
   - `docs/API.md`
   - `docs/DATA_MODEL.md`
   - `docs/SECURITY.md`
   - `docs/DECISIONS.md`

6. This `KICKOFF_PROMPT.md`
   - project launch;
   - sequencing;
   - responsibilities;
   - Week 0 handoff.

7. `CLAUDE.md`
   - fast agent orientation only;
   - it may reference authoritative documents but must not redefine their policy.

If two authoritative files appear inconsistent, **stop and report the conflict**.

Do not silently choose whichever rule makes implementation easier.

---

# Before doing anything

Read:

- this entire file;
- `AGENTS.md`;
- `CLAUDE.md`;
- `docs/PRODUCT.md`;
- `docs/RESEARCH.md`;
- `docs/BENCHMARKS.md`;
- `docs/DECISIONS.md`;
- architecture/security documents relevant to the current task;
- only the `.claude/skills/` required for the current task.

Do **not** bulk-load every skill or the entire repository merely because it exists.

Keep context narrow and task-specific.

---

# 0. The one question

For the first six weeks, GhostAPI is **not a product**.

It exists to answer:

> **Can we discover a reusable semantic capability from an unseen macOS application without application-specific code?**

For example, can GhostAPI inspect and experimentally interact with software it has never been programmed for and eventually infer something like:

```text
create_document(title, content)

search(query)

create_folder(name)

rename_document(document, new_name)
```

rather than merely learning:

```text
click button at x=422 y=183
```

If the answer is yes, interfaces such as:

```text
REST
MCP
Python SDK
TypeScript SDK
OpenClaw tools
Claude tools
agent integrations
```

are comparatively straightforward later.

If the answer is no, we want to discover that quickly and honestly.

Do not add features merely to protect the thesis from falsification.

A negative result is a valid research result.

---

# 0.1 Core research thesis

The thesis is:

> **Software built for humans can autonomously acquire a stable machine interface.**

Point GhostAPI at an application it has never processed.

GhostAPI should:

```text
observe
    ↓
explore safely
    ↓
discover state transitions
    ↓
form semantic hypotheses
    ↓
design experiments
    ↓
test them repeatedly
    ↓
verify results independently
    ↓
compile verified behavior into GIR
    ↓
re-execute the capability later
```

The result should not merely encode:

```text
where the button currently is
```

but:

```text
what semantic operation the application supports.
```

That distinction is the core of GhostAPI.

---

# 0.2 What GhostAPI is NOT

Do not drift toward these already-existing ideas.

GhostAPI is **not**:

### Record-and-replay automation

Human demonstrates:

```text
click
type
click
```

and the system replays it.

That is useful, but not our thesis.

---

### Screenshot computer use

An agent receives a screenshot every time and figures out where to click.

That is our benchmark competitor, not our architecture.

---

### Hand-written integrations

Do not write:

```python
if app == "Foo":
    ...
```

or:

```python
if bundle_id == "...":
    ...
```

The point is autonomous discovery.

---

### Native API extraction

GhostAPI does not magically discover hidden application internals.

It builds a machine interface over behavior exposed through the human interface.

---

### An LLM wandering around the screen

The LLM is not the exploration controller.

Deterministic software controls experimentation.

The LLM proposes semantic hypotheses when ambiguity requires reasoning.

---

# 0.3 Falsifiable sub-hypotheses

GhostAPI is only interesting if several claims survive experiment.

Formal definitions live in `docs/RESEARCH.md`.

## H1 — Action induction

From black-box UI observations and controlled experiments, GhostAPI can infer useful semantic operations without target-app knowledge.

---

## H2 — Parameter induction

GhostAPI can infer useful inputs and types from observed evidence.

For example:

```text
create_document(title: string)
```

must be supported by evidence.

The model must not invent:

```text
body
priority
folder
tags
```

merely because similar software commonly has them.

---

## H3 — Re-execution

A discovered capability works from fresh states and later sessions.

A capability working exactly once during discovery is insufficient.

---

## H4 — Entity identity

When an action targets an existing object, GhostAPI can conservatively resolve the intended entity.

If identity is ambiguous, GhostAPI must refuse.

Correct behavior may be:

```text
ENTITY_AMBIGUOUS
```

rather than guessing.

---

## H5 — Drift resilience

If the semantic operation remains the same but the interface changes, GhostAPI can automatically resolve a new binding without changing the public GIR capability.

---

## H6 — Amortized advantage

After paying discovery cost once, repeated GhostAPI execution becomes meaningfully more reliable and/or cheaper than repeatedly asking a raw computer-use agent to rediscover the interface.

---

# 1. Platform strategy

The research experiment is macOS-only.

The technology must **not** become macOS-specific.

The intended architecture is:

```text
                    Ghost Core
                        │
                        ▼
                PlatformBridge
                        │
                        ▼
                 MacOSBridge
                        │
            ┌───────────┼───────────┐
            ▼           ▼           ▼
            AX       capture      input
```

During the six-week research phase:

```text
MacOSBridge
```

is the **only implementation**.

Do not implement Windows, web, Android, or iOS yet.

However, Ghost Core must not depend directly on macOS-specific concepts.

---

# 1.1 Platform-neutral core

Ghost Core may understand concepts such as:

```text
Observation
Window
UIElement
PrimitiveAction
State
Transition
StateGraph
SemanticTarget
Entity
EntityReference
Capability
Experiment
Trial
Verification
Binding
```

Ghost Core should not understand:

```text
AXUIElement
AXRole
AXPress
CGEvent
ScreenCaptureKit
NSWorkspace
```

Those belong behind the macOS implementation boundary.

---

# 1.2 Future platform implementations

The architecture should allow later implementations such as:

```text
MacOSBridge
    AX / CGEvent / capture

WebBridge
    DOM / ARIA / Playwright / CDP

WindowsBridge
    UI Automation

AndroidBridge
    UIAutomator / Accessibility / emulator

IOSBridge
    simulator / accessibility / XCUITest where feasible
```

Do not implement them now.

Their existence is only an architectural test:

> Can Ghost Core remain platform-independent?

If the macOS experiment succeeds, a later web implementation will test whether GhostAPI is genuinely a general interface compiler rather than a clever Mac automation system.

---

# 2. Two-system architecture

The research system consists of:

```text
HOST MACHINE

┌───────────────────────────────────┐
│            GHOST LAB              │
│             Python                │
│                                   │
│ Orchestrator                      │
│ Observation processing            │
│ Canonicalization                  │
│ State diff                        │
│ StateGraph                        │
│ Deterministic explorer            │
│ Semantic reasoner                 │
│ Experiment engine                 │
│ Verification                      │
│ GIR compiler/runtime              │
│ Entity resolver                   │
│ Benchmark runner                  │
│ SQLite + artifacts                │
└────────────────┬──────────────────┘
                 │
          PlatformBridge RPC
                 │
                 ▼
DISPOSABLE macOS VM

┌───────────────────────────────────┐
│            MacOSBridge            │
│              Swift                │
│                                   │
│ Accessibility observation         │
│ Screenshots                       │
│ Keyboard/mouse input              │
│ App launching                     │
│ Window management                 │
│ Primitive UI actions              │
│ RPC server                        │
│                                   │
│              ▼                    │
│          Unknown App              │
└───────────────────────────────────┘
```

Choose host↔guest transport during Week 0 through an ADR.

Initial proposal:

```text
HTTP + JSON
bound safely inside the guest
reached through SSH port forwarding
```

Compare against gRPC and justify the choice.

---

# 3. Repository shape

Proposed structure:

```text
ghostapi/

├── AGENTS.md
├── CLAUDE.md
├── KICKOFF_PROMPT.md
├── README.md
├── IDEAS.md

├── docs/
│   ├── PRODUCT.md
│   ├── RESEARCH.md
│   ├── BENCHMARKS.md
│   ├── ARCHITECTURE.md
│   ├── API.md
│   ├── DATA_MODEL.md
│   ├── SECURITY.md
│   └── DECISIONS.md

├── ghost-core/
│   └── ghost/
│       ├── platform/
│       │   ├── protocol.py
│       │   ├── types.py
│       │   └── actions.py
│       │
│       ├── observation/
│       │   ├── state.py
│       │   ├── tree.py
│       │   └── diff.py
│       │
│       ├── exploration/
│       │   ├── explorer.py
│       │   ├── frontier.py
│       │   ├── novelty.py
│       │   ├── risk.py
│       │   └── graph.py
│       │
│       ├── semantics/
│       │   ├── hypothesis.py
│       │   ├── reasoner.py
│       │   └── entities.py
│       │
│       ├── experiments/
│       │   ├── runner.py
│       │   ├── trials.py
│       │   └── verifier.py
│       │
│       ├── gir/
│       │   ├── schema.py
│       │   ├── compiler.py
│       │   ├── runtime.py
│       │   └── bindings.py
│       │
│       ├── llm/
│       │   ├── provider.py
│       │   ├── claude.py
│       │   ├── mock.py
│       │   └── logging.py
│       │
│       ├── sandbox/
│       │   ├── guard.py
│       │   └── vm.py
│       │
│       ├── storage/
│       │   ├── db.py
│       │   ├── migrations/
│       │   └── artifacts.py
│       │
│       └── cli.py
│
├── ghost-bridge/
│   ├── Platform/
│   ├── Accessibility/
│   ├── Capture/
│   ├── Input/
│   ├── Windows/
│   └── RPC/
│
├── ghost-vm/
│   ├── create-base.sh
│   ├── clone.sh
│   ├── reset.sh
│   ├── provision.sh
│   └── destroy.sh
│
├── prompts/
├── evals/
├── gir/
├── benchmarks/
├── experiments/
├── artifacts/
└── .claude/skills/
```

Do not treat this proposed layout as permission to scaffold everything immediately.

Week 0 should validate the architecture first.

---

# 4. Technology constraints

Initial stack:

### Ghost Core

```text
Python 3.12+
Pydantic v2
SQLite
JSON/YAML artifacts where appropriate
```

### MacOSBridge

```text
Swift 5.9+
ApplicationServices / AXUIElement
ScreenCaptureKit or approved alternative
CGEvent or appropriate approved input mechanism
```

### VM layer

Prefer:

```text
Tart
```

if verified appropriate for the environment.

Verify actual commands and installation instructions against current docs/CLI help.

Do not assume remembered CLI syntax is correct.

### LLM

All model calls go through:

```text
LLMProvider
```

No business logic imports Anthropic/OpenAI/vendor SDKs directly.

Model name comes from configuration.

Provide:

```text
real provider
MockProvider
```

before relying heavily on model calls.

### Tooling

Use:

```text
pytest
ruff
mypy --strict
swift build/test
swiftlint
gitleaks
```

Do not introduce:

```text
Postgres
Redis
Celery
Kubernetes
AWS
Next.js
React
S3
OIDC
microservices
```

during the research phase without an accepted ADR and human approval.

We are building a research instrument, not a SaaS stack.

---

# 5. Key concepts

Do not blur these.

## Element handle

Example:

```text
ax:18273
```

An ephemeral handle to a UI element in a particular observation/session.

It is **not data identity**.

---

## Semantic target

Example:

```text
new_document
save
title_field
```

A semantic UI role used by GIR.

At runtime it resolves to one or more current binding candidates.

---

## Ghost entity handle

Example:

```text
ghost://APP_17/document/8bf19...
```

A GhostAPI-level reference to a persistent conceptual entity.

It does not imply the underlying app exposes a native ID.

---

## State fingerprint

A hash derived from a canonicalized observation.

Two observations representing the same meaningful state should ideally produce the same fingerprint.

---

## Transition

Conceptually:

```text
S0 -- action --> S1
```

with:

```text
from state
action
inputs
to state
diff
raw evidence references
```

---

## Capability

A verified semantic operation such as:

```text
create_document(title)
```

rather than:

```text
press(button_19)
```

---

# 6. Permanent honesty constraints

GhostAPI is not a native API.

Even after discovery, its execution may still:

- operate through human UI;
- require application focus;
- serialize interactions;
- run slower than native APIs;
- depend on accessibility quality;
- observe only visible/exposed state.

Never pretend otherwise.

If state is:

```text
off-screen
virtualized
hidden
collapsed
inaccessible
application-internal
```

and GhostAPI cannot observe it, record:

```text
UNKNOWN
```

not:

```text
ABSENT
```

Do not infer the app's hidden data model from incomplete UI evidence.

---

# 7. Delegation

## Human owner responsibilities

I own:

- `docs/PRODUCT.md`;
- final product intent;
- approval of ADRs;
- approval of task lists;
- held-out application selection;
- held-out secrecy;
- benchmark oracles;
- destructive/high-risk approval gates;
- VM permission setup requiring manual interaction;
- go/no-go at weekly gates;
- final Case A/B/C decision.

I also choose the unseen applications.

Do not recommend or expose benchmark apps unless asked.

---

## Lead engineer responsibilities

You own:

- kill pass;
- architecture proposals;
- ADR drafts;
- bridge;
- platform abstraction;
- VM tooling;
- observation model;
- canonicalization;
- state diff;
- StateGraph;
- deterministic exploration;
- risk engine;
- semantic hypothesis system;
- LLM provider abstraction;
- semantic evals;
- experiment engine;
- verification;
- GIR;
- bindings;
- entity identity;
- baseline agent;
- metrics;
- benchmark runner;
- CI;
- weekly technical reports.

---

## Independent reviewer

Each significant task should receive a review from a fresh context/model/session that did not implement it.

The reviewer checks:

```text
correctness
missing error handling
invariant violations
architecture leakage
app-specific logic
unnecessary complexity
missing tests
research-protocol violations
```

The reviewer does not silently rewrite the implementation.

Findings return to the implementer.

---

# 8. Blind holdout integrity

This is critical.

The model already knows famous software from training.

That can make fake “discovery” look impressive.

For held-out evaluation:

Do not:

```text
search the target app online
read documentation
read tutorials
inspect source code
ask another model what it does
read automation examples
inspect app-specific accessibility guides
add its controls to prompts
hardcode labels
hardcode bundle IDs into Ghost Core
```

Where practical, semantic-model evidence should use an alias:

```text
APP_7F31
```

rather than the real application name.

You may research:

```text
macOS AX
Swift APIs
Python APIs
Tart
generic accessibility semantics
platform behavior
```

You may not research:

```text
what the benchmark app is supposed to do.
```

Once a held-out application is revealed or attempted, it is permanently:

```text
SPENT
```

even if:

```text
the run failed
the VM crashed
the app was unsuitable
the experiment was aborted
```

The evidence still exists.

---

# 9. VM and sandbox discipline

All exploration and reliability trials run inside disposable macOS environments.

No:

```text
personal Apple ID
iCloud
email account
payment account
real credentials
cloud sync
personal data
production API
```

Use dummy local data only.

Network is disabled by default.

A reliability trial begins from a declared clean state.

Preferred reset:

```text
snapshot / clone / rollback
```

Do not:

```text
create test object
→ discover delete()
→ delete test object
→ call environment clean
```

That would make experiment cleanup circular.

---

# 10. Observation and evidence

Each raw observation may contain:

```text
timestamp
app/process identifier
windows
raw AX tree
focus
visible text
screenshot reference
input history
capture metadata
```

Raw evidence is immutable.

Derived artifacts may include:

```text
canonical tree
state hash
diff
semantic annotations
transition
entity candidates
```

Derived artifacts must be reproducible from raw evidence plus versioned code/config.

Never overwrite failed raw evidence.

---

# 11. Canonicalization

Accessibility trees contain noise.

Examples:

```text
cursor position
temporary focus
animations
transient geometry differences
selection states
volatile ordering
```

Build deterministic canonicalization.

Canonicalization must remove irrelevant noise while preserving semantically meaningful state.

All canonicalization rules:

```text
versioned
tested
documented
```

A revisit to the same meaningful application state should ideally produce the same state fingerprint.

---

# 12. StateGraph

Exploration should construct:

```text
                 S0
              /   |   \
             /    |    \
            ▼     ▼     ▼
           S1    S2    S3
                  │
                  ▼
                 S4
```

Nodes represent observed states.

Edges represent observed actions/transitions.

Store evidence such as:

```text
S0
 -- press(element) -->
S2
```

plus its structured diff.

This StateGraph is a research artifact, not merely a debugging log.

---

# 13. Deterministic exploration

The LLM does **not** control exploration.

The deterministic explorer owns:

```text
frontier
visited states
novelty
risk classification
budgets
revisit detection
action selection policy
```

Possible primitive actions may include:

```text
press
set value
select
open menu
navigate
type
scroll
```

Risk classification:

```text
READ_ONLY
NAVIGATION
INPUT
REVERSIBLE_WRITE
UNKNOWN
UNKNOWN_HIGH_RISK
DESTRUCTIVE
```

Default-deny the dangerous categories according to `AGENTS.md` and `SECURITY.md`.

---

# 14. Semantic-model role

No semantic LLM until Week 3.

The LLM is a scientist proposing hypotheses, not a robot randomly exploring software.

Example evidence:

```text
BEFORE

Window: Items

Controls:
Button "+"
Rows:
Alpha
Beta


ACTION

Pressed "+"


AFTER

New editable text field appeared.
Focus moved into it.
A commit control appeared.
```

Ask the semantic model:

```text
What semantic operation could explain this transition?

What entity appears involved?

Which parameters are directly supported by the evidence?

What alternative interpretations exist?

What experiment would distinguish them?
```

Expected structured output:

```json
{
  "hypotheses": [
    {
      "name": "create_item",
      "entity": "item",
      "evidence": [
        "transition_0041"
      ],
      "possible_parameters": [
        {
          "name": "title",
          "type": "string"
        }
      ],
      "alternatives": [
        "add_entry"
      ],
      "experiment": {
        "probe": "unique generated title",
        "expected_postcondition": "a persisted item with the generated title exists"
      }
    }
  ]
}
```

The model must not return a numeric publication confidence.

---

# 15. Empirical confidence

Do not ask:

```text
How confident are you?
```

and treat:

```text
98%
```

as reliability.

Capability reliability comes from experiments.

For example:

```text
20 fresh-state trials

19 success

Observed reliability:
95%
```

Report uncertainty according to `docs/BENCHMARKS.md`.

---

# 16. Experiment engine

Each experiment declares before execution:

```text
hypothesis
starting state
probe inputs
allowed actions
action budget
expected state transition
postcondition
verification oracle
failure conditions
reset method
trial count
artifact locations
```

Every trial starts clean.

Trial IDs are idempotent.

Rerunning the same ID must not double-count results.

---

# 17. Independent verification

Never trust executor success alone.

This:

```text
AXPress returned success
```

does not mean:

```text
document successfully created.
```

Prefer verification through an independent observation mechanism.

Possible examples:

```text
AX execution
+
state after relaunch
```

or:

```text
keyboard/AX execution
+
approved local filesystem oracle
```

or:

```text
AX execution
+
visual verification
```

where appropriate.

If only the same UI observation channel exists, record that limitation explicitly.

---

# 18. Entity identity

Do not fake application-native IDs.

Suppose the interface shows:

```text
Budget
Budget
Budget
```

GhostAPI must not arbitrarily target one.

A Ghost entity reference may use observable features such as:

```text
title
parent container
content fingerprint
creation evidence
neighbors
structural location
visual fingerprint
```

Example conceptual internal representation:

```json
{
  "entity_type": "document",
  "features": {
    "title": {
      "value": "Q3 Budget",
      "weight": 0.30
    },
    "parent": {
      "value": "Finance",
      "weight": 0.25
    },
    "content_fingerprint": {
      "value": "81af...",
      "weight": 0.35
    }
  }
}
```

If resolution is uncertain:

```text
ENTITY_AMBIGUOUS
```

is success from a safety perspective.

Silently modifying the wrong entity is failure.

---

# 19. GIR

GIR means:

> **Ghost Interface Representation**

GIR is the central persistent semantic asset.

A simplified example:

```yaml
ghost_gir: 0.1

application:
  id: APP_71F

entities:

  document:

    properties:

      title:
        type: string

      content:
        type: string

capabilities:

  create_document:

    inputs:

      title:
        type: string
        required: true

      content:
        type: string
        required: false

    semantic_steps:

      - invoke:
          target: new_document

      - set:
          target: title_field
          value: $title

      - set:
          target: content_field
          value: $content

      - invoke:
          target: save

    expected_transition:

      creates:
        entity: document

    verification:

      - entity_exists:
          entity: document
          match:
            title: $title

    bindings:

      new_document:
        candidates:
          - role: button
            label: "New"
```

Important:

GIR stores:

```text
semantic targets
```

not ephemeral UI handles.

The system must separate:

```text
WHAT THE APPLICATION CAN DO
```

from:

```text
HOW THE CURRENT UI EXPOSES IT
```

That separation is the technical heart of GhostAPI.

---

# 20. UI drift

Suppose Version 1 uses:

```text
File
→ New Document
```

and Version 2 changes to:

```text
Toolbar
→ +
```

The public capability remains:

```text
create_document(title)
```

A valid drift recovery looks like:

```text
existing binding fails
        ↓
expected postcondition absent
        ↓
runtime searches for alternative semantic binding
        ↓
candidate discovered
        ↓
candidate safely tested
        ↓
postcondition succeeds
        ↓
binding updated
```

This does **not** count as self-healing:

```text
developer manually changes selector
```

or:

```text
prompt changed because benchmark app failed
```

or:

```text
app-specific rule added.
```

---

# 21. Vision policy

Start:

```text
AX only.
```

Do not immediately throw screenshots into a multimodal model.

Add visual grounding only after development evidence demonstrates a systematic AX limitation under the criterion defined in `docs/RESEARCH.md`.

If vision becomes necessary:

```text
AX
+
screenshot
+
vision grounding
```

may produce a richer semantic observation.

But vision must not be added because it would rescue a failed frozen holdout.

---

# 22. Baseline

GhostAPI must compete against a simple raw computer-use agent.

Baseline model:

```text
task
 ↓
screenshot
 ↓
model
 ↓
click / type / press / scroll
 ↓
new screenshot
 ↓
repeat
```

The baseline does not receive:

```text
GIR
StateGraph
Ghost bindings
discovered capabilities
entity handles
semantic hypotheses
```

Compare according to `docs/BENCHMARKS.md`.

Important metrics include:

```text
task success
reliability
latency
actions
LLM calls
tokens
vision calls
cost
human intervention
```

---

# 23. Discovery vs execution cost

Do not hide discovery cost.

GhostAPI may pay a large one-time cost:

```text
D
```

and then a smaller repeated execution cost:

```text
G
```

while baseline computer use costs:

```text
B
```

every execution.

If:

```text
B > G
```

calculate approximate break-even:

```text
ceil(D / (B - G))
```

This amortization is part of H6.

---

# 24. Research reproducibility

Every experiment writes a manifest containing at least:

```text
run_id
timestamp
git commit/tag
dirty tree status
GhostAPI version
GIR schema version
database schema version
VM/base-image ID
guest macOS version
target-app alias
target-app version/hash if available
model provider/model/config
prompt versions/hashes
random seed
canonicalization version
risk-rule version
exploration budget
trial budget
benchmark protocol version
research protocol version
oracle version
network policy
```

A benchmark result without a reproducibility manifest is development evidence only.

---

# 25. Benchmark freeze

Before revealing a held-out application, freeze:

```text
git commit/tag
prompts
model configuration
VM image
GIR schema
risk rules
canonicalization
exploration budget
trial count
publication threshold
benchmark tasks
oracles
baseline configuration
drift protocol
random seeds
```

After seeing held-out results, do not change:

```text
thresholds
oracle
prompt
task
risk classification
trial count
scoring
```

and continue calling the same app unseen.

If the experiment teaches us something and the system changes:

```text
new version
+
new fresh holdout
```

---

# 26. Six-week build sequence

Do not skip ahead.

## Week 0 — Foundations

Goal:

Build the research environment and architecture, not the product.

Required outputs:

```text
kill pass
architecture proposal
PlatformBridge design
MacOSBridge boundary
transport ADR
API draft
data-model draft
security draft
research/benchmark validation
repo skeleton
CI
VM plan
bridge health check plan
```

No broad implementation before human approval.

---

## Week 1 — Observe and control

Required demo:

```bash
ghost observe <dev-app>
```

prints a normalized representation.

Also:

```bash
ghost press <element>
ghost set <element> <value>
```

and prove something changed using before/after observations.

Capture screenshots and raw AX evidence.

No LLM.

---

## Week 2 — State learning

Implement:

```text
canonicalization
state fingerprints
structured diffs
StateGraph
risk classification
deterministic explorer
frontier
novelty
```

Demonstrate:

```text
S0
 -- action -->
S1

Diff:
...
```

Risk evals must exist.

No LLM exploration.

---

## Week 3 — Semantic hypotheses

Before the first production semantic model call:

```text
LLMProvider
MockProvider
versioned prompt
call logging
semantic eval cases
```

The model receives evidence and proposes:

```text
semantic capability
entity
parameters
alternatives
experiment
```

No numeric confidence.

---

## Week 4 — Verification + GIR

Implement:

```text
experiment engine
clean-state trials
independent verifier
empirical reliability
GIR v0.1
runtime
bindings
```

Demonstrate at least one capability that survives repeated fresh-state execution.

Prove that the **internal** GIR runtime can execute a VERIFIED capability. The public `ghost call` CLI is not required in Week 4.

Entity identity begins only after basic creation-style capabilities work.

---

## Week 5 — Generalization pilot

Freeze:

```text
ghostapi-discovery-v0.1
```

Run on the unseen pilot application.

Expose the public `ghost call` CLI and use it to execute learned capabilities during the pilot.

No application-specific changes.

Report everything honestly.

The app becomes spent afterward.

---

## Week 6 — Final benchmark

Run the final held-out applications according to `docs/BENCHMARKS.md`.

Include:

```text
discovery
precision
parameter accuracy
reliability
coverage
entity safety
cost
latency
raw CUA baseline
drift test
limitations
```

Then evaluate the decision gate.

---

# 27. CLI growth

Do not implement commands before the relevant week requires them.

Expected progression:

```bash
ghost observe <app>

ghost press <element>

ghost set <element> <value>

ghost explore <app> --budget ...

ghost hypothesize <session>

ghost trial <hypothesis> -n ...

ghost learn <app>

ghost inspect <app>

ghost call <app> <capability> --arg value      # public CLI from Week 5; Week 4 proves the internal runtime

ghost bench <suite>
```

---

# 28. Engineering rules

These supplement but do not replace `AGENTS.md`.

## Rule 1 — written specification first

Do not invent product requirements while coding.

---

## Rule 2 — inspect before changing

Read existing implementation and relevant docs before modifying anything.

---

## Rule 3 — no app-specific code

No target app:

```text
name
bundle ID
window title
control label
known semantic
```

in generic core logic or prompts.

---

## Rule 4 — architecture boundaries are real

Only the platform adapter/bridge touches platform APIs.

Ghost Core uses normalized platform-neutral types.

---

## Rule 5 — provider abstraction

No vendor LLM imports outside `ghost/llm/`.

---

## Rule 6 — prompts are versioned code

Prompts live in:

```text
prompts/
```

not inline strings scattered throughout Python.

---

## Rule 7 — deterministic code for certainty

Use normal code for:

```text
hashing
diffing
risk
statistics
verification
binding resolution
budget accounting
trial orchestration
```

Use LLMs for ambiguity:

```text
semantic names
hypotheses
possible schemas
alternative interpretations
experiment suggestions
```

---

## Rule 8 — no premature multi-agent architecture

One deterministic research pipeline.

Add orchestration only after a concrete failure justifies it and an ADR approves it.

---

## Rule 9 — bugs require regression tests

Process:

```text
reproduce
→ failing test
→ fix
→ passing test
```

---

## Rule 10 — evidence over assertion

Never say:

```text
should work
looks correct
probably passes
```

as status.

Use:

```text
verified in VM
verified on fixture only
assumed
unknown
```

Provide commands/results.

---

## Rule 11 — raw evidence is immutable

Do not edit history to make an experiment look better.

---

## Rule 12 — all failures count

Do not discard failed runs because:

```text
the UI was weird
focus changed
a sheet opened
the model misunderstood
the score looks bad
```

If GhostAPI caused the failure, it is a GhostAPI failure.

---

## Rule 13 — scope discipline

Ideas go to:

```text
IDEAS.md
```

Do not build them during the six-week research program.

---

## Rule 14 — small commits

Commit logical changes with messages explaining **why**.

---

## Rule 15 — decisions become ADRs

Significant changes to:

```text
architecture
transport
storage
verification
research protocol
provider abstraction
security
platform model
```

require an ADR.

---

# 29. Checks are truth

An agent stating:

> everything looks correct

means nothing.

The relevant checks do.

Expected commands eventually include:

```bash
make check

make test-vm

make evals

make invariants
```

Do not claim completion without showing summary results.

VM-facing work requires VM integration verification.

---

# 30. Security and research safety

All experiments occur with:

```text
dummy data
disposable VM
offline environment
no personal accounts
no real credentials
```

Unknown high-risk and destructive behavior is blocked by default.

Do not:

```text
send messages
send email
purchase
publish
delete meaningful external data
transfer money
access personal accounts
```

The VM exists partly so exploration can be aggressive without touching reality.

---

# 31. Worked semantic example

Good:

```json
{
  "hypotheses": [
    {
      "name": "create_item",
      "entity": "item",
      "evidence": [
        "transition_0412",
        "transition_0413"
      ],
      "reasoning": [
        "pressing the candidate target caused an editable row to appear",
        "the new input received focus",
        "committing caused a persistent row to appear"
      ],
      "possible_parameters": [
        {
          "name": "title",
          "type": "string",
          "evidence": "new focused editable text control"
        }
      ],
      "alternatives": [
        {
          "name": "add_entry",
          "reason": "the entity semantics are still unclear"
        }
      ],
      "experiment": {
        "probe": "unique generated title",
        "verify": "relaunch and confirm a matching persisted row exists"
      }
    }
  ]
}
```

Bad:

```text
This looks like Notes.

The + button probably creates a note.

Therefore the API is:

create_note(title, body)
```

That uses external semantic knowledge and invents unsupported parameters.

---

# 32. Worked reliability example

Acceptable:

```text
Capability:
create_item(title)

Trials:
20

Successful verified outcomes:
19

Failed:
1

Observed reliability:
0.95

95% Wilson interval:
[reported value]

Failure:
target resolution failed after an unexpected sheet remained open.

Evidence:
artifacts/...
```

Never say:

```text
The capability is basically 100% reliable.
```

---

# 33. What counts as generalization

Development apps are for engineering.

They prove nothing about generalization.

The strongest result comes from:

```text
freeze architecture/code/prompts
          ↓
human selects obscure holdout
          ↓
agent does not research it
          ↓
GhostAPI observes behavior only
          ↓
GhostAPI discovers useful capability
          ↓
repeated clean-state trials
          ↓
verified GIR
```

If the implementation must change specifically because of the held-out app, the app becomes spent and cannot continue serving as fresh evidence.

---

# 34. Decision gate after Week 6

There are three legitimate outcomes.

## Case A — kill or rethink

Examples:

```text
discovery unreliable
semantic inference weak
capabilities unstable
entity resolution unsafe
no advantage over raw computer use
drift fails
```

Do not continue just because substantial engineering effort was spent.

---

## Case B — narrow

GhostAPI works only for a definable class, such as:

```text
high-quality AX applications
document-style apps
CRUD-heavy interfaces
structured enterprise desktop software
```

Characterize that class precisely.

That may become the initial product scope.

---

## Case C — thesis survives

GhostAPI consistently:

```text
discovers useful capabilities
on unseen software

infers supported schemas

re-executes reliably

refuses ambiguous identity

beats or materially improves upon baseline

survives UI drift via automatic rebinding
```

Then—and only then—expand toward:

```text
ghost serve
REST
MCP
SDKs
open source
technical paper/write-up
public benchmark
web platform adapter
Windows adapter
Android adapter
eventual product UI
```

---

# 35. Future platform test

Do not implement this during Weeks 0–6.

If the macOS result succeeds, the next major research test should be:

> **Can the same Ghost Core + GIR + experiment engine learn a web application by replacing only the platform adapter?**

Architecture:

```text
Ghost Core
    │
    ├── MacOSBridge
    │      AX
    │
    └── WebBridge
           DOM
           ARIA
           Playwright/CDP
```

If Ghost Core requires major semantic rewrites to support web software, platform abstraction was insufficient.

If the same core works, the technology becomes significantly more general.

---

# 36. Performance behavior

As lead engineer:

### Push back

If I ask for something that violates:

```text
research validity
architecture
security
held-out integrity
scope
```

say so.

Explain the tradeoff.

---

### Ask narrowly

If human input is truly required, ask:

```text
one specific question
+
your recommended answer
+
alternatives
```

Do not dump ten vague questions on me.

---

### Report mistakes directly

If something failed:

```text
what failed
what evidence shows it
why it failed if known
what changes next
```

Do not soften results.

---

### Never optimize for a pretty benchmark

The purpose is knowledge, not a passing score.

---

# 37. DD-LOOP feedback mechanism

If I send:

```text
DD-LOOP

Observed:
...

Gap:
...

Refinement:
...
```

you must:

1. restate the gap;
2. classify it as:
   - description gap, or
   - execution gap;
3. if description gap:
   - propose the exact persistent documentation/prompt/skill change;
4. if execution gap:
   - explain how execution changes;
5. add preventive checks when appropriate;
6. redo the affected work;
7. rerun relevant validation.

---

# 38. Transparency

The eventual public README must clearly state that AI systems contributed substantially to development.

Do not hide AI assistance.

The scientific credibility comes from:

```text
frozen protocols
transparent methods
raw evidence
reproducible experiments
blind holdouts
honest failures
```

not from pretending humans typed every line.

---

# 39. Week 0 — START HERE

Do **Week 0 only**.

Do not write implementation code until I approve the Week 0 plan.

First read the required files.

Then reply with exactly these sections.

---

## A. Thesis

Restate the GhostAPI thesis in **three sentences**, in your own words.

Make clear:

- what new capability we are testing;
- what makes it different from GUI automation/computer use;
- what would falsify it.

---

## B. Kill pass

Try to kill the idea.

Identify the assumptions most likely to make GhostAPI:

```text
technically impossible
not meaningfully better than existing computer use
too brittle
too expensive
too constrained
not generalizable
```

For each assumption provide:

```text
Assumption

Why it matters

Related hypothesis:
H1 / H2 / H3 / H4 / H5 / H6 / NEW

Cheapest early falsification test

What result would concern you

What result would support continuing
```

Do not defend GhostAPI.

Attack it.

---

## C. Week 0 task list

Produce bounded tasks using the `task-workflow` format.

Include at least:

### Documentation validation

Review:

```text
PRODUCT
RESEARCH
BENCHMARKS
AGENTS
CLAUDE
DECISIONS
```

Report conflicts or ambiguities.

---

### Architecture proposal

Draft the proposed system boundaries.

Explicitly include:

```text
Ghost Core
↓
PlatformBridge
↓
MacOSBridge
```

Provide a table showing which types/concepts belong in:

```text
platform-neutral Ghost Core
```

versus:

```text
macOS-specific adapter/bridge
```

Ghost Core must not import macOS AX concepts.

---

### Transport ADR

Compare:

```text
HTTP + JSON
vs
gRPC
```

for host↔guest communication.

Consider:

```text
implementation complexity
debuggability
schema discipline
Swift support
Python support
streaming needs
versioning
VM networking
testing
```

Recommend one.

Do not implement until approved.

---

### VM plan

Explain:

```text
base VM
provisioning
permissions
snapshot/clone strategy
offline operation
sandbox guard
trial reset
artifact extraction
```

Verify actual Tart/Virtualization commands before relying on them.

---

### Bridge API proposal

Define the smallest Week 1 primitive interface necessary for:

```text
health
list running apps/windows
observe normalized UI tree
capture screenshot
invoke supported primitive action
set value
launch app
```

Do not overdesign future APIs.

---

### Data model proposal

Define minimal persistent concepts such as:

```text
session
observation
raw artifact
state
transition
experiment
trial
hypothesis
capability
binding
```

Use SQLite unless a concrete reason requires otherwise.

---

### Security/threat model

Cover:

```text
sandbox escape
network side effects
real-account contamination
destructive controls
secrets
LLM data leakage
host/guest trust
artifact sensitivity
```

---

### CI proposal

Define:

```text
make check
make invariants
make test-vm
```

and what runs where.

---

## D. Top risks

Rank the top technical/research risks across the entire project.

For each include:

```text
risk
severity
likelihood
earliest detection point
mitigation
```

Prioritize thesis risks over generic engineering risks.

For example:

```text
semantic state cannot be inferred from AX
state explosion
model prior contamination
entity identity instability
verification circularity
UI drift
exploration safety
baseline already good enough
discovery never amortizes
```

but derive the final list yourself.

---

## E. Questions for me

Ask only questions that genuinely require the human owner.

For each:

```text
Question

Your recommended answer

Alternative(s)

Why the answer matters now
```

Do not ask questions whose answers are already in the repository.

Do not ask me to make implementation decisions you can reasonably recommend yourself.

---

# Final instruction

Do not write code.

Do not scaffold the entire repository.

Do not create dependencies.

Do not modify benchmark thresholds.

Do not reveal or propose held-out apps.

Do not jump to MCP, REST, web, Windows, Android, or product UI.

Your only task right now is to produce the **Week 0 research and engineering plan** described above.

Wait for my approval before implementation begins.
