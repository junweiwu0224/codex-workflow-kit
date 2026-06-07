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

## Subagents

完整边界见 `docs/subagents.md`。

- 全局/仓库 subagent 协议就是长期授权；不要因为当前对话没有再次说“使用子代理/并行”就跳过 subagent suitability check 或 dispatch。
- L/XL、已有实施计划、跨模块、多个独立失败源、多文件审查或预计可并行的调查，先做 subagent suitability check。
- 存在 2 个以上互不重叠、可独立推进、不会共享写入状态的子任务时，主动使用 subagents；不使用时说明原因。
- 主 agent 保留需求澄清、架构判断、共享文件、最终集成、diff review 和验证。
- 长期 L/XL 产品落地如果采用垂直切片集中写入，可以不强行派实现 subagent；每 2-3 个切片后优先派只读 explorer 审查方案覆盖率、风险和验收缺口。

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
- 需要主动评估 subagent suitability check 的任务：L/XL、已有实施计划、跨模块、多个独立失败源、多文件审查、可并行调查。
- 存在 2 个以上互不重叠、可独立推进、不会共享写入状态的子任务时，应主动使用 subagents。
- 适合并行的独立领域：
- 禁止并行的共享状态/文件：
- 不使用时需要说明的原因：强耦合、下一步阻塞依赖、文件 ownership 冲突、共享状态风险、高风险外部操作。
- 主 agent 保留事项：需求澄清、架构判断、共享文件、外部/生产风险、最终集成、diff review 和验证。
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
