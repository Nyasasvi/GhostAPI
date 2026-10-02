# 25. Remaining human approval gates

Nothing below has been done. Each item needs your explicit decision. IDs refer to `03-change-register.md` (CR-xx) and `01-repo-init-plan.md`.

## A. Repository

| ID | Decision | Recommendation |
|---|---|---|
| G-A1 | Run the init plan (`git init -b main`, `.gitignore`, commit 1 = build kit as received, commit 2 = this proposal package) | approve |
| G-A2 | v5 transcription is accurate (diff `reference/KICKOFF_v5_as_supplied.md` against your source) | you verify |

## B. Documents (applied per group only after approval; you may approve partially)

| ID | Group | Includes |
|---|---|---|
| G-B1 | Kickoff v5 + Week 4/5 `ghost call` patch; README → v5 | CR-21 |
| G-B2 | `RESEARCH.md` v0.2 | CR-01, 02, 03, 04, 06, 07, 08, 10, 11, 14, 15, 16, 17, 18 |
| G-B3 | `BENCHMARKS.md` v0.2 | CR-03 … CR-13, CR-15, CR-18 |
| G-B4 | `PRODUCT.md` (human-owned): MVP baseline wording, vision paragraph, success metric, kill-pass rows | CR-14, CR-22 |
| G-B5 | `AGENTS.md` + `CLAUDE.md` | CR-01, CR-14, CR-20 |
| G-B6 | `DECISIONS.md`: amend + accept ADR-004; add ADR-007 … ADR-014 (status "proposed"; accept each individually) | CR-19, 23, 24 and the ADRs |
| G-B7 | New `ARCHITECTURE.md`, `API.md`, `DATA_MODEL.md` (incl. 3 added tables: `publication_snapshot`, `approval`, `llm_call`), `SECURITY.md` | |
| G-B8 | `.claude/skills/task-workflow/SKILL.md` + empty `IDEAS.md` | |

## C. New numeric values (thresholds unchanged; these are *new* gates)

| ID | Value | Proposed | Alternatives |
|---|---|---|---|
| G-C1 | Necessary-parameter recall target | ≥ 0.80 | ≥ 0.90; report-only (weaker) |
| G-C2 | Strata allocation | 4 × {S0 clean, S1 relaunch, S2 window/focus, S3 entity population, S4 preference/modal} | 5 × 4 strata (drop S4); different weights |
| G-C3 | Concentration rule | at most 1 failure per stratum | report-only |
| G-C4 | Futility stop | stop at 3 failures (or 2 in one stratum) | none (costs about 3.5 VM-hours per app) |
| G-C5 | Entity usefulness | correct-resolution ≥ 0.80 on the resolvable set; 0 unsafe resolutions; ≥ 10 + 10 requests per app | ≥ 0.70; report-only |
| G-C6 | Rebinding budget | ≤ 25% of `D_search` (actions, wall-clock, LLM $) | 50%; report-only |
| G-C7 | H6 reliability materiality | ≥ +10 pp, with the 95% Newcombe interval of the difference excluding 0 | ≥ +5 pp; interval-only |
| G-C8 | H6 cost materiality | ≤ 50% success-adjusted cost, ≤ 5 pp reliability loss, break-even ≤ horizon | ≤ 70% |
| G-C9 | Usage horizon | 1,000 successful calls per app over 90 days, 1 drift event | 100 calls; 10,000 calls |
| G-C10 | Shadow rates | $1 per VM-hour; $60 per human-hour | your own rates |
| G-C11 | Baseline Ns (held-out apps) | B1 ≥ 10, B2 ≥ 5, B4 ≥ 10, B3 ≥ 5 if run; development N ≥ 10 | all ≥ 10 (+about 2 VM-hours and $20–50 per app) |
| G-C12 | Baseline per-run budget | ≤ 30 steps, ≤ 10 min, ≤ $2 | your values |
| G-C13 | AXI-1 vision-escalation criterion | ≥ 30% of predeclared useful capability families blocked by AX absence on ≥ 2 development apps | different threshold; never escalate |
| G-C14 | `INVALID_INFRA` replacement limit / indeterminate rule | at most 3 attempts per slot; > 10% `INFRA_EXHAUSTED` means indeterminate | 2 attempts; 5% |

## D. Budget (no paid model call before this is approved)

| ID | Proposal (ADR-013) |
|---|---|
| G-D1 | Development semantic caps: $5 per run, 40 calls per session, 12k input tokens per packet, 8k max output, $15 per day, $50 per week |
| G-D2 | Development baseline probes: $40 per week from Week 4 |
| G-D3 | Benchmark caps (frozen at Week 5, per app): semantic $25, router $3, baselines $150 |
| G-D4 | Model tier used identically by GhostAPI and the baselines: current Opus tier (research-phase ceiling about $900) or Sonnet tier (about half) |

## E. Environment and security (no action taken)

| ID | Decision | Recommendation |
|---|---|---|
| G-E1 | Free disk: ≥ 90 GB to start, ≥ 150 GB recommended; or a dedicated APFS external SSD for `TART_HOME` | free internal space if possible |
| G-E2 | Install Tart (`brew install openai/tools/tart`) and dev tools (swiftlint, gitleaks; ruff, mypy, and pytest through uv) | approve after G-E1 |
| G-E3 | Download a pinned macOS 14.x IPSW (about 13–16 GB) from Apple's servers | approve after G-E1 |
| G-E4 | Create `ghost-base-build`; you complete Setup Assistant (no Apple ID) and grant Accessibility + Screen Recording to the bridge; sealing `ghost-base-v01` is an AGENTS gate | your manual steps |
| G-E5 | Network isolation: option B (guest filter, no host privilege) now | approve B; decide C (Softnet, needs SUID/sudo) separately |
| G-E6 | Self-signed code-signing identity on the host for the bridge (a keychain item; no system security change) | approve, or choose ad-hoc signing and accept re-granting permissions after rebuilds |
| G-E7 | Clone deletion policy: delete trial clones only after artifact hashes are committed; quarantine otherwise | approve |
| G-E8 | CI location: local `make check` only (recommended now), or a private GitHub repository with Actions (an external service; the holdout denylist check stays local) | local-only for now |

## F. Decisions you owe later (preregistered deadlines)

| ID | Decision | Deadline |
|---|---|---|
| G-F1 | Development apps (2–3 offline apps of your choice; well-known apps are fine) | before Week 1 |
| G-F2 | Eligible-population definition and screening procedure | before holdout selection (Week 4) |
| G-F3 | H5 route: fixture / real-app / both | before the Week 5 freeze |
| G-F4 | Run B3 or not | before the Week 5 freeze |
| G-F5 | Per-holdout task suites, oracle bundles (with capture steps and necessary parameters), entity request sets, S3/S4 seed variants, drift mechanism | before each reveal |
| G-F6 | Preregistered schedule rules (`feasibility.md` §5) | now, with G-B3 |
| G-F7 | Whether internal verification may use a generic probe-token filesystem check (hash the guest home tree before and after an action; require the unique probe in a changed file) as a second channel, for verification only and never for discovery. Default if undecided: not used, and the same-channel limitation is recorded per trial. | before Week 3 |

## G. Still not started (per your instruction)

Bridge, VMs, Tart, image downloads, TCC changes, host storage changes, sudoers/SUID/firewall/routing, future-week scaffolding, LLM dependencies, paid calls, semantic inference, GIR runtime, rebinding, baseline agents, fixture code, Week 1, holdout selection, threshold changes.
