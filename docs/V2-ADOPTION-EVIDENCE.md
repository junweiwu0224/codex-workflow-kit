# V2 Adoption Evidence

本文件记录 Codex Workflow Kit V2 采用计划的当前证据。目标是让每个晋升、拒绝和暂缓决定都有可审计依据，而不是凭主观感觉扩大默认自动化。

## Baseline Verification

已验证的 V2 baseline：

```bash
python3 scripts/verify_toolkit.py
# Workflow toolkit OK

<trial-repo-ai-quant-trading>/.venv/bin/python -m pytest -p no:cacheprovider tests/test_audit_repo_adoption.py tests/test_render_usage_row.py tests/test_verify_toolkit.py -q
# 45 passed

cd repo-template
python3 scripts/verify_context_pack.py
# Context pack OK

<trial-repo-ai-quant-trading>/.venv/bin/python -m pytest -p no:cacheprovider tests/test_verify_context_pack.py -q
# 12 passed

cd releases
env LC_ALL=C LANG=C LC_CTYPE=C shasum -a 256 -c codex-workflow-kit-2026.06.07.10.tar.gz.sha256
# codex-workflow-kit-2026.06.07.10.tar.gz: OK
```

`2026.06.07.10` 临时解包演练：

```text
Workflow toolkit OK
global dry-run/install completed against temporary Codex and agents homes
installed AGENTS.md and repo-onboarding skill verified
repo-only dry-run/install completed against a temporary repo
Context pack OK
baseline usage row appended and found in docs/codex-usage.md
```

## Trial Repo Scan

只读扫描找到 5 个候选仓库：

| Repo | Shape | Existing context | Dry-run result | Current decision |
|---|---|---|---|---|
| `<trial-repo-ai-quant-trading>` | Python + frontend/dashboard | 已有 `AGENTS.md` 和 context docs | `AGENTS.md` conflict | Use as evidence source; do not overwrite |
| `<trial-repo-coze-studio>` | Go backend repo | No root context pack found | Dirty worktree; can create repo context pack after review | Manual merge until local changes are reviewed |
| `<trial-repo-ai-workflows>` | Docs/tooling repo | V2 context pack installed and repo-specific calibration completed | `Context pack OK` | Ready for real workflow doc task records |
| `<trial-repo-dify>` | Large multi-package app | Existing root and nested `AGENTS.md` files | `AGENTS.md` conflict | Manual merge only; no mechanical install |
| `<trial-repo-dify-plugin-daemon>` | Go service/plugin daemon | V2 context pack installed and repo-specific calibration completed | `Context pack OK` | Ready for real code task records; Go tests remain manual-only by repo policy |

只读 adoption audit 命令：

```bash
python3 scripts/audit_repo_adoption.py /path/to/repo
python3 scripts/audit_repo_adoption.py --json /path/to/repo-a /path/to/repo-b
python3 scripts/audit_repo_adoption.py --markdown /path/to/repo-a /path/to/repo-b
```

该脚本只读取目标 repo，输出 `repo-only-install` 或 `manual-merge` 建议，不复制模板、不写文件、不创建备份。`--json` 输出用于批量 adoption 和后续自动化评估；`--markdown` 输出可直接粘贴为 adoption evidence 表格，减少手工整理误差。

Baseline usage row 生成命令：

```bash
python3 scripts/render_usage_row.py baseline
python3 scripts/render_usage_row.py baseline --verification-command ".venv/bin/python scripts/verify_context_pack.py"
```

该脚本只打印 Markdown 表格行，不写目标 repo。安装和验证 context pack 后，可把输出追加到目标 repo 的 `docs/codex-usage.md`，减少多 repo 首次采用记录的手工漂移。

安装前 audit 结果：

| Repo | Recommendation | Findings | Command |
|---|---|---|---|
| `<trial-repo-ai-quant-trading>` | `manual-merge` | `architecture-case-match`, `dirty-worktree`, `existing-agents`, `existing-context-file` x12 | `./install.sh --repo-only --repo <trial-repo-ai-quant-trading> --backup` |
| `<trial-repo-coze-studio>` | `manual-merge` | `dirty-worktree` | `./install.sh --repo-only --repo <trial-repo-coze-studio> --backup` |
| `<trial-repo-ai-workflows>` | `repo-only-install` | 0 | `./install.sh --repo-only --repo <trial-repo-ai-workflows> --backup` |
| `<trial-repo-dify>` | `manual-merge` | `dirty-worktree`, `existing-agents` | `./install.sh --repo-only --repo <trial-repo-dify> --backup` |
| `<trial-repo-dify-plugin-daemon>` | `repo-only-install` | 0 | `./install.sh --repo-only --repo <trial-repo-dify-plugin-daemon> --backup` |

安装和校准后再次 audit，两个已落地 repo 会因为已有 `AGENTS.md`、context docs 和 dirty worktree 正确返回 `manual-merge`。这表示后续更新应人工合并，而不是重复机械安装。

## Real Usage Evidence

`<trial-repo-ai-quant-trading>/docs/codex-usage.md` already contains:

- Context pack onboarding evidence.
- Quality gate side-effect calibration.
- Hooks candidate design.
- Subagents parallel boundary calibration.
- Five real implementation task records.
- Phase reviews after representative tasks.

Reusable signals from that repo:

- `scripts/verify_context_pack.py` is a strong A-level low-side-effect gate.
- Targeted pytest works best when selected by affected scope.
- Report-writing scans and TestClient/app health checks should not be default hooks.
- Subagents help in read-only or disjoint-ownership work. They should not become unconditional implementation behavior, but L/XL, planned, cross-module, multi-failure or multi-file-review tasks now require a proactive suitability check and active dispatch when 2+ independent non-overlapping subtasks exist.
- Small frontend JS contract changes can often use Node/pytest contract tests; layout/CSS/interaction risk still needs browser QA.

External repo baseline installs completed after explicit user approval:

| Repo | Verification | Usage record | Git status |
|---|---|---|---|
| `<trial-repo-ai-workflows>` | `python3 scripts/verify_context_pack.py` -> Context pack OK | Baseline row added to `docs/codex-usage.md` | New context pack files only |
| `<trial-repo-dify-plugin-daemon>` | `python3 scripts/verify_context_pack.py` -> Context pack OK | Baseline row added to `docs/codex-usage.md` | New context pack files only |

Repo-specific onboarding calibration completed after baseline install:

| Repo | Calibration | Verification | Reusable signal |
|---|---|---|---|
| `<trial-repo-ai-workflows>` | Replaced generic app-template assumptions with docs-only workflow repo facts in `AGENTS.md` and context docs | `PYTHONDONTWRITEBYTECODE=1 python3 scripts/verify_context_pack.py` -> Context pack OK | Lightweight docs/tooling repos should keep commands and gates focused on Markdown/context verification rather than app/build assumptions |
| `<trial-repo-dify-plugin-daemon>` | Replaced generic template assumptions with Go daemon/CLI facts, runtime boundaries, CI commands, generated-code boundaries, and manual-only test policy | `PYTHONDONTWRITEBYTECODE=1 python3 scripts/verify_context_pack.py` -> Context pack OK | Repo policy can override default Codex verification behavior; record exact Go test commands but do not run them automatically when project docs prohibit it |

Real M-level tasks after repo-specific calibration:

| Repo | Task | Verification | Reusable signal |
|---|---|---|---|
| `<trial-repo-dify-plugin-daemon>` | Align Go version docs with go.mod/CI by updating stale `CLAUDE.md` Go version from `1.23.3` to `1.26.2` and cleaning context pack stale-version notes | `rg -n "1\\.23\\.3|1\\.26\\.2|Go [0-9]|go-version|go 1\\." README.md CLAUDE.md AGENTS.md docs go.mod .github/workflows`; `PYTHONDONTWRITEBYTECODE=1 python3 scripts/verify_context_pack.py` -> Context pack OK | Context pack successfully surfaced a stale project doc fact; Go tests were intentionally not run because repo policy forbids automatic tests |
| `<trial-repo-ai-workflows>` | Guard README agent instruction append snippets so Claude/Codex setup commands detect an existing `## Code changes` section before appending and show a scoped `git diff` review | `pytest tests/test_readme_install_safety.py -q` red -> green; `pytest tests/test_verify_context_pack.py tests/test_readme_install_safety.py -q` -> 14 passed; `PYTHONDONTWRITEBYTECODE=1 python3 scripts/verify_context_pack.py` -> Context pack OK | Docs-only workflow repos benefit from tiny static content-contract tests; no need to promote full Markdown lint yet |
| `<trial-repo-dify-plugin-daemon>` | Lock manual-only Go test policy with static docs test by adding `manual-only-test-policy` markers to project docs and a Python policy test | `pytest tests/test_manual_test_policy.py -q` red -> green; `pytest tests/test_verify_context_pack.py tests/test_manual_test_policy.py -q` -> 15 passed; `PYTHONDONTWRITEBYTECODE=1 python3 scripts/verify_context_pack.py` -> Context pack OK | The most important hook boundary is now test-protected without running Go tests, Docker services, daemon startup, or migrations |
| `<trial-repo-dify-plugin-daemon>` | Validate CLAUDE.md repo paths with static docs test by fixing stale architecture paths, real package test examples, and shell block path drift | `pytest tests/test_claude_doc_paths.py -q` red -> green; `pytest tests/test_verify_context_pack.py tests/test_manual_test_policy.py tests/test_claude_doc_paths.py -q` -> 16 passed; `PYTHONDONTWRITEBYTECODE=1 python3 scripts/verify_context_pack.py` -> Context pack OK | Static docs/path tests can protect high-value repo guidance without running Go tests, Docker services, daemon startup, or migrations |
| `<trial-repo-ai-workflows>` | Make raw workflow downloads fail fast by changing README raw workflow install commands from `curl -L` to `curl --fail --location --show-error` and locking the rule with a static README test | `pytest tests/test_readme_install_safety.py::test_raw_workflow_download_commands_fail_fast -q` red -> green; `pytest tests/test_verify_context_pack.py tests/test_readme_install_safety.py -q` -> 15 passed; `PYTHONDONTWRITEBYTECODE=1 python3 scripts/verify_context_pack.py` -> Context pack OK | Static README content-contract tests caught an install safety issue that full Markdown lint would not specifically protect |

## Post-V2 Practical Calibration

本节记录进入“实战校准期”后的 3 个大型只读样本。目标不是完成业务实现，而是验证这套 workflow 在真实 L 级任务面前，subagents、frontend QA、MCP/code graph 是否真的降低返工或只是增加流程成本。

| Repo | L-level calibration task | Evidence run | Tool signal | Decision |
|---|---|---|---|---|
| `<trial-repo-ai-quant-trading>` | LocalMCP 股票操作工具图谱与命令面板/详情页端到端收敛：`ActionRegistry -> LocalMCP -> CommandPalette/AppStockOps -> 页面按钮/股票详情` | 3 个只读 explorer 子任务之一完成；`rg -n "LocalMCP|ActionRegistry|CommandPalette|data-stock-action|data-app-action|open_stock_detail|add_to_watchlist|remove_from_watchlist" dashboard/static dashboard/templates tests/e2e tests`; `node --check dashboard/static/core/local-mcp.js`; `node --check dashboard/static/core/action-registry.js`; `node --check dashboard/static/core/command-palette.js`; `node --check dashboard/static/core/stock-actions.js`; `.venv/bin/python scripts/verify_context_pack.py` -> Context pack OK | subagents 有收益：能把工具合同、页面入口、E2E/QA 设计分开调查；frontend QA 有强触发：真实命令面板/详情页/按钮行为不能只靠 Node 契约；code graph/MCP 有局部收益：当前无专用 code graph MCP，但 `rg` 调用链已暴露跨文件依赖 | 纳入 L 样本；未来真正实现时必须启用 frontend QA，subagents 适合只读/独立实现切片，主 agent 串行公共入口和 service worker/cache busting |
| `<trial-repo-ai-workflows>` | 4 条真实 M 任务后的 workflow/docs 阶段复盘：判断 README 安装安全、workflow 语义、context pack、quality gates、Markdown lint/link checker、hooks、MCP/code graph 是否晋升 | 1 个只读 explorer 子任务完成；`rg -n 'context pack|subagents?|frontend QA|frontend-qa|MCP|code graph|quality|testing|Markdown lint|link checker|hooks' AGENTS.md docs README.md code-change-workflow.md`; `rg -n '^```' README.md code-change-workflow.md docs`; `PYTHONDONTWRITEBYTECODE=1 python3 scripts/verify_context_pack.py` -> Context pack OK; `<trial-repo-ai-quant-trading>/.venv/bin/python -m pytest -q -p no:cacheprovider tests/test_verify_context_pack.py tests/test_readme_install_safety.py` -> 15 passed | subagents 有收益但应限只读审查：README 安装安全、workflow 语义、context pack 一致性可并行；frontend QA 不适用；MCP/code graph 无默认收益，Markdown + 小 Python verifier 用 `rg` 足够 | 不启用 frontend QA；不默认 MCP/code graph；保留 narrow static docs/content-contract tests，不提升 full Markdown lint/link checker |
| `<trial-repo-dify-plugin-daemon>` | Serverless Runtime 安装、重装、回滚 endpoint 与 backwards-invocation transaction 流程加固：跨 plugin manager、serverless connector/runtime、transaction handler、DB/cache/config | 1 个只读 explorer 子任务完成；`rg --files AGENTS.md docs scripts tests internal/core/serverless_connector internal/core/serverless_runtime internal/core/plugin_manager internal/core/io_tunnel/backwards_invocation`; `rg -n "Serverless|serverless|SwitchServerlessEndpoint|LaunchPlugin|SetupFunction|backwards-invocation|transaction" internal docs README.md`; `PYTHONDONTWRITEBYTECODE=1 python3 scripts/verify_context_pack.py` -> Context pack OK; Go tests intentionally not run due repo `manual-only-test-policy` | subagents 有收益：runtime/connector、service/transaction、DB/cache/config、CI/docs 可并行只读；frontend QA 不适用；code graph 类能力有潜在收益，因为跨模块调用链复杂，但当前没有可用专用 code graph MCP，`rg + architecture docs` 是可接受 baseline | 纳入 L 样本；不默认 Go tests、daemon startup、migration 或 build；code graph/MCP 只作为可选增强，不作为 portable default |

Calibration conclusion:

- **Subagents:** promote active assessment for L/XL and planned/cross-module work, but keep ownership boundaries strict. The 3 samples show real benefit for independent read-only investigation and verification design; they do not justify unbounded parallel implementation.
- **Frontend QA:** keep conditional. It is mandatory for the `ai-quant-trading` LocalMCP/user-action chain because real browser behavior is the risk. It is N/A for docs-only and service/CLI repos. Do not force browser QA onto non-UI work.
- **MCP/code graph:** do not enable by default. Current available tooling did not expose a dedicated code graph MCP; `rg`, context pack docs, tests and targeted file maps were enough for docs/tooling and acceptable as baseline for Go serverless mapping. Code graph should be considered when L/XL work repeatedly crosses runtime/service/generated/transaction boundaries and `rg` evidence is insufficient.
- **Hooks/quality gates:** keep default conservative. Context pack verifier and narrow static docs/content-contract tests have repeated evidence; full Markdown lint, external link checking, Go tests, Playwright, service startup, migrations and external downloads remain manual or repo-specific.

## First Adoption Review

结论基于两个已校准外部 repo 的 3 条真实 M 级任务记录：

- `dify-plugin-daemon`: Align Go version docs with go.mod/CI。
- `ai-workflows`: Guard README agent instruction append snippets。
- `dify-plugin-daemon`: Lock manual-only Go test policy with static docs test。

Promote now:

- Keep `python3 scripts/verify_context_pack.py` as the default A-level context pack gate.
- Promote tiny static docs/content-contract tests as repo-specific gate candidates when they protect a repeated operational rule, such as README install safety or manual-only test policy.
- Keep `scripts/audit_repo_adoption.py` and `scripts/render_usage_row.py` as V2 default toolkit helpers because they reduced multi-repo adoption drift.

Keep documented, not default:

- Go tests, integration tests, benchmarks, daemon startup, migrations, build scripts, install scripts, and release/publish actions remain manual-only for `dify-plugin-daemon`.
- Markdown lint/link checking remains a candidate for `ai-workflows`, but the current evidence supports narrow static tests over full Markdown lint.
- Subagents remain useful for read-only or clearly partitioned work. They should not become unconditional implementation mode, but large/planned/cross-module work must actively assess and use them when the split is safe.
- Browser/frontend QA remains conditional; neither calibrated repo produced browser/UI evidence in this review.

Reject as default for this V2 checkpoint:

- Blocking hooks by default.
- MCP/code graph/memory by default.
- `go test` in default hooks for repositories whose project docs prohibit automatic tests.

Next review trigger:

- Satisfied by the fourth and fifth calibrated-repo task records below; see Second Adoption Review.

## Second Adoption Review

结论基于两个已校准外部 repo 的 5 条真实 M 级任务记录：

- `dify-plugin-daemon`: Align Go version docs with go.mod/CI。
- `ai-workflows`: Guard README agent instruction append snippets。
- `dify-plugin-daemon`: Lock manual-only Go test policy with static docs test。
- `dify-plugin-daemon`: Validate CLAUDE.md repo paths with static docs test。
- `ai-workflows`: Make raw workflow downloads fail fast。

Promote now:

- Keep `python3 scripts/verify_context_pack.py` as the default A-level context pack gate.
- Promote static docs/content-contract tests as repo-specific quality gate candidates when they protect high-value operational rules: install snippets, raw download safety, documented repo paths, command examples, generated-code boundaries, or manual-only test policy markers.
- Update the repo-template quality gate/testing guidance to name `静态文档契约测试` explicitly, so new repos can adopt narrow tests without pulling in full Markdown lint/link-checking by default.

Keep documented, not default:

- Blocking hooks remain opt-in per repo. The evidence supports documenting A-level candidates, not enabling hooks automatically in new repos.
- Markdown lint and link checking remain candidates. The current evidence favors narrow static tests because they directly encode the risky contract and avoid network/link-check noise.
- Go tests, integration tests, daemon startup, migrations, build scripts, install scripts, release/publish actions, and README `curl` commands remain manual or explicitly approved actions when they access network, external services, generated outputs, or repo-specific runtime behavior.
- Subagents remain boundary-based rather than unconditional; L/XL, planned, cross-module, multi-failure and multi-file-review tasks must actively assess them and use them when 2+ independent non-overlapping subtasks exist.

Reject as default for this V2 checkpoint:

- MCP/code graph/memory as always-on defaults.
- Default blocking hooks in the portable toolkit.
- Full Markdown lint/link checker as the default docs repo gate.
- `go test` as a default hook for repos whose project docs prohibit automatic Go tests.

Next review trigger:

- Revisit only after a missed validation, a user correction, or adoption into another representative repo changes the evidence. The current V2 package has enough evidence to keep static docs/content-contract tests as repo-specific candidates without expanding default automation.

## Promotions

Promoted into V2:

- `install.sh --repo-only`
  - Evidence: multi-repo dry-run showed global AGENTS/skills checks create noise when only repo context pack is needed.
  - Validation: `test_install_repo_only_skips_global_files`; temporary release install drill.
  - Boundary: requires `--repo PATH`; skips global writes.

- `scripts/audit_repo_adoption.py`
  - Evidence: external repo adoption needs a reusable read-only preflight before writing context pack files.
  - Validation: `tests/test_audit_repo_adoption.py` including dirty worktree detection, machine-readable `--json` output, and evidence-ready `--markdown` output.
  - Boundary: read-only audit; does not replace `install.sh --dry-run`.

- `scripts/render_usage_row.py`
  - Evidence: V2 adoption requires every installed repo to record a baseline row before collecting real task evidence.
  - Validation: `tests/test_render_usage_row.py` including default row rendering, Markdown escaping, date default, and verification command override.
  - Boundary: prints rows only; does not write `docs/codex-usage.md` by itself.

- `docs/architecture.md` as a required context pack file
  - Evidence: quickstart and template assume architecture docs exist, but verifier did not enforce it.
  - Validation: `test_check_context_pack_requires_architecture_document`.
  - Boundary: checks only context pack completeness; does not validate architecture quality.

- Static docs/content-contract tests as repo-specific gate candidates
  - Evidence: `ai-workflows` protected README append guards and fail-fast raw downloads; `dify-plugin-daemon` protected manual-only test policy and stale documented repo paths.
  - Validation: red -> green static pytest tests in both calibrated repos; toolkit verifier requires this evidence and template guidance.
  - Boundary: not a global hook, not full Markdown lint, not external link checking; candidate tests must be narrow, fast, local-only, and tied to a repeated repo contract.

## Rejections

Rejected as V2 defaults:

- Blocking hooks by default.
  - Reason: evidence supports documentation and candidate evaluation, not automatic repo-wide blocking.

- MCP/code graph/memory by default.
  - Reason: current evidence shows repo docs, `rg`, language tools and targeted tests solve most observed context problems.

- Unbounded subagents as the default implementation mode.
  - Reason: subagents are useful with clear ownership and now require proactive suitability checks for large/planned/cross-module work, but shared files, lifecycle, schemas and product semantics remain main-agent controlled.

- Browser QA for every frontend change.
  - Reason: pure JS contract changes can be validated cheaply; browser QA remains required for layout, CSS, interaction, route, media, canvas/chart or viewport risk.

## V2.1 Tooling Layer

V2.1 adds an optional experience and observability layer without changing V2 defaults.

Baseline verification target:

```bash
cd releases
env LC_ALL=C LANG=C LC_CTYPE=C shasum -a 256 -c codex-workflow-kit-2026.06.07.11.tar.gz.sha256
# codex-workflow-kit-2026.06.07.11.tar.gz: OK
```

Promoted into the portable toolkit:

- `repo-template/docs/observability.md`
  - Evidence: post-V2 review showed the next useful improvement is seeing usage/session and long-task behavior, not adding heavier workflow rules.
  - Boundary: documents local usage, menu bar status, long-task monitoring, notifications and HUD tools as candidates only; no default automation, no default install, no hooks, no background service, and no raw log sharing.

- `repo-template/docs/subagents.md` prompt cards
  - Evidence: user observed that large tasks were not consistently using subagents despite the suitability rule.
  - Boundary: prompt cards keep the existing proactive suitability check, forbid shared writes without explicit ownership, and require main-agent integration review. They are copy-ready delegation prompts, not an unconditional implementation mode.

- `repo-template/docs/mcp-pilot.md`
  - Evidence: practical calibration found MCP/code graph may help in L/XL cross-module work, but `rg + context pack` remains the default baseline.
  - Boundary: `deepcontext-mcp` and other code graph tools are MCP/code graph pilot candidates only. A pilot requires baseline comparison, scoped indexing, privacy exclusions, rollback, and `docs/codex-usage.md` evidence before any promotion.

- `scripts/render_usage_row.py pilot`
  - Evidence: V2 had a baseline row helper; V2.1 needs standard evidence rows for observability, subagents, and MCP/code graph pilot trials.
  - Boundary: `render_usage_row.py pilot` prints Markdown only. It does not write target repos, install tools, enable hooks, start MCP servers, or promote defaults.

Rejections preserved:

- no default automation for observability or notifications.
- no default MCP/code graph/memory.
- no full subagent role pack import.
- no blocking hooks or background monitor by default.

Next V2.1 review trigger:

- After 3-5 representative M/L/XL tasks using observability, prompt cards, or MCP/code graph pilot records, review whether any candidate actually reduced context misses, waiting time, validation gaps, or subagent integration cost.

## V2.2 P0 Specialist Skills

V2.2 promotes three narrow specialist skills into the portable toolkit after reviewing the local V2.1 boundary, the 100 GitHub repository research pack, high-signal skill/subagent/MCP repositories, and read-only subagent investigations. The decision is to add targeted review/research skills, not broad skill packs or new default automation.

Baseline verification target:

```bash
cd releases
env LC_ALL=C LANG=C LC_CTYPE=C shasum -a 256 -c codex-workflow-kit-2026.06.07.13.tar.gz.sha256
# codex-workflow-kit-2026.06.07.13.tar.gz: OK
```

Promoted into the portable toolkit:

- `skills/security-review`
  - Evidence: current global rules and `completion-review` name security/data/production risk, but there was no focused pre-final AppSec review flow for auth, permissions, secrets, user data, payments, production config, CI, hooks, MCP/plugin setup, external writes, or trust boundaries.
  - Boundary: diff/repo review only; no external penetration testing, key rotation, production config edits, deployments, migrations, permission changes, or external writes without explicit approval.

- `skills/dependency-upgrade-review`
  - Evidence: dependency upgrades have distinct risk from ordinary debugging: manifest/lockfile diff, direct/transitive scope, release notes, CVE/advisory, license, install scripts, provenance, peer/runtime compatibility, test matrix, and rollback.
  - Boundary: no default full upgrades and no dependency install/network/download hook by default; changing facts require current primary sources and repo policy checks.

- `skills/research-brief`
  - Evidence: the workflow repeatedly needs evidence-backed promote/hold/reject decisions for GitHub repositories, skills, MCP servers, hooks, subagents, models/APIs, and ecosystem tools. GitHub/API/docs rate limits during research showed the need to record source availability and evidence quality instead of pretending sources were checked.
  - Boundary: research only; does not install, enable, authenticate, index, deploy, publish, or write external state. Prefer repo docs, deterministic scripts, hooks candidates, MCP pilots, or subagent prompt cards when those are smaller surfaces than a global skill.

Rejections preserved:

- no large cybersecurity skill pack import.
- no full skill marketplace import.
- no Composio/SaaS write-action skills by default.
- no full subagent role pack import.
- no GitHub/CI/Sentry, language/framework, secret-scan, license-review, or supply-chain-review global skill until repeated repo evidence proves low-noise value.
- no default hooks, MCP/code graph/memory, background monitors, external installs, or production-affecting automation.

## Deferred Work

External repo baseline installation and repo-specific onboarding calibration are no longer deferred for the two safe candidates:

```text
<trial-repo-ai-workflows>
<trial-repo-dify-plugin-daemon>
```

`<trial-repo-coze-studio>` should still be reviewed first because it has uncommitted changes.

After its local changes are reviewed, rerun:

```bash
python3 scripts/audit_repo_adoption.py <trial-repo-coze-studio>
```

Next V2 evidence gap: apply the toolkit to another representative repo only after its dirty worktree or existing `AGENTS.md` conflict is reviewed, then compare whether the same static docs/content-contract pattern still holds.

## Final V2 Completion Audit

本节按 V2 adoption plan 的 10 个阶段审计当前完成度。结论只基于当前文件、release artifact 和本轮新鲜验证，不基于意图或记忆。

| Plan stage | Evidence | Conclusion |
|---|---|---|
| Freeze V1 baseline | `scripts/verify_toolkit.py`、release checksum、`implementation-plan` 仅作为 removed skill 边界出现 | Satisfied |
| Select representative trial repos | 扫描 5 个候选 repo；`ai-workflows` 和 `dify-plugin-daemon` 完成安装和校准；有冲突/dirty repo 保持 manual merge | Satisfied with conservative scope |
| Run real M/L/XL tasks | 两个校准外部 repo 有 5 条真实 M 级任务记录；`ai-quant-trading` 另有 5 条真实试跑和 5 条实现任务记录作为旁证 | Satisfied |
| First adoption review | `First Adoption Review` 基于前 3 条 M 级任务，晋升 context verifier 和窄静态测试候选，拒绝默认 hooks/MCP/subagents | Satisfied |
| Evaluate hooks candidates | `docs/quality-gates.md` 模板和各 trial repo 记录将 context verifier、targeted tests、静态文档契约测试列为候选；未启用 blocking hooks | Satisfied: documented candidates, no default hook |
| Evaluate MCP/code graph/memory | 证据显示 repo docs、`rg`、语言工具和 targeted tests 解决当前观察到的问题；无重复失败支持默认启用 | Satisfied by rejection/default-defer decision |
| Evaluate subagents | `ai-quant-trading` 完成只读 subagent 边界校准；post-V2 refinement 将大型/计划/跨模块任务升级为主动 suitability check，安全拆分时主动使用 | Satisfied by proactive boundary |
| Browser/frontend QA calibration | `ai-quant-trading` 证据支持前端契约测试与 browser QA 触发条件分离；V2 review 保持 browser QA conditional | Satisfied by trigger calibration |
| Prepare V2 toolkit update | V2 baseline release 为 `2026.06.07.10`；V2.1 release 为 `2026.06.07.11`；V2.2 current release 为 `2026.06.07.13`；`WORKFLOW-REVIEW.md`、`QUICKSTART.md`、repo-template docs、verifier/tests、skill metadata quality gates、practical calibration evidence、P0 specialist skills 和 release 已更新 | Satisfied |
| Final verification and migration drill | toolkit self-check、toolkit tests、repo-template checks、checksum、final temporary install drill、trial repo checks 均有新鲜通过输出 | Satisfied |

Final decision:

- V2 end state is achieved as an evidence-driven portable package, not as a maximal automation package.
- Promoted by evidence: repo-only install, adoption audit/render helpers, required architecture context, context pack verifier, static docs/content-contract tests as repo-specific candidates.
- Deliberately not defaulted: blocking hooks, MCP/code graph/memory, unbounded subagents, browser QA, Go tests, full Markdown lint, link checking, external install/download commands. Subagents are now proactively evaluated for L/XL, planned, cross-module, multi-failure and multi-file-review work; 3 practical calibration samples confirm this should stay boundary-based.
- Remaining work is future adoption scope, not a blocker for V2: apply the kit to another representative repo after its dirty worktree or existing instruction conflicts are reviewed.

## Current V2.2 Status

`2026.06.07.13` is the current V2.2 portable package. It preserves the V2 evidence-backed baseline, including repo-only installation, read-only adoption audit, required architecture context, evidence-ready audit reporting, two verified external baseline installs, repo-specific onboarding calibration for a docs-only workflow repo plus a Go service/CLI repo, five real calibrated-repo M-level task records, adoption reviews, post-V2 proactive subagent guidance, 3 practical L-level calibration samples, and skill metadata/boundary quality gates.

V2.1 adds optional observability docs, subagent prompt cards, MCP/code graph pilot guidance, and `render_usage_row.py pilot` evidence rows. It deliberately keeps hooks, MCP/code graph/memory, browser QA, Go tests, Markdown lint, link checking, external installs, background monitors, and usage/session tools conditional rather than default automation. Subagents remain actively evaluated for L/XL, planned, cross-module, multi-failure and multi-file-review work, and used only when 2+ independent non-overlapping subtasks exist.

V2.2 adds `security-review`, `dependency-upgrade-review`, and `research-brief` as P0 specialist skills. They are narrow review/research workflows that complement Superpowers and the existing core skills; they do not default any external tool, scanner, SaaS action, MCP server, hook, subagent pack, or background automation.

## V2.2 Closeout

V2.2 closeout adds `scripts/verify_live_install.py` so the portable output package can prove the current machine's installed `~/.codex/AGENTS.md` and `~/.agents/skills/*/SKILL.md` match the package. This is a read-only drift check: it reports missing or different files, but never overwrites live Codex configuration.

Closeout verification targets:

```bash
python3 scripts/verify_toolkit.py
# Workflow toolkit OK

python3 scripts/verify_live_install.py
# Live install OK (12 files checked)
```

Closeout invariants:

- 9 skills verified: `repo-onboarding`, `spec-kit-xl`, `debug-loop`, `frontend-qa`, `decision-record`, `completion-review`, `security-review`, `dependency-upgrade-review`, `research-brief`; packaged skill assets are also compared by `scripts/verify_live_install.py`.
- `security-review`, `dependency-upgrade-review`, and `research-brief` remain P0 specialist skills, not a broad skill pack.
- skill metadata/boundary quality gates remain enforced by `scripts/verify_toolkit.py` and toolkit tests.
- live install drift detection is now part of the portable reuse path; new machines should run it after `./install.sh`.
