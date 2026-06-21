# Workflow Review

本文件记录这套 Codex Workflow Kit 的最终路线、完成状态、可复用范围、仍保持候选的能力，以及后续真实使用时的触发条件。

## 最终路线

```text
个人 Codex 宪法
-> 任务分级协议
-> repo context pack
-> Superpowers/spec-kit
-> 自定义核心 skills
-> 外部组件准入
-> MCP/代码图谱/memory
-> hooks 质量门禁
-> subagents 并行
-> usage/效果评估
-> real repo trial runs
-> 新机器演练
```

## 完成状态

已完成并打包：

- `global/AGENTS.md`：个人 Codex 宪法、任务分级、Superpowers/spec-kit 总控、MCP/memory/hooks/subagents 边界。
- `reverse-skill/`：完整逆向工程/安全分析能力树，保留 routing、子技能、CTF orchestrator、Burp/Ghidra bridge、bootstrap 脚本、platform docs 和 field journal 结构。
- `reverse-skill-router/reverse-engineering/SKILL.md`：全局 reverse router 入口，安装到 `~/.codex/skills/reverse-engineering/`，把 Desktop 侧逆向/渗透类请求稳定路由到 `~/.codex/reverse-skill/`。
- `repo-template/`：项目级 `AGENTS.md`、commands/testing/quality-gates/subagents/observability/mcp-pilot/usage/playbook/ADR/specs/glossary 模板。
- `skills/`：`repo-onboarding`、`spec-kit-xl`、`debug-loop`、`frontend-qa`、`decision-record`、`completion-review`、`security-review`、`dependency-upgrade-review`、`research-brief`、`skill-plugin-intake-review`、`release-readiness`、`junwei-frontend-design`、`junwei-browser-automation`、`junwei-product-demo-video`。
- `install.sh`：非破坏式安装器，支持 dry-run、自定义 Codex/Agents home、repo 模板安装、backup/force。
- `scripts/verify_toolkit.py`：包级自检，覆盖必需文件、manifest、14 个 skills、Superpowers 边界、外部组件准入、Junwei 前端/浏览器/demo 视频 workflow、release-readiness pilot、质量门禁模板、usage/observability/MCP/codegraph/memory pilot 复盘机制、生成缓存、私有路径和敏感模式。
- `scripts/audit_external_component.py`：只读外部组件准入扫描，用于 skill/plugin/MCP/hook/subagent prompt/workflow pack 的 promote/pilot/repo-local/hold/reject 判断。
- `scripts/benchmark_skill_polish.py`：对比 pre-polish `2026.06.12` release 和当前 post-polish tree，量化 skill count、Output Shape、accessibility、release readiness 和 progressive disclosure。
- `scripts/verify_live_install.py`：只读比较当前机器 `~/.codex/AGENTS.md` 和 `~/.agents/skills/` 是否与 output 包一致，用于发现 live install drift。
- `scripts/codex_runtime_smoke.py`：只读汇总本机 live install、local doctor、Codex CLI、可选 prompt-input skill 可见性和 `docs/agent-collaboration-smoke.md` 手动 agent smoke 证据。
- `scripts/audit_skill_contracts.py`：只读审计 14 个 packaged skills 的 metadata、trigger、Output Shape、边界、验证条件、progressive disclosure 和 Superpowers overlap 信号。
- `docs/agent-collaboration-smoke.md`：V3.1 subagent runtime 手动/HITL smoke checklist，覆盖 read-only dual explorer、No-Dispatch、local-write boundary、visibility policy、skill coupling 和 Lifecycle Ledger。
- `scripts/build_release.py`：刷新 `MANIFEST.sha256`，构建 release tarball 和 checksum。

已移除并保持移除：

- `implementation-plan` skill。计划、TDD、阶段推进和执行由 Superpowers 负责，个人 skills 只做专项补强。

## 可复用能力

以下内容已经通过真实仓库试跑和新机器演练，适合直接复用：

- 个人 Codex 宪法和任务分级：XS/S 不过度流程化，M/L/XL 使用 Superpowers 或 `spec-kit-xl`。
- repo context pack 模板：用于快速建立项目事实、命令、测试、架构、质量门禁和 usage 记录。
- context pack verifier：适合作为 A 级低副作用文档/context pack 门禁。
- 自定义核心 skills：作为 Superpowers 的补充，而不是替代总控流程。
- quality-gates 模板：按副作用分层，把 targeted tests 按受影响范围选择，不要求每次全部运行。
- V2.1 observability / MCP pilot 模板：把 usage/session 观测、长任务监控、MCP/code graph 试点写成候选和回退流程，不默认安装外部工具、不启用 hooks、不启动 MCP。
- V2.1 subagent prompt cards：为 read-only code mapper、test/debug investigator、frontend QA reviewer、docs/content-contract reviewer、architecture/migration reviewer 提供可复制 prompt，同时保留主 agent 集成和共享状态边界。
- V2.2 P0 专项 skills：`security-review`、`dependency-upgrade-review`、`research-brief` 补齐安全审查、依赖升级审查和生态研究选型缺口；它们不替代 Superpowers 计划/TDD/debug，不默认安装外部工具、不启用 hooks、不启动 MCP。
- install/release 流程：可在新机器解包、验证、dry-run、安装、live install drift 检查、重复安装和冲突保护。
- reverse-skill 迁移：通过保留独立子树和原相对路径，跨机器复用 reverse routing、bootstrap、MCP bridge 和 CTF 子技能，而不把能力摊平成噪音式平铺目录。
- Junwei 前端/浏览器/demo 视频 workflow：`junwei-frontend-design` 负责 taste/interface 和反模板化方向，`junwei-browser-automation` 负责浏览器证据、Playwright CLI/MCP 路由和安全边界，`junwei-product-demo-video` 负责产品 demo 视频脚本、录制输入、组合和渲染 QA。三者吸收精华，不照搬外部仓库，也不默认安装 Playwright MCP、DigitalSamba toolkit、云 GPU、API、voice cloning 或 publish 流程。

## 候选边界

以下能力保持文档化候选，不作为默认动作：

- hooks：默认不启用阻断型 hooks。只有 A 级、短耗时、稳定、无外部依赖、无业务数据写入、无隐藏产物的命令才考虑前移。
- MCP/代码图谱/memory：先用 repo context pack、`rg`、语言工具和测试建立临时上下文；只有重复收益明确、边界清楚、可回退时再增加长期服务。
- subagents：L/XL、已有实施计划、跨模块、多独立失败源、多文件审查和可并行调查必须先做 suitability check；AGENTS/AGENTS.override 中的长期授权即视为显式授权，本轮重复授权不是必要条件。只有 subagent 工具实际可用且未被平台权限阻止，并且存在 2 个以上互不重叠的独立子任务时，才主动使用 subagents；若当前会话没有加载到这类长期授权且本轮也未明确授权，记录 No-Dispatch Decision: tool permission constraint；这不包括已加载长期授权后缺少本轮重复授权。共享入口、schema/storage、应用生命周期、交易/生产路径由主 agent 串行控制。
- subagent lifecycle：主 agent 记录本轮派出的 agent id；收到结果、决定不采纳或不再需要时必须 `close_agent`，最终回复前检查是否还有未关闭 agent。只读 explorer / reviewer / 竞品观察也必须收口。
- observability：本地 usage、菜单栏状态、长任务监控、通知或 HUD 工具仅作为候选；必须确认本地日志读取范围、网络/后台行为和关闭方式后试用。
- `spec-kit-xl`：只用于 XL、正式规格、长期验收标准或用户明确要求规格文档的任务。
- browser/frontend QA：前端布局、CSS、交互、资源加载、跨 viewport 或用户可见风险较高时触发；纯 JS 契约或小 empty-state 改动可先用 targeted tests。
- Playwright MCP：仅作为 `junwei-browser-automation` 的 pilot 路径。默认先用 repo 测试、in-app Browser 或 Playwright CLI；只有持久浏览器状态、结构化 accessibility snapshots 或多步探索明显值得额外上下文/权限成本时才评估 MCP。
- 产品 demo 视频工具链：仅作为 `junwei-product-demo-video` 的 repo-local pilot。默认先做脚本、场景、capture plan 和本地 QA；安装 Remotion/FFmpeg wrapper、配置 API、cloud GPU、voice cloning、upload 或 publish 都必须另行确认。
- 大型 skill/subagent/security/SaaS 包：只作为研究素材或 repo-local 候选，不全局安装；优先把确定性检查放脚本/hooks 候选，把外部能力放 MCP pilot，把角色分工放 subagent prompt cards。

## V3.1 Delivery Review

V3.1 Core 的默认语义已锁定为文档规则、边界、prompt cards、只读审查能力和窄触发 skill；它不表示默认安装、启用、注册或启动外部工具。

必须保持以下术语边界：

- `promote != install`：吸收为规则、文档、只读脚本、prompt card、窄 skill 或模板边界，不等于安装外部组件。
- `pilot != enable`：试点必须有 baseline、权限级别、退出条件和回滚方式，不等于默认启用。
- `core != runtime/background`：core 不包含默认 MCP server、memory writer、code graph daemon、hook stack、plugin runtime、dashboard 或 watcher。
- `approved docs/script != approved external write`：文档或只读脚本获批，不等于允许外部写入、账号操作、生产操作或真实数据变更。

本轮 V3.1 吸收并打包：

- `docs/external-component-intake.md`：统一外部组件准入协议，覆盖评分维度、风险标签、加载预算、决策结果和拒绝线。
- `repo-template/docs/subagents.md`：升级 prompt cards，要求目标、范围、相关文件、allowed write set、off-limits、禁止事项、验证命令、输出格式和 lifecycle close。
- `docs/V3.1-AGENT-RESEARCH-20.md`：记录 20 个高星/流行 agent 仓库的本地源码研究证据，以及 promote/pilot/hold/reject 决策。
- Agent contract upgrade：`repo-template/docs/subagents.md`、`global/AGENTS.md` 和 `repo-template/AGENTS.md` 已吸收 Handoff Envelope、Return Envelope、History/Input Filter、Command/Tool Risk Policy、Step Budget / Stop Condition、Lifecycle Ledger 和 No-Dispatch Decision。
- `repo-template/docs/mcp-pilot.md`：增加 MCP/plugin 权限分级和 pilot 必填字段，默认从 docs-only 或 read-only local 评估。
- `repo-template/docs/quality-gates.md`：增加 hook review checklist、advisory/fail-open 初始模式和 external component gate。
- `repo-template/docs/codegraph-pilot.md`：把 code graph 定义为 orientation 试点，不替代 `rg`、源码回读、语言工具、测试和 repo docs。
- `repo-template/docs/memory-recall-pilot.md`：明确 repo facts first、provenance required、no raw logs、no secrets、no automatic memory write。
- `repo-template/docs/codex-usage.md`：增加 V3.1 pilot 记录模板，用真实任务信号判断 promote/pilot/repo-local/hold/reject。
- `scripts/audit_external_component.py`：只读审查外部组件，不安装、不启用、不联网、不写目标组件。
- `skills/skill-plugin-intake-review`：窄触发准入 skill，负责外部组件吸收前的 promote/pilot/repo-local/hold/reject 结论。
- `skills/debug-loop` 和 `skills/completion-review`：补 `goal drift`、`context drift`、`unsupported claim` 和 subagent lifecycle 自诊断/收口检查。
- `scripts/render_usage_row.py`：补 V3.1 pilot defaults：`codegraph`、`memory-recall`、`plugin-mcp-trust`、`agent-config-lint`、`domain-pilot`、`external-component-intake`。
- `scripts/render_usage_row.py`：新增 `subagent-contract`、`agent-lifecycle-ledger`、`agent-eval-evidence` pilot rows，用于记录 agent handoff/return、close hygiene 和 eval evidence。
- `scripts/render_usage_row.py trial`：新增真实 M/L/XL 试跑记录行，用于记录 efficiency signal、friction 和 keep/tighten/loosen/remove 决策。
- `docs/codex-usage.md`：记录本 toolkit 仓库 4 个 V3.1 实战样本和阶段复盘，和 `repo-template/docs/codex-usage.md` 模板分离。
- `scripts/benchmark_agent_contract.py`：对比 `2026.06.12.1` 和当前 tree，量化 agent contract coverage。
- `skills/release-readiness`：新增 pilot 级 artifact evidence gate，用于 reusable artifact、portable toolkit、release archive、checksum bundle、install drill、rollback 和 release evidence，不替代生产发布审批。
- Skill polish：`debug-loop` 补 Feedback Loop First / deterministic loop / regression test / Output Shape；`completion-review` 补 Artifact / Release Evidence Gate；`frontend-qa` 补 Keyboard / Focus / Contrast / ARIA / Reduced motion；`decision-record` 补 ADR Output Shape / Completion Conditions；`repo-onboarding` 区分 minimal context pack 和 optional context pack；`spec-kit-xl` 将完整模板移到 `references/spec-template.md`。

本轮仍明确拒绝：

- 新 orchestrator、planner、dispatcher、queue 或 agent swarm。
- 恢复 `implementation-plan` 或换名恢复同类总控。
- 默认阻断 hook stack、默认 MCP server、默认 memory writer、默认 code graph daemon、默认 background dashboard/watcher。
- 批量安装外部 skill/plugin/catalog、默认 marketplace installer/manager。
- 自动 PR、ticket、deploy、production write、账号/权限/支付/密钥操作。
- 自动学习并写入全局规则、memory 或多层指令文件。
- 复制 GPL/unknown license 正文或未确认授权资产进 portable kit。

V3.1 verifier/tests/README/QUICKSTART/VERSION/MANIFEST/release 必须同步通过；文档层通过不再单独视为完成。

## V3.2 Reverse Merge

本轮 v3.2 的核心收口是把 Codex Desktop 当前 `reverse-skill` 相关文件并入 workflow-kit，同时保留全量逆向能力，不把它退化成“只有一个 router skill 的薄壳”。

合并原则：

- 保留独立 `reverse-skill/` 子树，不把内容硬塞进 `skills/` 平铺层。
- 保留关键 bridge/runtime 文件：`burp-mcp-full/mcp-bridge.js`、`ghidra-mcp/headless/ghidra_headless_mcp.py`、CTF orchestrator、bootstrap 脚本、field journal、平台文档。
- 排除机器态和生成噪音：`.venv/`、`__pycache__/`、`.pyc`、生成的 `tool-index.md/json`、`.bak-*`、`.DS_Store`。
- 安装器把 reverse pack 落到 `~/.codex/reverse-skill/`，把 router 落到 `~/.codex/skills/reverse-engineering/`，避免破坏原有路径假设。
- live verifier 把 global AGENTS、11 个个人 skills、reverse router、reverse pack 和活跃插件路径一起校验，避免“仓库里有文件但 Desktop 里没接上”。
- `install.sh --with-reverse-core` 提供新机器 `reverse-ready` 安装档：文件安装完成后，再 bootstrap 一批高频 reverse core 工具，并自动调用 `scripts/verify_reverse_ready.py` 做机器级只读检查。
- `install.ps1` 提供 Windows 顶层安装入口，复用同一套 global AGENTS / skills / reverse pack / repo-template 安装语义，并可透传 `-WithReverseCore`、`-VerifyReverseReady` 到 Windows PowerShell bootstrap 路径。

## V3.2 Frontend Browser Video Workflow

本轮 v3.2 同时把高星/流行前端和 demo 生产素材吸收到 Junwei 个人 workflow，但吸收方式是“吸收精华，不照搬”：

- `junwei-frontend-design`：吸收 Anthropic `frontend-design` 和 Leonxlnx `taste-skill` 的强项，形成个人高审美前端设计层，覆盖模式路由、反 AI 模板化、设计方向、review rubric 和固定验证案例。
- `junwei-browser-automation`：吸收 `microsoft/playwright-mcp` 的结构化页面检查、accessibility snapshot 和持久浏览器状态价值，但不默认添加 MCP config；它是浏览器工具路由层，优先 tests / in-app Browser / Playwright CLI，再按证据决定 Playwright MCP pilot。
- `junwei-product-demo-video`：吸收 `digitalsamba/claude-code-video-toolkit` 的视频生产生命周期、Playwright recording、Remotion/FFmpeg、scene review、brand/audio/render QA 思路，但不 vendor 外部 toolkit，不默认全局安装，不触发 cloud GPU、paid API、voice cloning 或 publish。

Role Separation:

- Design direction: `junwei-frontend-design`.
- Browser evidence and recordings: `junwei-browser-automation`.
- Demo narrative, scenes, render QA: `junwei-product-demo-video`.
- Final browser/UI verification: `frontend-qa` or project tests, with `completion-review` before delivery.

No-Conflict Matrix:

- UI task without video: use `junwei-frontend-design`, then `frontend-qa` or tests.
- Browser smoke/automation without design change: use `junwei-browser-automation`, not the design skill.
- Demo video from product UI: use `junwei-product-demo-video`; call `junwei-browser-automation` only for capture inputs.
- External tool absorption: use `research-brief` + `skill-plugin-intake-review`; security-sensitive MCP/video boundaries require `security-review`; release/package work requires `release-readiness`.

## 真实验证

已完成的验证层：

- toolkit 自检：`scripts/verify_toolkit.py` 输出 `Workflow toolkit OK`。
- live install 自检：`scripts/verify_live_install.py` 输出 `Live install OK`，确认全局 AGENTS、14 个 skill 入口、reverse router、reverse pack 和 packaged skill assets 与 output 包一致。
- repo-template 自检：`repo-template/scripts/verify_context_pack.py repo-template` 输出 `Context pack OK`。
- toolkit tests：覆盖 toolkit 自检、manifest/release、安装器 preflight、质量门禁模板和 workflow review。
- repo-template tests：覆盖 context pack verifier。
- 新机器演练：`2026.06.13.2` release checksum 通过；临时解包后 toolkit 自检通过；安装到临时 Codex/Agents/repo 成功；live install、doctor、runtime smoke、skill contract audit 和目标 repo context pack 均通过；旧版演练也覆盖过第二次安装跳过相同文件、冲突安装返回失败且不会提前写入 Codex/Agents home。
- reverse merge drill：v3.2 安装路径新增 `~/.codex/skills/reverse-engineering/` 和 `~/.codex/reverse-skill/`，由 `verify_live_install.py` 逐文件比对，避免 reverse router 漂移或 reverse pack 缺文件。
- reverse-ready drill：`install.sh --with-reverse-core` + `scripts/verify_reverse_ready.py` 把“文件已安装”推进到“高频逆向工具链已尽量补齐”；报告仍明确区分 core tools、optional tools 和 MCP 配置缺口，不把半自动状态伪装成全自动。
- APK decode smoke：`scripts/verify_apk_decode_smoke.py --apk-fixture <apk>` 真实调用已安装 reverse pack 的 `decode.sh`，要求 `apktool_exit_code=0`、`package` 非空、`smali_dirs > 0`，补上 fresh install APK 主链的最终闭环。
- Skill polish benchmark：`scripts/benchmark_skill_polish.py` 输出显式 contract points `17 -> 53`，增量 `+36`，`+211.76%`；其中 Output Shape `4 -> 11`，accessibility `0 -> 5`，release readiness `0 -> 6`，progressive disclosure `0 -> 3`。
- Agent contract benchmark：`scripts/benchmark_agent_contract.py` 输出显式 agent contract points `5 -> 114`，增量 `+109`，`+2180.0%`；其中 20-repo research source coverage `0 -> 20`，prompt card contract coverage `0 -> 40`，verifier contract checks `0 -> 7`，usage pilot defaults `0 -> 3`。
- Local Codex smoke：`docs/V3.1-LOCAL-CODEX-SMOKE-REPORT.md` 记录本机 `codex-cli 0.140.0-alpha.2`、live install、prompt-input skill 可见性、三个只读 subagent 的 return/close 证据，以及 `codex_doctor.py` bytecode 修复。结论是 V3.1 skills 和 subagents 可配合使用，但 runtime envelope enforcement 仍依赖主 agent prompt/review/close。
- Runtime evidence split：`scripts/codex_runtime_smoke.py` 将 package integrity 之外的 live install、doctor、Codex CLI、prompt-input 和手动 agent smoke 分层记录；`scripts/audit_skill_contracts.py` 输出 14/14 skill contract audit OK，避免后续 skill polish 只靠人工 `rg`。
- V3.1 real usage calibration：`docs/codex-usage.md` 记录第一阶段 4 个 M/L 实战样本和 closeout 4 个 M/L 实战样本。结论是保留 package verifier、runtime smoke、skill audit、release-readiness 和 render-only `render_usage_row.py trial --preset`；继续把 No-Dispatch、Local-Write Boundary、Visibility Policy 留在 HITL checklist，不做伪自动化，不给 usage row 增加自动追加写入。

已校准的副作用判断：

- A 级：context pack verifier、无写入 targeted tests、确认无产物的 lint/typecheck。
- B 级：coverage、静态报告、截图、trace、会写 ignored 报告的扫描。
- C 级：TestClient/app health/dev server/preview server，可能触发应用生命周期、本地 DB、缓存、端口或后台任务。
- D 级：外部服务、真实数据同步、迁移、部署、权限、交易、支付、生产或凭证相关操作。

## 触发条件

在新仓库中按以下方式使用：

- 首次进入仓库且上下文不足：使用 `repo-onboarding` 建立 context pack。
- XS/S 任务：直接读相关文件、做最小改动、跑 targeted verification。
- M 任务：使用 Superpowers 做轻量澄清、TDD/实现和验证；必要时记录 usage 信号。
- L 任务：先调查影响范围，再由 Superpowers 写计划并推进；长期取舍用 `decision-record`。
- XL/正式需求：先用 `spec-kit-xl` 写规格，规格确认后再交给 Superpowers 写计划和执行。
- 测试、构建、启动、E2E 或运行失败：进入 `debug-loop`。
- 前端用户可见风险：使用 `frontend-qa`，必要时浏览器截图或多 viewport 验证。
- 创建、重做或打磨 UI/视觉/页面/app/tool/game 前端设计：使用 `junwei-frontend-design` 先定模式、审美方向、反模板化风险和验收重点；验证阶段仍使用 `frontend-qa` 或项目测试。
- 浏览器自动化、Playwright、MCP-vs-CLI、localhost UI inspection、可重复 walkthrough 或 demo capture 输入：使用 `junwei-browser-automation`，默认不启用 Playwright MCP。
- 产品 demo、demo video、walkthrough recording、Remotion render、launch/sprint review 视频或 video QA：使用 `junwei-product-demo-video`，默认不安装 DigitalSamba toolkit、不发布、不配置云 GPU/API/voice cloning。
- 安全敏感代码、配置、依赖、hooks、MCP/plugin、CI、认证、权限、密钥、用户数据、支付、生产配置、外部写入或信任边界变化：使用 `security-review`。
- 新增、删除、升级、固定或审计依赖、lockfile、Docker base image、GitHub Actions、vendored code、CVE/advisory、license 或供应链风险：使用 `dependency-upgrade-review`。
- 评估 GitHub 仓库、skills、MCP、hooks、subagents、模型/API、工具或生态现状，并需要 promote/hold/reject 判断：使用 `research-brief`。
- 完成实现和验证后：使用 `completion-review` 再最终回复。
- 每 3-5 个代表性任务后：更新 `docs/codex-usage.md`，决定是否把候选晋升到 repo 规则、quality gates、hooks、skills 或 memory。
- 试用 V2.1 候选工具后：用 `scripts/render_usage_row.py pilot --pilot observability|subagents|mcp-code-graph` 记录证据；没有重复收益前不晋升默认自动化。

## 新机器演练

推荐迁移命令：

```bash
cd codex-workflow-kit
python3 scripts/verify_toolkit.py
./install.sh --dry-run
./install.sh
python3 scripts/verify_apk_decode_smoke.py --apk-fixture /path/to/app.apk
```

Windows:

```powershell
powershell -ExecutionPolicy Bypass -File .\install.ps1 -DryRun
powershell -ExecutionPolicy Bypass -File .\install.ps1 -WithReverseCore -VerifyReverseReady
python scripts/verify_apk_decode_smoke.py --apk-fixture C:\path\to\app.apk
```

给某个仓库安装 context pack：

```bash
./install.sh --repo /path/to/repo --dry-run
./install.sh --repo /path/to/repo --backup
cd /path/to/repo
python3 scripts/verify_context_pack.py
```

默认安装器是非破坏式的：遇到不同内容会先报冲突，不会覆盖。`--backup` 用于保留旧文件后替换，`--force` 只在确认覆盖时使用。

## V2 Adoption Review

Evidence source:

- Baseline toolkit: `python3 scripts/verify_toolkit.py` 输出 `Workflow toolkit OK`；current release checksum 输出 `codex-workflow-kit-2026.06.13.2.tar.gz: OK`。
- Trial repo scan: 找到 `ai-quant-trading`、`coze-studio`、`ai-workflows`、`dify`、`dify-plugin-daemon` 5 个候选仓库。
- Dry-run install: `ai-quant-trading` 和 `dify` 因已有 `AGENTS.md` 正确报冲突；`coze-studio` 因 dirty worktree 暂缓。
- Dirty-worktree-aware audit: `ai-workflows` 和 `dify-plugin-daemon` 输出 `repo-only-install`、findings 为 0。
- External baseline install: `ai-workflows` 和 `dify-plugin-daemon` 已完成 `--repo-only --backup` 安装，`python3 scripts/verify_context_pack.py` 输出 `Context pack OK`，并写入 baseline usage row。
- Repo-specific onboarding calibration: `ai-workflows` 已校准为 docs-only workflow repo；`dify-plugin-daemon` 已校准为 Go daemon/CLI repo，并记录 manual-only test policy、runtime 边界、CI 命令和 generated-code 边界。两者复跑 `python3 scripts/verify_context_pack.py` 均输出 `Context pack OK`。
- First calibrated-repo task: `dify-plugin-daemon` 已完成 “Align Go version docs with go.mod/CI”，修正 `CLAUDE.md` stale Go version，并用 targeted `rg` 搜索和 context pack verifier 验证；Go tests 按 repo policy 未自动运行。
- Second calibrated-repo task: `ai-workflows` 已完成 “Guard README agent instruction append snippets”，通过红绿静态测试保护 README 安装命令，避免重复追加 agent 指令。
- Third calibrated-repo task: `dify-plugin-daemon` 已完成 “Lock manual-only Go test policy with static docs test”，用 Python 静态测试锁住 Go tests 不进默认 hooks 的 repo policy。
- Fourth calibrated-repo task: `dify-plugin-daemon` 已完成 “Validate CLAUDE.md repo paths with static docs test”，用 Python 静态测试锁住 `CLAUDE.md` 中 inline code 和 shell block 的 repo 路径，修正 stale architecture path 和命令示例漂移。
- Fifth calibrated-repo task: `ai-workflows` 已完成 “Make raw workflow downloads fail fast”，用 Python 静态测试锁住 README raw workflow 下载命令必须使用 fail-fast curl flags。
- First Adoption Review: 基于 3 条 calibrated repo M 级任务，晋升 narrow static docs/content-contract tests 为 repo-specific gate candidates；继续拒绝 blocking hooks、MCP/code graph/memory、无边界 subagents 默认启用和 `go test` default hooks。
- Second Adoption Review: 基于 5 条 calibrated repo M 级任务，将 static docs/content-contract tests 明确晋升为 repo-specific gate candidates，并更新 repo-template 质量门禁/测试模板；仍不默认启用 blocking hooks、MCP/code graph/memory、无边界 subagents、full Markdown lint 或 link checker。
- Post-V2 subagent refinement: live global AGENTS 和 portable toolkit 已加入 proactive subagent suitability check；大型或可并行任务必须主动评估，dispatch 受当前运行时或工具权限门禁约束。存在 2 个以上独立非重叠子任务且工具允许主动派发时才主动 dispatch，不使用时说明原因，最终集成和 diff review 仍由主 agent 负责。
- Final V2 Completion Audit: 对 V2 plan 10 个阶段逐项审计，确认当前完成的是证据驱动、可迁移、可验证的 V2 package，而不是扩大默认自动化。
- Post-V2 Practical Calibration: 3 个大型只读校准样本覆盖 `ai-quant-trading` LocalMCP/前端动作链、`ai-workflows` workflow/docs 阶段复盘、`dify-plugin-daemon` serverless runtime 跨模块图谱；结论是 subagents 对 L 级边界发现有收益，frontend QA 只对真实前端风险强制，MCP/code graph 不默认启用。
- Post-V2.2 subagent lifecycle fix: 真实检查发现只读观察 agent 完成或不再需要后可能停留 running；live/toolkit 规则已补充派出 id 记录、结果集成后 `close_agent`、最终回复前 lifecycle check。
- Real usage evidence: `ai-quant-trading/docs/codex-usage.md` 已有 context pack、质量门禁、副作用分级、subagents 边界和 5 个真实实现任务记录。

Promotions:

- `install.sh --repo-only`：用于全局工具已安装后，只给新仓库落地 context pack，减少多仓库 dry-run 输出噪音和写入面。
- `repo-template/scripts/verify_context_pack.py`：将 `docs/architecture.md` 纳入必需文件，和 repo 模板、Quickstart、AGENTS 引用保持一致。
- `scripts/audit_repo_adoption.py`：提供只读 repo adoption preflight，在写入目标 repo 前区分 `repo-only-install` 和 `manual-merge`，并检查 dirty worktree。
- `scripts/render_usage_row.py`：生成标准 baseline usage 行，安装后可追加到目标 repo 的 `docs/codex-usage.md`，减少多 repo 首次采用记录漂移。
- Static docs/content-contract tests：作为 repo-specific gate candidates 写入模板，用于保护安装说明、路径引用、命令示例、README 安全约束和 repo policy 标记。

Rejections:

- 不把 hooks 默认启用；当前证据支持候选集和 side-effect audit，不支持阻断型自动启用。
- 不把 MCP/code graph/memory 默认启用；当前证据显示多数问题可先用 repo docs、`rg`、语言工具和 targeted tests 解决。
- 不把 subagents 设为无条件默认实现路径；但 L/XL、已有实施计划、跨模块或多独立失败源任务必须主动评估，边界清晰、存在 2 个以上独立子任务且 subagent 工具实际可用、未被平台权限阻止时才主动使用。

Remaining candidates:

- 将 toolkit 应用到另一个代表性 repo 前，先处理 dirty worktree 或已有 `AGENTS.md` 冲突；不要机械覆盖。
- 对已有 `AGENTS.md` 的大型 repo，优先人工合并而不是 `--backup` 机械替换。
- 如果两个以上真实 repo 都证明同一条规则稳定减少误判，再考虑升级到全局 `AGENTS.md` 或个人 skill。
