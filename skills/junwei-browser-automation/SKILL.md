---
name: junwei-browser-automation
description: Use when browser automation, web UI inspection, Playwright workflows, MCP-vs-CLI browser tool routing, accessibility snapshot reasoning, local app verification, scripted walkthroughs, product flow capture, or repeatable frontend/browser smoke checks are needed. Trigger for Playwright MCP evaluation, browser workflow automation, localhost UI inspection, DOM/accessibility-tree verification, self-healing browser steps, or recording product walkthrough inputs before demo/video work.
risk: medium
source_repo: personal-workflow-kit
source_type: curated-local
date_added: 2026-06-22
setup: optional-mcp-or-cli
write_surface: task-dependent
auth: task-dependent
network: local-by-default
status: pilot
---

# Junwei Browser Automation

## Goal

Use this skill to choose and operate the smallest safe browser automation surface for Codex work. It distills the useful parts of `microsoft/playwright-mcp` into a personal workflow: structured page inspection, repeatable browser actions, and evidence-producing UI checks, without default-enabling any MCP server.

## Tool Routing

Prefer the lowest-cost tool that proves the claim:

1. Local tests or DOM contracts for deterministic component behavior.
2. In-app Browser for localhost, file URLs, screenshots, manual UI checks, and Codex-side visual QA.
3. Existing project Playwright/Cypress/Vitest browser tests when the repo already has them.
4. Playwright CLI or one-off scripts for repeatable local flows, screenshots, traces, or recordings.
5. Playwright MCP only when persistent browser state, structured accessibility snapshots, exploratory page interaction, or self-healing multi-step inspection is worth the extra tool/schema/context surface.
6. Chrome only when the user explicitly requires Chrome or the task depends on existing Chrome login state, cookies, extensions, or open tabs.

Read `references/tool-routing.md` before enabling or recommending any MCP configuration.

## MCP Intake Position

`microsoft/playwright-mcp` is a strong pilot candidate, not a default install. Current source evidence: GitHub repo `microsoft/playwright-mcp`, Apache-2.0, high popularity, Node.js 18+ requirement, MCP server via `npx @playwright/mcp@latest`, and README guidance that CLI + skills may be more token-efficient for coding agents while MCP remains useful for persistent state and rich introspection.

For this workflow, preserve that upstream distinction as `CLI+SKILLS` first, Playwright MCP second: MCP is valuable when its persistent browser state and structured accessibility snapshots beat the cost of tool schemas and extra context.

Do not add `codex mcp add playwright ...`, edit `~/.codex/config.toml`, start a daemon, or install browser dependencies unless the user explicitly asks for that setup. Record the proposed config and rollback path first.

## Workflow

1. Define the proof needed: visual rendering, DOM state, accessibility tree, interaction path, screenshot, trace, recording, or regression test.
2. Identify the target: URL, route, viewport, auth/session needs, fixtures, and allowed data.
3. Pick the tool route using the table above.
4. Run read-only inspection first. Avoid form submissions, purchases, destructive actions, permission changes, or external writes without explicit confirmation.
5. Capture evidence: command output, screenshot path, trace path, accessibility snapshot summary, or test result.
6. If the flow is valuable beyond the current task, suggest repo-local test or script promotion rather than a global MCP default.

## Boundaries

- Do not use browser automation to bypass auth, scrape private data, submit production forms, buy things, change account settings, or alter permissions without explicit user confirmation.
- Do not assume MCP is better than CLI or tests. Compare overhead, persistence needs, and evidence quality.
- Do not leak cookies, local storage, tokens, screenshots with secrets, or private user data into logs or final responses.
- Do not silently downgrade from in-app Browser to Chrome for local UI QA.
- Do not run unbounded crawls. Set target routes, step budgets, timeouts, and stop conditions.

## Verification

- For frontend verification, include desktop and mobile when layout risk exists.
- For automation scripts, prefer dry-run or fixture environments first.
- For MCP pilots, document: config, permission surface, auth/session source, rollback, evidence produced, and why tests/CLI were insufficient.
- For product demo recording inputs, confirm route, viewport, cursor timing, sensitive data masking, and output path before recording.

## Output Shape

```text
Browser automation result:
- Goal:
- Tool route:
- Target:
- Evidence:
- Safety boundary:
- Promotion decision:
- Residual risks:
```
