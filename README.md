# Codex Workflow Kit

中文 | [English](#english)

一套可迁移的个人 Codex 工作流工具包：全局工作原则、repo context pack 模板、专项 skills、安装脚本、自检脚本，以及保守的质量门禁/并行/观测边界。

它的核心目标不是“装更多工具”，而是让 Codex 在新机器和新仓库里更快建立上下文、更少误判、更稳定验证，同时避免默认启用高副作用自动化。

## 包含内容

```text
VERSION                         当前版本
MANIFEST.sha256                 包内容 checksum manifest
QUICKSTART.md                   双语快速开始
WORKFLOW-REVIEW.md              双语工作流复盘
global/AGENTS.md                 个人级 Codex 工作原则
repo-template/                   新仓库 context pack 模板
skills/                          9 个专项 skills
scripts/verify_toolkit.py        工具包完整性自检
scripts/verify_live_install.py   当前机器安装漂移检查
scripts/audit_repo_adoption.py   新仓库只读采用审计
scripts/render_usage_row.py      usage/evidence 表格行生成器
scripts/build_release.py         刷新 MANIFEST.sha256 并构建 release tarball
install.sh                       非破坏式安装器
```

## 9 个 Skills

- `repo-onboarding`: 建立仓库 context pack。
- `spec-kit-xl`: 只用于 XL/正式规格任务。
- `debug-loop`: 测试、构建、运行失败后的证据驱动调试循环。
- `frontend-qa`: 前端/UI/交互的真实浏览器和响应式验证。
- `decision-record`: 长期技术取舍和 ADR。
- `completion-review`: 实现和验证之后的交付前检查。
- `security-review`: 安全、权限、密钥、用户数据、生产配置和信任边界审查。
- `dependency-upgrade-review`: 依赖、lockfile、base image、GitHub Actions、CVE/license/supply-chain 审查。
- `research-brief`: GitHub 仓库、MCP、hooks、subagents、模型/API、工具选型的证据化 promote/hold/reject。

这些 skills 是对 Superpowers 或其他主流程的专项补强，不替代计划、TDD、阶段推进和最终验证。

## 快速安装

```bash
git clone https://github.com/junweiwu0224/codex-workflow-kit.git
cd codex-workflow-kit
python3 scripts/verify_toolkit.py
./install.sh --dry-run
./install.sh --backup
python3 scripts/verify_live_install.py
```

预期关键输出：

```text
Workflow toolkit OK
Live install OK (12 files checked)
```

默认安装位置：

```text
~/.codex/AGENTS.md
~/.agents/skills/
```

## 应用到新仓库

先做只读审计：

```bash
python3 scripts/audit_repo_adoption.py /path/to/repo
python3 scripts/audit_repo_adoption.py --json /path/to/repo
python3 scripts/audit_repo_adoption.py --markdown /path/to/repo
```

如果建议为 `repo-only-install`，再安装 context pack：

```bash
./install.sh --repo-only --repo /path/to/repo --dry-run
./install.sh --repo-only --repo /path/to/repo --backup
cd /path/to/repo
python3 scripts/verify_context_pack.py
```

已有 `AGENTS.md`、已有 context docs、dirty worktree 或大小写等价文档时，优先人工合并，不要机械覆盖。

安装后可以记录 baseline usage 行，也可以为 observability、subagents、MCP/code graph pilot 生成只记录证据的 `pilot` 行：

```bash
python3 scripts/render_usage_row.py baseline
python3 scripts/render_usage_row.py pilot --pilot observability
python3 scripts/render_usage_row.py pilot --pilot subagents
python3 scripts/render_usage_row.py pilot --pilot mcp-code-graph
```

## 默认边界

- 不默认启用 blocking hooks。
- 不默认启用 MCP/code graph/memory。
- 不默认安装外部监控、后台服务或 SaaS 写入能力。
- 不把 subagents 设为无条件执行路径；L/XL、跨模块、多独立失败源或多文件审查时先做 suitability check。
- 不把浏览器 QA 强加给所有任务；只在 UI、布局、交互、资源、viewport 或真实用户可见风险存在时触发。

## 验证

```bash
python3 scripts/verify_toolkit.py
python3 scripts/verify_live_install.py
python3 -m pytest tests/test_verify_toolkit.py tests/test_verify_live_install.py tests/test_audit_repo_adoption.py tests/test_render_usage_row.py -q
cd repo-template
python3 scripts/verify_context_pack.py
python3 -m pytest tests/test_verify_context_pack.py -q
```

## 公开版说明

这个仓库是公开可复用版本，已移除个人机器路径、私有试跑仓库证据和历史 release tarball。模板里的规则仍然偏个人工作流风格，建议 fork 后按自己的团队和项目约束调整。

---

## English

A portable personal workflow kit for Codex: global working principles, a repo context-pack template, specialist skills, non-destructive install scripts, self-checks, and conservative boundaries for quality gates, subagents, observability, MCP/code graph, and memory.

The goal is not to install more tools. The goal is to help Codex build context faster, make fewer wrong assumptions, verify more consistently, and avoid enabling high-side-effect automation by default.

## What's Included

```text
VERSION                         Current version
MANIFEST.sha256                 Package checksum manifest
QUICKSTART.md                   Bilingual quickstart
WORKFLOW-REVIEW.md              Bilingual workflow review
global/AGENTS.md                 Personal Codex working principles
repo-template/                   Context-pack template for new repositories
skills/                          9 specialist skills
scripts/verify_toolkit.py        Package integrity verifier
scripts/verify_live_install.py   Local installed-file drift checker
scripts/audit_repo_adoption.py   Read-only adoption audit for target repos
scripts/render_usage_row.py      Usage/evidence table row generator
scripts/build_release.py         Refresh MANIFEST.sha256 and build release tarballs
install.sh                       Non-destructive installer
```

## The 9 Skills

- `repo-onboarding`: create a repo context pack.
- `spec-kit-xl`: only for XL/formal specification work.
- `debug-loop`: evidence-driven debugging after test/build/runtime failures.
- `frontend-qa`: real browser and responsive checks for frontend/UI/interaction work.
- `decision-record`: durable technical decisions and ADRs.
- `completion-review`: pre-delivery check after implementation and verification.
- `security-review`: security, permissions, secrets, user data, production config, and trust-boundary review.
- `dependency-upgrade-review`: dependency, lockfile, base image, GitHub Actions, CVE/license/supply-chain review.
- `research-brief`: evidence-backed promote/hold/reject decisions for repos, MCP, hooks, subagents, models/APIs, and tooling.

These skills are specialist supplements to your main workflow. They do not replace planning, TDD, phased execution, or final verification.

## Quick Install

```bash
git clone https://github.com/junweiwu0224/codex-workflow-kit.git
cd codex-workflow-kit
python3 scripts/verify_toolkit.py
./install.sh --dry-run
./install.sh --backup
python3 scripts/verify_live_install.py
```

Expected key output:

```text
Workflow toolkit OK
Live install OK (12 files checked)
```

Default install locations:

```text
~/.codex/AGENTS.md
~/.agents/skills/
```

## Apply to a New Repo

Run a read-only audit first:

```bash
python3 scripts/audit_repo_adoption.py /path/to/repo
python3 scripts/audit_repo_adoption.py --json /path/to/repo
python3 scripts/audit_repo_adoption.py --markdown /path/to/repo
```

If the recommendation is `repo-only-install`, install the context pack:

```bash
./install.sh --repo-only --repo /path/to/repo --dry-run
./install.sh --repo-only --repo /path/to/repo --backup
cd /path/to/repo
python3 scripts/verify_context_pack.py
```

If the target repo already has `AGENTS.md`, context docs, a dirty worktree, or case-equivalent docs, prefer manual merge over mechanical overwrite.

After install, you can generate a baseline usage row, or generate `pilot` rows for observability, subagents, and MCP/code graph pilots. These commands only print evidence rows; they do not enable automation:

```bash
python3 scripts/render_usage_row.py baseline
python3 scripts/render_usage_row.py pilot --pilot observability
python3 scripts/render_usage_row.py pilot --pilot subagents
python3 scripts/render_usage_row.py pilot --pilot mcp-code-graph
```

## Defaults and Boundaries

- No blocking hooks by default.
- No MCP/code graph/memory by default.
- No external monitors, background services, or SaaS write actions by default.
- Subagents are not unconditional; use a suitability check for L/XL, cross-module, multi-failure, or multi-file review work.
- Browser QA is conditional; use it for UI, layout, interaction, resource, viewport, or real user-visible risk.

## Verification

```bash
python3 scripts/verify_toolkit.py
python3 scripts/verify_live_install.py
python3 -m pytest tests/test_verify_toolkit.py tests/test_verify_live_install.py tests/test_audit_repo_adoption.py tests/test_render_usage_row.py -q
cd repo-template
python3 scripts/verify_context_pack.py
python3 -m pytest tests/test_verify_context_pack.py -q
```

## Public Edition Note

This is the public reusable edition. Personal machine paths, private trial-repo evidence, and historical release tarballs have been removed. The templates are still opinionated toward a personal Codex workflow, so fork and adapt them to your own team and repository constraints.
