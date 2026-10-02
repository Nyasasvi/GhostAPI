# Architecture Decision Records

Format: **Context → Decision → Consequences**, plus Status (proposed / accepted / superseded by ADR-n). New ADRs are appended; accepted ones are never edited, only superseded.

---

## ADR-001: Research-instrument stack instead of a web SaaS stack
**Status:** accepted
**Context:** Generic startup templates suggest Next.js, FastAPI, PostgreSQL, Celery/Redis, S3, OIDC, and Docker on AWS. GhostAPI's first six weeks answer one research question on a single Mac, with no users, no UI, and no server.
**Decision:** Python 3.12 + pydantic v2, Swift 5.9+, SQLite, and JSON/PNG files on disk. No web frontend, Postgres, job queue, object store, auth, or cloud deployment.
**Consequences:** Near-zero ops; everything is replayable locally. If the decision gate lands on Case C, a new ADR revisits serving, storage, and deployment.

## ADR-002: Tart for macOS VMs
**Status:** accepted (verify install and flags in Week 0)
**Context:** We need disposable macOS guests on Apple silicon, cloned from a base image and destroyed per run.
**Decision:** Use Tart (Cirrus Labs) through the `ghost-vm` adapter. Alternatives: raw Virtualization.framework (more work) and UTM (less scriptable).
**Consequences:** Its license terms need recording; the adapter lets us swap it later. Hosts are limited to 2 concurrent macOS guests.

## ADR-003: Deterministic exploration; the LLM only generates hypotheses
**Status:** accepted
**Context:** LLM-driven exploration is non-reproducible, expensive, and hard to make safe.
**Decision:** The explorer, observation, diff, risk rules, trials, statistics, and runtime are deterministic code. The LLM is called only in `semantics/`, via `LLMProvider`, to name capabilities and propose experiments from evidence.
**Consequences:** Reproducible runs; the LLM can't cause unsafe actions directly; we may discover less than an LLM wanderer would.

## ADR-004: Reliability rule
**Status:** proposed → accept as amended (owner approval requested in Week 0)
**Context:** A Wilson 95% lower bound ≥ 0.90 needs ≥35/35 successes, which is impractical per capability. At the chosen rule, 18/20 passes with a 95% Wilson interval of [0.70, 0.97], and 20/20 gives [0.84, 1.00].
**Decision:** `verified` = observed reliability ≥ 0.90 over N ≥ 20 clean-state trials, spread across the preregistered state strata in `BENCHMARKS.md` §6.1, with the concentration rule and futility stop defined there. Always report the Wilson 95% interval. Report aggregates both macro-averaged across capabilities and micro-averaged across trials (per `BENCHMARKS.md` §7.3), never only the pooled figure.
**Consequences:** Per-capability claims carry wide intervals, and reports must state them. VERIFIED means "passed the screen", not "at least 90% reliable".

## ADR-005: Scope gate: no serving layer before the decision gate
**Status:** accepted
**Context:** REST, MCP, and SDKs are easy once GIR is proven and irrelevant if it isn't.
**Decision:** Nothing beyond `ghost call` until the Week 6 decision gate lands on Case C.
**Consequences:** No external demo surface early; all effort goes into discovery.

## ADR-006: Provider abstraction for LLMs
**Status:** accepted
**Context:** Models, pricing, and APIs change; tests must run without network access.
**Decision:** `LLMProvider` interface (`generate`, `generate_structured`) with `ClaudeProvider` and `MockProvider`. The model name, prompt version, and parameters come from config. Every call logs model, prompt version, input hash, output, latency, tokens, cost, and errors.
**Consequences:** Swapping models is a config change; evals can compare providers.

## ADR-007: Platform boundary and observation pipeline
**Status:** proposed
**Context:** Ghost Core must not depend on macOS concepts, so that a later adapter (web, Windows) could be added without rewriting it. Derived evidence must be regenerable from raw evidence (AGENTS rule 16).
**Decision:** `Ghost Core -> PlatformBridge -> MacOSBridge`. `PlatformBridge` is a neutral Python protocol plus a neutral, versioned wire contract; it is not a separate service. `MacOSBridge` is the only implementation in the research phase, and it has two parts. (1) The guest service (Swift) captures a `RawObservation` (verbatim AX attributes, window/focus info, capture metadata) and returns it with a `PlatformObservation` produced by a **pure, versioned Swift normalizer**. (2) The same normalizer ships as a host-side command-line tool, so a PlatformObservation can be regenerated offline from stored raw evidence without a VM. Ghost Core consumes only neutral DTOs and derives `CanonicalState` itself. All AX vocabulary lives in Swift. Python contains none.
**Alternatives:** normalization in a Python `platform/macos` module (rejected: it puts AX vocabulary into the Python tree and weakens the invariant check); normalization only in the guest (rejected: regenerating would need a VM).
**Consequences:** Core invariants can be checked mechanically (no AX/CG/NS/SCK identifiers under `ghost-core/`). Normalizer changes bump a version and can be replayed over stored raw evidence. Adding WebBridge later means a new adapter behind the same DTOs.

## ADR-008: Host↔guest transport: HTTP/1.1 + strict versioned JSON
**Status:** proposed
**Context:** Week 1 needs about 9 low-rate request/response operations, with no streaming. Raw bridge responses are research evidence and should be stored verbatim and be human-readable.
**Decision:** HTTP/1.1 with strict, versioned JSON (`/v1/...`). The guest service binds only to guest `127.0.0.1`. The host reaches it only through an SSH local forward that also binds to host `127.0.0.1`, with key-only auth and a pinned host key. A per-boot bearer token adds defense in depth. Requirements: request and correlation IDs, client deadlines and server timeouts, body-size limits, typed stable errors, JSON Schemas as the contract source, golden-fixture contract tests on both sides, malformed-input tests, and compatibility tests. Binary artifacts use a bounded `GET /v1/artifacts/{id}` endpoint, not base64 JSON. Mutations are never retried automatically.
**Alternatives:** gRPC (rejected for now: protobuf/HTTP-2/NIO toolchain and dependencies bring no Week 1 value).
**Revisit when:** measured evidence shows a need for sustained streaming, better transport performance, stronger generated cross-language contracts, or hard-to-control schema drift.
**Consequences:** Small dependency surface and easy debugging (`curl` through the tunnel). Schema discipline depends on contract tests. This is internal RPC, not the scope-gated product REST surface (ADR-005).

## ADR-009: Vision policy and baseline exemption
**Status:** proposed
**Context:** `PRODUCT.md` listed vision as a non-goal, while `RESEARCH.md` §17 allowed conditional escalation and `BENCHMARKS.md` §9 requires a screenshot computer-use baseline, which is visual inference by definition. `AGENTS.md` cited ADR-005 for the vision gate, but ADR-005 covers only serving.
**Decision:** (1) Screenshot capture is allowed from the start as immutable raw evidence. (2) Visual inference by GhostAPI is off by default. It can be enabled only through the preregistered escalation rule in `RESEARCH.md` §17: a criterion registered before the measurement, development-only evidence, owner approval, and timing before any affected holdout freeze. It is never enabled to rescue a held-out result. (3) The screenshot computer-use baseline arms are exempt, because screenshots are their intended sensor. The exemption applies only to the evaluation harness. (4) Baseline outputs and anything learned from them never reach GhostAPI discovery, prompts, bindings, or evals.
**Consequences:** The PRODUCT/RESEARCH/AGENTS conflict is resolved. Any GhostAPI vision use is auditable against a preregistered criterion.

## ADR-010: LLM use in the evaluation harness (supplements ADR-003 and ADR-006)
**Status:** proposed
**Context:** ADR-003 limits LLM calls to `semantics/`, but the benchmark needs LLM-driven baseline arms (B1–B3) and a frozen natural-language router (Evaluation C). ADR-006's interface (`generate`, `generate_structured`) does not cover multimodal tool-use loops.
**Decision:** The benchmark harness (baseline arms, router, adjudication tooling) is a separate package outside the discovery pipeline. It may call LLMs, but only through `LLMProvider`, which gains a tool-use/multimodal method used only by the harness. Discovery packages must not import the harness, and the harness must not import or modify discovery state. Invariant checks enforce both directions. ADR-003 still governs GhostAPI itself: within the pipeline, the LLM is used only in `semantics/`.
**Consequences:** Baselines and routing get the same logging and budget enforcement as semantic calls, without weakening ADR-003.

## ADR-011: Automatic rebinding boundary
**Status:** proposed
**Context:** H5 needs automatic rebinding, but `gir/runtime` must contain no LLM. Label and workflow drift may need semantic matching.
**Decision:** The flow is: GIR runtime → deterministic binding resolution → unresolved → generic rebinding request → (if needed) semantic subsystem in `semantics/` proposes candidate bindings → deterministic experiment and verifier → validated new `binding_version` → GIR runtime. `gir/runtime` may detect failure, search deterministic candidates, request rebinding, and consume validated bindings only. The LLM may propose but never install a binding. Activation requires deterministic verification of the unchanged semantic postcondition. Rebinding is scoped to the failed semantic target and bounded by the rebinding budget in `BENCHMARKS.md` §7.9. Every candidate, verdict, and binding version is recorded.
**Consequences:** Rebinding cost is measurable and comparable with rediscovery. A wrong candidate cannot silently become active.

## ADR-012: VM lifecycle, base image, and network isolation
**Status:** proposed (network mechanism pending owner decision)
**Context:** Every trial needs a clean disposable environment. The Cirrus Labs base image template runs a script that edits the TCC database (`update-tcc-database.sh`), so its permission state is not a clean macOS. `--net-host` needs a macOS 26 host (Tart source), and this host runs macOS 14.6. Softnet needs a SUID bit or passwordless sudo on the host. Tart moved to `openai/tart` under FSL-1.1-ALv2.
**Decision:** The lifecycle is `generic base -> sealed base -> app seed -> disposable trial clone`. The base is built with `tart create --from-ipsw` from a pinned macOS IPSW whose SHA-256 is recorded. No convenience images, no SIP changes, no TCC database edits: permissions are granted manually by the owner and verified. The sealed base is never booted for experiments. Reset is by reclone only, never suspend/resume and never in-app cleanup. Network: default to **NAT + default-deny packet filter inside the sealed base + non-admin GUI user + per-trial egress probes**, which needs no host privilege. Softnet host-side isolation is an optional upgrade that requires explicit owner approval. Details are in `docs/proposals/week0/vm-storage-network-preflight.md`.
**Consequences:** No host privilege escalation by default. Guest-side filtering sits inside the guest, so it is weaker than host-side filtering. That residual risk is documented in `SECURITY.md`, and the per-trial probe is fail-closed.

## ADR-013: LLM spend budget and call logging
**Status:** proposed (numbers need owner approval before any paid call)
**Context:** `AGENTS.md` gates "spend beyond the configured LLM budget", but no budget was configured.
**Decision:** `LLMProvider` enforces hard caps from a budget config that carries the owner's approval ID. With no approved config, every paid call is refused. Proposed caps for the development phase:
- semantic calls: $5 per run; 40 calls per exploration session; 12,000 input tokens per evidence packet; 8,000 max output tokens; $15 per day; $50 per week;
- development baseline probes, from Week 4: $40 per week;
- benchmark (frozen at Week 5, per app): semantic $25, router $3, baselines $150 (per baseline run: at most $2, 30 steps, 10 minutes).

Before each call, `LLMProvider` estimates the cost and refuses if the call would exceed any remaining cap. It then records the actual cost. When a cap is exhausted, the run stops cleanly with `BUDGET_EXHAUSTED` and is never raised silently. Every call logs: provider, model, prompt version, evidence hash, input tokens, output tokens, estimated cost, latency, run ID, correlation IDs, call purpose (semantic / router / baseline), and error status.
**Consequences:** Estimated research-phase ceiling is about $900 with the current Opus-tier model, or about half with a Sonnet-tier model. GhostAPI and the baselines must use the same tier either way.

## ADR-014: Benchmark and research protocol v0.2 (Week 0 repair)
**Status:** proposed
**Context:** The v0.1 protocol could pass H2–H6 without showing what they claim: fewer declared parameters inflated precision; 20 runs from one snapshot looked like re-execution; refusing everything satisfied entity safety; rediscovery could pass as rebinding; latency alone could satisfy H6; internal verification and semantic correctness were not separated.
**Decision:** Adopt `RESEARCH.md` v0.2 and `BENCHMARKS.md` v0.2. Headline thresholds are unchanged (N ≥ 20, ≥ 0.90, precision ≥ 90%, supported-parameter ≥ 90%, coverage ≥ 60%, 0 false targets). Added:
- state strata within N, with a concentration rule and futility stop;
- necessary-parameter recall;
- entity usefulness;
- rebinding budget and cost ratio;
- an H6 materiality definition;
- `INVALID_INFRA` fault codes and trial/attempt accounting;
- baseline arms B1–B4, evaluations A/B/C, and a frozen router;
- a full amortization model with usage horizon;
- sealed adjudication, population/exclusion rules, and the H5 route decision.

New numeric values are marked "proposed" and require owner approval.
**Consequences:** The protocol can no longer pass H2–H6 on technicalities. Added experimentation is limited to the extra ambiguous-entity trials, Evaluation C runs, and baseline arms. Cost impact is in `docs/proposals/week0/feasibility.md`.
