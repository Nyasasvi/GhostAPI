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
**Status:** proposed (confirm in Week 4 planning)
**Context:** A Wilson 95% lower bound ≥ 0.90 needs ≥35/35 successes, which is impractical per capability.
**Decision:** `verified` = observed reliability ≥ 0.90 over N ≥ 20 clean-state trials. Always report the Wilson 95% interval. Headline claims pool trials across capabilities.
**Consequences:** Per-capability claims carry wide intervals, and reports must state them.

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
