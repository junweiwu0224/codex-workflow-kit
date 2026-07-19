# Kali Reverse Profile Rules (V4.2)

> This file is a platform supplement to the root V4.2 reverse rules. It does
> not grant authorization, inject client-global rules, install packages, or
> start services merely because it was read.

## Scope

Before network probing, exploitation, credential use, package installation,
service startup, or writes outside the workspace, record the target, allowed
scope, approvals, external effects, and acceptance checks in the active Task
Contract. User-provided files and CTF/sandbox artifacts may be analyzed
offline in the workspace. Ambiguous scope stops at read-only analysis.

## Kali routing

1. Read the root reverse router and skills/routing.md.
2. Read the selected sub-skill only as needed.
3. Check skills/tool-index.md before selecting a command.
4. Use kali/scripts/bootstrap-reverse.sh only for an approved capability.
5. Run deterministic verification and report unverified platform or target steps.

## Package and service boundary

- The Kali bootstrap consumes the reverse lock where enforcement is available.
- apt installs are blocked unless REVERSE_ALLOW_UNPINNED_PLATFORM_PACKAGES=1
  is explicitly set.
- kali/scripts/quick-setup.sh is a legacy convenience script and is
  fail-closed by default.
- MCP registration, config writes, service startup, and index refresh are
  external effects; request approval and record them before execution.
- The PentestSwarm container fallback remains blocked until a digest is
  independently verified.

Completion is the approved acceptance criteria and evidence. Do not write
global configuration, journal entries, or reports by ritual.
