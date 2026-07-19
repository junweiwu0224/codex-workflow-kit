---
name: completion-review
description: Use when implementation and verification are complete and Codex is preparing the final response for code, docs, config, automation, frontend, security, data, build, or cross-file work.
---

# completion-review

## 目标

在任务最终回复前，确认目标已经真正完成、验证已经足够、风险已经说明、需要沉淀的项目知识已经处理。

这个 skill 是交付前闸门，不替代测试、debug、frontend QA、Superpowers 计划或人工 review。

## 触发场景

在以下情况触发：

- 完成代码修改、文档修改、配置修改或自动化任务后，准备给用户最终回复前。
- 中大型任务、跨文件任务、前端任务、安全/数据/构建相关任务完成后。
- 用户要求“确认完成”“收尾”“最终检查”“交付前 review”。
- Superpowers 或其他流程已经完成实现和验证，需要最终收口。

不要在实现前或验证前触发，除非用户明确要求先做完成标准检查。

## 执行时机

标准顺序：

```text
实现 -> 针对性验证/测试 -> 修复失败 -> 必要时更全面验证 -> completion-review -> 最终回复
```

如果本 skill 发现验证缺失或不足，应先补做验证，再重新执行完成检查。

## 检查清单

### 0. Evidence Gate

- No diff, no review：代码、文档或配置任务在最终回复前必须查看实际改动证据，例如 `git diff`、文件列表、manifest 变化、命令输出或当前文件内容；不能只凭记忆说完成。
- 如果当前目录不是 git repo，也要用文件清单、验证器、release manifest、archive listing 或 targeted readback 替代 diff。
- 最终回复中的每个完成声明都应能指向一个文件、命令结果、截图、日志、归档内容或明确的未验证说明。
- 检查是否有生成物、缓存、临时文件、无关格式化或用户未要求的依赖/配置变化混进交付。

### 0.1 Artifact / Release Evidence Gate

如果任务交付的是可复用 artifact、toolkit、release archive、安装包、文档包、脚本包或迁移包，必须额外确认：

- `VERSION`、manifest、archive、checksum、install docs 和 release notes / evidence docs 彼此一致。
- 至少跑过 package verifier；如果包声称可安装，还要跑 dry-run install 和 live install / unpack drill。
- archive listing 或解包后的文件树包含新增文件、引用资源和脚本权限；没有遗漏 `references/`、`scripts/`、assets 或 verifier tests。
- 最终回复要说明 artifact 路径、checksum 验证、安装验证和未覆盖的发布风险。
- 这不是生产 deploy 许可；涉及外部发布、账号、权限、生产配置或真实用户影响时仍需用户确认。

### 1. 目标完成度

- 用户最初目标是否已经完成？
- 是否存在被遗漏的子任务？
- 是否有新增问题导致目标没有真正达成？
- 实际完成内容是否和用户请求一致？
- 是否存在 `goal drift`：最终答复回答的是旧目标、缩小后的目标或中途产生的方便目标？
- 长线程或上下文压缩后是否发生 `context drift`：需要回读最新用户请求、当前 goal、计划和当前文件状态。
- 是否存在 `unsupported claim`：声称已完成、已验证、已关闭或已发布，但没有对应文件、命令、manifest、截图、release 或工具返回证据？
- 如本轮使用 subagents，是否完成 subagent lifecycle 检查：记录 id、review 结果、集成/丢弃结论，并在不再需要时 close。

### 2. 改动范围

- 改动是否集中在相关文件和模块？
- 是否出现无关重构、格式化噪音、依赖升级或元数据改动？
- 是否保留了用户已有改动？
- 是否有生成文件、锁文件、快照或配置文件被意外修改？

### 3. 验证充分性

- 是否运行了与改动最相关的验证？
- 验证命令是否成功？
- 如果验证失败，是否已经进入 debug loop 并复测？
- 是否需要更全面验证，例如 build、typecheck、lint、E2E、集成测试？
- 如果无法验证，是否有明确原因和残余风险？

### 4. 前端和用户可见行为

如果改动影响前端/UI/视觉/交互：

- 是否执行了 frontend QA？
- 是否检查了实际受影响页面，而不是只看首页？
- 是否至少考虑桌面和移动端？
- 是否检查 loading、empty、error、success、long content 等关键状态？
- 是否检查 console/runtime 错误和资源加载？

### 5. 安全、数据和生产风险

如果改动涉及认证、权限、支付、数据库、迁移、生产配置、密钥、日志、用户数据：

- 是否遵守最小权限和最小改动？
- 是否避免暴露敏感信息？
- 是否需要用户确认但尚未确认？
- 是否需要额外测试、review 或 rollout 说明？

### 6. 文档和知识沉淀

- 项目命令、架构、测试策略是否发生变化？
- 是否发现应该更新 `AGENTS.md`、`docs/commands.md`、`docs/testing.md`、`docs/architecture.md` 或 `docs/codex-playbook.md` 的长期知识？
- 是否出现需要 ADR 的长期技术取舍？
- 如果明显应该沉淀，是否已经更新合适文件？
- 如果不适合当前直接更新，是否在最终回复中说明建议？

### 7. 最终回复质量

最终回复应包含：

- 结果：完成了什么。
- 关键改动：主要文件或模块。
- 验证：运行了什么，结果如何。
- 未验证内容：如果有，说明原因。
- 残余风险：如果有，说明。
- 具体后续：只有当自然衔接当前任务时才提出。

## 打回规则

发现以下情况时，不要直接最终回复，先继续处理：

- 没有运行任何相关验证，且验证可运行。
- 前端改动没有实际页面/组件验证，且验证可行。
- 验证失败但没有调查。
- 用户目标明显没有完成。
- 出现无关改动且未处理。
- 有明显应该沉淀到 repo `AGENTS.md` 或 docs 的长期知识但尚未处理。
- 触及高风险红线但没有用户确认。

## 允许最终回复的条件

满足以下条件时可以最终回复：

- 用户目标已经完成，或未完成原因已明确且无法继续自行推进。
- 相关验证已成功，或无法验证的原因和风险已说明。
- 无关改动已避免或解释。
- 安全/数据/生产风险已处理或标明。
- 必要的项目知识沉淀已完成或已提出具体建议。

## Output Shape

最终回复前，用这个形状自检并压缩成用户可读结果：

- Result：目标是否完成，交付物在哪里。
- Changed：关键文件、模块、artifact 或 release archive。
- Verification：运行过的测试、lint、build、verifier、browser QA、checksum、install drill 或 readback。
- Evidence：diff、manifest、archive listing、截图、日志、命令输出或明确的未验证说明。
- Risk：残余风险、用户确认红线、外部依赖或未执行项。
- Follow-up：只有自然衔接当前任务时给出具体下一步，不写空泛建议。

## 不要做

- 不要把 completion-review 当成计划阶段。
- 不要用它替代测试或 frontend QA。
- 不要在验证缺失时直接说“完成”。
- 不要为了收尾而隐藏失败、跳过风险或淡化未验证内容。
- 不要加入空泛后续建议。
