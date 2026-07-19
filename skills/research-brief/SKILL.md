---
name: research-brief
description: Use when evaluating current external options such as GitHub repositories, skills, MCP servers, hooks, subagents, APIs, models, tools, libraries, standards, pricing, release status, or ecosystem recommendations.
---

# research-brief

## Goal

Turn current research into a short, evidence-backed recommendation. This skill is for selecting, promoting, holding, or rejecting options; it does not install tools or change configuration by itself.

## When to Use

Use when:

- Comparing GitHub repositories, skills, MCP servers, hooks, subagents, plugins, libraries, tools, models, APIs, or vendors.
- The user asks for latest, high-star, current ecosystem, best option, recommendation, or "look it up".
- A workflow candidate may become a global skill, repo rule, hook, MCP pilot, memory entry, or release dependency.
- Facts may have changed: docs, releases, security status, pricing, maintainers, compatibility, APIs, legal/licensing, standards.

Do not use for repo-local implementation details that can be answered from source files and tests alone.

## Workflow

1. Define the decision.
   - What decision will this research support?
   - What would be promoted, held, rejected, or tested as a pilot?
   - What current local design constraints apply?

2. Gather sources.
   - Prefer primary sources: official docs, repository README, release notes, source, standards, advisories, current repo files.
   - For OpenAI/Codex facts, use official OpenAI docs/manual routes when available.
   - Use local evidence first when evaluating this workflow kit: `WORKFLOW-REVIEW.md`, `docs/V2-ADOPTION-EVIDENCE.md`, repo templates, tests, and current installed skills.

3. Grade evidence.
   - Strong: primary source plus local fit evidence or working verification.
   - Medium: primary source only, or local evidence without a current external check.
   - Weak: secondary source, stale cache, rate-limited source, marketing copy, or inference.
   - Missing: source unavailable; do not pretend it was checked.

4. Compare fit, not popularity.
   - Scope and trigger clarity.
   - Conflict with Superpowers, existing skills, AGENTS rules, hooks, MCP, repo docs, or user red lines.
   - Side effects: external writes, auth, background services, network, indexing, credentials, production, cost.
   - Portability: can it live in `outputs/codex-workflow-kit` and install safely on a new machine?
   - Verification and rollback.

5. Recommend one of:
   - Promote now: clear repeated benefit, low false triggers, no better lower-level mechanism.
   - Pilot: plausible benefit but needs bounded trial and usage evidence.
   - Repo-local only: useful in specific projects, not global.
   - Hold: insufficient evidence or unclear payoff.
   - Reject: conflicts, high risk, too broad, duplicate, or better as tool/script/MCP/hook.

## Output Shape

```text
Research brief:
- Decision:
- Sources checked:
- Evidence quality:
- Options:
  - Promote / Pilot / Repo-local / Hold / Reject:
- Recommended next step:
- Risks and non-goals:
```

## Boundaries

- Do not install, enable, authenticate, index, deploy, publish, or write external state as part of the brief.
- Do not recommend a global skill when a repo `AGENTS.md`, deterministic script, hook candidate, MCP pilot, subagent prompt card, or existing plugin is the smaller surface.
- If a source is blocked, rate-limited, stale, or unavailable, say that directly and lower confidence.
