# Browser Tool Routing

Use this reference before enabling or recommending Playwright MCP, browser scripts, or browser-based verification.

## Route Selection

| Need | Preferred route | Why |
|---|---|---|
| Prove component behavior | Existing unit/component tests | Deterministic and cheap |
| Inspect localhost UI visually | in-app Browser or frontend-qa | Fits Codex Desktop local verification policy |
| Repeat a flow in CI | Repo Playwright/Cypress test | Durable, reviewable, repo-local |
| Capture screenshots/traces locally | Playwright CLI or one-off script | Lower context cost than MCP |
| Explore page structure iteratively | Playwright MCP pilot | Structured accessibility snapshots and persistent browser state |
| Use existing logged-in Chrome state | Chrome plugin, explicit user request only | Depends on user cookies/extensions/tabs |

## Playwright MCP Pilot Checklist

Before adding or using an MCP config, record:

- Target repo and task.
- Why tests, CLI, or in-app Browser are insufficient.
- MCP command and args.
- Whether `npx @playwright/mcp@latest` would fetch packages.
- Required Node.js version.
- Browser/session/auth source.
- Allowed tools and denied tools.
- Timeout and step budget.
- Rollback: remove MCP config and stop any spawned process.

## Safety Rules

- Treat browser state as sensitive. Cookies, local storage, screenshots, traces, and accessibility snapshots may contain private data.
- Use local fixtures or test accounts for forms.
- Prefer read-only navigation before any mutation.
- Stop at payment, account, permission, production config, or destructive action boundaries and ask for confirmation.
- Do not run broad crawls. Route, viewport, and stop condition must be explicit.

## Evidence Quality

Strong evidence:

- Passing repo browser test.
- Screenshot/trace tied to the affected route and viewport.
- Accessibility snapshot summary with route and state.
- Recorded flow using test data and masked secrets.

Weak evidence:

- "It loaded" without route, viewport, or state.
- Browser output from a different page.
- Screenshot with hidden console errors.
- MCP success without checking the user-visible state.

