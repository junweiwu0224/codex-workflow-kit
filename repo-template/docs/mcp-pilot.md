# MCP Pilot

本文件记录当前仓库是否、何时、如何试点 MCP、代码图谱或 memory。目标是给大型仓库提供受控实验路径，而不是把 MCP/code graph/memory 变成默认依赖。

## 原则

- 默认使用 `rg`、`rg --files`、语言工具、测试、repo context pack 和源码回读。
- MCP/code graph 只在 L/XL、跨模块、调用链复杂、`rg + context pack` 反复不足时试点。
- memory 只记录跨项目长期偏好或稳定工作方式；项目事实仍优先写入 `AGENTS.md` 和 `docs/`。
- 所有 MCP 写操作、外部服务、认证、生产数据、数据库、云服务、issue tracker 或发布动作都需要用户明确确认。
- 试点必须有 baseline、退出条件和回滚方式。
- V3.1 Core 不默认注册 MCP server、plugin runtime、code graph daemon 或 memory writer；`pilot` 不等于启用。

## 权限分级

先按最低权限评估，每个 MCP/plugin/code graph/memory pilot 必须标注权限级别：

| 级别 | 含义 | 默认处理 |
|---|---|---|
| `docs-only` | 只读文档、schema、manifest 或 README，不运行工具 | 可作为准入审查起点 |
| `read-only local` | 只读本地仓库文件，不联网、不写入 | 可在明确范围内试点 |
| `local write` | 写本地报告、缓存、索引或配置 | 需要输出位置、清理方式和敏感排除 |
| `external read` | 读取外部 API、云服务、浏览器状态、issue 或账号数据 | 需要用户确认认证和读取范围 |
| `external write` | 写 issue、PR、ticket、云资源、账号状态或外部系统 | 必须单独确认，默认禁止 |
| `destructive / production-risk` | 部署、迁移、权限、支付、删除、生产数据变更 | 不作为 pilot 默认内容 |

## Pilot 必填字段

- tool/server/plugin 名称：
- 来源和版本：
- plugin/MCP 配置路径：
- 权限级别：
- auth 模型：
- allowed tools：
- denied tools：
- dry-run/read-only mode：
- 允许读取范围：
- 必须排除范围：
- 是否联网：
- 是否写入本地文件：
- 是否外部写入：
- 是否读取 browser/cookie/account：
- 日志/缓存/索引位置：
- uninstall/disable path：
- rollback/fallback：

## 试点准入

同时满足以下条件，才考虑 MCP/plugin/code graph/memory pilot：

- 任务为 L/XL，或连续多次 M 任务跨越同一复杂边界。
- 已经阅读 `AGENTS.md`、`docs/architecture.md`、`docs/commands.md`、`docs/testing.md`。
- `rg + context pack` 无法稳定回答调用关系、模块边界、影响范围或重复上下文问题。
- 目标目录、排除目录、隐私边界和输出位置清楚。
- 有明确的对比指标，例如定位时间、漏文件数量、误判次数、验证覆盖提升。
- 已按外部组件准入协议做 promote/pilot/hold/reject 判断。

不要试点：

- XS/S 任务。
- 只需要单文件或小范围修改的任务。
- 需要真实外部写入、生产凭证、数据库迁移、部署或权限变更的任务。
- 工具需要默认索引 `.env`、凭证、私有用户数据、生成大文件、build 产物或外部网络。
- 工具无法列出 allowed/denied tools、禁用路径或日志/缓存位置。

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

本节不预置默认工具。记录候选时只写已审查过的 repo-local 候选：

| 工具 | 权限级别 | 适用场景 | 默认状态 | 风险 |
|---|---|---|---|---|
|  |  |  | 试点候选 / hold / reject |  |

兼容旧版 verifier 的历史候选词：`deepcontext-mcp` 只能作为试点候选示例保留；不得默认安装、注册、联网或启用。真实采用前仍必须按本节记录权限级别、baseline、回滚和外部组件准入决策。

## 试点记录

把试点结果写入 `docs/codex-usage.md`：

```bash
python3 scripts/render_usage_row.py pilot --pilot mcp-code-graph
```

记录字段：

- 试点任务：
- Baseline 命令：
- MCP/plugin/code graph/memory 工具：
- 权限级别：
- allowed tools：
- denied tools：
- 索引范围：
- 排除范围：
- 是否访问网络：
- 是否写入文件：
- 是否有 external write：
- 日志/缓存位置：
- 禁用/回滚方式：
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
- 撤销或删除临时凭证、token、授权会话或浏览器连接。
- 在 `docs/codex-usage.md` 记录停止原因。
- 如果试点产生了有效架构事实，把事实移入 repo docs，而不是依赖工具缓存。

## 待确认

- 当前仓库是否有值得试点的跨模块痛点。
- 允许索引的目录：
- 必须排除的目录：
- 是否允许外部网络或 API key：
- 试点负责人和复盘触发条件：
