# Memory Recall Pilot

本文件记录当前仓库是否、何时、如何试点 memory/recall。memory 只作召回提示，不是真相源。

## 默认状态

- 项目事实优先写入 repo `AGENTS.md` 和 `docs/`。
- 跨项目稳定偏好才考虑进入 memory。
- 不默认启用 memory hook。
- 不默认启用 MCP memory writer。
- 不自动保存 prompt、assistant answer、raw transcript、logs 或私有数据。

## 适用场景

可以考虑 pilot：

- 同一项目或跨项目反复出现稳定规则，用户多次重复解释。
- 长线程被压缩后，稳定偏好和长期决策容易丢失。
- 需要搜索过去已确认的工作流决策，但 repo docs 不适合承载跨项目规则。

不要用于：

- 一次性调试过程。
- 未验证推断。
- 项目事实、命令、架构、测试策略，这些应 repo-local。
- secrets、token、账号、生产数据、用户隐私、raw logs。
- 自动创建 skill 或全局规则。

## Pilot 准入

试点前记录：

- 召回目标：
- memory 存储位置：
- 写入方式：
- 删除方式：
- provenance 字段：
- 禁止写入内容：
- stale memory 审查方式：
- 回退到 repo docs 的方式：

## 写入规则

允许：

- 跨项目稳定偏好。
- 多次重复验证的工作方式。
- 用户明确要求长期记住的非敏感规则。

禁止：

- raw transcript。
- secret 原文。
- `.env`、私钥、token、账号、生产数据。
- 未经确认的推断。
- 只适合当前 repo 的事实。
- 自动生成并写入全局 skill。

## Recall 使用规则

- recall 结果必须标注来源和时间。
- recall 结果可能过期，低成本时回读当前 repo。
- 与 repo docs、源码、测试冲突时，以当前 repo 为准。
- stale 或错误 memory 要记录删除或修正建议。

## 成功标准

至少满足两项才继续试点：

- 减少用户重复解释。
- 更快找到跨项目稳定偏好。
- 减少错误假设或目标漂移。
- 没有引入 secret、隐私、stale memory 或触发噪音问题。

## Usage 记录

```bash
python3 scripts/render_usage_row.py pilot --pilot memory-recall
```

