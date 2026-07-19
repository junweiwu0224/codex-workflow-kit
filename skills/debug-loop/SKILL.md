---
name: debug-loop
description: Use when tests, builds, typecheck, lint, E2E, startup commands, CI, runtime behavior, logs, screenshots, or user-reported bugs fail and Codex needs an evidence-driven debugging loop.
---

# debug-loop

## 目标

在测试失败、构建失败、运行错误、线上 bug、类型错误、lint 错误或行为不符合预期时，按可验证的循环推进：观察、定位、假设、最小修复、复测、总结。

这个 skill 的目标是减少盲改、重复尝试和修复后未验证。

## 触发场景

在以下情况触发：

- 测试、typecheck、lint、build、E2E、启动命令失败。
- 用户报告 bug、报错、异常行为、回归或性能问题。
- Codex 自己运行验证失败。
- 日志、截图、堆栈、CI 输出显示问题。
- 修改后行为不符合验收标准。

## 工作原则

- 先建立反馈回路，再动手修复：优先拿到可重复的失败命令、最小复现、日志断言、截图状态或静态契约。
- 先观察，再修改。
- 一次只验证一个主要假设。
- 优先找到最小复现或最小失败命令。
- 优先修根因，不只修表面错误。
- 修复后必须复测触发失败的命令或场景。
- 如果失败链很长，先收敛到第一个有用错误。
- 不因为第一个命令失败就停止，除非缺少凭证、外部服务不可用、继续有破坏性风险或触及用户确认红线。

## Feedback Loop First

在修复前，先回答：

- 失败是否可以用一个命令、一个测试、一个页面状态、一个日志断言或一个内容契约稳定复现？
- 最优反馈回路优先级：failing test、curl/HTTP script、CLI fixture、headless browser script、captured trace replay、throwaway harness、property/fuzz loop、differential loop、HITL checklist。
- 如果没有现成测试，是否能加一个窄的 regression test：只覆盖触发 bug 的边界、输入、输出或文档契约，不把实现细节锁死。
- 如果不能加测试，是否有更轻的验证方式：静态搜索、AST/语法检查、配置解析、fixture、截图、instrumented log 或人工可复查步骤。
- 如果反馈回路会访问外部服务、生产、账号、密钥、迁移、部署或长期服务，先停下并按用户确认红线处理。
- 如果无法建立可信 feedback loop，明确说明尝试过什么、缺什么证据、下一步需要用户提供哪类 artifact；不要在没有可观察信号时继续猜。

Regression test 的目标是防止同类问题回来，不是为了增加仪式感。优先保护公共 contract、解析边界、权限判断、错误路径、数据格式、路径引用、缓存/生命周期边界和用户可见行为。

反馈回路本身也要迭代：让它更快、更确定、更贴近用户报告的症状。30 秒 flaky loop 通常要继续收窄；2 秒 deterministic loop 才适合作为修复依据。

## 调试循环

1. 观察
   - 记录失败命令、错误信息、堆栈、日志、截图或行为差异。
   - 区分当前改动引起的问题和既有问题。
   - 找到最小可复现路径。

2. 定位
   - 用 `rg` / `rg --files` 找相关代码、测试、配置、调用方。
   - 阅读近期改动和相似实现。
   - 找到错误从哪里产生、在哪里传播。

3. 假设
   - 写出 1-3 个可能原因。
   - 选择最可能且最容易验证的假设先验证。
   - 不要同时修改多个无关方向。

4. 修复
   - 做最小安全改动。
   - 遵循现有模式。
   - 不引入无关重构。
   - 必要时补测试、静态契约或 regression test；不要为了通过测试而削弱测试意义。

5. 复测
   - 先运行最小失败命令。
   - 再按影响面运行更全面验证。
   - 如果失败变化，回到观察阶段。

6. 总结
   - 说明根因、修复、验证结果。
   - 如果学到长期项目知识，更新 `AGENTS.md`、`docs/testing.md` 或 `docs/codex-playbook.md`。

## 处理多重失败

- 先修最早、最确定、最可能导致后续错误的失败。
- 把独立失败分组。
- 不要在一个补丁里混合多个无关修复，除非它们有共同根因。
- 如果发现失败是既有问题，说明证据，并只在任务需要时修复。

## Agent 自诊断和上下文漂移

当失败不是来自代码，而是来自 Codex 自身执行过程，也进入本 skill。典型信号包括：重复调用同一工具没有新信息、当前操作和用户目标不一致、最终声明缺少文件/命令证据、subagent 返回后没有集成或关闭、长线程压缩后开始执行旧目标。

按以下顺序恢复：

1. 标记失败类型：`goal drift`、`context drift`、`unsupported claim`、tool loop、subagent lifecycle、verification gap。
2. 回读当前状态：用户最新请求、当前 goal、计划、相关文件、命令输出、subagent id 和已关闭状态。
3. 找最小纠偏动作：停止无收益循环、重开相关文件、重跑最小验证、补做 lifecycle close，或把不确定声明降级为待验证。
4. 修复后回到原验证路径；不要把“我以为完成了”当成证据。
5. 如果发现长期规则缺口，交给 `completion-review` 判断是否需要沉淀到 repo docs、全局规则或 skill。

## 信息不足时

如果缺少复现步骤、日志、输入数据或环境：

- 先尝试从仓库、测试、CI、错误输出中推断最小复现。
- 如果仍无法推进，向用户提出最少数量的具体问题。
- 不要泛泛询问“能提供更多信息吗”；要说明需要哪一类信息以及为什么。

## Output Shape

完成 debug-loop 后，最终回复或阶段汇报应包含：

- Feedback loop：使用了哪个失败命令、测试、页面状态、日志断言或 artifact；是否稳定复现。
- Root cause：最终确认的根因，以及排除过的关键假设。
- Fix：改了什么文件或行为，是否增加 regression test / contract。
- Verification：复跑了哪些命令或场景，结果如何；如果仍有失败，说明下一轮观察点。
- Residual risk：不能验证的部分、外部依赖、flaky 信号或需要用户提供的证据。

## 不要做

- 不要盲目改代码。
- 不要只看错误最后一行。
- 不要修完不复测。
- 不要为了让测试过而削弱测试意义。
- 不要把真实 bug 标成测试问题，除非有证据。
- 不要吞掉错误、扩大 catch、静默失败，除非这是明确需求。
- 不要因为验证失败就立刻把问题交还给用户。
