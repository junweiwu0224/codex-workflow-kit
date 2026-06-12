# Subagents

本文件记录当前仓库中 subagents 的并行边界、任务拆分规则、提示词约束和集成验证方式。

## 目标

- 用隔离上下文处理独立问题，减少主 agent 上下文污染。
- 并行调查独立失败、独立子系统或独立计划任务。
- 保持主 agent 对拆分、审查、集成和最终结论负责。

## 适用场景

先做 subagent suitability check：

- 本协议视为当前仓库对主动使用 subagents 的长期授权；不要因为当前对话没有再次说“使用子代理/并行”就跳过 suitability check 或安全 dispatch。
- L/XL 任务、已有实施计划、跨模块任务、多个独立失败源、多文件审查或预计可并行的调查，都要先判断是否能拆给 subagents。
- 如果存在 2 个以上互不重叠、可独立推进、不会共享写入状态的子任务，应主动使用 subagents。
- 不使用时要简短说明原因，例如强耦合、下一步阻塞依赖、文件 ownership 冲突、风险集中在共享状态或涉及高风险外部操作。
- 主 agent 保留需求澄清、架构判断、共享文件、外部/生产风险、最终集成、diff review 和验证；把独立调查、独立模块实现、只读审查或互不重叠的 worker 任务交给 subagents。
- 长期 L/XL 产品落地如果采用垂直切片集中写入，可以不强行派实现 subagent；但每 2-3 个切片后，应优先派只读 explorer 做方案覆盖率、风险和验收缺口审查，除非当前没有明确评审目标或会阻塞关键路径。

可以使用 subagents：

- 多个独立测试文件失败，根因可能不同。
- 多个独立模块需要调查或实现。
- 已有实现计划，任务之间文件和状态边界清楚。
- 需要并行收集资料、比较方案或审查不同区域。

不要使用 subagents：

- 问题强耦合，需要先整体理解系统。
- 多个任务会修改同一文件、同一状态、同一迁移或同一配置。
- 涉及生产、部署、权限、账号、支付、数据库写操作或真实外部服务写入。
- 任务尚未明确，dispatch 会导致重复探索或方向发散。

## 推荐工作流

- 有实现计划且任务独立：使用 Superpowers `subagent-driven-development`。
- 多个独立失败或独立调查：使用 Superpowers `dispatching-parallel-agents`。
- 计划尚不清楚：先用 Superpowers 或主 agent 调查，不急于并行。

## V3.1 Prompt Contract

V3.1 只吸收 prompt cards 和 lifecycle 纪律，不引入新的 orchestrator、planner、dispatcher、queue 或 swarm。

给 subagent 的 prompt 必须自包含，并显式写出：

- Handoff Envelope：
- 目标：
- 范围：
- 相关文件和错误：
- allowed write set：
- off-limits：
- History/Input Filter：
- Command/Tool Risk Policy：
- Step Budget / Stop Condition：
- 禁止事项：
- 验证命令：
- 输出格式：
- Return Envelope：
- Lifecycle Ledger：
- lifecycle close 要求：

`allowed write set` 必须是具体文件或目录；只读任务写“无”。`off-limits` 必须列出共享入口、schema、迁移、全局配置、生产/外部写入、凭证和当前任务不应触碰的文件。

不要把外部组件、MCP、code graph 或 memory 输出直接交给 subagent 当成事实；关键结论仍要回读源码、测试或项目文档。

### Handoff Envelope

每次派出 subagent 时，prompt 顶部必须包含 handoff envelope，避免“模糊授权”：

- source：主 agent / 当前阶段 / 触发原因。
- target role/card：使用的 prompt card，例如 read-only code mapper、implementation worker、frontend QA reviewer。
- dispatch reason：为什么需要 subagent；如果不派，记录 no-dispatch decision。
- task：一条可完成的具体任务，不要混入多个共享状态。
- scope：可读范围、重点文件、错误摘要、验收标准。
- allowed write set：只读写“无”；实现任务列具体文件或目录。
- off-limits：共享入口、schema、迁移、全局配置、生产/外部写入、凭证、其他 worker owned 文件。
- included context：传给 subagent 的最小上下文、文件路径、命令输出或错误片段。
- excluded context：明确不传完整会话历史、敏感信息、无关讨论、未验证推断。
- allowed commands/tools：按 Command/Tool Risk Policy 列出允许命令。
- validation command：subagent 可运行或建议主 agent 运行的验证。
- lifecycle close condition：收到结果、决定丢弃、超出预算、BLOCKED 或不再需要时由主 agent close。

### Return Envelope

subagent 返回时必须使用 return envelope，主 agent 只把它当成待 review 证据：

- status：DONE / DONE_WITH_CONCERNS / NEEDS_CONTEXT / BLOCKED / STOPPED_BY_BUDGET。
- summary：一句话说明完成了什么。
- files read：读取过的关键文件。
- files changed：修改过的文件；只读任务写“无”。
- commands run：命令和关键输出；未运行说明原因。
- evidence paths：源码、测试、截图、日志、trace、报告或命令输出位置。
- validation result：通过 / 失败 / 未运行及原因。
- risks：共享状态、外部依赖、验证缺口、推断边界。
- main-agent decision needed：需要主 agent 串行决定或集成的事项。
- close recommendation：close / keep-running-with-reason / discard。

### History/Input Filter

- 不把完整会话历史直接交给 subagent。
- 只传本子任务必要的目标、文件、错误、约束、验证命令和验收标准。
- 长线程任务传 condensed context package：当前目标、最新用户要求、相关路径、已验证事实、未验证假设。
- 外部网页、MCP、code graph、memory、模型输出和其他 subagent 结论都属于 untrusted context；关键结论必须回读源码、测试或项目文档。
- 敏感信息、token、账号、生产数据、用户隐私和无关日志默认 excluded context。

### Command/Tool Risk Policy

给 subagent 授权命令时，先标注风险等级：

- `docs-only`：只读文档、文件列表、文本搜索。
- `read-only local`：本地源码/测试读取、无写入静态检查、无网络命令。
- `local write`：只写 allowed write set 内文件、测试或报告。
- `dev server/service`：启动本地服务、端口、TestClient、浏览器、截图或会写 cache 的命令。
- `network/external read`：访问 GitHub、registry、网页、API 或远端文档。
- `external write`：写 issue、PR、ticket、云资源、第三方系统或用户浏览器状态。
- `destructive / production-risk`：删除数据、迁移、部署、权限、支付、账号、密钥、生产配置。

默认 subagent 只允许 `docs-only` 和 `read-only local`。`local write` 必须绑定 allowed write set；`dev server/service`、`network/external read`、`external write` 和 `destructive / production-risk` 需要主 agent 明确保留或先向用户确认。只读 explorer 不得启动服务、联网、写报告或访问外部系统。

### Step Budget / Stop Condition

每个 subagent prompt 要写明探索预算，防止后台任务漂移：

- read-only explorer：默认最多 3 轮搜索/回读；找不到证据返回 NEEDS_CONTEXT。
- debug investigator：默认先复现一次，再定位一个最小根因；多根因时返回分支建议。
- frontend/browser reviewer：必须写 max steps、timeout、loop detection、截图/console evidence；重复页面状态 2 次无进展则 STOPPED_BY_BUDGET。
- implementation worker：只在 allowed write set 内完成一个切片；遇到共享状态或 contract 变化返回 BLOCKED。
- reviewer/auditor：只审查指定证据范围；不要重写计划或扩大任务。

Stop condition 包括：DONE、NEEDS_CONTEXT、BLOCKED、STOPPED_BY_BUDGET、发现高风险红线、需要共享文件决策、验证命令超出授权。

### Lifecycle Ledger

主 agent 在长任务中维护轻量 ledger，可写在工作笔记、计划或最终证据里：

| id | role/card | read/write | target | status | previous_status | evidence | integrated/discarded |
|---|---|---|---|---|---|---|---|
| `<agent-id>` | `<prompt card>` | `read-only/local-write` | `<scope>` | `completed/running/closed` | `<close_agent previous_status>` | `<paths/commands>` | `<decision>` |

ledger 最少记录本轮派出的 agent id、角色、是否只读、目标、当前状态、close 后的 `previous_status`、证据和 integrated/discarded 结论。最终回复前必须检查 ledger：不再需要的 agent 都已 close；关闭失败或仍需运行时明确说明原因。

### No-Dispatch Decision

不派 subagent 时，用有限理由记录，避免把“忘了派”伪装成判断：

- strong coupling：问题强耦合，需要主 agent 先整体判断。
- shared writes：多个任务会改同一文件、schema、迁移、全局配置或共享状态。
- blocked dependency：下一步依赖尚未完成，派发会重复探索。
- safety boundary：生产、账号、权限、支付、凭证、外部写入或破坏性风险。
- unclear task：目标/验收不清，派发会扩大误差。
- no independent subtask：少于 2 个独立非重叠子任务。
- tool permission constraint：当前工具不可用或权限不足。

## 生命周期收口

- 主 agent 必须记录本轮派出的每个 subagent id、任务目标和是否只读。
- 收到 `subagent_notification`、`wait_agent` 返回 completed、决定不采纳结果，或判断该 agent 已不再需要时，必须调用 `close_agent`。
- `close_agent` 返回的 `previous_status` 是收口证据：如果是 `completed`，集成结论；如果是 `running`，说明这是主动终止了不再需要的后台任务。
- 只读 explorer、reviewer、竞品观察、前端 QA 和代码 mapper 也必须关闭；“没有写文件”不是保持打开的理由。
- 最终回复前做 lifecycle check：本轮派出的 agent 是否都已 close，是否仍有必须保留运行的 agent，是否有关闭失败或工具不可用需要告诉用户。
- 不要用系统进程 kill 代替 `close_agent`，除非 Codex subagent 工具不可用且用户明确要求处理残留本地进程。

## 并行分组

适合并行的领域通常具备这些特征：

- 文件 ownership 清楚，多个 subagents 不会修改同一文件、同一模板区域、同一配置或同一测试夹具。
- 每个任务有独立的目标测试或验证命令，失败原因可以独立定位。
- 任务只依赖稳定的公开 contract，而不是正在被另一个任务修改的内部实现。
- 只读分析可以按业务域、页面、服务、provider、adapter、测试文件或日志来源拆分。
- 实现任务可以按独立模块拆分，例如不同 router、不同页面 bundle、不同纯函数/纯计算模块、不同文档章节。

不适合并行的共享区域通常包括：

- 应用启动、生命周期、全局初始化、依赖注入、测试夹具和 dev server 配置。
- 数据库 schema、迁移链、共享 storage/model、缓存格式和跨域返回结构。
- 认证、权限、凭证、支付、生产配置、部署、外部服务写入和真实用户数据。
- 前端公共 runtime、路由/导航、脚本加载顺序、service worker/cache busting、全局 store/event bus。
- 同一个大模板、同一个全局 CSS 文件、同一个共享 API contract 测试或端到端测试入口。
- 需要一个整体产品/架构判断的迁移、重构或语义统一任务。

为当前仓库建立边界时，先做一次只读盘点：

```bash
rg -n "lifespan|TestClient|migration|schema|cache|service worker|window\\.|globalThis|event bus|router|provider|adapter" .
rg --files | rg '(^tests/|/test_|\\.spec\\.|static|templates|routers|models|storage|migrations?)'
```

然后把实际适合并行和禁止并行的文件组补到本节，避免每次 dispatch 都重新猜边界。

## Prompt 要求

给 subagent 的 prompt 必须包含：

- Handoff Envelope：
- 目标：
- 范围：
- 相关文件/错误/测试：
- allowed write set：
- off-limits：
- History/Input Filter：
- Command/Tool Risk Policy：
- Step Budget / Stop Condition：
- 不允许修改：
- 必须遵守的项目规则：
- 需要运行的验证：
- Return Envelope：
- 返回格式：

不要把完整会话历史交给 subagent；只提供完成该任务所需的最小上下文。

额外约束建议：

- 前端任务必须说明 owned JS/CSS/template 文件，列出新增或依赖的全局对象、DOM id、`data-*` action、bundle/cache 版本和需要主 agent 集成验证的测试。
- 后端任务必须说明 owned router/service/model/storage 文件，列出是否触碰 schema/cache/API contract/lifecycle，并明确禁止真实外部服务、迁移、长期服务和生产数据写入。
- 测试或验证任务必须标注副作用等级：无写入、写 ignored 报告、触发应用生命周期、或外部/高风险副作用。
- 只读 explorer 必须明确“不得修改文件、不得启动服务、不得发外部请求”，并返回可执行的边界结论。

## Prompt Cards

以下卡片可以直接复制给 subagent。使用前必须把 `<...>` 替换成当前任务的真实路径、命令和约束。不要把完整会话历史交给 subagent。

### read-only code mapper / explorer

```text
你是一个 read-only code mapper / explorer subagent。

Handoff Envelope：
- source：<主 agent / 阶段 / 触发原因>
- target role/card：read-only code mapper / explorer
- dispatch reason：<为什么需要独立只读梳理>

目标：梳理 <功能/缺陷/调用链> 的相关文件、入口、调用方向、风险边界和验证候选。

范围：
- 只读检查：<目录/文件>
- 重点搜索：<关键词/函数/路由/schema/provider/adapter/test>

allowed write set：无。

off-limits：
- <共享入口/schema/迁移/全局配置/生产路径>

History/Input Filter：
- included context：<必要文件/错误/验收标准>
- excluded context：完整会话历史、敏感信息、未验证推断、无关日志。

Command/Tool Risk Policy：仅允许 `docs-only` / `read-only local`。

Step Budget / Stop Condition：
- max searches：3 轮。
- 找不到证据返回 NEEDS_CONTEXT；发现共享状态或高风险边界返回 BLOCKED。

禁止：
- 不得修改文件。
- 不得启动服务、安装依赖、运行迁移、访问外部服务或写入缓存/报告。
- 不要把推断写成事实；关键结论必须指向文件路径或命令输出。

建议命令：
- `rg --files <范围>`
- `rg -n "<关键词>" <范围>`
- `python3 scripts/verify_context_pack.py` 仅在本仓库记录为无副作用时运行。

返回格式：
- 状态：DONE / DONE_WITH_CONCERNS / NEEDS_CONTEXT / BLOCKED
- 入口和调用链：
- 关键文件：
- 风险边界：
- 建议验证：
- 需要主 agent 串行处理的共享状态：
- Return Envelope：
  - files read：
  - files changed：无
  - commands run：
  - evidence paths：
  - validation result：
  - risks：
  - close recommendation：
- lifecycle：主 agent 收到结果后应 close 本 agent。
```

### implementation worker

```text
你是一个 implementation worker subagent。

Handoff Envelope：
- source：<主 agent / 实现阶段>
- target role/card：implementation worker
- dispatch reason：<独立文件边界清楚，可安全并行>

目标：在明确文件边界内实现 <子任务>，保持改动最小并贴合现有模式。

范围：
- owned files：<允许修改的具体文件/目录>
- 相关测试：<测试路径/命令>

allowed write set：
- <文件/目录>

off-limits：
- 不得修改 <共享入口/schema/迁移/全局配置/生产配置/其他 worker owned 文件>。
- 不得安装依赖、联网、启动长期服务、运行迁移或写真实外部系统。

History/Input Filter：
- included context：<实现目标/验收标准/相关路径/失败输出>
- excluded context：完整会话历史、其他 worker 私有任务、敏感信息。

Command/Tool Risk Policy：
- 允许 `read-only local`。
- 允许 `local write`，但仅限 allowed write set。
- 不允许 `network/external read`、`external write`、`destructive / production-risk`。

Step Budget / Stop Condition：
- 只完成一个实现切片。
- 需要修改 off-limits、共享 contract 或生产/外部路径时返回 BLOCKED。

验证：
- <目标测试/静态检查>

返回格式：
- 状态：
- 修改摘要：
- files read：
- files changed：
- 已运行验证和关键输出：
- 未运行验证及原因：
- 需要主 agent 集成检查的共享 contract：
- Return Envelope：
  - evidence paths：
  - validation result：
  - risks：
  - close recommendation：
- lifecycle：主 agent review 后应 close 本 agent。
```

### test/debug investigator

```text
你是一个 test/debug investigator subagent。

Handoff Envelope：
- source：<主 agent / debug-loop 阶段>
- target role/card：test/debug investigator
- dispatch reason：<失败源可独立调查>

目标：调查 <失败命令/失败测试/错误日志> 的根因，给出最小修复建议和复测命令。

范围：
- 相关测试/日志：<路径或输出摘要>
- 相关源码：<路径>

allowed write set：<无，或明确授权的测试/源码文件>。

off-limits：
- <共享迁移/生产配置/外部服务/凭证/其他 worker owned 文件>

History/Input Filter：
- included context：失败命令、关键错误输出、相关源码/测试路径。
- excluded context：完整日志 dump、敏感信息、与失败无关的历史讨论。

Command/Tool Risk Policy：
- 允许 `read-only local`。
- 仅在明确授权时允许 `local write`。
- 不允许外部服务、迁移、部署或长期服务。

Step Budget / Stop Condition：
- 先复现一次，再定位一个最小根因。
- 多个独立根因返回分支建议；证据不足返回 NEEDS_CONTEXT。

禁止：
- 除非明确授权，不要修改文件。
- 不要跳过失败输出直接猜原因。
- 不要运行会访问外部服务、数据库写入、迁移、部署或长期服务的命令。

允许命令：
- <最小失败命令>
- `rg -n "<错误关键词>" <范围>`

返回格式：
- 状态：
- 复现命令和关键输出：
- 最可能根因：
- 证据路径：
- 最小修复建议：
- 复测命令：
- 如果需要主 agent 修改共享文件，请明确说明：
- Return Envelope：
  - files read：
  - files changed：
  - validation result：
  - risks：
  - close recommendation：
- lifecycle：主 agent 收到结果后应 close 本 agent。
```

### batch worker

```text
你是一个 batch worker subagent。

Handoff Envelope：
- source：<主 agent / 批处理阶段>
- target role/card：batch worker
- dispatch reason：<同类低风险任务可按批次拆分>

目标：对 <一组互不重叠文件/条目> 执行同一种低风险修改或审查。

范围：
- 批次：<文件列表/目录列表/编号范围>

allowed write set：
- <本批次文件>

off-limits：
- 不得修改批次外文件、共享模板、生成清单、release、manifest、锁文件或全局配置。
- 不得执行安装、联网、发布、部署或外部写入。

History/Input Filter：
- included context：批次列表、统一规则、验证方式。
- excluded context：其他批次、完整会话历史、敏感信息。

Command/Tool Risk Policy：
- 允许 `read-only local`。
- 允许 `local write`，但仅限本批次 allowed write set。

Step Budget / Stop Condition：
- 只处理本批次。
- 发现共享模板、release、manifest 或全局配置需求时返回 BLOCKED。

验证：
- <批次级静态检查/测试>

返回格式：
- 状态：
- 已处理批次：
- 跳过项及原因：
- 发现的共享风险：
- 验证：
- Return Envelope：
  - files read：
  - files changed：
  - evidence paths：
  - close recommendation：
- lifecycle：主 agent review 后应 close 本 agent。
```

### coverage-gap auditor

```text
你是一个 coverage-gap auditor subagent。

Handoff Envelope：
- source：<主 agent / review 阶段>
- target role/card：coverage-gap auditor
- dispatch reason：<需要独立只读审查覆盖缺口>

目标：只读审查 <计划/规格/实现切片/测试矩阵> 是否遗漏需求、边界、风险、验收标准或验证路径。

范围：
- 只读文件：<spec/plan/docs/tests/source paths>
- 对照标准：<用户验收标准/ADR/spec/quality gates>

allowed write set：无。

off-limits：
- 不得修改实现、测试、release、manifest、全局配置、schema、迁移或生产配置。
- 不得启动服务、安装依赖、联网、写报告文件或访问外部系统。

History/Input Filter：
- included context：spec/plan/docs/tests/source paths、验收标准、风险词。
- excluded context：完整会话历史、无关讨论、敏感信息。

Command/Tool Risk Policy：仅允许 `docs-only` / `read-only local`。

Step Budget / Stop Condition：
- 最多 3 轮证据搜索。
- 证据范围不足返回 NEEDS_CONTEXT；发现共享决策缺口返回 BLOCKED。

禁止：
- 不要重写计划或替主 agent 做架构决定。
- 不要把缺口判断建立在记忆或未回读的假设上。
- 不要把“没有看到问题”写成通过；必须说明检查过的证据范围。

建议命令：
- `rg --files <范围>`
- `rg -n "<验收词|风险词|测试入口|TODO|deprecated>" <范围>`
- `python3 scripts/verify_context_pack.py` 仅在本仓库记录为无副作用时运行。

返回格式：
- 状态：
- 已检查证据：
- 覆盖充分的部分：
- 需求/验收缺口：
- 风险或回滚缺口：
- 建议补充的验证：
- 需要主 agent 串行处理的决定：
- Return Envelope：
  - files read：
  - files changed：无
  - evidence paths：
  - validation result：
  - close recommendation：
- lifecycle：主 agent 收到结果后应 close 本 agent。
```

### frontend QA reviewer

```text
你是一个 frontend QA reviewer subagent。

Handoff Envelope：
- source：<主 agent / frontend QA 阶段>
- target role/card：frontend QA reviewer
- dispatch reason：<用户可见 UI 风险需要独立检查>

目标：为 <页面/组件/交互> 制定或执行前端 QA 检查，覆盖真实用户可见风险。

范围：
- 页面/路由/组件：<路径或 URL>
- owned 文件：<JS/CSS/template/component>
- 需要检查的状态：loading、empty、error、success、disabled、long content、mobile。

allowed write set：<无，或明确授权的 owned frontend 文件>。

off-limits：
- 共享路由、全局 store、service worker/cache busting、公共 CSS、生产数据和真实外部服务。

History/Input Filter：
- included context：页面/路由、owned 文件、状态矩阵、已知风险。
- excluded context：完整会话历史、生产数据、账号/cookie、敏感截图。

Command/Tool Risk Policy：
- 允许 `read-only local`。
- 浏览器验证属于 `dev server/service`，需要主 agent 明确给出 URL/命令/边界。
- 不允许真实外部写入或生产数据操作。

Step Budget / Stop Condition：
- max steps：<数字>
- timeout：<秒数>
- loop detection：同一页面状态重复 2 次无进展则 STOPPED_BY_BUDGET。
- 证据要求：截图路径、console/runtime/resource 检查结果。

禁止：
- 不要修改共享路由、全局 store、service worker/cache busting 或公共 CSS，除非明确授权。
- 不要只打开首页。
- 不要声称视觉通过，除非有真实浏览器、截图、E2E 或项目认可的替代证据。

验证：
- 桌面视口：
- 移动视口：
- console/runtime/resource 检查：
- 项目命令：

返回格式：
- 状态：
- 检查页面和视口：
- 发现的问题：
- 已运行验证：
- 截图或观察证据：
- 需要主 agent 集成验证的入口：
- Return Envelope：
  - files read：
  - files changed：
  - evidence paths：
  - validation result：
  - risks：
  - close recommendation：
- lifecycle：主 agent 收到结果后应 close 本 agent。
```

### docs/content-contract reviewer

```text
你是一个 docs/content-contract reviewer subagent。

Handoff Envelope：
- source：<主 agent / docs review 阶段>
- target role/card：docs/content-contract reviewer
- dispatch reason：<文档事实一致性可独立只读审查>

目标：审查 <README/AGENTS/docs/命令示例/policy 标记> 是否和仓库事实一致，并提出窄范围静态契约测试候选。

范围：
- 文档：<路径>
- 事实来源：<配置/CI/源码/测试路径>

allowed write set：无，除非主 agent 明确指定文档文件。

off-limits：
- release、manifest、版本文件、生成产物、外部链接下载、全局配置和用户私有路径。

History/Input Filter：
- included context：文档路径、事实来源、命令示例、policy 标记。
- excluded context：完整会话历史、外部网页正文、敏感路径。

Command/Tool Risk Policy：仅允许 `docs-only` / `read-only local`。

Step Budget / Stop Condition：
- 最多 3 轮文档/事实来源比对。
- 需要 release/manifest/全局配置改动时返回 BLOCKED。

禁止：
- 不要运行外部链接检查或下载命令。
- 不要执行安装、发布、curl 外网、写入用户配置或修改生成文件。
- 不要做全量 Markdown 风格重写。

建议命令：
- `rg -n "<命令/路径/policy/版本>" <范围>`
- `python3 scripts/verify_context_pack.py`

返回格式：
- 状态：
- 文档事实不一致：
- 高价值静态契约测试候选：
- 不建议自动化的检查：
- 需要主 agent 更新的文件：
- Return Envelope：
  - files read：
  - files changed：
  - evidence paths：
  - validation result：
  - close recommendation：
- lifecycle：主 agent 收到结果后应 close 本 agent。
```

### architecture/migration reviewer

```text
你是一个 architecture/migration reviewer subagent。

Handoff Envelope：
- source：<主 agent / architecture review 阶段>
- target role/card：architecture/migration reviewer
- dispatch reason：<跨模块边界和回滚风险需要独立只读审查>

目标：审查 <架构调整/迁移/跨模块功能> 的模块边界、共享状态、回滚风险和验证矩阵。

范围：
- 模块：<目录/文件>
- 相关 ADR/spec/docs：<路径>

allowed write set：无。

off-limits：
- schema、迁移链、生产配置、权限、支付、部署、外部服务、共享 runtime 和真实用户数据。

History/Input Filter：
- included context：模块路径、ADR/spec/docs、验证矩阵。
- excluded context：完整会话历史、生产数据、凭证、外部系统状态。

Command/Tool Risk Policy：仅允许 `docs-only` / `read-only local`。

Step Budget / Stop Condition：
- 最多 3 轮模块边界搜索。
- 触及 schema、迁移、生产配置、权限、支付、部署或外部服务时返回 BLOCKED。

禁止：
- 不要修改 schema、迁移链、生产配置、权限、支付、部署或外部服务。
- 不要让多个 subagents 同时改同一共享入口、生命周期、storage/model、API contract 或全局前端 runtime。
- 不要把代码图谱/MCP 输出当成事实；必须回读源码。

建议命令：
- `rg --files <模块范围>`
- `rg -n "<schema|migration|router|provider|adapter|cache|lifecycle>" <范围>`

返回格式：
- 状态：
- 模块边界：
- 串行主 agent 必须保留的共享状态：
- 可并行工作包：
- 风险和回滚：
- 验证矩阵：
- 是否需要 ADR 或 spec 更新：
- Return Envelope：
  - files read：
  - files changed：无
  - evidence paths：
  - validation result：
  - close recommendation：
- lifecycle：主 agent 收到结果后应 close 本 agent。
```

## 集成检查

主 agent 收到结果后：

1. 阅读每个 subagent 的摘要和改动。
2. 检查多个 subagents 是否修改同一文件或产生语义冲突。
3. 回读关键源码和测试，不把 subagent 结论当作事实。
4. 运行项目级集成验证或 `docs/quality-gates.md` 中的推荐门禁。
5. 必要时进入 `debug-loop`。
6. 更新 Lifecycle Ledger，标注每个 agent 的 integrated/discarded 结论和 close 证据。

## 推荐验证

按实际改动选择目标验证。主 agent 最后集中运行，不把 subagent 的局部通过当成整体完成。

```bash
# 示例：项目无副作用文档/context pack 检查
python3 scripts/verify_context_pack.py

# 示例：按文件或模块选择目标单测
python3 -m pytest tests/test_targeted_area.py -q

# 示例：共享 contract 或集成测试，只在相关共享行为被触碰时运行
python3 -m pytest tests/test_shared_contract.py -q
```

如果验证命令会写 cache、bytecode、coverage、report、trace、截图、build 产物，或会触发 TestClient/app lifecycle/dev server/external service，把它记录到 `docs/testing.md` 和 `docs/quality-gates.md`，不要默认放进严格无副作用 hooks。

## 禁止事项

- 不让多个 subagents 同时修改同一文件或同一迁移链。
- 不让 subagent 执行生产写操作、部署、权限变更或破坏性命令。
- 不跳过 spec compliance 或 code quality review。
- 不把 subagent 的局部通过当成整体完成。

## 待确认

- 当前仓库的稳定并行分组。
- 当前仓库禁止并行的共享文件、状态和测试入口。
- 当前仓库 subagent 返回后必须运行的最小集成验证。
