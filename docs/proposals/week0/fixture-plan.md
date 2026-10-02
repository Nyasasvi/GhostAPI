# 18. Configurable synthetic research fixture: plan

**Status:** plan only; nothing built. Governed by `RESEARCH.md` §4.4 (proposed): **one** fixture, used for mechanics, adversarial, and falsification tests, and **never** as evidence of generalization.

## 1. Purpose and limits

- It tests mechanics that real development apps can't provide on demand: true duplicates, archive-vs-delete ambiguity, drift classes D1–D7, prompt-injection text, and misleading risk labels.
- It is a "bespoke app unknown to pretrained models", used in the Week 3 contamination ablation (kill-pass K10).
- **Limits:** written by the implementer, so it reflects the implementer's assumptions about UIs. Every result is labeled "fixture only". It is timeboxed so it can't displace GhostAPI work.

## 2. Shape

- One small AppKit app (standard `NSTableView`, `NSToolbar`, `NSMenu`, sheets) built with the Command Line Tools, installed only into development seeds.
- **Scenario config:** a JSON file baked into each fixture seed selects toggles at launch, so each scenario is a separate frozen seed and never an in-app switch that GhostAPI could flip.
- **Development oracle:** the fixture writes its model state to a JSON file in its container. Only the development harness and adjudication read it. Discovery code never does (same invariant as the sealed adjudication store).
- **No-app-specific-code rule:** the fixture's name and distinctive labels go into `benchmarks/denylist.txt`, so core code and prompts can't special-case it.

## 3. Scenarios

| Scenario | Tests | When needed | Build estimate |
|---|---|---|---|
| **Core list app:** items with a title; create (toolbar button and menu command); rename; persistence to file | H1/H2/H3 mechanics; relaunch verification | Week 1–2 | 1.5 days |
| **Archive vs delete** (config: "Remove" archives or deletes; the visible transition is identical) | semantic identifiability (K2), false-positive postcondition (K5) | Week 3–4 | 0.25 day |
| **Duplicates / rename / reorder** seeds | H4 safety and usefulness (K8) | Week 4 | 0.25 day (seeds) |
| **Risk adversarial:** dangerous-looking benign control; benign-looking dangerous control; submit-on-enter field; confirm sheet on/off | risk evals (≥50 cases), K13 | Week 2 | 0.5 day |
| **Prompt-injection text** in a row title and a label | SECURITY prompt-injection evals | Week 3 | included above |
| **Drift toggles D1–D7:** label, hierarchy, reorder, menu↔toolbar, distractor, wrapper, extra confirm step | H5 mechanics, rebinding budget, rediscovery comparison (K9) | Week 4 | 1 day |
| *Extensions only if a logged failure needs them:* typed/conditional fields (date, enum, number, checkbox), delayed persistence, long virtualized list, hidden mode (same visible tree, different behavior) | H2 recall (K6), state aliasing (K3) | on demand | about 0.25–0.5 day each |

**Timebox:** core + risk + drift ≤ **3.5 engineering days** spread over Weeks 1–4. Any extension needs a logged reason and counts against the same budget. A second fixture needs logged evidence and your approval.

## 4. Not done with the fixture

- It does not replace development apps for AX-coverage measurement (AXI-1 excludes the fixture).
- It is not used for H6 claims, H5 real-app claims, or any headline metric.
- It is not tuned until GhostAPI passes on it.
