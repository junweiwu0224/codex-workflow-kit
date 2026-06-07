---
name: security-review
description: Use when code, configuration, dependencies, hooks, MCP/plugin setup, CI, auth, permissions, secrets, user data, payments, production settings, external writes, or trust boundaries need security review.
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
   - Inputs and validation.
   - Authn/authz and tenant/data isolation.
   - Secret handling and logging.
   - Injection or execution paths.
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
