---
name: repo-onboarding
description: Use when a repository needs onboarding, AGENTS.md setup, project command discovery, architecture/testing docs, or a repo context pack so Codex can work reliably in the codebase.
---

# repo-onboarding

## 目标

让 Codex 快速、可靠地理解一个仓库，并为后续长期工作建立最小但高质量的 repo context pack。

这个 skill 的产出不是“大而全项目文档”，而是让 Codex 以后少猜、少漏测、少重复问、少踩坑。

## 触发场景

在以下情况触发：

- 用户要求熟悉、接手、整理、初始化或增强一个仓库。
- 用户要求生成或补全 `AGENTS.md`、项目命令、架构说明、测试策略。
- 用户说“让 Codex 更懂这个项目”“做 repo onboarding”“整理 repo context pack”。
- 当前仓库缺少关键上下文，而任务预计会多次继续推进。

不要在一次性小改动中自动触发完整 onboarding。

## 工作原则

- 先读后写。
- 只把可确认的信息写成事实。
- 不确定的信息标为 `待确认`，不要伪装成结论。
- 优先生成短、准、可维护的文档。
- 不覆盖人工已有内容；只做合并、补全、纠错和去噪。
- repo `AGENTS.md` 只放项目级规则和索引，不重复用户全局 Codex 宪法。
- 文档语言默认跟随仓库；如果仓库没有明显惯例，使用中文。

## 扫描顺序

1. 仓库结构
   - 使用 `rg --files`、目录列表、关键配置文件了解项目形态。

2. 项目入口
   - 阅读 README、package scripts、Makefile、CI 配置、主要 manifest，例如 `package.json`、`pyproject.toml`、`go.mod`、`Cargo.toml`、`pom.xml` 等。

3. 代码结构
   - 找入口文件、核心模块、测试目录、配置目录、生成文件、docs。

4. 验证能力
   - 确认可运行的 test、lint、typecheck、build、e2e、storybook、dev server 等命令。
   - 写入命令前先探测命令是否真实可用；不要假设 `python`、`node`、`npm`、`make` 等入口存在。优先记录当前仓库已验证的解释器或工具路径。

5. 风险区域
   - 标记认证、权限、支付、数据库迁移、生产配置、密钥、CI/CD、生成文件、legacy 区域。

## 产出策略

如果缺少 context pack，创建：

- `AGENTS.md`
- `docs/architecture.md`
- `docs/commands.md`
- `docs/testing.md`
- `docs/quality-gates.md`
- `docs/subagents.md`
- `docs/observability.md`
- `docs/mcp-pilot.md`
- `docs/codex-usage.md`
- `docs/codex-playbook.md`
- `docs/glossary.md`
- `docs/decisions/README.md`
- `docs/decisions/0001-template.md`
- `docs/specs/README.md`
- `docs/specs/0001-template.md`

如果这些文件已经存在：

- 保留原结构和人工内容。
- 只补明显缺失且可确认的信息。
- 把推断内容写入 `待确认` 或最终回复，不直接写成事实。
- 如果发现过期信息，先用证据修正；证据不足时标注待确认。
- 在大小写不敏感文件系统上，先检查大小写等价文件；例如已有 `docs/ARCHITECTURE.md` 时，不再创建 `docs/architecture.md`，而是索引并补充现有文件。

## 信息分配

- `AGENTS.md`：项目级规则、命令索引、验证矩阵、边界、已知坑。
- `docs/architecture.md`：架构事实、目录职责、模块关系、可选 Mermaid 简图。
- `docs/commands.md`：安装、运行、测试、lint、build、格式化、常见失败。
- `docs/testing.md`：测试策略、验证矩阵、前端视觉验证、性能/回归验证。
- `docs/quality-gates.md`：hooks、CI、本地门禁、阻断规则和豁免方式。
- `docs/subagents.md`：subagents 并行边界、任务拆分、提示词约束和集成验证方式。
- `docs/observability.md`：usage/session 可观测性、长任务监控候选、隐私边界和效果记录方式。
- `docs/mcp-pilot.md`：MCP、代码图谱和 memory 的试点准入、baseline、回滚和晋升标准。
- `docs/codex-usage.md`：Codex 使用效果、复盘信号、流程调整依据和工具收益评估。
- `docs/codex-playbook.md`：本仓库中 Codex 已验证有效的工作经验。
- `docs/glossary.md`：业务术语、技术术语、缩写、命名约定。
- `docs/decisions/`：长期技术决策和取舍。
- `docs/specs/`：XL/正式规格任务的需求、非目标、验收标准和风险边界。

## 验证

完成文档创建或更新后：

- 检查 Markdown 链接和路径是否真实。
- 确认命令来自实际配置或文档。
- 确认写入 docs 的命令在当前环境中可发现或已标注待确认。
- 不运行有副作用的命令。
- 如运行验证命令，优先只读或轻量命令，例如列 scripts、解析配置、运行已有静态检查。
- 最终说明哪些命令已确认，哪些仍待确认。

## 最终输出

输出应包含：

- 创建或更新了哪些文件。
- 识别出的项目技术栈和入口。
- 识别出的关键命令。
- 识别出的风险区域。
- 尚未确认的信息。
- 建议下一步最有价值的动作。

## 不要做

- 不要为了填满模板而编造内容。
- 不要把 README 机械复制到 docs。
- 不要机械复制模板覆盖或重复已有文档；优先合并、索引和补缺。
- 不要创建冗长架构文档。
- 不要覆盖已有人工判断。
- 不要在小任务里强行执行完整 onboarding。
- 不要把一次性调试过程写进长期文档。
