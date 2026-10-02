# 3. Change register: every proposed higher-authority change

Each entry gives the nine fields you asked for. Diffs are in `diffs/`.

Cost figures use the planning assumptions in `feasibility.md` §1. **They are assumptions until the VM preflight measures real median and p95 trial times.** "Per app" means per held-out app (pilot + 3 finals = 4 apps).

Legend: **When:** `W1` = the decision is needed before Week 1 starts; `W4` = decide now or by Week 3, implement in Week 4; `F` = must be frozen before the Week 5 freeze.

---

### CR-01 Observation terminology (`RawObservation -> PlatformObservation -> CanonicalState`)
- **Diff:** `docs_RESEARCH.md.diff` (§7, §8, §14, §15), `CLAUDE.md.diff`; new ARCHITECTURE §3.2, DATA_MODEL.
- **Problem fixed:** RESEARCH and CLAUDE defined "Observation" differently.
- **Hypotheses:** all (evidence lineage).
- **Old-rule risk:** raw and derived evidence could be mixed up, so a changed noise filter could silently rewrite what counts as "evidence".
- **Complexity:** none beyond naming. It shapes the API and schema.
- **Extra trials:** 0. **Time:** 0. **Cost:** 0.
- **When:** W1.

### CR-02 H1 construct validity and semantic identifiability
- **Diff:** `docs_RESEARCH.md.diff` (H1, §11, §21).
- **Problem fixed:** a recorded path with a nice name could count as a capability; the model could pick the familiar meaning (delete vs archive).
- **Hypotheses:** H1, H3.
- **Old-rule risk:** capabilities that only replay one path pass H1; wrong-but-familiar semantics pass internal checks.
- **Complexity:** prompt rule plus a GIR check (one contract across strata); the B4 comparison covers the rest.
- **Extra trials:** 0 (uses the strata and B4). **Time/cost:** covered by CR-04 and CR-12.
- **When:** W4 (prompt in Week 3).

### CR-03 H2 necessary-parameter recall (proposed target ≥ 0.80)
- **Diff:** `docs_RESEARCH.md.diff` (H2), `docs_BENCHMARKS.md.diff` (§7.4, §17.4).
- **Problem fixed:** precision alone rewards under-declaration.
- **Hypothesis:** H2.
- **Old-rule risk:** `create_event(title)` scores 100% when four parameters are necessary.
- **Complexity:** a scoring script, plus the oracle lists necessary parameters.
- **Extra trials:** 0. **Time:** your oracle authoring grows by about 10–20 min per app. **Cost:** 0.
- **When:** F (scoring). Tell the semantic prompt in Week 3.

### CR-04 H3 state strata inside N = 20 + concentration rule
- **Diff:** `docs_RESEARCH.md.diff` (H3), `docs_BENCHMARKS.md.diff` (§6, §6.1, §7.3, §17.3); ADR-004 amendment.
- **Problem fixed:** 20 runs from one snapshot measure repeatability, not reuse.
- **Hypothesis:** H3.
- **Old-rule risk:** a capability that breaks after relaunch or with more rows gets VERIFIED.
- **Complexity:** harness setup for S1 (relaunch) and S2 (window/focus); you prepare 2 seed variants per app (S3/S4). Bridge needs `apps/quit` and `windows/arrange` (Week 4).
- **Extra trials:** **0** (N is spread, not multiplied).
- **Time:** about +30 s setup on 8 of 20 trials, so about +0.5–0.8 VM-hours per app. You spend about 30–60 min per app on seed variants.
- **Cost:** 0 model $. Storage: seed variants are copy-on-write, about 0.5–2 GB per app.
- **When:** W4 (engine), F (allocation frozen).

### CR-05 Futility stop
- **Diff:** `docs_BENCHMARKS.md.diff` (§6.2).
- **Problem fixed:** trial budget is wasted on candidates that can no longer pass.
- **Hypotheses:** none weakened. It can only stop runs for candidates already excluded.
- **Old-rule risk:** none (cost only).
- **Complexity:** a small check in the trial scheduler.
- **Extra trials:** **−60 to −90 per app** (rejected candidates stop at about 3–8 trials instead of 20).
- **Time:** **about −2.5 to −3.5 VM-hours per app.** **Cost:** 0.
- **When:** W4.

### CR-06 H4 safety plus usefulness (proposed correct-resolution ≥ 0.80; 0 unsafe resolutions)
- **Diff:** `docs_RESEARCH.md.diff` (H4), `docs_BENCHMARKS.md.diff` (§7.6, §17.6).
- **Problem fixed:** refusing every request met the old safety target.
- **Hypothesis:** H4.
- **Old-rule risk:** a resolver that returns `ENTITY_AMBIGUOUS` always passes.
- **Complexity:** oracle request sets and scoring; the resolver itself is Week 4 work anyway.
- **Extra trials:** **+10 per app** (ambiguous set); the resolvable set reuses reliability trials.
- **Time:** about +0.4 VM-hours per app; you spend about 30 min per app on request sets. **Cost:** 0 model $.
- **When:** F.

### CR-07 H5 drift: taxonomy, rebinding budget (proposed 25% of `D_search`), cost ratio, sources, route
- **Diff:** `docs_RESEARCH.md.diff` (H5, §16), `docs_BENCHMARKS.md.diff` (§7.9, §14, §17.7); ADR-011.
- **Problem fixed:** "rebinding" could be full rediscovery; a label change alone was weak evidence; no rule for closed-source drift.
- **Hypotheses:** H5, H6.
- **Old-rule risk:** rediscovery passes as self-healing, and manufactured drift could come from binary edits.
- **Complexity:** fixture drift toggles (CR-16); budget meter on rebinding.
- **Extra trials:** real-app drift is the same as v0.1 (20 post-drift trials). **Development only:** one actual rediscovery per drift class tested on the fixture, about 3 classes × 1–2 VM-hours = **3–6 VM-hours in Week 4**.
- **Cost:** about $3–10 in semantic calls for the fixture rediscoveries.
- **When:** W4 (mechanics), F (route and budget).

### CR-08 H6 definition of material advantage (proposed: +10 pp reliability with the difference interval excluding 0, or ≤ 50% success-adjusted cost with ≤ 5 pp reliability loss and break-even within the horizon)
- **Diff:** `docs_RESEARCH.md.diff` (H6), `docs_BENCHMARKS.md.diff` (§7.10, §17.8).
- **Problem fixed:** "meaningful" was undefined, and latency alone could pass.
- **Hypothesis:** H6.
- **Old-rule risk:** a faster but less reliable GhostAPI "beats" the baseline.
- **Complexity:** analysis only.
- **Extra trials:** 0. **Time/cost:** 0.
- **When:** F.

### CR-09 Full amortization model, usage horizon (proposed 1,000 successful calls per app over 90 days, 1 drift event), shadow rates (proposed $1/VM-hour, $60/human-hour)
- **Diff:** `docs_BENCHMARKS.md.diff` (§10, §7.7, §7.8).
- **Problem fixed:** `ceil(D/(B−G))` ignored failures, retries, VM time, maintenance, approvals, and acquisition cost.
- **Hypothesis:** H6.
- **Old-rule risk:** break-even looks much earlier than it really is.
- **Complexity:** log VM-hours and human minutes (already in the data model); analysis script.
- **Extra trials:** 0. **Time:** 0. **Cost:** 0.
- **When:** W4 (logging), F (horizon and rates).

### CR-10 Internal verification vs hidden adjudication; sealed capture; publication snapshot
- **Diff:** `docs_RESEARCH.md.diff` (§13), `docs_BENCHMARKS.md.diff` (§6, §7.2, §13.1, §20); DATA_MODEL adjudication DB; ARCHITECTURE §5.
- **Problem fixed:** GhostAPI could invent a meaning, invent its own oracle, pass it, and claim proof.
- **Hypotheses:** H1, H2, H3.
- **Old-rule risk:** a mislabeled but repeatable transition is VERIFIED **and** scored as correct.
- **Complexity:** a separate store and an import/path invariant; the harness runs the capture step last.
- **Extra trials:** **0** (both judgments come from the same trials).
- **Time:** about +15 s per trial for capture, so about +0.5 VM-hours per app. Writing capture steps is part of your oracle work, about +1 h per app.
- **Cost:** 0.
- **When:** W4 (separation designed now), F.

### CR-11 `INVALID_INFRA` fault codes; trial vs trial attempt; at most 3 attempts per slot; 10% indeterminate rule
- **Diff:** `docs_RESEARCH.md.diff` (§19), `docs_BENCHMARKS.md.diff` (§8.3).
- **Problem fixed:** infra relabeling could erase failures; reruns could double-count.
- **Hypothesis:** H3 (all reliability numbers).
- **Old-rule risk:** a GhostAPI-caused failure gets called infra and silently rerun until it passes.
- **Complexity:** harness fault codes and an attempt table (in the data model).
- **Extra trials:** only replacements for real infra faults (expected to be small; measured).
- **Time/cost:** proportional to the infra fault rate.
- **When:** W4 (engine); decided now because it shapes the data model.

### CR-12 Baseline arms B1–B4 (B1, B2, B4 required; B3 can wait)
- **Diff:** `docs_BENCHMARKS.md.diff` (§9.0–§9.4, §9.6, §17.8); ADR-010.
- **Problem fixed:** a single screenshot-only baseline can't tell GIR's value apart from sensors, memory, or selectors.
- **Hypotheses:** H6, H1 (vs replay).
- **Old-rule risk:** GhostAPI "wins" because AX is a better sensor than pixels, not because of GIR.
- **Complexity:** B1 loop (needed anyway); B2 about +1–2 days (sensor swap and element actions); B4 recorder/replayer about +2 days; B3 composition about +1 day.
- **Extra runs per app vs v0.1:** B2 30 runs (about 2 VM-hours); B4 60 replays (about 2.5 VM-hours); B3 30 runs (about 1.5 VM-hours, if run).
- **Cost per app:** B2 about $15–45; B3 about $10–20; B4 $0. Storage about +0.5 GB per app.
- **When:** W4 (build on development apps), F (Ns and budgets).

### CR-13 Evaluations A/B/C and frozen router
- **Diff:** `docs_BENCHMARKS.md.diff` (§9.5); AGENTS baseline-fairness line.
- **Problem fixed:** a human mapping tasks to capability calls is hidden assistance.
- **Hypothesis:** H6 (end-to-end fairness).
- **Old-rule risk:** GhostAPI gets perfect routing for free while every baseline arm routes itself.
- **Complexity:** one prompt plus schema-validated output, about 1 day.
- **Extra runs per app:** 60 end-to-end runs (6 tasks × 10), about **2.5 VM-hours**.
- **Cost:** about $1–3 per app in router calls.
- **When:** W4 (build), F (router frozen).

### CR-14 Vision gate + baseline exemption (+ proposed AXI-1 criterion)
- **Diff:** `docs_PRODUCT.md.diff`, `docs_RESEARCH.md.diff` (§2.1, §17), `AGENTS.md.diff` (inv. 11); ADR-009.
- **Problem fixed:** PRODUCT, RESEARCH, AGENTS, and BENCHMARKS contradicted each other on vision.
- **Hypotheses:** H1 (contamination via vision), H6 (baseline validity).
- **Old-rule risk:** either the required baseline is forbidden, or vision slips into GhostAPI through the baseline.
- **Complexity:** none, plus one invariant (harness ↛ discovery).
- **Extra trials:** 0. **Time/cost:** 0.
- **When:** W1.

### CR-15 Eligible population, screening, exclusion log
- **Diff:** `docs_RESEARCH.md.diff` (§4.5, §21), `docs_BENCHMARKS.md.diff` (§3.1).
- **Problem fixed:** three hand-picked apps imply a population claim nobody defined.
- **Hypothesis:** generalization scope (all).
- **Old-rule risk:** AX-rich success is presented as general success.
- **Complexity:** documentation; your private screening.
- **Extra trials:** 0. **Time:** about 1–2 h once, plus about 15 min per screened candidate. **Cost:** 0.
- **When:** F (before selection).

### CR-16 One configurable synthetic research fixture, never evidence
- **Diff:** `docs_RESEARCH.md.diff` (§4.4); plan in `fixture-plan.md`.
- **Problem fixed:** there was no controlled place to test H4/H5 mechanics and adversarial cases, and many fixture apps were a risk.
- **Hypotheses:** H4, H5, safety (development only).
- **Old-rule risk:** none. This prevents over-claiming from fixtures.
- **Complexity:** minimal core about 2–3 days; drift toggles about +1 day.
- **Extra trials:** development only. **Cost:** development VM time.
- **When:** W4 (core by Week 2 for risk and adversarial evals).

### CR-17 UNKNOWN mutations fail closed until a policy is approved
- **Diff:** `docs_RESEARCH.md.diff` (§10); SECURITY §4.
- **Problem fixed:** the rule pointed to a document that did not exist.
- **Hypotheses:** safety (K13).
- **Old-rule risk:** an unclassified mutating action executes without any rule.
- **Complexity:** one branch in the risk gate.
- **Extra trials:** 0. **Time/cost:** 0 (may reduce coverage; measured).
- **When:** W1 decision; implemented in Week 2.

### CR-18 Manifest and freeze fields
- **Diff:** `docs_RESEARCH.md.diff` (§18), `docs_BENCHMARKS.md.diff` (§5, §15).
- **Problem fixed:** the new protocol elements weren't frozen or recorded.
- **Hypotheses:** all (reproducibility).
- **Old-rule risk:** unrecorded normalizer, strata, or budget changes between runs.
- **Complexity:** manifest writer fields.
- **Extra trials:** 0. **Time/cost:** 0.
- **When:** W4 / F.

### CR-19 ADR-004 amendment and acceptance
- **Diff:** `docs_DECISIONS.md.diff`.
- **Problem fixed:** a rule still marked "proposed" was already in force; its pooling contradicted BENCHMARKS.
- **Hypothesis:** H3.
- **Old-rule risk:** only pooled figures are reported.
- **Complexity / trials / time / cost:** 0.
- **When:** W1.

### CR-20 AGENTS boundary lines (platform-neutral core, rebinding, harness) and "source files" < 500 lines
- **Diff:** `AGENTS.md.diff`.
- **Problem fixed:** C3, C7, C9 in `02-authority-reconciliation.md`.
- **Hypotheses:** H1 (leakage), H5, H6.
- **Old-rule risk:** harness outputs leak into discovery; AX vocabulary leaks into core; the invariant check fails on docs.
- **Complexity:** invariant scripts, about 0.5 day in the skeleton task.
- **Extra trials:** 0.
- **When:** W1.

### CR-21 Kickoff: `ghost call` Week 4 → internal runtime, Week 5 → CLI
- **Diff:** `KICKOFF_PROMPT.md.v5-patch.diff`.
- **Problem fixed:** C6.
- **Hypotheses:** none.
- **Old-rule risk:** scope creep in Week 4.
- **Complexity / trials / time / cost:** 0.
- **When:** W1.

### CR-22 PRODUCT: MVP baseline wording, vision paragraph, success metric aligned with BENCHMARKS, kill-pass rows
- **Diff:** `docs_PRODUCT.md.diff`. **Human-owned: apply only what you approve verbatim.**
- **Problem fixed:** the success metric allowed "a measurable advantage" (latency) and omitted recall, usefulness, and drift cost.
- **Hypotheses:** H2–H6.
- **Old-rule risk:** as CR-03 to CR-08.
- **Complexity / trials / time / cost:** 0.
- **When:** W1.

### CR-23 LLM budget and logging (ADR-013)
- **Diff:** `docs_DECISIONS.md.diff` (ADR-013).
- **Problem fixed:** the "configured budget" gate referenced a budget that didn't exist.
- **Hypotheses:** none (governance).
- **Old-rule risk:** unbounded spend, or unlogged calls breaking cost metrics.
- **Complexity:** budget guard plus logging in `LLMProvider`, about 0.5–1 day (Week 3).
- **Extra trials:** 0.
- **Cost:** sets the ceiling (about $900 total at the current Opus tier; see `feasibility.md`).
- **When:** before the first paid call (Week 3).

### CR-24 VM lifecycle, base image, network isolation (ADR-012)
- **Diff:** `docs_DECISIONS.md.diff` (ADR-012); `vm-storage-network-preflight.md`.
- **Problem fixed:** the convenience image edits TCC; `--net-host` is unavailable on macOS 14.6; Softnet needs root.
- **Hypotheses:** safety; H3 (clean state).
- **Old-rule risk:** pre-granted permissions and non-vanilla state; network leakage.
- **Complexity:** base build (manual steps by you), guest packet-filter rules, per-trial probes.
- **Extra trials:** 0. **Time:** about 10–20 s per trial for isolation probes. **Cost:** 0.
- **When:** W1 (blocked on storage).
