# Subagents

本文件记录当前仓库中 subagents 的并行边界、任务拆分规则、提示词约束和集成验证方式。

## 目标

- 用隔离上下文处理独立问题，减少主 agent 上下文污染。
- 并行调查独立失败、独立子系统或独立计划任务。
- 保持主 agent 对拆分、审查、集成和最终结论负责。

## 适用场景

先做 subagent suitability check：

- 全局/仓库 AGENTS 中的 subagent 协议就是长期授权；不要因为当前对话没有再次说“使用子代理/并行”就跳过 suitability check 或 dispatch。
- L/XL 任务、已有实施计划、跨模块任务、多个独立失败源、多文件审查或预计可并行的调查，都要先判断是否能拆给 subagents。
- 如果存在 2 个以上互不重叠、可独立推进、不会共享写入状态的子任务，应主动使用 subagents。
- 不使用时要简短说明原因，例如强耦合、下一步阻塞依赖、文件 ownership 冲突、风险集中在共享状态或涉及高风险外部操作。
- 主 agent 保留需求澄清、架构判断、共享文件、外部/生产风险、最终集成、diff review 和验证；把独立调查、独立模块实现、只读审查或互不重叠的 worker 任务交给 subagents。

可以使用 subagents：

- 多个独立测试文件失败，根因可能不同。
- 多个独立模块需要调查或实现。
- 已有实现计划，任务之间文件和状态边界清楚。
- 需要并行收集资料、比较方案或审查不同区域。
- 长期 L/XL 产品落地采用垂直切片集中写入时，每 2-3 个切片后派只读 explorer 审查方案覆盖率、风险和验收缺口。

不要使用 subagents：

- 问题强耦合，需要先整体理解系统。
- 多个任务会修改同一文件、同一状态、同一迁移或同一配置。
- 涉及生产、部署、权限、账号、支付、数据库写操作或真实外部服务写入。
- 任务尚未明确，dispatch 会导致重复探索或方向发散。

## 推荐工作流

- 有实现计划且任务独立：使用 Superpowers `subagent-driven-development`。
- 多个独立失败或独立调查：使用 Superpowers `dispatching-parallel-agents`。
- 计划尚不清楚：先用 Superpowers 或主 agent 调查，不急于并行。

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

- 目标：
- 范围：
- 相关文件/错误/测试：
- 不允许修改：
- 必须遵守的项目规则：
- 需要运行的验证：
- 返回格式：

不要把完整会话历史交给 subagent；只提供完成该任务所需的最小上下文。

额外约束建议：

- 前端任务必须说明 owned JS/CSS/template 文件，列出新增或依赖的全局对象、DOM id、`data-*` action、bundle/cache 版本和需要主 agent 集成验证的测试。
- 后端任务必须说明 owned router/service/model/storage 文件，列出是否触碰 schema/cache/API contract/lifecycle，并明确禁止真实外部服务、迁移、长期服务和生产数据写入。
- 测试或验证任务必须标注副作用等级：无写入、写 ignored 报告、触发应用生命周期、或外部/高风险副作用。
- 只读 explorer 必须明确“不得修改文件、不得启动服务、不得发外部请求”，并返回可执行的边界结论。

## Prompt Cards

以下卡片可以直接复制给 subagent。使用前必须把 `<...>` 替换成当前任务的真实路径、命令和约束。不要把完整会话历史交给 subagent。

### read-only code mapper

```text
你是一个只读 code mapper subagent。

目标：梳理 <功能/缺陷/调用链> 的相关文件、入口、调用方向、风险边界和验证候选。

范围：
- 只读检查：<目录/文件>
- 重点搜索：<关键词/函数/路由/schema/provider/adapter/test>

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
```

### test/debug investigator

```text
你是一个 test/debug investigator subagent。

目标：调查 <失败命令/失败测试/错误日志> 的根因，给出最小修复建议和复测命令。

范围：
- 相关测试/日志：<路径或输出摘要>
- 相关源码：<路径>

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
```

### frontend QA reviewer

```text
你是一个 frontend QA reviewer subagent。

目标：为 <页面/组件/交互> 制定或执行前端 QA 检查，覆盖真实用户可见风险。

范围：
- 页面/路由/组件：<路径或 URL>
- owned 文件：<JS/CSS/template/component>
- 需要检查的状态：loading、empty、error、success、disabled、long content、mobile。

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
```

### docs/content-contract reviewer

```text
你是一个 docs/content-contract reviewer subagent。

目标：审查 <README/AGENTS/docs/命令示例/policy 标记> 是否和仓库事实一致，并提出窄范围静态契约测试候选。

范围：
- 文档：<路径>
- 事实来源：<配置/CI/源码/测试路径>

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
```

### architecture/migration reviewer

```text
你是一个 architecture/migration reviewer subagent。

目标：审查 <架构调整/迁移/跨模块功能> 的模块边界、共享状态、回滚风险和验证矩阵。

范围：
- 模块：<目录/文件>
- 相关 ADR/spec/docs：<路径>

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
```

## 返回格式

subagent 应返回：

- 状态：`DONE` / `DONE_WITH_CONCERNS` / `NEEDS_CONTEXT` / `BLOCKED`
- 做了什么：
- 改了哪些文件：
- 运行了哪些验证：
- 仍有哪些风险或问题：
- 需要主 agent 集成检查的点：

## 集成检查

主 agent 收到结果后：

1. 阅读每个 subagent 的摘要和改动。
2. 检查多个 subagents 是否修改同一文件或产生语义冲突。
3. 回读关键源码和测试，不把 subagent 结论当作事实。
4. 运行项目级集成验证或 `docs/quality-gates.md` 中的推荐门禁。
5. 必要时进入 `debug-loop`。

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
