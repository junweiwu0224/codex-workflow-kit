---
name: spec-kit-xl
description: Use when an XL task, formal product or engineering specification, durable PRD, long-lived acceptance criteria, large cross-module initiative, architecture migration, platform rewrite, or user-explicit spec/spec-kit request needs a versioned specification before Superpowers planning and execution. Do not use for normal bug fixes, small features, routine refactors, ordinary cross-file changes, or lightweight implementation plans.
---

# spec-kit-xl

## 目标

把大型、长期、跨模块或高风险任务先变成可版本化、可审查、可执行的规格说明。

这个 skill 只负责回答“要做什么、为什么、如何验收、有哪些约束”。规格确认后，再交给 Superpowers 的 planning、TDD、executing-plans、verification 流程处理“怎么一步步实现”。

## 适用边界

使用本 skill：

- XL 任务、新功能区域、大型重构、架构迁移、平台级改造。
- 需求可能持续多轮迭代，需要长期验收标准或 PRD。
- 大型跨模块事项，且涉及用户流程、API、数据模型、权限、安全、性能、部署或迁移。
- 用户明确要求 spec、PRD、验收标准、spec-kit、规格驱动开发。
- 实现前必须先对齐范围、非目标、风险、验证方式。

不要使用本 skill：

- XS/S/M 日常任务、普通 bug fix、小型 UI 调整、单文件改动。
- 普通跨文件改动或普通跨模块功能，只需要 Superpowers 轻量计划即可。
- 已经有清楚验收标准，只需要写实现计划的任务。
- Superpowers 的轻量 brainstorm、writing-plans、TDD 流程已经足够的任务。
- 只需要 ADR 的长期技术取舍；这种情况优先用 `decision-record`。

## 与 Superpowers 的关系

- 本 skill 在 Superpowers 写实现计划之前使用。
- 本 skill 不替代 `superpowers:writing-plans`，也不生成逐步代码任务。
- 规格达到 `Accepted` 后，使用 Superpowers 将规格转换为实现计划、测试策略和执行步骤。
- 如果执行中发现规格错误，先更新规格，再继续计划或实现。

## 工作流

1. 判断是否真的需要规格
   - 如果不是 XL/正式规格场景，说明将直接使用更轻量流程并继续任务。

2. 收集证据
   - 阅读用户请求、现有代码、README、AGENTS.md、docs、已有 issues/spec/ADR。
   - 对会变化的事实查当前一手来源。
   - 不确定内容标记为 `待确认`，不要编造成事实。

3. 起草规格
   - 新规格默认保存到 `docs/specs/YYYY-MM-DD-短名称.md`。
   - 如果仓库已有 `specs/`、`.specify/`、ADR 或产品文档惯例，沿用现有位置。
   - 小心写入仓库外部位置；除非用户明确要求全局模板。

4. 自检规格质量
   - 需求是否可测试。
   - 验收标准是否可验证。
   - 非目标是否足够防止范围膨胀。
   - 风险、迁移、回滚、观测是否覆盖到任务复杂度。
   - 是否遗漏安全、隐私、权限、性能、兼容性或数据影响。

5. 对齐状态
   - 如果存在关键开放问题，先给用户看规格草案和最少量问题。
   - 如果用户已经授权高自主推进，且开放问题不影响第一阶段实现，写入 `待确认` 并继续到计划。

6. 交接执行
   - 规格状态变为 `Accepted` 或用户确认后，使用 Superpowers 创建实现计划。
   - 执行完成后，用规格的验收标准做最终验证。

## 规格模板

```markdown
# <功能或项目名称> Spec

状态：Draft | Review | Accepted | Planned | Implemented | Superseded
负责人：
创建日期：
最后更新：
相关链接：

## 1. 背景和问题

- 当前状态：
- 用户/业务问题：
- 为什么现在要做：
- 证据来源：

## 2. 目标

- 目标 1：
- 目标 2：
- 成功后用户或系统能做到什么：

## 3. 非目标

- 本次不做：
- 明确不改变：
- 延后处理：

## 4. 用户和场景

- 主要用户：
- 次要用户：
- 核心场景：
- 失败/边界场景：

## 5. 需求

### 功能需求

- FR-1：
- FR-2：

### 非功能需求

- NFR-1 性能：
- NFR-2 安全/隐私：
- NFR-3 可用性/可访问性：
- NFR-4 兼容性：
- NFR-5 可观测性：

## 6. 验收标准

- AC-1：
  - Given：
  - When：
  - Then：
- AC-2：

## 7. 当前系统影响

- 相关模块：
- API/接口：
- 数据模型/存储：
- 前端/UX：
- 后台任务/队列：
- 配置/部署：
- 文档/支持：

## 8. 技术约束和原则

- 必须遵守：
- 推荐方向：
- 禁止方向：
- 需要沿用的现有模式：

## 9. 风险

- 安全/权限：
- 数据一致性：
- 迁移/回滚：
- 性能/容量：
- 兼容性：
- 依赖/外部服务：

## 10. 验证计划

- 单元测试：
- 集成/API 测试：
- E2E/用户流程：
- 前端视觉验证：
- 性能/负载：
- 安全/权限：
- 手动 smoke test：

## 11. 发布、迁移和回滚

- 发布策略：
- 数据迁移：
- Feature flag：
- 监控指标：
- 回滚方案：

## 12. 开放问题

- Q1：
- Q2：

## 13. 决策记录

- 已决定：
- 待 ADR：
- 被拒绝方案：
```

## 状态定义

- `Draft`：正在起草，允许有 `待确认`。
- `Review`：需要用户、团队或后续 agent 审查。
- `Accepted`：范围和验收标准已确认，可以进入计划。
- `Planned`：已有实现计划。
- `Implemented`：已实现并按验收标准验证。
- `Superseded`：被新规格替代，需链接替代文档。

## 写作规则

- 规格写“什么/为什么/如何验收”，不要提前写具体实现步骤。
- 技术约束可以写，但实现细节留给 Superpowers plan。
- 所有验收标准必须可观察、可测试。
- 使用编号 `FR-*`、`NFR-*`、`AC-*`，便于计划和测试追踪。
- 对事实和推断分开表达；推断要标明。
- 保持精炼。规格越大越要结构清晰，不靠堆字数显得完整。
- 如果一项决定会长期影响架构，触发 `decision-record` 写 ADR。
- 如果改动包含前端体验，验收标准必须包含真实浏览器或截图验证。
- 如果涉及用户数据、认证、权限、支付、密钥、生产配置，必须明确安全边界和回滚方式。

## 质量门禁

规格进入 `Accepted` 前，检查：

- 没有会阻塞第一阶段实现的关键 `待确认`。
- 每个目标至少有一个验收标准。
- 每个验收标准能映射到测试、截图、命令、日志或手动验证。
- 非目标能阻止最明显的范围蔓延。
- 风险章节覆盖了任务真实风险，而不是模板填空。
- 和 `AGENTS.md`、repo docs、已有 ADR 没有冲突。
- 下一步能自然交给 Superpowers 写计划。
