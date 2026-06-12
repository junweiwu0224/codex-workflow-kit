# Codex Usage

本文件记录 Codex 在当前仓库中的使用效果、复盘信号和流程调整依据。目标是减少返工、漏测、误判和沟通成本，不追求更多流程、更多文件或更多工具。

## 什么时候记录

默认不记录 XS/S 小任务。以下情况才记录：

- M/L/XL 任务完成后发现了可复用经验。
- 出现明显返工、漏测、验证失败、用户纠偏或上下文误判。
- 使用了 Superpowers、`spec-kit-xl`、subagents、hooks、MCP/plugin、code graph、memory/recall、frontend QA 或 debug loop，且结果值得以后参考。
- 准备新增、修改或删除 repo 规则、hooks、skills、MCP、memory 记录、外部组件准入规则或质量门禁。
- 做了外部组件 intake、repo-local pilot、V3.1 prompt card 或权限分级试点。

不要记录一次性过程流水账、未验证猜测、敏感信息、凭证、生产数据或用户隐私。

## 轻量记录

| 日期 | 任务/范围 | 分级 | 使用的流程/工具 | 验证 | 效果信号 | 后续动作 |
|---|---|---|---|---|---|---|
|  |  |  |  |  |  |  |

`效果信号` 可以写：

- 正信号：上下文定位更快、验证更完整、返工减少、用户纠偏减少、失败后更快收敛。
- 正信号也可以记录：subagent 减少重复探索、verifier 发现真实问题、pilot 找到 `rg` 漏掉的边界、新机器复用更顺畅。
- 负信号：流程过重、文档噪音、skill 触发过宽、hook 误报、subagent 集成成本高、MCP/plugin/code graph/memory 带来额外复杂度。

## V3.1 试点记录

用于外部组件、MCP/plugin、code graph、memory/recall、hook、domain skill 或 subagent prompt card 试点。先记录证据，再决定是否晋升。

```markdown
### V3.1 Pilot: <名称>

- 日期：
- 类型：external-component / MCP-plugin / codegraph / memory-recall / hook / domain-skill / subagent
- baseline：
- 权限级别：
- 读写范围：
- 风险标签：
- 验证：
- 正信号：
- 负信号：
- 决策：promote / pilot / repo-local / hold / reject
- 下一步：
```

判断术语：

- `promote`：吸收为规则、文档、只读检查、prompt card 或窄触发能力，不表示安装。
- `pilot`：继续单独试点，不默认启用。
- `repo-local`：只保留在当前仓库。
- `hold`：证据不足或收益不清。
- `reject`：风险、冲突、license 或维护成本不接受。

## 周期复盘

每完成 3-5 个有代表性的 M/L/XL 任务，或发生一次明显返工/漏测后，回看上方记录：

- 哪些规则确实减少了误判或漏测？
- 哪些规则让小任务变慢或让文档变嘈杂？
- 哪些验证命令最常用、最可靠、最应该前移到 `docs/quality-gates.md`？
- 哪些静态文档契约测试稳定保护了安装说明、路径引用、命令示例或 repo policy，且没有引入 lint/link-check 的额外成本？
- 哪些命令被误判为低副作用？是否触发了应用生命周期、本地数据库、缓存、报告、网络或外部服务？
- 哪些 hooks 候选实际会写 cache、bytecode、coverage、report、trace、截图或 build 产物？
- 哪些项目知识应该晋升到 repo `AGENTS.md`、`docs/testing.md`、`docs/architecture.md` 或 ADR？
- 哪些经验已经跨项目稳定，应该升级到全局 `AGENTS.md`、个人 skill 或 memory？
- 哪些 hooks、MCP、subagent 模式或 skills 没有实际收益，应该放宽或删除？
- 哪些外部组件 intake 决策需要从 `pilot` 收紧为 `repo-local/hold/reject`？
- 哪些 code graph 或 memory/recall 试点没有超越 baseline，应该停止？

## 阶段复盘模板

当轻量记录达到 3-5 条后，在本节补一次短复盘。目标是收敛流程，而不是增加更多自动化。

```markdown
## 阶段复盘：N 次真实试跑后

结论基于 YYYY-MM-DD 到 YYYY-MM-DD 的真实任务记录。当前优先减少误判、漏测和不必要流程。

保留并继续使用：

- 

保持文档化、暂不自动启用：

- 

暂不推进：

- 

下一轮观察：

- 
```

判断标准：

- 连续带来定位速度、验证准确性或返工减少的规则，可以晋升到 `AGENTS.md`、`docs/testing.md`、`docs/quality-gates.md` 或 `docs/codex-playbook.md`。
- 只在一次任务中有用、或让 XS/S 任务变慢的规则，留在记录中观察，不晋升。
- hooks、MCP、subagents、memory 和新 scripts 必须有重复收益证据、清晰副作用边界和回退方式，再从“文档化候选”升级为默认动作。
- 外部组件的 `promote` 不等于安装；真实安装、启用、注册、联网或外部写入必须单独确认。
- 如果一条流程只是在弥补文档缺失，优先修正文档或命令索引，而不是新增更重的流程。

## 调整决策

把复盘结果放到最窄且最可维护的位置：

- 项目规则：更新 repo `AGENTS.md`。
- 项目命令或验证：更新 `docs/commands.md`、`docs/testing.md` 或 `docs/quality-gates.md`。
- 项目工作经验：更新 `docs/codex-playbook.md`。
- 长期技术取舍：写入 `docs/decisions/`。
- XL/正式需求边界：写入 `docs/specs/`。
- 跨项目稳定偏好：升级到全局 `AGENTS.md`、个人 skill 或 memory。
- 外部组件准入事实：写入当前 repo 文档或 toolkit `docs/external-component-intake.md` 的规则，不复制外部仓库正文。

## 待评估事项

-
