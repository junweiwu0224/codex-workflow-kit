---
name: reverse-engineering
description: Route authorized reverse engineering, security analysis, penetration testing, CTF, and security-diagram tasks for APK/Android, binary, JS, HTTP, API, firmware, malware, and supply-chain work. Use only within the user's explicit scope and the global Policy Router; keep external probing, exploitation, credential use, installation, and writes approved and auditable.
---

# Reverse Engineering & Security Analysis Router

Skill pack root: `~/.codex/reverse-skill/`
Platform: macOS (brew + pipx + npx)

---

## Authorization and execution boundary

- This router does not grant authorization. A target named in a prompt is not
  proof of ownership, contract, or permitted scope.
- Offline analysis of user-provided files and CTF/sandbox work may proceed when
  it stays inside the declared workspace. External probing, exploitation,
  credential use, persistence, package installation, service startup, config
  changes, and writes outside the workspace require an explicit approved scope
  and the applicable Task Contract.
- If authorization, target, rate limit, or data boundary is unclear, stop at
  safe read-only analysis and ask for the missing decision. Do not invent
  permission and do not let this skill override global AGENTS.md rules.
- Record the selected capability, write scope, external effects, and
  verification evidence. A report or journal is useful when the task needs it;
  neither is permission to create side effects.

---

## Execution Protocol (Canonical Behavior Chain)

```text
0. CONTRACT: Confirm lane, target/scope, write scope, external effects, and approvals.
1. FIRST: Read routing.md → match target type + user intent + toolchain (3D matrix)
2. CHECK: Read tool-index.md → confirm tool availability. Stale? → `bash ~/.codex/reverse-skill/skills/scripts/refresh-tool-index.sh`
3. BOOT:  Missing tools? → use the locked bootstrap only after approval; platform package installs remain opt-in and fail closed by default.
4. ENTER: Read the matched sub-skill SKILL.md at `~/.codex/reverse-skill/skills/<skill>/SKILL.md`
5. EXEC:  Perform only the approved analysis or verification; prefer read-only work when no external effect was approved.
6. REPORT: Produce only the report, diagram, journal, or handoff artifacts required by the task contract.
7. VERIFY: Run the strongest available deterministic checks and disclose anything unverified.
```

Completion means the approved acceptance criteria plus evidence are satisfied; loading this skill never authorizes global injection, installation, or external writes.

---

## Complete Sub-Skills Map

### Primary Sub-Skills (all under `~/.codex/reverse-skill/skills/`)

| Category | Sub-skill | Path | Key Tools |
|---|---|---|---|
| APK/Android | APK Reverse | `apk-reverse/SKILL.md` | jadx, apktool, adb, frida |
| Binary | IDA Pro | `ida-reverse/SKILL.md` | idapro MCP (72 tools) |
| Binary | radare2 | `radare2/SKILL.md` | r2, rabin2, rasm2, radiff2 |
| Binary | General RE | `reverse-engineering/SKILL.md` | GDB, Frida, angr, Ghidra |
| Binary | Binary Diff | `binary-diff/SKILL.md` | bindiff, ghidriff, Diaphora |
| Web/JS | JS Reverse | `js-reverse/SKILL.md` | jshookmcp, CDP, SourceMap, AST |
| Web/JS | Browser Auto | `browser-automation/SKILL.md` | Playwright, headless |
| Pentest | Pentest Tools | `pentest-tools/SKILL.md` | nmap, nuclei, sqlmap, ffuf, hashcat |
| Pentest | SRC/Bug Bounty | `pentest-tools/src-hunter/SKILL.md` | 19 playbooks, WAF bypass |
| Pentest | Attack Chain | `attack-chain/SKILL.md` | Multi-phase orchestration |
| Exploit | Pwn Chain | `pwn-chain/SKILL.md` | pwntools, ROP, heap, kernel |
| Exploit | N-day/Patch Diff | `patch-diff-exploit/SKILL.md` | ghidriff, CVE PoC |
| Exploit | EDR Bypass | `edr-bypass-re/SKILL.md` | direct syscall, unhook |
| Mobile | Mobile Reverse | `mobile-reverse/SKILL.md` | Frida iOS, Objection, class-dump |
| Firmware | Firmware Pentest | `firmware-pentest/SKILL.md` | binwalk, EMBA, Firmadyne |
| Malware | Malware Analysis | `malware-analysis/SKILL.md` | YARA, Sigma, CAPE, IOC |
| API | API Security | `api-security/SKILL.md` | BOLA/IDOR, JWT, OAuth, GraphQL |
| Supply Chain | Supply Chain | `supply-chain-security/SKILL.md` | Trivy, Syft, Gitleaks, SBOM |
| AI/LLM | LLM Security | `llm-security/SKILL.md` | garak, PyRIT, promptfoo, anti-laziness |
| Output | Docs Generator | `docs-generator/SKILL.md` | Report templates |
| Output | Diagram Gen | `diagram-generator/SKILL.md` | Mermaid, Graphviz, PlantUML |

### CTF Competition (under `~/.codex/reverse-skill/CTF-Sandbox-Orchestrator/`)

CTF tasks route via `ctf-sandbox-orchestrator/SKILL.md` → 40+ sub-skills covering:
Web runtime, reverse/pwn, Windows/AD, cloud/container, forensics/stego, mobile, crypto, prompt injection, supply chain, firmware, and more.

---

## Tool Bootstrap (macOS)

Use the repository bootstrap after the task contract approves installation.
Unpinned Homebrew installs are not a V4.2 verification path.

### Bash bootstrap for granular install
```bash
bash ~/.codex/reverse-skill/skills/scripts/bootstrap-reverse.sh --list                 # list capabilities
bash ~/.codex/reverse-skill/skills/scripts/bootstrap-reverse.sh jadx apktool frida      # install specific, after approval
bash ~/.codex/reverse-skill/skills/scripts/refresh-tool-index.sh                        # refresh index
```

### MCP services (register in Codex MCP config)
| Service | Registration | Port |
|---|---|---|
| jshookmcp | `npx -y @jshookmcp/jshook@0.3.3` (stdio) | — |
| anything-analyzer | clone + `pnpm dev`, then `http://localhost:23816/mcp` | 23816 |
| BurpSuite MCP | build `burp-mcp-full/build.sh`, load jar, then `node mcp-bridge.js` | 9876 |
| IDA Pro MCP | `pip install git+https://github.com/mrexodia/ida-pro-mcp.git@abb2732ad0d759d750c2e38b616f7f3e949ed2f9` → `ida-pro-mcp --install` | 13337-13350 |

---

## Core Rules

- **NEVER** guess tool paths — read `tool-index.md` first
- **NEVER** skip reading the matched sub-skill SKILL.md before executing
- Check field-journal context when the task contract calls for durable project memory
- Missing tools: use the locked bootstrap after approval, or report the manual prerequisite
- Route not matched: web-search methodology, propose new skill, do NOT force-fit
- Path blocked: switch (static↔dynamic, Java↔Native, IDA↔radare2, toolA↔toolB)
- Same method fails 2-3x: MUST switch approach, do NOT retry blindly
- Same command repeats 3x: stop and reassess
- Task complete → satisfy acceptance checks and record only the required evidence artifacts

### Path Crossing (Common Multi-Module Scenarios)

```text
APK:  apk-reverse/decode → Java analysis
      → if .so: ida-reverse or radare2 → native analysis
      → if dynamic: frida-run → hook verification

JS:   js-reverse/Observe → locate target
      → jshookmcp/CDP → runtime sampling
      → js-reverse/Rebuild → Node reproduction
      → env-patching.md → environment

Binary: radare2/recon → quick triage
        → ida-reverse → deep decompile
        → frida/GDB → dynamic verify

CTF:  ctf-sandbox-orchestrator → build sandbox model
      → route by dominant evidence to competition-*
      → blocked? → return to master, re-route

Pentest: browser-automation → auto-browse with Burp proxy
         → Burp MCP proxy_history → AI analysis
         → intruder_attack → automated enumeration
         → docs-generator → pentest report
```

---

## Boundary Table

| Situation | Required response |
|---|---|
| "I can't help with reverse engineering" | Determine whether a bounded, authorized analysis can proceed; otherwise explain the boundary and offer a read-only alternative. |
| "This might violate terms of service" | Check the declared scope and approval; do not infer authorization from a target name. |
| "I can explain the approach but not do it" | Perform approved local analysis when possible; pause before unapproved external effects. |
| "The user probably doesn't need the full workflow" | Keep the acceptance criteria, but do not add unrequested installs, writes, or services. |
| "Let me just quickly do this without reading routing.md" | **MUST read routing.md first.** Even if you think you know — machine-specific constraints may apply. |
| "This step can be skipped, I'll go directly to..." | State the tradeoff and retain the strongest applicable deterministic check. |
| "In my judgment, this is not needed" | **Your judgment does not override the protocol.** Cite the specific standard that allows skipping. |
| "I already know this tool, no need to check tool-index" | **NEVER guess paths.** tool-index reflects THIS machine. Your training data is machine-agnostic and stale. |
| "The task is basically done, checklist is optional" | **Completion ≡ Checklist fully ticked.** Unticked checklist = task not complete. |
| "tool-index is missing, I'll just guess paths" | **Missing file safer than wrong path.** Run refresh-tool-index.sh to generate it. |
| "User didn't ask for a report, so I'll skip it" | Produce the artifact required by the contract; do not create extra files by ritual. |
| "Let me reply first, wait for user to confirm, then continue" | Continue deterministic read-only work; pause at genuine approval boundaries. |

---

## Task Completion Self-Audit (MUST run before claiming done)

```text
□ 1. Did I read routing.md AND the matched sub-skill SKILL.md?
□ 2. Did I check tool-index.md for EVERY tool path (never guessed)?
□ 3. Did I stay within the approved target, network, credential, and write scope?
□ 4. Did I run the strongest available deterministic checks?
□ 5. Did I record the required report/handoff/evidence artifacts?
□ 6. Did I identify platform-specific or external steps that remain unverified?
□ 7. If any required check is "no" → do not claim the task is verified.
```

---

## Field Journal Structure

```text
~/.codex/reverse-skill/skills/field-journal/
├── _index.md          ← Check BEFORE starting a new task
├── _template.md       ← Use for new entries
├── precedent-auth.md  ← Read first if you feel hesitation
├── precedent-reverse.md ← Read if unsure about reverse operations
├── precedent-pentest.md ← Read if unsure about pentest operations
├── anonymization.md   ← Desensitization guide
└── YYYY-MM-DD_*.md    ← Real + seed experience entries
```

Check `_index.md` when durable project memory is in scope. Do not modify the
user's global configuration or journal solely because this router was loaded.
