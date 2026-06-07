# Workflow Review / 工作流复盘

## 中文

这套工具包的路线：

```text
个人 Codex 宪法
-> 任务分级协议
-> repo context pack
-> Superpowers/spec-kit 边界
-> 自定义专项 skills
-> MCP/代码图谱/memory 候选边界
-> hooks 质量门禁候选
-> subagents 并行协议
-> usage/效果评估
```

已打包能力：

- `global/AGENTS.md`：个人级工作原则、任务分级、验证纪律、MCP/hooks/subagents/memory 边界。
- `repo-template/`：项目级 context pack 模板，覆盖命令、测试、架构、质量门禁、subagents、observability、MCP pilot、usage、ADR 和 specs。
- `skills/`：9 个专项 skills，补齐 onboarding、XL spec、debug、frontend QA、ADR、completion、security、dependency 和 research。
- P0 专项 skills：`security-review`、`dependency-upgrade-review`、`research-brief`。
- `install.sh`：非破坏式安装器，支持 dry-run、backup、force、repo-only 和自定义 home。
- `scripts/verify_toolkit.py`：包级自检。
- `scripts/verify_live_install.py`：当前机器安装漂移检查。
- `scripts/audit_repo_adoption.py`：目标 repo 只读采用审计。
- `scripts/render_usage_row.py`：usage/evidence 行生成器。

默认不启用：

- blocking hooks。
- MCP/code graph/memory。
- 外部监控、后台服务、SaaS 写入动作。
- 无边界 subagents。
- 所有任务都强制 browser QA。

推荐采用方式：

- XS/S：直接处理，做最小验证。
- M：轻量计划、实现、targeted verification。
- L：先调查影响范围，再计划和验证；可并行时做 subagent suitability check。
- XL：先写正式 spec/验收标准，再计划和执行。

## English

The workflow path:

```text
Personal Codex constitution
-> task sizing protocol
-> repo context pack
-> Superpowers/spec-kit boundaries
-> custom specialist skills
-> MCP/code graph/memory candidate boundaries
-> hooks quality-gate candidates
-> subagent parallelism protocol
-> usage/effectiveness review
```

Packaged capabilities:

- `global/AGENTS.md`: personal working principles, task sizing, verification discipline, and MCP/hooks/subagents/memory boundaries.
- `repo-template/`: repo context-pack template for commands, testing, architecture, quality gates, subagents, observability, MCP pilots, usage, ADRs, and specs.
- `skills/`: 9 specialist skills covering onboarding, XL specs, debugging, frontend QA, ADRs, completion review, security review, dependency review, and research briefs.
- `install.sh`: non-destructive installer with dry-run, backup, force, repo-only, and custom home support.
- `scripts/verify_toolkit.py`: package verifier.
- `scripts/verify_live_install.py`: local install drift checker.
- `scripts/audit_repo_adoption.py`: read-only adoption audit for target repos.
- `scripts/render_usage_row.py`: usage/evidence row generator.

Not enabled by default:

- Blocking hooks.
- MCP/code graph/memory.
- External monitors, background services, or SaaS write actions.
- Unbounded subagents.
- Browser QA for every task.

Recommended use:

- XS/S: handle directly and run minimal verification.
- M: light plan, implementation, targeted verification.
- L: investigate impact first, then plan and verify; run a subagent suitability check when work can be split safely.
- XL: write a formal spec/acceptance criteria first, then plan and execute.
