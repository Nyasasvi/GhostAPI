# GhostAPI: Product Spec (DRAFT, owned by Yasasvi)

> Drafted from the build plan. Edit it until it's what you believe, then have the agent attack it (see "Kill pass" below). The agent critiques this file but never edits it without your approval.

## Problem
AI agents can't reliably use most software, because most software has no API. Computer-use agents re-discover every UI from pixels on every run: slow, expensive, brittle, and with no memory between agents or runs.

**Who has it:** developers building agents that need to act in desktop apps without APIs (internal tools, legacy apps, niche pro software).

## User
For the research phase: **agent developers** (starting with me) who want an agent to call a capability in a macOS app that has no API or scripting support.
*Open question: is the eventual user the agent developer, an enterprise automation team, or the app's own vendor?*

## Pain (what they do today)
- Write brittle UI automation by hand (AppleScript, RPA, Playwright-style scripts) that breaks on UI changes
- Use screenshot computer-use agents: slow, costly per step, unreliable, and they re-learn the UI each run
- Record a workflow and replay it (works only for demonstrated paths)
- Give up on the app

## Solution
Point GhostAPI at an unseen app. It autonomously discovers capabilities, proves them by repeated experiment, and records them in GIR, a typed interface separated from the current UI binding, so capabilities survive UI changes and can be reused by any agent.

## MVP (smallest version that proves value)
`ghost learn <unseen app>` → ≥5 verified capabilities → `ghost call` runs them reliably. No app-specific code, on held-out apps, compared against the benchmark's baseline arms (screenshot computer use plus the AX-enabled, cached, and trace-replay diagnostics), with one drift recovery.

## Non-goals (for now)
REST/MCP serving, SDKs, web apps, Windows/Linux, canvas-heavy apps, a hosted service, a UI, multi-agent orchestration, anything with network side effects.

**Vision:** GhostAPI captures screenshots as raw evidence from day one, but *visual inference* (model reasoning over images) is off for GhostAPI. It can be turned on only through the preregistered escalation rule in `docs/RESEARCH.md` §17, with my approval, before any affected holdout freeze, and never to rescue a failed held-out result. The screenshot computer-use baseline is exempt, because screenshots are its intended sensor. That exemption never extends to GhostAPI, and baseline results never flow into GhostAPI discovery (ADR-009).

## Success metric
**Research phase:** the Week 6 targets on 3 held-out apps, as defined in `docs/BENCHMARKS.md` §17: ≥5 useful capabilities per app, ≥90% precision, ≥90% observed reliability at N≥20 across state strata with intervals reported, supported-parameter precision and necessary-parameter recall, safe *and* useful entity resolution, a reliability or success-adjusted cost advantage over the required baseline arms (latency alone does not count), and one drift recovery that is cheaper than rediscovery. Claims are limited to the eligible app population recorded before selection.

**Proof users care (after the gate):** at least 3 external agent developers run `ghost learn` on an app of *their* choice and call a learned capability from their own agent. *Define a concrete number and time window before launching.*

## Kill pass
Before Week 1, the agent answers: *"Try to kill this idea. Which assumptions, if false, make GhostAPI fail or not matter? For each, what's the cheapest experiment that would tell us early?"* The answers go below, and the ones worth testing become tasks.

### Assumptions under attack
| # | Assumption | Why it might be false | Cheapest early test | Status |
|---|---|---|---|---|
| K1 | Deterministic exploration reaches useful *multi-step* operations within a fixed budget (H1) | Useful operations are chains (press, a field appears, type, commit); menus, modals, and open inputs blow up the search | Week 2: on one dev app, you pre-list useful operations; count how many the budgeted explorer observes as transition chains; plot coverage against actions | open, Week 2 |
| K2 | UI evidence can tell apart the semantics that matter (H1) | delete/archive/hide can look identical; the model may pick the familiar name | Week 3: fixture archive/delete pair; check the reasoner proposes a discriminating experiment or stays generic/UNKNOWN | open, Week 3 |
| K3 | AX exposes enough labelled, actionable, state-reflecting structure (H1, population) | Obscure apps, which the holdout rules prefer, often use toolkits with poor AX; hidden/transient state can make identical fingerprints behave differently | Week 1: AX audit of dev apps; Week 2: same-fingerprint/same-action divergence check on fixture | open, Weeks 1–2 |
| K4 | GIR is more than record-and-replay with better names (H1, H3) | One "capability" per path or state would just be a trace | Week 4: one contract across unseen probes and all strata; compare with B4 trace replay on dev | open, Week 4 |
| K5 | Internal verification tells us something about meaning (H1, H3) | Self-written postconditions can pass a wrong interpretation | Week 4: decoy hypotheses on fixture; false-positive postcondition rate against adjudication | open, Week 4 |
| K6 | Parameters are induced, not invented or under-declared (H2) | High precision by declaring fewer parameters | Week 3: fixture with typed/conditional fields; measure precision *and* recall | open, Week 3 |
| K7 | Clean-state reliability reflects real reuse (H3) | 20 runs from one snapshot measures repeatability, not reuse | Week 4: stratified trials (relaunch, window/focus, entity population, preferences) | open, Week 4 |
| K8 | Entity resolution is safe *and* useful (H4) | Zero false targets is trivial if everything is refused | Week 4: fixture duplicates/rename/reorder; correct-resolution rate and refusal rate | open, Week 4 |
| K9 | Drift repair is cheaper than rediscovery (H5) | Label changes need semantics; weak postconditions accept wrong controls | Week 4: fixture drift classes D1–D7 under a rebinding budget; compare with actual rediscovery | open, Week 4 |
| K10 | Model memory is not doing the discovery (H1, H2) | Labels and structure identify famous apps even when aliased | Week 3: ablation (real / aliased / neutralized labels / no-transition control) | open, Week 3 |
| K11 | Any advantage comes from GIR, not from AX sensors, memory, or selectors (H6) | Beating only screenshot-only computer use proves little | Week 4: B1/B2/B4 on a dev app vs GhostAPI | open, Week 4 |
| K12 | Discovery amortizes within a realistic horizon (H6) | D includes hours of VM trials, rejected candidates, approvals, drift upkeep | Week 4: full cost model on first end-to-end dev capability; break-even band | open, Week 4 |
| K13 | Safe exploration still finds useful writes (H1) | Conservative risk rules may block every useful write; approvals may leak hints | Week 2: adversarial fixture controls and ≥50 risk cases; coverage under the safe policy | open, Week 2 |
| K14 | Clean-clone trials are affordable on this hardware (feasibility) | One VM at a time; 25 GiB free disk | Week 0/1 preflight: measure median/p95 trial cycle and disk growth | blocked on storage |
| K15 | Three eligible apps can support any population claim | Eligibility favors AX-rich local apps | Before selection: population definition, screening, exclusion log | open, before Week 5 |
