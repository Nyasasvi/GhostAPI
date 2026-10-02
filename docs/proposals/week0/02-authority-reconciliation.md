# 2. Authority and version reconciliation

Authority order (v5): `AGENTS.md` > `PRODUCT.md` > `RESEARCH.md` > `BENCHMARKS.md` > `ARCHITECTURE/API/DATA_MODEL/SECURITY/DECISIONS` > `KICKOFF_PROMPT.md` > `CLAUDE.md`.

Every conflict below was reported, not silently resolved. The "Fix" column names the proposed diff. Nothing is applied until you approve it.

| # | Conflict or gap | Who wins today | Proposed fix | Where |
|---|---|---|---|---|
| C1 | Kickoff on disk is v4; intended kickoff is v5; README says v4 | your decision: v5 | replace with v5 (+ `ghost call` patch); README → v5; v4 kept in Git history | `01-repo-init-plan.md`, `diffs/README.md.diff`, `diffs/KICKOFF_PROMPT.md.v5-patch.diff` |
| C2 | PRODUCT lists "vision" as a non-goal; RESEARCH §17 permits conditional escalation; BENCHMARKS §9 requires a screenshot baseline; AGENTS inv. 11 cites ADR-005 for vision, but ADR-005 covers only serving | PRODUCT (visual inference forbidden) | split screenshot *capture* (allowed evidence) from *visual inference* (off for GhostAPI; preregistered escalation only); explicit baseline exemption; AGENTS points to the new ADR | ADR-009; PRODUCT, RESEARCH §2.1/§17, AGENTS inv. 11 |
| C3 | ADR-003 says the LLM is called only in `semantics/`; the baseline arms and the router need LLM calls | ADR-003 (accepted) | ADR-010 supplements ADR-003: the evaluation harness sits outside the discovery pipeline, calls LLMs only via `LLMProvider`, and imports are forbidden in both directions | ADR-010; AGENTS boundary line; ARCHITECTURE §7 |
| C4 | "Observation" means raw evidence in RESEARCH §7 but a normalized, hashed snapshot in CLAUDE | RESEARCH | `RawObservation -> PlatformObservation -> CanonicalState` everywhere | RESEARCH §7/§8/§14/§15; CLAUDE glossary and pipeline; ARCHITECTURE §3.2; DATA_MODEL |
| C5 | RESEARCH H6 is about reliability and/or cost, but BENCHMARKS §17.8 lets latency alone pass | RESEARCH | only reliability or success-adjusted cost can support H6; "material" is defined | RESEARCH H6; BENCHMARKS §7.10, §17.8 |
| C6 | v4 kickoff: `ghost call` is due Week 4 in the plan table but Week 5 in the CLI list | unresolved within one doc | Week 4 proves the internal runtime; Week 5 exposes and uses the `ghost call` CLI | kickoff v5 patch; API.md §7 |
| C7 | H5 requires automatic rebinding, but AGENTS bans LLMs in `gir/runtime` | AGENTS | deterministic runtime; semantic proposals only in `semantics/`; activation only after deterministic verification; scoped and budgeted | ADR-011; AGENTS; ARCHITECTURE §6; RESEARCH §16.3 |
| C8 | ADR-004 is still "proposed" but is already operative; it says "pool trials", while BENCHMARKS requires macro and micro aggregates | BENCHMARKS | amend ADR-004 (still proposed, so editable) to match BENCHMARKS and strata; accept | DECISIONS ADR-004 |
| C9 | AGENTS rule 7 (files < 500 lines) vs RESEARCH (855) and BENCHMARKS (925) | AGENTS (literal) | "source files" (docs exempt) | AGENTS rule 7 |
| C10 | RESEARCH §10 delegates UNKNOWN-risk rules to a SECURITY.md that does not exist | undefined | UNKNOWN mutations fail closed until you approve a policy | RESEARCH §10; SECURITY §4 |
| C11 | Internal verification and semantic correctness are conflated (BENCHMARKS §6 "experiment oracle confirms the intended outcome"; §13 one oracle for everything) | none | split into §13.1 internal behavioral verification and §13.2 hidden adjudication; sealed capture; publication snapshot | RESEARCH §13; BENCHMARKS §6, §7.2, §13.1 |
| C12 | No rule says who turns benchmark tasks into `ghost call` invocations (a human doing it is hidden assistance) | none | Evaluations A/B/C; frozen router; no human routing | BENCHMARKS §9.5; AGENTS baseline fairness |
| C13 | "Configured LLM budget" is referenced but undefined | none | ADR-013 caps; no paid calls without an approved budget config | ADR-013 |
| C14 | AGENTS "every trial starts from a clean snapshot" vs H3 state variation | AGENTS | consistent reading: clean snapshot, then a preregistered stratum setup; AGENTS line clarified | AGENTS trial protocol; BENCHMARKS §6.1 |
| C15 | ARCHITECTURE, API, DATA_MODEL, SECURITY, `task-workflow` skill, and IDEAS.md are missing | n/a | drafts in `proposed/`; IDEAS.md created empty at commit 6f | `proposed/docs/*`, `proposed/.claude/skills/*` |
| C16 | No Git repository, but manifests require a SHA | n/a | init plan | `01-repo-init-plan.md` |
| C17 | My earlier Week 0 plan named `brew install cirruslabs/cli/tart`, the Cirrus base image, and `--net-host`. Verified today: Tart moved to `openai/tart` (FSL-1.1-ALv2; install `brew install openai/tools/tart`); the Cirrus base template runs `update-tcc-database.sh`; `--net-host` needs a macOS 26 host | verified sources | vanilla pinned IPSW; no TCC edits; network options re-evaluated for a macOS 14.6 host | ADR-012; `vm-storage-network-preflight.md` |

## Lower-authority residue (not edited; superseded by the authority order)

To keep the kickoff patch minimal, these v5 passages are left as written. Where they differ from the approved higher-authority docs, those docs govern:

- v5 §5: element-handle example `ax:18273`. RESEARCH §14 now uses a neutral, generation-scoped handle.
- v5 §10: "raw observation / canonical tree". RESEARCH §7 now defines three levels.
- v5 §17: "AX execution + visual verification". Visual inference by GhostAPI is gated by ADR-009.
- v5 §22–23: "simple raw computer-use agent" and `ceil(D / (B - G))`. BENCHMARKS §9–§10 now define diagnostic arms and the full cost model.
- v5 §24/§25: manifest and freeze lists. BENCHMARKS §5 and RESEARCH §18 now add fields.

If you prefer, these can be patched in v5 too. That would be a small, separate diff.
