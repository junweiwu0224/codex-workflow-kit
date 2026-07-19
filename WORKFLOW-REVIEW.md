# Workflow Review

本文件记录这套 Codex Workflow Kit 的最终路线、完成状态、可复用范围、仍保持候选的能力，以及后续真实使用时的触发条件。

## 最终路线：当前 V4.2

```text
薄 global/AGENTS.md
-> Fast / Standard / Governed Policy Router
-> 分级 Task Contract
-> 当前状态转换的唯一 Driver
-> Overlay / Guardrail
-> Deterministic Checks
-> Verifier Policy
-> lifecycle / release evidence / rollback
```

治理事实按 `catalog -> resolver -> lock -> eval report -> release manifest` 流动。Catalog 表达期望，lock 表达已解析内容，eval report 表达运行证据，release manifest 表达实际发布内容；四者不能互相冒充。

## 完成状态：当前实现

V4.2 当前是 **implementation candidate**，不是“proven optimal”或已公开发布的 Stable 套件。

已进入工作树并有机器验证的能力：

- `global/AGENTS.md` 已收敛为风险路由、安全边界、验证和协作原则；按需细节由 Skill 和 repo context 提供。
- `catalog/components.yaml` 记录 14 个 packaged Skill 的 owner、角色、状态、隐式调用、网络、写入和 License；Skill frontmatter 只保留规范字段。
- `catalog/upstreams.lock.json` 和 `catalog/reverse-dependencies.lock.yaml` 分别记录 repo-local 内容 hash 与 reverse 精确依赖；无法验证 digest 的容器保持 blocked，不会静默安装。
- Policy Router、Task Contract schema/validator、单 transition Driver、runtime policy gate 和 hash-chained event log 已实现；关键审批或 enforcement 缺失时 fail closed。
- Eval Harness 支持 clean HOME/worktree、paired 随机顺序、Shadow、held-out、重复稳定性、盲评包、安全负例和脱敏报告。
- Skill lifecycle 支持 Discovered、Audited、Shadow、Repo Pilot、Stable、Deprecated、Retired，以及 scoped Canary、kill switch 和 last-known-good rollback。
- `eval/suites/v4.2-routing-baseline.json` 固定 40 个独立路由 Prompt，其中 16 个 held-out，覆盖 14 个 Skill 与 12 个 no-Skill control。
- 安装器支持 Stable/Pilot/reverse Profile、write-ahead journal、状态记录、prune preview、prune、uninstall 和最近事务 rollback；修改过的用户文件默认保留，只有 prune/uninstall 的显式 force 会改变该行为。
- Plugin builder 与 release evidence builder 可以生成 Profile 插件、release manifest、SBOM 和 third-party notices；公开发布受 License policy 门禁约束。
- `implementation-plan` Skill 继续保持移除；V4.2 不增加新的通用 orchestrator。

证据边界：

- 单元测试和 `eval/fixtures/routing-demo.json` 只证明机制与失败路径，fixture 的通过结果固定为 Hold，不能晋升任何 Skill。
- 40-Prompt baseline 是冻结输入集，不是已运行的真实 Codex report。真实 trigger precision/recall 必须由隔离 runner 执行后计算。
- Task Contract 和 runtime wrapper 不等于操作系统沙箱；平台无法强制的边界必须继续标记为 advisory 或 unavailable。
- 当前工作树构建不等于 clean checkout 发布、新机器演练或 Windows PowerShell 运行证据。
- 没有 paired real-task report 的外部候选和重复能力淘汰仍是 evidence pending。

## 可复用能力

当前可以直接复用的是机制和保守默认值：

- Fast 任务只保留内存中的 lane、写入范围和验收检查；Standard 使用上下文内 Contract；Governed 才持久化审批与副作用证据。
- repo context pack、targeted quality gates、`repo-onboarding` 和历史 V2/V3 的真实仓库校准仍有效，但不自动证明 V4.2 新候选优于旧能力。
- `security-review`、`dependency-upgrade-review` 和 `research-brief` 作为 Guardrail/治理能力使用，不争夺当前 transition 的 Driver 权限。
- `junwei-frontend-design`、`junwei-browser-automation`、`frontend-qa` 和 `junwei-product-demo-video` 按设计、浏览器证据、验证和媒体职责分离。
- reverse 保留完整独立子树，但只通过显式 Profile 安装；重量级工具和 blocked 依赖不进入默认安装。
- 确定性测试、schema、hash、截图断言和可复现渲染优先；主观或高风险结果再交给新上下文 Verifier。
- 外部组件只允许按 Discovered -> Audited -> Shadow -> Repo Pilot -> Stable 晋升；任一步都可 Hold/Reject，严重安全失败直接 kill/rollback。

## 候选边界

| 候选 | 当前决策 | 晋升所缺证据 |
| --- | --- | --- |
| Anthropic `frontend-design` | 方法已被本地设计 Skill 借鉴；不增加同名入口 | 合并前后路由与真实 UI 任务配对证据 |
| Superpowers | Hold；不复制进默认包 | 固定 SHA、Shadow、Standard/Governed 真实任务收益和交接证据 |
| OpenSpec | Hold；只考虑规格 transition | 与 `spec-kit-xl` 的单变量 A/B，且不得与实现 Driver 双控 |
| Find Skills | 仅候选发现 | 只读来源审计；永不自动全局安装 |
| AnySearch | Lab-only | 公开非敏感检索的来源质量、安全边界和一手资料复核证据 |
| Remotion | 项目缺口触发的 repo-local 候选 | 兼容版本锁、真实渲染 smoke 和媒体任务收益 |
| Skill Creator | 仅吸收创建与 Eval 方法 | 不作为日常 Driver，不进入默认发现面 |
| SkillFather | 仅研究模板与生命周期方法 | 来源、License、安全和独立收益审计 |

其他 hooks、MCP、代码图谱、memory、Playwright MCP、后台监控和 SaaS 能力继续保持显式 Pilot 或 Hold；默认不启用、不启动、不写入外部系统。Subagent 只在边界独立且能够并行时使用，主 agent 负责共享文件、集成、验证和收口。

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
- 安装器仅在 `--with-reverse` 或 `--with-reverse-core` 下把 reverse pack 落到 `~/.codex/reverse-skill/`、把 router 落到 `~/.codex/skills/reverse-engineering/`，避免默认上下文和安装面膨胀，同时保留原有路径假设。
- live verifier 默认校验 global AGENTS、Stable skills 和活跃插件路径；`--with-pilots` 要求 Pilot skills，reverse profile 启用后用 `--with-reverse` 加验 router 与 reverse pack，避免“仓库里有文件但 Desktop 里没接上”。
- `install.sh --with-reverse-core` 提供新机器 `reverse-ready` 安装档：文件安装完成后，再 bootstrap 一批高频 reverse core 工具，并自动调用 `scripts/verify_reverse_ready.py` 做机器级只读检查。
- `install.ps1` 提供 Windows 顶层安装入口，复用同一套 global AGENTS / skills / reverse pack / repo-template 安装语义；Windows reverse bootstrap 当前默认 fail closed，只有显式设置 `REVERSE_ALLOW_UNPINNED_WINDOWS_BOOTSTRAP=1` 才会进入兼容路径，且该放开不构成供应链验证证据。

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

## V2/V3 历史验证

以下记录是既有版本的真实仓库和机器演练证据，用于保留回归基线。它们不会自动证明 V4.2 Router、外部候选或新生命周期已经通过真实任务评测；V4.2 的当前证据边界以本文开头和 `docs/V4.2-IMPLEMENTATION-PLAN.md` 第 19 节为准。

已完成的验证层：

- toolkit 自检：`scripts/verify_toolkit.py` 输出 `Workflow toolkit OK`。
- live install 自检：`scripts/verify_live_install.py` 输出 `Live install OK`，默认确认全局 AGENTS、10 个 Stable skill 入口和 packaged assets；使用 `--with-pilots` 时扩展到 14 个，启用 reverse profile 时再用 `--with-reverse` 验证 router 和 reverse pack。
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

## V4.2 运行触发条件

在新仓库中按以下方式使用：

- 首次进入仓库且上下文不足：使用 `repo-onboarding` 建立 context pack。
- Fast：需求明确、工作区内可逆、无外部副作用、有强判定器且不跨安全/公开接口边界；native Codex 直接执行，不写持久化 Contract。
- Standard：存在设计选择、多模块影响或需要 TDD，但仍可在工作区回滚；在上下文中维护 Task Contract，并为当前 transition 选择一个 native 或已明确启用的 Driver。
- Governed：生产/外部写入、凭据、权限、数据迁移、公开 API、不可逆动作或正式审批；持久化 Contract 和 event log，缺少有效审批或关键 enforcement 时 fail closed。
- 正式规格：只有用户或项目明确要求时显式使用 `spec-kit-xl` Pilot；OpenSpec 在完成单变量 A/B 前不参与默认路由，Superpowers 在完成 Repo Pilot 前也不能被文档假定为已安装 Driver。
- 通道执行中只能自动升级，不能由当前 Driver 为减少流程而自动降级；一个 transition 始终只有一个权威 Driver。
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
python3 scripts/verify_live_install.py
./install.sh --prune-preview
```

`--prune`、`--uninstall` 和 `--rollback` 都依赖安装状态。prune/uninstall 默认保留修改文件但显式 force 可删除；rollback 只撤销最近提交，并且不会删除本次新建后又被用户修改的内容。reverse 只在显式需要时另行演练：

```bash
./install.sh --with-reverse --dry-run
./install.sh --with-reverse
python3 scripts/verify_live_install.py --with-reverse
python3 scripts/verify_apk_decode_smoke.py --apk-fixture /path/to/app.apk
```

Windows:

```powershell
powershell -ExecutionPolicy Bypass -File .\install.ps1 -DryRun
powershell -ExecutionPolicy Bypass -File .\install.ps1
powershell -ExecutionPolicy Bypass -File .\install.ps1 -PrunePreview
```

Windows 的 reverse-ready、uninstall 和 rollback 必须在真实 PowerShell 环境另行演练；默认阻断和静态解析都不能写成跨平台通过。

给某个仓库安装 context pack：

```bash
./install.sh --repo /path/to/repo --dry-run
./install.sh --repo /path/to/repo --backup
cd /path/to/repo
python3 scripts/verify_context_pack.py
```

默认安装器只安装全局规则和 Stable skills；Pilot skills 需要 `--with-pilots`，reverse profile 需要显式启用。安装器仍是非破坏式的，遇到不同内容会先报冲突，不会覆盖。`--backup` 用于保留旧文件后替换，`--force` 只在确认覆盖时使用。

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
