# GhostAPI Architecture

**Status:** Draft v0.1 (Week 0 proposal; not yet authoritative)
**Owns:** components, deployment boundaries, dependency rules, and the platform boundary.
**Does not own:** research protocol (`RESEARCH.md`), benchmark rules and thresholds (`BENCHMARKS.md`), RPC details (`API.md`), schemas (`DATA_MODEL.md`), or security policy (`SECURITY.md`).
**Related ADRs:** 001 (stack), 002 (Tart), 003 (deterministic exploration), 006 (LLMProvider), 007 (platform boundary), 008 (transport), 009 (vision), 010 (evaluation harness), 011 (rebinding), 012 (VM lifecycle).

---

## 1. System shape

```text
HOST (Apple-silicon Mac)                                    DISPOSABLE macOS VM (one at a time)
┌───────────────────────────── Ghost Lab (Python) ───────┐  ┌──────── MacOSBridge guest service (Swift) ───┐
│ Ghost Core (platform-neutral)                          │  │ LaunchAgent in the GUI user's session        │
│   observation/  exploration/  semantics/  experiments/ │  │   Accessibility/  raw AX capture, AX actions │
│   gir/  storage/  llm/  cli.py                         │  │   Capture/        screenshots                │
│        │ neutral DTOs only                             │  │   Input/          (Week 2+) key/type events  │
│        ▼                                               │  │   Windows/        apps, windows, launch      │
│ platform/  PlatformBridge protocol + neutral types     │  │   Normalize/      pure RawObs -> PlatformObs │
│            + HTTP/JSON client (neutral wire contract)  │  │   RPC/            HTTP/1.1 JSON on 127.0.0.1 │
│        │                                               │  │          ▲                                    │
│ sandbox/   VM adapter (only caller of ghost-vm/)       │  │          │ SSH local forward (127.0.0.1)     │
└────────┼───────────────────────────────────────────────┘  │          ▼                                    │
         │  HTTP/1.1 + strict JSON over SSH tunnel ───────────►  Unknown app                              │
         │                                                   └───────────────────────────────────────────────┘
┌────────┴──────── Benchmark harness (Python, separate) ─┐
│ baseline arms B1–B4, NL router, sealed adjudication    │   never imported by Ghost Core
└────────────────────────────────────────────────────────┘
Host-side tools: macos-normalize (same Swift normalizer, offline replay), ghost-vm/ scripts (Tart).
LLM provider calls originate only on the host, through ghost/llm (LLMProvider).
```

There is one deterministic pipeline and no multi-agent orchestration. The LLM is called only at defined points: `semantics/` for GhostAPI, and the benchmark harness for evaluation (ADR-010).

---

## 2. Dependency rules (one-way)

```text
cli.py ─► (observation, exploration, semantics, experiments, gir, storage, sandbox)
exploration ─► observation ─► platform (types/protocol)
semantics ─► llm, observation, storage
experiments ─► gir.bindings, observation, platform, storage, sandbox
gir.runtime ─► gir.bindings, platform, observation      (no llm, no semantics)
gir.rebinding_request ─► (message to semantics via experiments; see §6)
benchmark harness ─► platform, llm, storage (read-only on published artifacts), sandbox
```

`make invariants` checks these rules, and they fail closed:

| Rule | Mechanism |
|---|---|
| No vendor LLM SDK outside `ghost/llm/` | AST import scan |
| No `ghost.llm` / `ghost.semantics` import from `exploration`, `observation`, `experiments`, `gir.runtime` | AST import scan |
| Ghost Core is platform-neutral: no `AX*`, `CG*`, `NS*`, `SCK*`, `kAX*`, `bundle_id`, `pid` identifiers anywhere under `ghost-core/ghost/` (the wire contract is neutral, and raw AX artifacts are opaque bytes that Python never parses) | token scan; allowlist only for reviewed false positives (for example the English word "AXIS") |
| Discovery never imports the harness; harness never writes discovery state | AST import scan both ways, and a path check on the sealed adjudication store |
| `tart` invoked only from `ghost-vm/` and `ghost/sandbox/vm.py` | grep on subprocess calls |
| Explore/trial entry points need a `SandboxAttestation` value | type signature and mypy; only `sandbox.guard` can construct one |
| No hardcoded model IDs | regex scan outside config |
| No app names or labels from the denylist | grep of `benchmarks/denylist.txt` + `$GHOST_HOLDOUT_DENYLIST` (holdout list checked locally only) |

---

## 3. Platform boundary: `Ghost Core -> PlatformBridge -> MacOSBridge`

`PlatformBridge` is a neutral interface (a Python `Protocol`) plus a neutral wire contract (JSON Schemas in `API.md`). It is not a third service. `MacOSBridge` is its only implementation during the research phase. It turns macOS objects into neutral DTOs **before** they leave the Swift boundary. WebBridge, WindowsBridge, AndroidBridge, and IOSBridge are **not** built. The boundary exists only so that they could be added later without rewriting Ghost Core.

### 3.1 Boundary table

| Concern | Ghost Core / PlatformBridge (neutral) | MacOSBridge only |
|---|---|---|
| Application | `ApplicationRef` (opaque id, alias, version hash) | pid, bundle identifier, `NSRunningApplication`, `NSWorkspace` |
| Window | `WindowRef` (opaque), title text, `Rect` + coordinate-space metadata, focused/main/minimized flags | `CGWindowID`, AX window element, display scale and coordinate conversion |
| UI element | `UIElement {handle, role, label, value, states, bounds, actions, stable_id_hint, children, truncated}` | `AXUIElement`, `AXRole`, `AXSubrole`, `AXTitle`, `AXDescription`, `AXIdentifier`, attribute errors |
| Element handle | `ElementHandle` = opaque `(observation_generation, index)`; invalid once stale | table mapping handles to live `AXUIElement` references for one generation |
| Roles | neutral enum: `button, text_field, text_area, checkbox, radio, menu, menu_item, list, row, cell, table, tab, popup, slider, window, static_text, image, group, toolbar, unknown` | versioned AX-role/subrole → neutral-role mapping table (inside the normalizer) |
| Primitive actions | `PrimitiveAction`: `INVOKE`, `SET_VALUE` (Week 1). Neutral additions (`TYPE_TEXT`, `KEY_CHORD`, `SHOW_MENU`, `SCROLL`) come later by ADR/API change | `AXPress`, `AXShowMenu`, `AXSetValue`/`AXValue`, `CGEvent`, keyboard mappings |
| Evidence | `RawObservation` (artifact refs + hashes, treated as opaque by core), `PlatformObservation`, `ArtifactRef(sha256)` | raw AX JSON encoding, `CGImage`, ScreenCaptureKit objects |
| Normalization | consumes `PlatformObservation` and its `normalizer_version` | pure Swift normalizer (also a host command-line tool for offline replay) |
| State | `CanonicalState`, fingerprint, diff, Transition, StateGraph | none; no canonicalization, no state semantics |
| Semantics | Hypothesis, Experiment, Trial, Verification, Capability, SemanticTarget, EntityRef, GIR | none |
| Bindings | neutral binding candidates (role, label, stable_id_hint, neutral ancestor path, menu path, effect signature), versions, evidence | runtime lookup of the current element that matches a neutral candidate |
| Readiness / errors | neutral readiness (`ax_permission`, `capture_permission`, `input_ready`, `is_vm`) and typed error codes | TCC/AX/capture status, `AXError`, platform error conversion |
| Sandbox | `SandboxAttestation` (typed token) | Tart clone name, VM identity evidence (`hw.model`, `kern.hv_vmm_present`, to verify in the spike) |

### 3.2 Observation pipeline

```text
bridge capture ─► RawObservation (immutable; stored first, hashed)
             └─► PlatformObservation (Swift normalizer vN; stored with parent hash + normalizer version)
Ghost Core    ─► CanonicalState (canonicalizer vM; stored with parent hash + canonicalizer version)
               ─► fingerprint, structured diff, Transition, StateGraph
```

- Raw evidence is written and hashed before anything is derived from it.
- A PlatformObservation can be regenerated offline by `macos-normalize --version N < raw.json`.
- A CanonicalState can be regenerated from the PlatformObservation by the Python canonicalizer.
- Truncation (depth/node limits, virtualized content) is carried explicitly, so core records **UNKNOWN**, not absent.

---

## 4. Ghost Core packages

| Package | Responsibility | LLM? |
|---|---|---|
| `platform/` | neutral types, `PlatformBridge` protocol, HTTP client (timeouts, correlation IDs, no mutation retries) | no |
| `observation/` | canonicalization, fingerprints, structured diff | no |
| `exploration/` | frontier, novelty, risk gating, budgets, StateGraph | no |
| `semantics/` | evidence packets (aliased, minimized), hypothesis generation, rebinding candidate proposals | yes, via `llm/` |
| `experiments/` | experiment specs, trial scheduling across strata, executor, **internal verifier** (separate component), statistics | no |
| `gir/` | schema, compiler, `runtime` (deterministic), `bindings` (versions, deterministic resolution), rebinding request | no |
| `llm/` | `LLMProvider`, providers, mock, budget enforcement, call logging | n/a |
| `storage/` | SQLite, migrations, content-addressed artifact store | no |
| `sandbox/` | VM adapter (the only `ghost-vm/` caller), sandbox guard, `SandboxAttestation` | no |
| `cli.py` | thin argument parsing only | no |

Packages are created only when the week that needs them starts. The table is a boundary map, not a scaffolding plan.

---

## 5. Executor, verifier, adjudicator

```text
executor (experiments) ──► actions through PlatformBridge ──► executor claim (never evidence)
verifier (experiments) ──► fresh observation(s), relaunch where persistence matters ──► behavioral verdict
harness capture step    ──► sealed adjudication store (after the verifier; unreadable by discovery)
adjudicator (harness)   ──► semantic verdict, after the publication snapshot
```

The verifier never reads executor return values. The adjudicator never writes to anything discovery reads.

---

## 6. Automatic rebinding boundary (ADR-011)

```text
GIR runtime
  │ resolve semantic target via current binding_version (deterministic)
  ▼
resolved? ── yes ──► execute ──► verifier
  │ no (or postcondition failed under a declared drift)
  ▼
deterministic candidate search (neutral candidates: role/label/stable_id_hint/path/effect signature)
  │ found candidates ──► deterministic experiment + verifier ──► validated? ─ yes ─► new binding_version
  │ none, or all rejected
  ▼
generic rebinding request {capability, semantic_target, failure evidence refs, budget}
  ▼
semantics/ (only if semantic reasoning is needed): LLM proposes candidate bindings (proposal only)
  ▼
deterministic experiment + verifier (unchanged capability contract and postcondition, unique probes)
  ▼
validated new binding_version (recorded with evidence) ──► GIR runtime consumes it
```

Invariants:

- `gir/runtime` contains no LLM. It may detect failure, search deterministic candidates, emit a rebinding request, and consume validated binding versions.
- An LLM-proposed candidate is never installed directly. Activation requires deterministic verification of the unchanged postcondition.
- The rebinding search is scoped to the failed semantic target and bounded by the rebinding budget (`BENCHMARKS.md` §7.9). Exceeding the budget counts as failure ("equivalent to rediscovery").
- Every candidate, verdict, cost, and binding version is recorded. The GIR capability contract never changes during rebinding.

---

## 7. Benchmark harness (ADR-010)

This is a separate package outside Ghost Core. It contains:

- baseline arms B1–B4 (`BENCHMARKS.md` §9);
- the frozen natural-language router (Evaluation C);
- the oracle capture runner and adjudication tooling.

It uses `PlatformBridge` and `LLMProvider`. B1/B2 need raw-input bridge endpoints (coordinate click, type, key), which are added to `API.md` in the baseline task, not in Week 1. Visual inference is allowed here only (ADR-009). Nothing flows from the harness into discovery.

---

## 8. External calls: timeouts and retries

| Call | Timeout | Retry |
|---|---|---|
| Bridge reads (`health`, `apps`, `windows`, `observations`, `captures`, `artifacts`) | per-endpoint deadline (API.md) | up to 2 retries, exponential backoff, same request ID |
| Bridge mutations (`launch`, `invoke`, `set-value`) | per-endpoint deadline | **never automatic**; the caller re-observes and decides |
| VM adapter (`tart` commands) | per-command timeout | clone/stop/delete only, with idempotency checks; `run` is never blindly retried |
| LLM provider | per-call timeout | SDK retries for 429/5xx only, bounded; budget checked before each attempt |

---

## 9. Deployment and resources (research phase)

- One host (M3, 16 GB RAM): **one VM at a time** by default (proposed 4 vCPU / 6 GB RAM per VM). A second concurrent VM only after measurement shows it is safe.
- Tart home, seeds, and clones must share one APFS volume, because copy-on-write clones only work within a volume. The artifact store is local and gitignored.
- No cloud services, queues, object storage, or hosted databases (ADR-001).

Future adapters (WebBridge and so on) are post-gate. They would add a new platform implementation behind the same DTOs, and that is their only test of this architecture.
