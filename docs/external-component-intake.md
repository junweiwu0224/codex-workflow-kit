# External Component Intake

本文件定义 V3.1 外部组件准入协议。它适用于外部 skill、plugin、MCP server、hook、subagent prompt、脚本、模板、workflow 仓库或领域规则被吸收到 V3.1、全局规则、repo-template、个人 skill、hook、MCP pilot 或 output toolkit 之前。

## Core 语义

V3.1 Core 默认只加入规则、边界、prompt cards、只读审查能力和窄触发 skill。

`promote` 不等于 install 或 enable。它只表示吸收为文档规则、只读脚本、窄 skill、repo-template 指南或 pilot 边界。任何真实 MCP、memory、code graph、hook、plugin、外部 skill 安装或启用，都必须作为单独 pilot 再确认。

## 适用范围

使用本协议：

- 外部组件准备进入 V3.1、全局 AGENTS、个人 skill、repo-template 或 output toolkit。
- 外部工具准备作为 MCP、hook、memory、code graph、plugin 或 subagent 模式试点。
- 领域 skill 或 skill library 准备从参考资料升级为可复用规则。
- research-brief 已经给出候选，需要做最终吸收判断。

不使用本协议：

- 普通阅读外部资料。
- 临时引用官方文档或源码事实。
- repo-local 实现细节可以直接从当前仓库和测试判断。

## 评分维度

每个候选按 0-3 分辅助评分，分数只辅助判断，不替代证据。

| 维度 | 0 | 1 | 2 | 3 |
|---|---|---|---|---|
| `v31_fit` | 无关 | 有启发但间接 | 可复用模式 | 直接补 V3.1 缺口 |
| `user_value` | 价值不清 | 小便利 | 明显减少返工或风险 | 显著降低沟通、误判或漏测 |
| `portability` | 难迁移 | 依赖特定项目 | 可适配 | 可安全进入 toolkit |
| `safety` | 高风险默认 | 严格限制可控 | opt-in 低风险 | 本地只读、无认证、无写入 |
| `non_overlap` | 直接重复 Superpowers/V2.2 | 部分重叠 | 互补 | 明确补空档 |
| `evidence_quality` | README/营销 | 源码可读 | 源码+测试/配置 | 本地验证或清晰契约 |

## 风险标签

每个候选必须标注：

- `license`: SPDX、missing、unknown、GPL/viral-risk。
- `auth`: none、optional、required、broad。
- `side_effect`: docs-only、read-only、writes-local、writes-external、production-risk。
- `daemon`: none、optional、required/background。
- `network`: none、optional、required。
- `install`: none、package-manager、curl-script、binary、docker。
- `superpowers_overlap`: none、possible、direct。
- `v22_conflict`: none、possible、direct。
- `private_path_secret`: none、possible、confirmed-redacted。

## 决策结果

- `promote`: 明确低风险、反复有价值、与 V2.2 互补，可进入 docs/script/narrow skill/repo-template。
- `pilot`: 有潜力但需要边界、试点指标、回滚和真实 usage evidence。
- `repo-local`: 只适合特定项目，不进入全局或 portable kit。
- `hold`: 证据不足、收益不清或等待更好来源。
- `reject`: 与 Superpowers/V2.2 冲突、风险过高、license 不适合、触发过宽或有更小吸收面。

## 组件加载预算

通过准入后，还要决定加载层级：

- `DAILY`: 当前 repo 高频、低风险、明确触发、能减少返工，可放入默认规则或常用 prompt。
- `LIBRARY`: 有价值但低频、领域特定或触发不稳定，只保留为可搜索参考或手动调用。
- `REJECT`: 风险、冲突、license、安装面或触发面不合格。

不要把 `LIBRARY` 伪装成默认加载内容。不要做第二套安装器，不自动移动、删除、安装或启用 skills。

## 吸收面

优先选择最小安全吸收面：

- `docs`: 规则、边界、checklist、playbook。
- `read-only script`: 确定性扫描、审查、渲染、验证。
- `narrow skill`: 触发明确、输出固定、边界窄。
- `repo-template`: 项目级文档、验证或 usage 记录。
- `pilot`: 有试点条件、退出条件和回滚。
- `hook`: 只允许快速、确定、本地、低误报、低副作用检查。
- `mcp/plugin`: 只读优先，外部写入单独确认。
- `do-not-absorb`: 价值不足或风险不值得。

## Skill / Plugin Intake Review

审查 skill/plugin 时检查：

- `SKILL.md` frontmatter 是否存在、name 是否匹配、description 是否有明确触发和负边界。
- `references/`、`examples/`、`scripts/`、`assets/` 是否按 progressive disclosure 分层。
- scripts 是否包含网络、安装、Docker、curl-to-shell、daemon、外部 API、全局写入或生产命令。
- plugin manifest 是否声明 apps、MCP、permissions、assets、repository、license 和 install 面。
- 是否与 Superpowers 的计划、TDD、阶段推进、验证总控重叠。
- 是否需要 `research-brief`、`security-review` 或 `dependency-upgrade-review` 协同。

## MCP / Plugin Trust Scoring

初筛只做本地只读 trust summary，不联网、不阻断、不修改配置：

- config 是否能 parse。
- server/tool 是否有明确名称。
- command/endpoint 是否明确。
- 是否有 dangerous command、postinstall、curl-to-shell、daemon/background。
- 是否有明文 secret、token、API key 或 private path。
- 是否需要 auth、external read、external write 或生产权限。
- 是否有 insecure transport 或 browser/account/cookie 状态读取。

分数不能作为唯一决策，必须保留 evidence paths 和 recommended decision。

## Domain Skill Boundary

领域 skill 先分类：

- `repo-local checklist`
- `optional prompt card`
- `narrow skill candidate`
- `reject`

高风险领域必须显式标注：medical、legal、finance、cybersecurity、infrastructure、production operations。

不复制 GPL/unknown license 正文，不安装领域大包，不默认联网，不让领域 prompt 覆盖 `research-brief`、`frontend-qa`、`security-review` 或人工判断。

## 明确拒绝线

V3.1 默认拒绝：

- 新 orchestrator、planner、dispatcher、queue。
- 恢复 `implementation-plan` 或换名恢复。
- 默认阻断 hook stack。
- 默认 MCP server。
- 默认 memory writer。
- 默认 background daemon、dashboard、watcher。
- 批量安装外部 skill、plugin、catalog。
- marketplace installer/manager 默认形态。
- 自动 PR、ticket、deploy、production write。
- 自动学习并写入全局规则。
- 自动层级 memory 或自动创建多层指令文件。
- GPL/unknown license 正文复制进 portable kit。

## 输出模板

```text
External component intake:
- Candidate:
- Source/evidence checked:
- Scores:
- Risk tags:
- Loading budget: DAILY / LIBRARY / REJECT
- What is good:
- Why it matters:
- What to absorb:
- How to absorb:
- Decision: promote / pilot / repo-local / hold / reject
- Required safeguards:
- Verification:
- Open questions:
```

