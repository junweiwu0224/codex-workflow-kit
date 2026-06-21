# AGENTS.md

本文件补充当前仓库的项目级规则。默认继承用户全局 Codex 工作原则；如有冲突，以本文件中更具体的项目规则为准。

## 项目快照

- 项目目标：
- 主要技术栈：
- 运行环境：
- 关键外部依赖：
- 主要入口：

## 设置和常用命令

优先查看 `docs/commands.md`。如果该文件不存在或内容过期，先从 package scripts、Makefile、README、CI 配置中确认命令。

- 安装依赖：
- 本地开发：
- 运行测试：
- 类型检查：
- Lint：
- 构建：
- 格式化：

## 仓库地图

优先查看 `docs/architecture.md`。修改前先理解相关目录的职责和调用关系。

- `src/`：
- `tests/`：
- `docs/`：
- 配置文件：
- 生成文件：

## 工具和外部上下文

- 可观测性和长任务监控候选：`docs/observability.md`
- MCP/code graph/memory 试点边界：`docs/mcp-pilot.md`
- Code graph 试点边界：`docs/codegraph-pilot.md`
- Memory/recall 试点边界：`docs/memory-recall-pilot.md`
- 外部 skill/plugin/MCP/hook/subagent prompt 接入前，先用 toolkit 的 `docs/external-component-intake.md` 和 `scripts/audit_external_component.py` 做只读准入审查；不要直接安装或启用。
- 本仓库推荐的 MCP/plugin：
- 本仓库可用的代码图谱、索引或语言服务器：
- 外部系统只读查询方式：
- 需要用户确认的外部写操作：
- 不应写入 memory 的项目敏感信息：

## 项目级工作规则

- 优先沿用本仓库已有模式、命名、格式、工具和 helper API。
- 修改前先阅读相关目录和既有实现，不要凭文件名猜测。
- 涉及公共 API、数据结构、权限、安全、构建配置、迁移、跨模块行为时，先明确影响范围和验证方式。
- 如果发现明显应该沉淀的项目知识，更新本文件或 `docs/` 中合适的位置。

## Codex 使用效果

- 效果评估文档：`docs/codex-usage.md`
- 需要记录的任务类型：
- 当前最有收益的流程/工具：
- 当前最容易过度流程化的场景：
- 下一次复盘触发条件：

## 验证矩阵

优先查看 `docs/testing.md` 和 `docs/quality-gates.md`。根据改动类型选择最相关验证。

- 文档改动：
- 单元逻辑改动：
- API/服务端改动：
- 前端/UI 改动：
- 构建/配置改动：
- 安全/权限相关改动：

## Hooks 和质量门禁

- 项目门禁文档：`docs/quality-gates.md`
- 可自动运行的快速门禁：
- 必须手动确认的慢速/外部门禁：
- 禁止放入 hooks 的命令：
- hook 豁免规则：

## Subagents

- 项目 subagents 指南：`docs/subagents.md`
- 本项目的 subagent 协议是用户写入 AGENTS/AGENTS.override 的长期授权即视为显式授权 Codex 在满足条件时使用 subagents；它授权主动执行 suitability check，也授权在 subagent 工具实际可用且未被平台权限阻止时按本协议 dispatch。已加载这类长期授权时，本轮重复授权不是必要条件，不得因当前对话没有再次说“subagents/并行/委派”而记录 tool permission constraint。
- 需要主动评估 subagent suitability check 的任务：L/XL、已有实施计划、跨模块、多个独立失败源、多文件审查、可并行调查。
- subagent 工具实际可用且未被平台权限阻止，且存在 2 个以上互不重叠、可独立推进、不会共享写入状态的子任务时，应主动使用 subagents；只有当前会话没有加载长期授权时，用户才需要在当前任务中写“本轮授权按需使用 subagents/并行代理/委派”补充一次性显式授权。
- 派发 subagent 时必须遵守 `docs/subagents.md` 的 Handoff Envelope、History/Input Filter、Command/Tool Risk Policy、Step Budget / Stop Condition、Return Envelope 和 Lifecycle Ledger。
- 默认 subagent 只允许 docs-only/read-only local；local write 必须绑定 allowed write set；dev server/service、network/external read、external write、destructive / production-risk 需要主 agent 明确保留或先向用户确认。
- 不要把完整会话历史、敏感信息、无关日志、未验证推断或外部组件/MCP/code graph/memory 输出直接交给 subagent。
- subagent 返回后，主 agent 必须 review Return Envelope、回读关键证据、运行集成验证，并记录 integrated/discarded 结论。
- 适合并行的独立领域：
- 禁止并行的共享状态/文件：
- 不使用时需要说明的原因：强耦合、下一步阻塞依赖、文件 ownership 冲突、共享状态风险、高风险外部操作。
- 不派 subagent 时记录 No-Dispatch Decision：strong coupling、shared writes、blocked dependency、safety boundary、unclear task、no independent subtask 或 tool permission constraint；其中 tool permission constraint 只表示 subagent 工具不可用、未暴露、调用被平台/权限拒绝，或当前会话既未加载长期授权也没有本轮明确授权，不包括已加载长期授权后缺少本轮重复授权。
- 主 agent 保留事项：需求澄清、架构判断、共享文件、外部/生产风险、最终集成、diff review 和验证。
- 长期 L/XL 产品落地如果采用垂直切片集中写入，可以不强行派实现 subagent；但每 2-3 个切片后，应优先派只读 explorer 做方案覆盖率、风险和验收缺口审查。
- 不要为了 subagent 协议引入新的 orchestrator、planner、dispatcher、queue、agent swarm 或后台 runtime；Superpowers 仍然负责计划、TDD 和阶段推进。
- 最终回复前检查 Lifecycle Ledger：不再需要的 subagent 都已 close，关闭失败或仍需运行时说明原因和残余风险。
- subagent 可用的验证命令：
- subagent 禁止执行的命令：

## Review 标准

自检和 review 时重点检查：

- 行为是否满足需求和验收标准。
- 是否覆盖关键路径和失败路径。
- 是否引入回归、竞态、数据不一致、权限绕过或敏感信息泄露。
- 是否符合现有架构和代码风格。
- 是否有不必要的复杂度或重复。
- 是否需要更新文档、测试、示例或迁移说明。

## 安全和数据

本仓库的敏感区域：

-
-

项目额外规则：

-
-

## 前端和 UX

如果本项目包含前端：

- 设计系统/组件库：
- 主要页面入口：
- 需要验证的视口：
- 视觉验证方式：
- 可访问性要求：

如果本项目不包含前端，写：N/A。

## 性能

性能敏感路径：

-
-

性能验证方式：

-

如果本项目没有已知性能敏感路径，写：N/A。

## 边界

谨慎或禁止修改：

- 生产配置：
- 数据库迁移：
- 认证/权限：
- 支付/账单：
- 生成文件：
- 锁文件：
- CI/CD：
- 大型快照或 fixture：
- 其他：

## 已知坑

-
-
-

## 文档和知识沉淀

- 项目结构、命令、测试策略变化时，更新 `docs/architecture.md`、`docs/commands.md` 或 `docs/testing.md`。
- 质量门禁、hooks、CI 检查变化时，更新 `docs/quality-gates.md`。
- subagents 并行边界、独立任务分组或禁止并行区域变化时，更新 `docs/subagents.md`。
- usage/session/长任务监控经验更新到 `docs/observability.md` 和 `docs/codex-usage.md`。
- MCP/code graph/memory 试点结果更新到 `docs/mcp-pilot.md` 和 `docs/codex-usage.md`。
- Codex 使用效果、复盘信号和流程调整依据更新到 `docs/codex-usage.md`。
- 重要技术取舍写入 `docs/decisions/`。
- XL/正式规格任务的需求、非目标、验收标准和风险边界写入 `docs/specs/`。
- Codex 在本仓库的工作方式、验证习惯、常见坑更新到本文件或 `docs/codex-playbook.md`。
- 新增内容应短、准确、可长期复用，不记录一次性过程细节。
