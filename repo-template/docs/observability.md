# Observability

本文件记录当前仓库可选的 Codex 使用可观测性、会话/用量查看、长任务提醒和效果复盘方式。目标是让优化有证据，而不是把监控、通知或 hooks 变成默认负担。

## 原则

- 默认不安装、不启动、不授权任何外部工具。
- 优先使用本地、只读、可关闭、可解释的工具。
- 不把 token、账号、凭证、会话全文、私有代码片段或生产数据写入共享文档。
- 工具只服务于效果评估；不替代 `docs/codex-usage.md` 的人工判断。
- 如果工具需要读取 Codex/Claude/Cursor 等本地日志，先确认读取范围、保存位置、是否上传网络、是否包含敏感内容。

## 候选工具

| 工具 | 用途 | 默认状态 | 进入条件 | 退出条件 |
|---|---|---|---|---|
| `ccusage` | 查看本地 agent CLI 用量、token、成本、日报/月报 | 候选 | 需要量化 usage 趋势，且确认只读本地日志 | 输出不准确、读取范围过宽、增加维护成本 |
| `CodexBar` | macOS 菜单栏或 CLI 查看 Codex/Claude/Cursor/Gemini usage/cost | 候选 | 长任务多、需要菜单栏状态或本地 dashboard | 需要不接受的授权、后台行为不清楚、数据暴露风险 |
| `CodexMonitor` / `oh-my-codex` | 长任务监控、通知、HUD 或 hooks 增强 | 候选 | 明确有长任务错过、等待批准未发现、或多 workspace 监控痛点 | 默认 hooks 过重、阻断规则不清楚、触发外部副作用 |

## 最小试用流程

试用前先记录目标：

- 要观察的问题：
- 使用的工具：
- 读取的数据范围：
- 是否访问网络：
- 是否写入文件：
- 如何关闭或卸载：

试用后只把结果信号写入 `docs/codex-usage.md`，不要写入原始日志：

```bash
python3 scripts/render_usage_row.py pilot --pilot observability
```

如工具安装在 toolkit 外部，可以从 toolkit 路径调用：

```bash
/path/to/codex-workflow-kit/scripts/render_usage_row.py pilot --pilot observability
```

## 记录标准

记录正信号：

- 更容易发现长任务等待、失败或完成。
- 更容易判断哪些任务 token/时间成本异常。
- 更容易对比 Superpowers、subagents、frontend QA 或 MCP pilot 的成本收益。

记录负信号：

- 输出和真实 Codex 使用不一致。
- 需要读取过宽的本地日志或敏感目录。
- 引入后台进程、网络、账号、通知噪音或维护成本。
- 小任务因为观测而变慢。

## 不自动晋升

以下情况不能把观测工具晋升为默认动作：

- 只有一次试用，没有 3-5 条代表性任务证据。
- 工具需要默认上传日志、会话内容或私有代码。
- 工具需要默认启用阻断型 hooks。
- 工具无法说明关闭、回滚或清理方式。

## 复盘问题

每完成 3-5 次有代表性的 M/L/XL 任务后，结合 `docs/codex-usage.md` 回看：

- usage/cost 数据是否改变了我们的流程判断？
- 哪类任务最容易超时、等待批准或反复恢复上下文？
- subagents 是否节省主 agent 上下文，还是增加集成成本？
- frontend QA 和 MCP/code graph pilot 的成本是否被结果证明值得？
- 哪些观察可以沉淀到 `AGENTS.md`、`docs/testing.md`、`docs/subagents.md` 或 `docs/mcp-pilot.md`？

## 待确认

- 当前仓库是否需要 usage/session 工具。
- 当前仓库允许读取的本地日志路径。
- 当前仓库是否有长任务通知或菜单栏监控需求。
