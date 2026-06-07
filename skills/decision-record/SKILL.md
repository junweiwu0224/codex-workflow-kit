---
name: decision-record
description: Use when a task involves long-term technical decisions, ADRs, architecture tradeoffs, framework/database/auth/deployment choices, module boundaries, public APIs, data models, risks, or accepted technical debt.
---

# decision-record

## 目标

在项目出现长期技术取舍时，创建或更新轻量 ADR，记录“为什么这么做”，帮助未来的人和 Codex 避免重复讨论、误改和丢失上下文。

这个 skill 的目标不是写正式论文，而是用短、清楚、可维护的方式保存关键决策。

## 触发场景

在以下情况触发：

- 选择或替换关键框架、库、数据库、缓存、队列、部署方式。
- 改变模块边界、依赖方向、公共 API、数据模型、权限模型。
- 做出会影响性能、安全、可靠性、可观测性或维护成本的取舍。
- 明确接受长期限制、风险或技术债。
- 用户要求记录决策、写 ADR、沉淀技术取舍。
- 任务过程中发现某个历史决策需要解释或更新。

不要为一次性 bug fix、小实现细节、普通文案、短期实验创建 ADR。

## 工作原则

- ADR 记录长期决策，不记录一次性过程。
- 优先短而清楚。
- 记录背景、决策、主要取舍、影响、后续。
- 不把未确认方案写成已接受决策。
- 如果决策还未定，状态使用 `Proposed`。
- 如果决策已被明确采用，状态使用 `Accepted`。
- 如果替代旧决策，不删除旧 ADR；把旧 ADR 标记为 `Superseded` 并链接新 ADR。
- ADR 使用项目文档语言；无明显惯例时使用中文。

## 操作步骤

1. 判断是否值得记录
   - 只有当决策会长期影响架构、数据、接口、安全、性能、部署或维护成本时，才创建 ADR。

2. 检查现有 ADR
   - 查看 `docs/decisions/`。
   - 找是否已有相关决策。
   - 如果是补充或替代，更新现有 ADR 或创建新 ADR 并建立链接。

3. 确定编号和文件名
   - 使用下一个递增编号。
   - 文件名使用简短英文 kebab-case。
   - 示例：`0003-use-postgres-for-primary-storage.md`

4. 写入 ADR
   - 使用轻量模板：

```md
# 0003 决策标题

- 状态：Proposed
- 日期：YYYY-MM-DD
- 相关链接：

## 背景

为什么需要做这个决策？当前目标、约束、问题是什么？

## 决策

我们决定：

## 主要取舍

为什么选择它？放弃了什么？接受了什么风险或限制？

## 影响

- 正面影响：
- 负面影响 / 风险：
- 需要同步修改的地方：

## 后续

-
```

5. 更新索引
   - 如果 `docs/decisions/README.md` 有索引，更新索引。
   - 如果没有，不强制新增复杂索引。

6. 回连相关文档
   - 如果决策影响架构、测试、命令或 Codex 工作方式，更新 `docs/architecture.md`、`docs/testing.md`、`docs/commands.md`、`AGENTS.md` 或 `docs/codex-playbook.md`。

## 质量标准

合格 ADR 应回答：

- 为什么需要这个决策？
- 具体决定了什么？
- 为什么不是其他方案？
- 接受了什么代价？
- 未来需要注意什么？
- 如果被替代，应该看哪条新决策？

## 不要做

- 不要为小改动创建 ADR。
- 不要写长篇历史流水账。
- 不要把猜测写成已接受事实。
- 不要删除旧 ADR。
- 不要创建没有取舍的 ADR。
- 不要把 ADR 当普通任务日志。
