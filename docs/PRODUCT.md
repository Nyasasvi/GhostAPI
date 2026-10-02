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
`ghost learn <unseen app>` → ≥5 verified capabilities → `ghost call` runs them reliably. No app-specific code, on held-out apps, compared against a screenshot computer-use baseline, with one drift recovery.

## Non-goals (for now)
REST/MCP serving, SDKs, web apps, Windows/Linux, canvas-heavy apps, vision, a hosted service, a UI, multi-agent orchestration, anything with network side effects.

## Success metric
**Research phase:** the Week 6 targets on 3 held-out apps (≥5 useful capabilities per app, ≥90% precision, ≥90% observed reliability at N≥20 with intervals reported, a measurable advantage over the baseline, one drift recovery).

**Proof users care (after the gate):** at least 3 external agent developers run `ghost learn` on an app of *their* choice and call a learned capability from their own agent. *Define a concrete number and time window before launching.*

## Kill pass
Before Week 1, the agent answers: *"Try to kill this idea. Which assumptions, if false, make GhostAPI fail or not matter? For each, what's the cheapest experiment that would tell us early?"* The answers go below, and the ones worth testing become tasks.

### Assumptions under attack
| # | Assumption | Why it might be false | Cheapest early test | Status |
|---|---|---|---|---|
| | | | | |
