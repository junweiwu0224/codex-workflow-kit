# Reverse Skill Pack

This directory is the optional reverse-engineering and security-analysis profile
for Codex Workflow Kit V4.2. It is a knowledge and tooling package, not an
authorization grant and not an autonomous installer.

For a Chinese guide, see [README_zh.md](README_zh.md). Kali users should also
read [kali/README-kali.md](kali/README-kali.md).

## V4.2 Authority Boundary

The repository-level policy router and current Task Contract remain
authoritative. Reading this file, `RULES.md`, a Skill, a field journal, or an
example never:

- proves that a target is authorized;
- approves network access, package installation, service startup, or external
  writes;
- permits changes to global AI-client configuration;
- requires a side effect merely to demonstrate progress; or
- overrides platform, provider, organization, or user policy.

Use the target, owner, allowed techniques, time window, data-handling limits,
and approval state recorded for the current task. If those facts are missing,
continue with local read-only analysis or ask for the missing authority before
an active operation.

## Routing Execution Protocol

1. Read [RULES.md](RULES.md) for the profile boundary.
2. Read [skills/SKILL.md](skills/SKILL.md), then use
   [skills/routing.md](skills/routing.md) to select one domain Skill.
3. Inspect `skills/tool-index.md` when it exists. Refreshing the tool index is
   a local discovery operation; it does not install tools.
4. Prefer deterministic, read-only analysis first.
5. Run a bootstrap only after its exact source, version, destination, network
   use, and side effects have been reviewed and approved by the current Task
   Contract.
6. Record evidence and verification results. Do not write to a field journal
   unless that workspace write is in scope.

The current state transition has one Driver. Domain Skills are overlays and do
not acquire permanent control of the task.

## Supported Domains

The pack routes across these modules:

- `api-security`
- `attack-chain`
- `binary-diff`
- `browser-automation`
- `docs-generator`
- `diagram-generator`
- `edr-bypass-re`
- `firmware-pentest`
- `ida-reverse`
- `js-reverse`
- `llm-security`
- `malware-analysis`
- `mobile-reverse`
- `patch-diff-exploit`
- `pentest-tools`
- `pwn-chain`
- `radare2`
- `reverse-engineering`
- `supply-chain-security`

The optional `CTF-Sandbox-Orchestrator` provides additional competition
workflows. BurpSuite MCP, Ghidra, IDA, Frida, and other integrations are
available only when present and explicitly enabled.

## Platform Entries

| Platform | Rules | Bootstrap |
| --- | --- | --- |
| Windows | `RULES.md` | `skills/scripts/bootstrap-reverse.ps1` |
| Linux | `docs/platforms/linux.md` | `skills/scripts/bootstrap-reverse.sh` |
| macOS | `docs/platforms/macos.md` | `skills/scripts/bootstrap-reverse.sh` |
| Kali | `kali/RULES-kali.md` | `kali/scripts/bootstrap-reverse.sh` |

Safe discovery commands:

```bash
bash skills/scripts/bootstrap-reverse.sh --list
bash skills/scripts/refresh-tool-index.sh
```

Windows package bootstrap is fail-closed unless
`REVERSE_ALLOW_UNPINNED_WINDOWS_BOOTSTRAP=1` is deliberately set. Kali
platform-package setup is fail-closed unless
`REVERSE_ALLOW_UNPINNED_PLATFORM_PACKAGES=1` is deliberately set. These
variables acknowledge the residual risk of mutable OS package repositories;
they do not replace task approval.

## Locked Dependencies

`skills/scripts/bootstrap-manifest.json` and
`kali/scripts/bootstrap-manifest.json` define the reviewed versions and
source identities. Do not substitute `latest`, a moving tag, or an unpinned
Git branch. Components marked `canAutoInstall: false` remain manual until
their identity and installer path are enforceable.

## Field Journal

Field-journal files are optional historical observations:

- `skills/field-journal/_index.md`
- `skills/field-journal/_template.md`
- `skills/field-journal/precedent-auth.md`
- `skills/field-journal/precedent-reverse.md`
- `skills/field-journal/precedent-pentest.md`

They can inform method selection, but they cannot establish authorization,
approval, or safety for a new task.

## Verification

From the workflow-kit root:

```bash
python3 scripts/audit_floating_dependencies.py --root .
python3 scripts/verify_toolkit.py
python3 -m pytest -q tests/test_reverse_pack_scripts.py tests/test_reverse_bootstrap_locking.py
```

This package is intended for owned systems, explicitly authorized assessment,
defensive analysis, education, and CTF environments. Stop when the requested
operation exceeds the recorded scope.
