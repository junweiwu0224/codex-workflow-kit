---
name: skill-plugin-intake-review
description: Use when deciding whether an external skill, plugin, MCP server, hook, subagent prompt, workflow pack, or component should be promoted, piloted, kept repo-local, held, or rejected before absorption into Codex workflow kit or repo rules.
risk: medium
source_repo: personal-workflow-kit
source_type: curated-local
date_added: 2026-06-11
setup: none
write_surface: none-by-skill
auth: none-by-skill
network: none-by-default
status: active
---

# skill-plugin-intake-review

## Goal

Review external Codex components before they are absorbed into the workflow kit, global rules, repo-template, hooks, MCP/plugin pilots, or personal skills.

This skill is an intake review. It does not install, enable, copy, authenticate, index, publish, deploy, or write external state.

## When To Use

Use when evaluating:

- External `SKILL.md` folders or skill libraries.
- Codex plugins, `.codex-plugin/plugin.json`, apps, assets, or MCP bindings.
- MCP servers or `.mcp.json` configs.
- Hook packs, agent rules, subagent prompt libraries, workflow packs, templates, scripts, or domain skill packs.
- Any candidate that might become V3.1 docs, a read-only script, a narrow skill, a repo-template rule, a hook, an MCP/plugin pilot, memory/recall guidance, or a global rule.

Do not use for ordinary package upgrades, app code review, or one-off reading of external documentation. Use `research-brief` for ecosystem comparison, `security-review` for security-sensitive trust boundaries, and `dependency-upgrade-review` for dependency/license/supply-chain changes.

## Inputs

Collect the smallest useful evidence:

- Candidate path or URL.
- Intended absorption surface: docs, script, skill, repo-template, pilot, hook, MCP/plugin, or reject.
- Local design constraints: Superpowers owns planning/TDD/phased execution; V3.1 Core does not default-enable external tools.
- Relevant files: `SKILL.md`, `plugin.json`, `.mcp.json`, hooks, scripts, README, LICENSE, package manifests.

## Workflow

1. Inspect local evidence first.
   - Read key files directly.
   - Prefer source, manifests, tests, and install scripts over README claims.
   - Do not run candidate code.

2. Run the read-only auditor when the candidate is local.

```bash
python3 scripts/audit_external_component.py /path/to/component
python3 scripts/audit_external_component.py /path/to/component --json
```

3. Score fit using `docs/external-component-intake.md`.
   - `v31_fit`
   - `user_value`
   - `portability`
   - `safety`
   - `non_overlap`
   - `evidence_quality`

4. Tag risks.
   - license
   - auth
   - side effect
   - daemon
   - network
   - install
   - Superpowers overlap
   - V2.2 conflict
   - private path / secret

5. Decide the smallest safe absorption surface.
   - promote
   - pilot
   - repo-local
   - hold
   - reject

6. Assign loading budget.
   - `DAILY`: current repo high-frequency, low-risk, clear trigger.
   - `LIBRARY`: valuable but low-frequency or domain-specific.
   - `REJECT`: conflict, unsafe, unclear license, too broad, or not portable.

## Review Checklist

- Does the trigger description start with a concrete “Use when” condition?
- Does it include negative boundaries or do-not guidance?
- Are scripts, references, examples, and assets progressively disclosed?
- Does any script install dependencies, use curl-to-shell, run Docker, start a daemon, write global config, call external APIs, or require credentials?
- Does a plugin declare apps, MCP servers, browser/account connectors, or Write capability?
- Does an MCP config expose commands, endpoints, external reads, external writes, or production-risk operations?
- Does the component duplicate Superpowers planning, TDD, phased execution, or orchestration?
- Is the license clear and compatible with a portable kit?
- Can the value be captured as docs/checklist/read-only script instead of installing the tool?

## Output Shape

```text
Skill/plugin intake review:
- Candidate:
- Evidence checked:
- Scores:
- Risk tags:
- Loading budget:
- Decision: promote / pilot / repo-local / hold / reject
- What is worth absorbing:
- How to absorb it:
- Boundaries:
- Verification:
- Open questions:
```

## Boundaries

- Do not install external skills, plugins, MCP servers, hooks, packages, binaries, Docker images, or dependencies.
- Do not enable hooks, MCP servers, memory writers, code graph indexers, daemons, dashboards, browser connectors, or external accounts.
- Do not copy GPL/unknown-license source text into the portable kit.
- Do not print secrets; rely on redacted findings.
- Do not reintroduce `implementation-plan`, planner, dispatcher, queue, or orchestrator behavior.
- Do not make a global skill when docs, a repo-local rule, a read-only script, or a pilot checklist is enough.

