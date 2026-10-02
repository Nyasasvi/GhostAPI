# 23. Six-week feasibility estimate

**Bottom line:** the v0.2 protocol fits in six weeks only if four conditions hold:

- storage is freed this week;
- a clean-clone trial cycle measures at about 2.5 minutes or less (median);
- the baseline harness is built in parallel from Week 3, not all in Week 4;
- Week 6 runs unattended for about 3 days of VM time.

The biggest threats are storage (a blocker today) and an overloaded Week 4. Methodology work is kept to documents in Week 0. Every added mechanism is built in the week that first needs it.

## 1. Planning assumptions (unmeasured; replaced by preflight medians and p95s)

| Parameter | Assumption |
|---|---|
| Clean-clone trial cycle (clone → boot → ready → launch → act → verify incl. relaunch → extract → delete) | 2.5 min median (plausible range 1.5–4) |
| Computer-use baseline run (B1/B2) | 4 min |
| Trace replay (B4) or routed GhostAPI call (C) | 2.5 min |
| Per-attempt overheads | isolation probe 15 s; sealed capture 15 s; S1/S2 stratum setup 30 s |
| Per app | 6 benchmark tasks; about 12 candidate capabilities (5 VERIFIED, 7 rejected); exploration 3 VM-hours |
| Semantic call | about $0.11 (about 8k input + 4k output tokens at $4/$20 per million) |
| Computer-use run | about $0.5–1.5 (10–20 steps; screenshots about 1.4k tokens each: an approximation to check with the token-count API before freezing budgets) |

## 2. Old vs new protocol: per-app and program cost

| | v0.1 (current) | v0.2 (proposed) |
|---|---|---|
| Capability reliability trials | 240 (12 × 20, no futility stop) | **156** (5 × 20 + 7 × about 8 with futility stop) |
| Entity ambiguous trials | 0 | 10 |
| Drift trials | 20 | 20 |
| B1 runs | 60 | 60 |
| B2 / B4 / C runs | none | 30 / 60 / 60 |
| **Executions per app** | **320** | **396** (+30 if B3) |
| **VM-hours per app (1 VM)** | **about 18** | **about 25** (+1.5 if B3) |
| Held-out apps | 4 (pilot + 3) | 4 |
| **VM-hours, all held-out apps** | about 73 | **about 101** (about 107 with B3) |
| LLM $ per app | about $37–103 | about $57–156 (+$10–24 if B3) |
| **LLM $, all held-out apps** | about $146–413 | **about $228–623** (+$40–96 if B3) |
| Development-phase LLM $ (Weeks 3–4) | n/a | about $100–190 |
| Storage per app | about 2.5 GB | about 3.5–5 GB |
| Your time per held-out app (tasks, oracle bundle + capture steps, necessary parameters, entity sets, S3/S4 seed variants, drift declaration, rubric, approvals) | about 3–5 h | **about 4–7 h** (16–28 h total over Weeks 4–6) |

Most of the extra cost is the baseline arms and Evaluation C, which is what makes H6 testable. The futility stop saves about 84 trials per app (about 3.5 VM-hours), which offsets most of the stratification and capture overhead.

## 3. Week by week

| Week | Must deliver | Protocol work in this week | Critical-path risk |
|---|---|---|---|
| **0** | approved docs/ADRs; repo init; VM preflight (after storage); bridge `/health` through the tunnel | documents only | **storage blocker**; permissions in the GUI session; headless AX |
| **1** | `ghost observe/press/set` on a development app with raw + platform observations and screenshots; fixture core started | terminology (CR-01), vision gate (CR-14), boundaries (CR-20) already in docs | bridge in the GUI session; stable signing so permissions survive rebuilds |
| **2** | canonicalization, fingerprints, diff, StateGraph, deterministic explorer, risk classifier; ≥50 risk cases; K1 reachability test | UNKNOWN fail-closed (CR-17) | multi-step reachability (K1); state explosion (K3/K6) |
| **3** | LLMProvider + Mock + budget guard + logging; prompt v1; ≥50 semantic eval cases incl. identifiability, injection, and ablation; **start the baseline harness track** (B1 loop, raw-input endpoints, B4 recorder) | budget (CR-23); prompt told about recall and identifiability | first paid call blocked until the budget is approved |
| **4** | experiment engine with strata + futility; separate verifier; trial/attempt; sealed capture; GIR v0.1 + deterministic runtime + bindings; minimal entity resolver; rebinding request + fixture drift; B2/B4 + router; cost logging; **end-to-end dry run of the benchmark pipeline on a development app** | CR-02..CR-13 implemented | **most overloaded week**; entity/H5 may slip (see §5) |
| **5** | freeze + tag; pilot (about 25 VM-hours); public `ghost call` CLI | nothing new; frozen | first real held-out integration; any fix means a refreeze |
| **6** | 3 held-out apps (about 76 VM-hours ≈ 3.1 days on one VM); adjudication; report; decision gate | nothing new; frozen | compute time; no slack for reruns |

## 4. Classification of proposed additions

| Addition | Class |
|---|---|
| Terminology (CR-01); vision gate (CR-14); AGENTS boundaries and invariants (CR-20); kickoff patch (CR-21) | **REQUIRED TO VALIDLY TEST THE THESIS** (cheap; docs and invariants) |
| Internal verification vs sealed adjudication (CR-10); trial/attempt + `INVALID_INFRA` rules (CR-11) | **REQUIRED** |
| Strata within N = 20 + concentration rule (CR-04) | **REQUIRED** (H3 is untestable without it) |
| Necessary-parameter recall (CR-03); entity usefulness metric (CR-06); H6 definition (CR-08); cost model and horizon (CR-09) | **REQUIRED** (scoring and analysis only) |
| Baselines B1, B2, B4 (CR-12); Evaluation C router (CR-13) | **REQUIRED** for any H6 claim beyond "vs screenshot-only" |
| Rebinding budget + cost ratio + drift taxonomy (CR-07) | **REQUIRED** for any H5 claim |
| Population definition + exclusion log (CR-15) | **REQUIRED** before holdout selection |
| UNKNOWN fail-closed (CR-17); LLM budget (CR-23); VM isolation option B + probes (CR-24) | **REQUIRED** (safety and governance) |
| Fixture core + risk adversarial + drift toggles | **REQUIRED** (H4/H5 mechanics, risk evals), timeboxed at 3.5 days |
| Futility stop (CR-05) | **USEFUL BUT CAN WAIT** (strongly recommended: it saves time and cannot create false positives) |
| B3 stateful/cached computer-use arm | **USEFUL BUT CAN WAIT** (if skipped, the report says so) |
| Fixture extensions (typed/conditional fields, virtualization, hidden mode) | **USEFUL BUT CAN WAIT** (only on a logged failure) |
| Actual rediscovery on the drifted fixture (proxy validation) | **USEFUL BUT CAN WAIT** (one class minimum) |
| Generic AX-surface screening instrument for your private eligibility checks | **USEFUL BUT CAN WAIT** (before selection) |
| AXI-1 measurement | **USEFUL BUT CAN WAIT** (only if AX gaps appear) |
| Second concurrent VM; Softnet upgrade; real-app drift test | **USEFUL BUT CAN WAIT** (decide before freeze) |
| Other platform bridges, REST/MCP/SDK/serve, gRPC, multiple fixtures, public benchmark, hosted service | **POST-GATE** |

## 5. Critical-path threats and preregistered responses

Proposed decision rules, frozen now so they are not made after seeing results:

1. **Storage not freed by the end of Week 0** → Week 1 slips day for day. Nothing else is cut.
2. **Measured median trial cycle > 4 min** → recompute §2. If projected Week 6 VM time is over 5 days, first try 2 concurrent VMs (after memory measurement). Then **extend the calendar**. Never cut N, arms, or strata after the fact.
3. **Week 4 overrun** → in order: (a) B3 is not run; (b) entity-targeting capabilities that are not ready are published as not tested for H4; (c) H5 is validated on the fixture only, and real-app H5 is reported as not tested. **Never:** skip the verifier/adjudication split, strata, B1/B2/B4, or the router.
4. **Pilot reveals a generic bug** → record the failure; any fix needs your approval, a new version and refreeze, and the pilot stays spent. Week 6 moves by the time the refreeze takes; the fix is not rushed.
5. **Budget cap reached** → the run stops cleanly. The cap is never raised mid-run. A future run with a new approved budget is a new protocol version for any held-out app.
