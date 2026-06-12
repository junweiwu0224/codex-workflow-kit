# Codex Usage

This file records real V3.1 workflow-kit usage samples from this toolkit repository itself. It is separate from `repo-template/docs/codex-usage.md`, which is the template copied into other repositories.

Goal: after 3-5 representative M/L/XL tasks, decide which workflow rules truly reduce steering, missed verification, or rework, and which parts add friction.

## Real Trial Records

| Date | Task / Scope | Level | Workflow / Tools | Verification | Positive Signal | Friction | Decision |
|---|---|---|---|---|---|---|---|
| 2026-06-13 | Trial row helper for real M/L/XL samples | M | render_usage_row, targeted pytest | `python3 -m pytest tests/test_render_usage_row.py -q` -> `12 passed` | Real usage rows become reproducible instead of hand-written tables | Adds another CLI mode that docs/verifier must cover | Promote helper; keep lightweight and docs-only |
| 2026-06-13 | Runtime smoke and skill audit evidence layer | L | codex_runtime_smoke, audit_skill_contracts, release-readiness | `codex_runtime_smoke.py --check-prompt-input` and `audit_skill_contracts.py` -> OK | Caught live install drift and proved 11/11 skill contracts before release | Runtime smoke still leaves manual agent cases as checklist evidence | Keep package/runtime split; do not fake automation for HITL subagent cases |
| 2026-06-13 | Package verifier coverage for real usage evidence | M | verify_toolkit, content contract tests | `python3 scripts/verify_toolkit.py` -> Workflow toolkit OK | Required-file and term gates caught stale README/evidence/manifest drift quickly | Every new durable doc or CLI mode must be named in verifier constants | Keep strict package verifier; avoid expanding it into runtime enforcement |
| 2026-06-13 | Release-readiness drill after workflow changes | L | release-readiness, build_release, checksum, unpack/install drill | archive `2026.06.13.1` checksum OK; unpack/install/context-pack drill OK | Release checklist prevented claiming success before archive and live install were aligned | Rebuilding after small docs edits is repetitive but prevented stale manifest claims | Keep release-readiness for portable toolkit changes; batch doc edits before final build |

## Closeout Trial Records

| Date | Task / Scope | Level | Workflow / Tools | Verification | Positive Signal | Friction | Decision |
|---|---|---|---|---|---|---|---|
| 2026-06-13 | Release evidence version alignment | M | rg audit, verify_toolkit, release-readiness | `rg 2026.06.13` and `python3 scripts/verify_toolkit.py` -> stale release references found before build | Caught old archive/version wording before publishing a new checksum | Version strings still appear in multiple human docs | Keep strict release evidence; bump VERSION for content changes instead of mutating old archives |
| 2026-06-13 | Trial row preset helper | M | render_usage_row --preset, targeted pytest | `PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -p no:cacheprovider tests/test_render_usage_row.py -q` -> 15 passed | Common usage rows no longer require repeating all eight trial fields | Presets can hide task-specific context if overused | Keep render-only presets with explicit overrides; do not auto-append docs |
| 2026-06-13 | Package and docs contract alignment | M | verify_toolkit, content contract tests | `PYTHONDONTWRITEBYTECODE=1 python3 scripts/verify_toolkit.py` -> Workflow toolkit OK; targeted pytest -> 75 passed | Docs, helper CLI, usage evidence, and verifier terms stay aligned | Every new durable term adds a small verifier maintenance cost | Add only closeout/preset terms; avoid turning verifier into a full prose linter |
| 2026-06-13 | Release-readiness closeout drill | L | release-readiness, build_release, checksum, unpack/install drill | archive `2026.06.13.2` checksum OK; unpack/install/live install/doctor/runtime smoke/skill audit/context-pack drill OK | Portable package claims are backed by archive and temporary-install evidence | Full drill is slower than targeted tests but only needed for release artifacts | Keep for toolkit releases; batch doc/code edits before final build |

## Stage Review: 4 Real V3.1 Trials

Conclusion based on four M/L samples on 2026-06-13: V3.1 is improving efficiency for this toolkit when it turns repeated judgment into narrow, read-only, evidence-producing scripts. It becomes friction when evidence has to be manually copied into multiple docs or when runtime behavior cannot honestly be automated.

Keep and continue:

- `verify_toolkit.py` as the package integrity gate. It caught stale manifest/docs coverage immediately and kept the release from drifting.
- `codex_runtime_smoke.py` as a separate runtime evidence layer. It found live install drift without pretending to prove interactive subagent behavior.
- `audit_skill_contracts.py` as the skill contract gate. It found a real `spec-kit-xl` boundary gap and now keeps all 11 skills auditable.
- `release-readiness` for portable toolkit changes. The checksum, unpack drill, install drill, live install, doctor, runtime smoke, and context-pack checks prevented unsupported completion claims.
- `render_usage_row.py trial` for real M/L/XL usage records. It keeps trial evidence lightweight and repeatable.

Keep documented, do not automate yet:

- `docs/agent-collaboration-smoke.md` manual/HITL cases for No-Dispatch, Local-Write Boundary, and Visibility Policy.
- Official `codex doctor --json` top-level status normalization. Current evidence still treats category output manually because terminal environment failures can be unrelated to workflow-kit health.

Tighten next:

- Make docs mention `render_usage_row.py trial` wherever real usage records are described.
- Keep package checks and runtime checks separate; do not add multi-agent runtime claims to `verify_toolkit.py`.
- For future workflow changes, update usage evidence once per coherent batch instead of after every small edit, then run one final release build.

Do not advance:

- No new orchestrator, planner, dispatcher, queue, daemon, watcher, default hook stack, MCP server, memory writer, or agent swarm.
- No automatic external write, production write, account, permission, payment, key, deploy, or PR operation from this toolkit.

## Closeout Review: 4 Additional V3.1 Trials

Conclusion based on four additional closeout samples on 2026-06-13: the workflow is strongest when it turns repeated release and evidence alignment into narrow scripts or checklists, and weakest when the same facts must be manually copied across several human docs.

Keep:

- Strict release evidence and version bumping. When content changes after a release, create the next archive version instead of mutating an existing checksum.
- `render_usage_row.py trial --preset` as a render-only shortcut for common M/L closeout rows. Explicit overrides remain the path for task-specific evidence.
- Package docs/content contracts in `verify_toolkit.py`, but keep them as small drift checks rather than a full prose linter.
- `release-readiness` for reusable toolkit releases, because archive, checksum, unpack, temporary install, live install, doctor, runtime smoke, skill audit, and context-pack drills catch unsupported completion claims.

Tighten next:

- Record the exact archive/checksum/install drill result after each release build, before final reply.
- Keep `README.md`, `QUICKSTART.md`, `WORKFLOW-REVIEW.md`, `docs/V3.1-ADOPTION-EVIDENCE.md`, `VERSION`, and release artifact names aligned in one batch before running `scripts/build_release.py`.
- Prefer presets only for repeated evidence shapes; if a task needs many overrides, write the row explicitly.

Do not advance:

- Do not add automatic doc append/write behavior to `render_usage_row.py`.
- Do not add background release watchers, default hooks, MCP servers, memory writers, or agent orchestration to solve version-copy friction.
- Do not automate HITL subagent visibility and local-write boundary checks beyond the existing manual checklist until runtime tooling can prove them directly.
