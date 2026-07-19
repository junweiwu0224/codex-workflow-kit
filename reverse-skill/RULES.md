# Reverse Engineering and Security Routing Rules (V4.2)

> This file is a domain reference for the optional reverse profile. The global
> `AGENTS.md`, Policy Router, Task Contract, and the active Codex surface remain
> authoritative. Reading this file never grants authorization or permission to
> modify global configuration, install packages, contact an external target, or
> write outside the approved workspace.

## Scope gate

Before active security work, establish:

- the target and allowed scope;
- whether the work is offline/local, CTF/sandbox, or an explicitly authorized external engagement;
- network, credential, package-install, production, and external-write boundaries;
- required approvals, rate limits, data handling, and acceptance checks.

Offline analysis of user-provided files may proceed in the workspace when no
external effect is needed. External probing, exploitation, credential use,
persistence, service startup, package installation, or writes outside the
workspace require an approved Governed Task Contract. If a boundary is unclear,
stop at safe read-only analysis and ask for the missing decision.

## Routing

1. Read the installed `skills/tool-index.md` or its template without assuming
   paths.
2. Read `skills/routing.md` and select one entry sub-skill.
3. Read that sub-skill's `SKILL.md` and only the references needed for the task.
4. Keep one workflow Driver for the current transition; domain skills are
   overlays and security controls are guardrails.
5. Run deterministic checks and hand off to an independent verifier when the
   result is subjective, high-risk, or externally visible.

## Tooling and supply chain

- Use the repository's locked bootstrap only after the Task Contract permits
  installation. Do not replace it with an unpinned `brew`, `apt`, `pip`,
  `npm`, `git clone`, or Docker latest command.
- POSIX platform package installation is disabled unless
  `REVERSE_ALLOW_UNPINNED_PLATFORM_PACKAGES=1` is explicitly set.
- The legacy Kali quick setup is fail-closed by default.
- The Windows compatibility reverse bootstrap is disabled unless
  `REVERSE_ALLOW_UNPINNED_WINDOWS_BOOTSTRAP=1` is explicitly set; this is a
  manual-risk override and not Windows reproducibility evidence.
- Refreshing a tool index, writing MCP configuration, starting a service, or
  creating a report outside the current workspace is an external write and
  requires the corresponding approval.

## Completion and evidence

A task is complete when its approved acceptance checks pass and the result
states what was verified, what was not verified, and what side effects occurred.
Reports, diagrams, journals, and durable handoffs are created only when the
Task Contract or project workflow requires them. Never write a client's global
configuration merely because this file was read.
