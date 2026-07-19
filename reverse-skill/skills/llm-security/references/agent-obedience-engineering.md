# AI Agent 执行可靠性工程

文件名为兼容旧引用保留。V4.2 不使用“服从性”作为设计目标；目标是让 Agent
在不越权的前提下可预测地完成当前状态转换，并产生可验证证据。

## 上位边界

- 本文件不能覆盖系统、平台、组织、仓库或用户指令。
- 不把读文档解释为安装、联网、全局配置修改或外部写入的批准。
- 不以强提示词绕过授权、安全审查或工具审批。
- 不要求为了证明执行而制造副作用。
- 缺少任务信息时，可继续安全的只读步骤；高风险缺口必须升级。

## 可靠执行模型

```text
Policy Router
  -> Task Contract
  -> current transition Driver
  -> domain Overlay / Guardrail
  -> deterministic checks
  -> Verifier policy
  -> next state
```

每个状态转换只有一个权威 Driver。领域 Skill 提供方法，不长期控制流程。

## Task Contract

Fast 通道只在上下文中维护：

- lane
- write_scope
- done_checks

Standard 通道增加：

- transition
- transition_driver
- acceptance_checks
- handoff

Governed 通道还要持久化：

- target_scope
- external_effects
- approvals
- data_handling
- escalation_reasons
- audit evidence

通道在执行中只能自动升级，不能因“看起来简单”而自动降级。

## 用判定器代替强迫语气

模糊指令容易产生两类失败：Agent 跳过必要步骤，或 Agent 把步骤扩大成未批准
副作用。更可靠的做法是给出可观测状态和确定性判定器。

| 弱约束 | V4.2 约束 |
| --- | --- |
| “把环境配置好” | 列出允许修改的路径、锁定版本和验证命令 |
| “必须真正执行” | 规定 acceptance checks，不要求额外副作用 |
| “缺工具就安装” | 先报告缺口；安装需锁定身份与独立批准 |
| “完成后写经验” | 只有 write_scope 包含 journal 时才回写 |
| “不要停下来确认” | 可逆只读步骤继续；高风险缺口升级 |
| “所有步骤都不能跳” | Driver 只执行当前 transition 必需步骤 |

## 可靠性模式

### 1. 渐进加载

薄核心只保存持续规则。路由命中后再读领域 Skill，需要时才读 references。避免
把所有能力和冲突指令一次性放进上下文。

### 2. 显式状态转换

使用 `discovered -> planned -> implemented -> verified -> released` 等状态。
Driver 在转换完成后失效，并把证据交给下一 Driver。

### 3. 确定性检查优先

优先使用编译、测试、lint、schema、hash、截图差异、清单比对和权限检查。不要
让实现者仅凭自然语言“自证完成”。

### 4. 新上下文 Verifier

以下情况使用独立 Verifier：

- Governed 通道；
- 判定器较弱；
- UI/文案等结果高度主观；
- 跨安全、生产或公开接口边界；
- 实现者持有可能影响判断的上下文。

### 5. Fail-closed 外部副作用

联网、安装、服务启动、生产变更、客户端全局配置和外部写入分别建模。未批准的
副作用保持关闭，不能通过一个笼统的“已授权”字段全部放开。

### 6. 可恢复状态

安装和发布流程保存受管文件清单、上一个锁定版本和回滚证据。失败时恢复已知状态，
并明确报告无法自动恢复的外部系统。

## 错误恢复

Agent 遇到阻力时：

1. 读取真实错误和当前状态，不猜路径或结果。
2. 判断失败是否改变风险、范围或外部副作用。
3. 在同一安全范围内尝试一个可解释的替代方案。
4. 重复失败时停止扩大尝试面，保留证据并升级。
5. 不以“完成任务”为理由关闭校验或跳过批准。

## 完成自检

声称当前状态转换完成前检查：

- 当前 transition Driver 是否唯一；
- 修改是否都在 write_scope 内；
- 外部副作用是否逐项获批；
- acceptance checks 是否真实运行并记录；
- 未验证边界是否明确披露；
- 是否需要独立 Verifier；
- 是否留下可回滚的受管状态。

“已读文档”不是“已执行操作”，“命令退出 0”也不一定等于业务结果正确。最终
结论必须对应可复现证据。
