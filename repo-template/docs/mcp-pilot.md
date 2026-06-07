# MCP Pilot

本文件记录当前仓库是否、何时、如何试点 MCP、代码图谱或 memory。目标是给大型仓库提供受控实验路径，而不是把 MCP/code graph/memory 变成默认依赖。

## 原则

- 默认使用 `rg`、`rg --files`、语言工具、测试、repo context pack 和源码回读。
- MCP/code graph 只在 L/XL、跨模块、调用链复杂、`rg + context pack` 反复不足时试点。
- memory 只记录跨项目长期偏好或稳定工作方式；项目事实仍优先写入 `AGENTS.md` 和 `docs/`。
- 所有 MCP 写操作、外部服务、认证、生产数据、数据库、云服务、issue tracker 或发布动作都需要用户明确确认。
- 试点必须有 baseline、退出条件和回滚方式。

## 试点准入

同时满足以下条件，才考虑 MCP/code graph pilot：

- 任务为 L/XL，或连续多次 M 任务跨越同一复杂边界。
- 已经阅读 `AGENTS.md`、`docs/architecture.md`、`docs/commands.md`、`docs/testing.md`。
- `rg + context pack` 无法稳定回答调用关系、模块边界、影响范围或重复上下文问题。
- 目标目录、排除目录、隐私边界和输出位置清楚。
- 有明确的对比指标，例如定位时间、漏文件数量、误判次数、验证覆盖提升。

不要试点：

- XS/S 任务。
- 只需要单文件或小范围修改的任务。
- 需要真实外部写入、生产凭证、数据库迁移、部署或权限变更的任务。
- 工具需要默认索引 `.env`、凭证、私有用户数据、生成大文件、build 产物或外部网络。

## Baseline

试点前先记录不使用 MCP 的 baseline：

```bash
rg --files | sed -n '1,120p'
rg -n "<关键术语|函数|路由|事件|schema|provider|adapter>" .
python3 scripts/verify_context_pack.py
```

根据仓库技术栈补充语言工具：

- TypeScript/JavaScript：
- Python：
- Go：
- Rust：
- Java：

## 候选工具

| 工具 | 适用场景 | 默认状态 | 风险 |
|---|---|---|---|
| `deepcontext-mcp` | 代码库语义搜索、symbol-aware search、大型 TS/Python 仓库理解 | 试点候选 | 需要确认索引范围、API key、外部网络和数据边界 |
| `codebase-memory-mcp` | 长期项目模式、决策和上下文记忆 | 试点候选 | 容易把项目事实放错位置；敏感信息必须排除 |
| 其他 code graph 工具 | 架构问答、影响分析、重构导航 | 试点候选 | 输出可能过期或不完整，必须回读源码验证 |

## 试点记录

把试点结果写入 `docs/codex-usage.md`：

```bash
python3 scripts/render_usage_row.py pilot --pilot mcp-code-graph
```

记录字段：

- 试点任务：
- Baseline 命令：
- MCP/code graph 工具：
- 索引范围：
- 排除范围：
- 是否访问网络：
- 是否写入文件：
- 是否发现 `rg` 漏掉的关键调用或边界：
- 是否减少返工、误判或用户纠偏：
- 是否值得保留：

## 成功标准

至少满足两项，才考虑继续使用：

- 比 baseline 更快定位跨模块调用链。
- 发现 baseline 漏掉的关键文件、接口、schema、provider、adapter 或测试。
- 让 subagents 拆分更清晰，减少重复探索。
- 让验证范围更准确，减少漏测或误测。
- 产生可沉淀到 `docs/architecture.md`、`docs/testing.md`、`docs/subagents.md` 或 ADR 的事实。

## 失败和退出条件

出现以下情况，停止试点并回到 baseline：

- 索引范围不清楚或包含敏感文件。
- 工具输出无法回读源码验证。
- 成本、延迟、安装维护或授权复杂度超过收益。
- 让 XS/S/M 普通任务变慢。
- 需要默认后台服务、默认网络访问或默认外部写入。

## 回滚

- 删除或禁用项目级 MCP 配置。
- 停止后台索引或服务。
- 删除本地索引产物，确认其不包含敏感内容。
- 在 `docs/codex-usage.md` 记录停止原因。
- 如果试点产生了有效架构事实，把事实移入 repo docs，而不是依赖工具缓存。

## 待确认

- 当前仓库是否有值得试点的跨模块痛点。
- 允许索引的目录：
- 必须排除的目录：
- 是否允许外部网络或 API key：
- 试点负责人和复盘触发条件：
