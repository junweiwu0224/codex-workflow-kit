---
name: security-review
description: Use when code, configuration, dependencies, hooks, MCP/plugin setup, CI, auth, permissions, secrets, user data, payments, production settings, external writes, or trust boundaries need security review.
risk: medium
source_repo: personal-workflow-kit
source_type: curated-local
date_added: 2026-06-07
setup: none
write_surface: task-dependent
auth: task-dependent
network: task-dependent
status: active
---

# security-review

## Goal

Review security-sensitive changes with evidence from the current repo and current primary sources. This skill is a focused AppSec review, not a penetration test, scanner replacement, or permission to touch production.

## When to Use

Use for:

- Auth, authorization, RBAC, sessions, cookies, JWT/OAuth, API keys, webhooks, CORS, CSP.
- User data, PII, logging, uploads, downloads, file paths, serialization, templating, SQL/query construction, shell/exec, SSRF, crypto.
- Payments, billing, production config, CI/CD, deployment, GitHub Actions, hooks, MCP servers, plugins, install scripts, external writes.
- Security alerts, CodeQL/Semgrep/scanner findings, reported vulnerabilities, threat modeling, OWASP/API security review.
- L/XL tasks that cross trust boundaries, permission models, data isolation, or external systems.

Do not use for normal code review with no security surface. Do not test third-party systems unless the user explicitly confirms authorization and scope.

## Workflow

1. Identify the reviewed surface.
   - Inspect the user request, local diff, touched files, repo `AGENTS.md`, security docs, and tests.
   - Name the trust boundary: caller, callee, data, privilege, external system, or execution context.

2. Build a threat-focused checklist for this diff only.
   - Actor gate: who can trigger the code path, workflow, hook, MCP/tool, install script, or external write; whether forks, untrusted users, copied prompts, or third-party content can influence it.
   - Inputs and validation.
   - Authn/authz and tenant/data isolation.
   - Secret handling and logging.
   - Injection or execution paths.
   - Prompt injection and instruction mixing when external docs, web pages, issues, PR comments, tool output, model output, or repo content can influence an agent/tool action.
   - Shell quoting and subprocess boundaries; prefer structured argv APIs, quote untrusted values, and reject string-built shell commands for user-controlled input.
   - Network, file, webhook, parser, serialization, or template exposure.
   - CI/plugin/hook/MCP/install-script trust.
   - Rollback, auditability, and least privilege.

3. Verify with evidence.
   - Read source and tests directly; do not rely on memory.
   - For changing standards, CVEs, APIs, platform behavior, or security guidance, use current primary sources.
   - Prefer local/static checks first. Ask before destructive, production, credential, deployment, migration, payment, or permission-changing actions.

4. Report findings like a code review.
   - Severity: Critical, High, Medium, Low, or Info.
   - Evidence: exact file/path, behavior, and data path.
   - Exploit or misuse path when applicable.
   - Minimal fix and verification command.
   - Residual risk or why no issue was found.

5. Escalate durable decisions.
   - Use `decision-record` when accepting risk, changing permission models, replacing auth/security libraries, disabling alerts, or creating a long-term exception.
   - Use `debug-loop` when a security scan or verification command fails.
   - Let `completion-review` confirm this review was completed before final delivery.

6. Do a sandbox-last-step check before final delivery.
   - Confirm no secret values were copied into logs, docs, tests, screenshots, prompts, memory, or final response.
   - Confirm no production config, permissions, accounts, billing, deployment, database, migration, token, key, webhook, or external write changed without explicit user approval.
   - For hooks, MCP servers, plugins, CI actions, or install scripts, confirm the manifest/command has bounded permissions, timeout, path scope, and rollback.
   - If the review depended on a tool or scanner, verify findings against source files before treating them as facts.

## Output Shape

```text
Security review:
- Scope:
- Findings:
  - [Severity] File/path: issue, evidence, fix, verification.
- No-issue notes:
- Verification:
- Residual risk:
```

## Boundaries

- Default to read-only review and minimal local checks.
- Do not expose secrets in the response.
- Do not rotate keys, change production config, run migrations, deploy, alter permissions, or perform external writes without explicit user approval.
- Do not install large security skill packs or scanners just to complete a review; recommend repo-specific tooling only when repeated evidence supports it.
