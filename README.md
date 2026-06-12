# Codex Workflow Kit

这是一套用于增强个人 Codex 工作流的可迁移工具包，包含全局规则、repo context pack 模板、个人 skills、安装脚本、自检脚本和发布归档脚本。当前包是 V3.1 稳定口径：外部组件准入、code graph/memory pilot、hook discipline、subagent prompt cards 和自诊断收口都已打包，但不默认启用外部工具。

## 目录

```text
VERSION
MANIFEST.sha256
QUICKSTART.md
WORKFLOW-REVIEW.md
docs/
  V2-ADOPTION-EVIDENCE.md
  V3.1-ADOPTION-EVIDENCE.md
  V3.1-BENCHMARK.md
  V3.1-BENCHMARK.json
  V3.1-SKILL-POLISH-BENCHMARK.md
  V3.1-SKILL-POLISH-BENCHMARK.json
  V3.1-AGENT-RESEARCH-20.md
  V3.1-AGENT-CONTRACT-BENCHMARK.md
  V3.1-AGENT-CONTRACT-BENCHMARK.json
  V3.1-LOCAL-CODEX-SMOKE-REPORT.md
  agent-collaboration-smoke.md
  codex-usage.md
  external-component-intake.md
  superpowers/
    plans/
      2026-06-07-workflow-kit-v2-adoption.md
      2026-06-07-workflow-kit-v2-1-observability-subagents-mcp.md

global/
  AGENTS.md

install.sh

scripts/
  audit_skill_contracts.py
  audit_external_component.py
  audit_repo_adoption.py
  benchmark_agent_contract.py
  benchmark_skill_polish.py
  benchmark_v31_vs_v22.py
  build_release.py
  codex_doctor.py
  codex_runtime_smoke.py
  render_usage_row.py
  verify_live_install.py
  verify_toolkit.py

tests/
  test_audit_skill_contracts.py
  test_codex_runtime_smoke.py
  ...

repo-template/
  AGENTS.md
  scripts/
    verify_context_pack.py
  tests/
    test_verify_context_pack.py
  docs/
    architecture.md
    commands.md
    testing.md
    quality-gates.md
    subagents.md
    observability.md
    mcp-pilot.md
    codegraph-pilot.md
    memory-recall-pilot.md
    codex-usage.md
    codex-playbook.md
    glossary.md
    decisions/
      README.md
      0001-template.md
    specs/
      README.md
      0001-template.md

skills/
  repo-onboarding/
  spec-kit-xl/
  debug-loop/
  frontend-qa/
  decision-record/
  completion-review/
  security-review/
  dependency-upgrade-review/
  research-brief/
  skill-plugin-intake-review/
  release-readiness/
```

## 用法

`QUICKSTART.md` 是迁移清单，包含新机器最短安装命令、验证命令、以及首次应用到新 repo 的 10 分钟流程。

`WORKFLOW-REVIEW.md` 是一页总复盘，记录最终路线、完成状态、可复用能力、候选边界、新机器演练结果和后续触发条件。迁移或继续扩展前，先读它确认当前边界。

`docs/superpowers/plans/2026-06-07-workflow-kit-v2-adoption.md` 是 V1 之后的详细后续计划，用于真实 repo 采用、效果评估、hooks/MCP/memory/subagents 候选晋升和 V2 打包。

`docs/superpowers/plans/2026-06-07-workflow-kit-v2-1-observability-subagents-mcp.md` 是 V2.1 的详细计划，用于新增 observability、subagent prompt cards、MCP/code graph pilot 和 `render_usage_row.py pilot`，同时保持 no default automation。

`docs/V2-ADOPTION-EVIDENCE.md` 是 V2 当前证据包，记录 baseline 验证、候选 repo dry-run、已晋升能力、拒绝默认化能力、外部 repo baseline 安装、repo-specific onboarding calibration、V2.1 tooling layer 和 V2.2 P0 specialist skills closeout。

`docs/V3.1-ADOPTION-EVIDENCE.md` 是当前 V3.1 证据包，记录 `promote != install`、`pilot != enable`、`core != runtime/background`、11 skills verified、reject lines、新机器演练要求和 release checksum 证据。

`docs/V3.1-BENCHMARK.md` / `docs/V3.1-BENCHMARK.json` 是 V3.1 对比 V2.2 的量化 benchmark，覆盖 XS/S/M/L 任务、耗时、检查覆盖、风险发现和任务通过数。对应脚本是 `scripts/benchmark_v31_vs_v22.py`。

`docs/V3.1-SKILL-POLISH-BENCHMARK.md` / `docs/V3.1-SKILL-POLISH-BENCHMARK.json` 是 V3.1 skill polish 对比 pre-polish release 的量化 benchmark，覆盖 skill count、Output Shape、accessibility、release readiness、progressive disclosure 等改进。对应脚本是 `scripts/benchmark_skill_polish.py`。

`docs/V3.1-AGENT-RESEARCH-20.md` 是 20 个高星/流行 agent 仓库的本地源码研究证据，记录哪些 agent 协作模式被 promote/pilot/hold/reject。

`docs/V3.1-AGENT-CONTRACT-BENCHMARK.md` / `docs/V3.1-AGENT-CONTRACT-BENCHMARK.json` 是 agent contract 对比 `2026.06.12.1` release 的量化 benchmark，覆盖 Handoff Envelope、Return Envelope、History/Input Filter、Command/Tool Risk Policy、Step Budget / Stop Condition、Lifecycle Ledger、usage pilots 和研究证据覆盖。对应脚本是 `scripts/benchmark_agent_contract.py`。

`docs/V3.1-LOCAL-CODEX-SMOKE-REPORT.md` 是本机 Codex 配合实测报告，记录 live skills、Codex CLI、prompt-input skill 可见性、真实 subagent spawn/return/close、doctor bytecode 修复、验证结果和后续优化方向。

`docs/agent-collaboration-smoke.md` 是 V3.1 subagent runtime 的手动/HITL smoke checklist，覆盖 read-only dual explorer、No-Dispatch、local-write boundary、visibility policy、skill coupling 和 lifecycle ledger。

`docs/codex-usage.md` 是本 toolkit 仓库自己的 V3.1 真实试跑记录，当前包含第一阶段 4 个 M/L 样本、closeout 4 个 M/L 样本和阶段复盘，用于判断哪些规则真的省时间、哪些仍增加摩擦。它不同于 `repo-template/docs/codex-usage.md`，后者是复制到目标仓库的模板。

`docs/external-component-intake.md` 是外部 skill/plugin/MCP/hook/subagent prompt/workflow pack 的准入协议。对应只读脚本是 `scripts/audit_external_component.py`。

### 1. 先验证 toolkit 包

在新机器或复制后的目录里，先运行：

```bash
python3 scripts/verify_toolkit.py
```

期望输出：

```text
Workflow toolkit OK
```

这个检查会确认：

- 全局 `AGENTS.md`、repo 模板、11 个个人 Codex skills 都在包里。
- 外部组件准入文档、`scripts/audit_external_component.py`、`skill-plugin-intake-review` 都在包里。
- `implementation-plan` 没有重新出现，避免和 Superpowers 计划职责冲突。
- repo 模板自带的 `scripts/verify_context_pack.py` 可以通过。
- repo 模板包含 `docs/codegraph-pilot.md` 和 `docs/memory-recall-pilot.md`。
- repo 模板 `docs/subagents.md` 包含 Handoff Envelope、Return Envelope、History/Input Filter、Command/Tool Risk Policy、Step Budget / Stop Condition、Lifecycle Ledger 和 No-Dispatch Decision。
- 包里没有 `__pycache__`、`.pytest_cache`、`.pyc` 等生成缓存。
- 文档里没有明显凭证模式或私有 home path。
- `MANIFEST.sha256` 和当前文件内容一致。

如果已经安装到当前机器，再检查 live install 是否和 toolkit 完全一致：

```bash
python3 scripts/verify_live_install.py
```

期望输出：

```text
Live install OK (15 files checked)
```

这个检查只读比较 `~/.codex/AGENTS.md` 和 `~/.agents/skills/` 下的所有 packaged skill 文件，并检查活跃 Codex/Chrome 插件、native host 和 plugin cache symlink 路径没有指向其他 macOS 用户目录；发现本机配置与 output 包不一致或插件路径跑偏时会报告问题，不会自动覆盖。

如果想跑一条更完整但仍然只读的本机巡检命令：

```bash
python3 scripts/codex_doctor.py
```

期望输出：

```text
Codex doctor OK
- live_install: OK
- active_plugin_paths: OK
```

如果要运行 toolkit 自身测试，需要使用已安装 `pytest` 的 Python 环境：

```bash
python3 -m pytest tests/test_verify_toolkit.py tests/test_verify_live_install.py tests/test_render_usage_row.py tests/test_codex_doctor.py tests/test_codex_runtime_smoke.py tests/test_audit_skill_contracts.py tests/test_audit_repo_adoption.py tests/test_audit_external_component.py tests/test_benchmark_skill_polish.py tests/test_benchmark_agent_contract.py -q
cd repo-template
python3 scripts/verify_context_pack.py
python3 -m pytest tests/test_verify_context_pack.py -q
```

两组测试的工作目录不同：toolkit 测试在包根目录运行，repo context pack 测试在 `repo-template/` 目录运行。

### 2. 构建可迁移发布包

目录可以直接复制，也可以构建带 checksum 的归档包：

```bash
python3 scripts/build_release.py
```

输出位置：

```text
releases/codex-workflow-kit-<VERSION>.tar.gz
releases/codex-workflow-kit-<VERSION>.tar.gz.sha256
```

归档包内容包含 `VERSION` 和 `MANIFEST.sha256`。换机器后可以解压并先运行：

```bash
python3 scripts/verify_toolkit.py
```

如果要校验归档文件本身：

```bash
cd releases
shasum -a 256 -c codex-workflow-kit-<VERSION>.tar.gz.sha256
```

### 3. 一键安装到当前机器

先 dry-run，看会写哪些文件：

```bash
./install.sh --dry-run
```

确认后安装全局 Codex 宪法和个人 skills：

```bash
./install.sh
```

默认行为是非破坏式：如果目标位置已经有不同内容，脚本会停止并提示冲突。需要保留旧文件再替换时使用：

```bash
./install.sh --backup
```

只在确认要覆盖时使用：

```bash
./install.sh --force
```

如果要安装到自定义位置，适合测试或迁移演练：

```bash
./install.sh --codex-home /tmp/codex-home --agents-home /tmp/agents-home
```

### 4. 全局 Codex 宪法

`global/AGENTS.md` 是个人全局工作原则。安装脚本会把它放到 Codex home 的 `AGENTS.md`。

安装位置：

```text
~/.codex/AGENTS.md
```

### 5. Repo context pack 模板

`repo-template/` 是项目级模板。复制到目标仓库根目录后，根据项目实际情况填写。

项目 `AGENTS.md` 只写项目事实、项目规则、项目边界和验证矩阵，不重复全局宪法。

落地到已有仓库时要合并而不是机械覆盖：先检查是否已经存在同类文档或大小写等价文件，例如已有 `docs/ARCHITECTURE.md` 时，不再创建重复的 `docs/architecture.md`，而是在 `AGENTS.md` 和相关 docs 中索引现有文件。

模板自带 `scripts/verify_context_pack.py` 和 `tests/test_verify_context_pack.py`。复制到新仓库后，先按目标仓库真实 Python 入口调整命令，再运行 context pack 验证，确认文件、命令、架构文档引用和敏感模式检查可用。

安装位置：

```text
<repo>/
  AGENTS.md
  scripts/
  tests/
  docs/
```

也可以让安装脚本把 repo 模板复制到目标仓库：

```bash
./install.sh --repo /path/to/repo --dry-run
./install.sh --repo /path/to/repo --backup
```

如果全局 `AGENTS.md` 和个人 skills 已安装，只想给新仓库落地 context pack，使用更安静、写入面更小的 repo-only 模式：

```bash
./install.sh --repo-only --repo /path/to/repo --dry-run
./install.sh --repo-only --repo /path/to/repo --backup
```

落地前可以先做只读 adoption audit，判断适合 repo-only 安装还是人工合并：

```bash
python3 scripts/audit_repo_adoption.py /path/to/repo
```

批量审计或需要机器可读输出时使用：

```bash
python3 scripts/audit_repo_adoption.py --json /path/to/repo-a /path/to/repo-b
```

需要直接生成 adoption evidence 表格时使用：

```bash
python3 scripts/audit_repo_adoption.py --markdown /path/to/repo-a /path/to/repo-b
```

安装并验证 context pack 后，可以生成一行标准 baseline usage 记录，再追加到目标 repo 的 `docs/codex-usage.md`：

```bash
python3 scripts/render_usage_row.py baseline
python3 scripts/render_usage_row.py baseline --verification-command ".venv/bin/python scripts/verify_context_pack.py"
python3 scripts/render_usage_row.py pilot --pilot observability
python3 scripts/render_usage_row.py pilot --pilot subagents
python3 scripts/render_usage_row.py pilot --pilot mcp-code-graph
python3 scripts/render_usage_row.py pilot --pilot codegraph
python3 scripts/render_usage_row.py pilot --pilot memory-recall
python3 scripts/render_usage_row.py pilot --pilot plugin-mcp-trust
python3 scripts/render_usage_row.py pilot --pilot agent-config-lint
python3 scripts/render_usage_row.py pilot --pilot domain-pilot
python3 scripts/render_usage_row.py pilot --pilot external-component-intake
python3 scripts/render_usage_row.py trial --task "Runtime smoke evidence" --level M --tools "codex_runtime_smoke" --verification "runtime smoke OK" --effect "drift found early" --friction "manual agent cases remain HITL" --decision "keep package/runtime split"
python3 scripts/render_usage_row.py trial --preset trial-preset-helper
```

`pilot` 子命令只打印 Markdown 行，用于把可选工具试点记录到 `docs/codex-usage.md`；它不会写目标 repo、安装外部工具、启用 hooks 或启动 MCP。

`trial` 子命令只打印真实 M/L/XL 使用样本行，用于记录效率收益、摩擦和收紧决策；`--preset` 只填充常见 closeout 行的默认字段，仍允许显式覆盖 verification 或 decision。它不修改目标 repo，也不自动追加文档或晋升规则。

评估外部 skill、plugin、MCP、hook、subagent prompt 或 workflow pack 时，先运行只读 intake audit：

```bash
python3 scripts/audit_external_component.py /path/to/component
python3 scripts/audit_external_component.py /path/to/component --json
```

这个脚本只读扫描本地文件，不安装、不启用、不联网、不写目标组件；输出用于决定 `promote`、`pilot`、`repo-local`、`hold` 或 `reject`。

需要审计 packaged skill 契约完整度时运行：

```bash
python3 scripts/audit_skill_contracts.py
python3 scripts/audit_skill_contracts.py --json
python3 scripts/audit_skill_contracts.py --markdown
```

它会检查 11 个个人 Codex skills 的 metadata、trigger、Output Shape、边界、验证条件、progressive disclosure 和 Superpowers overlap 信号；这是包内契约审计，不安装、不启用外部能力。

需要汇总本机 Codex runtime 证据时运行：

```bash
python3 scripts/codex_runtime_smoke.py
python3 scripts/codex_runtime_smoke.py --check-prompt-input
python3 scripts/codex_runtime_smoke.py --markdown
```

它会汇总 live install、local doctor、Codex CLI 和 `docs/agent-collaboration-smoke.md` 手动 checklist。默认不跑 `codex debug prompt-input`；只有加 `--check-prompt-input` 时才验证模型可见的 11 个 custom skills。

需要重新生成 V3.1/V2.2 量化对比时运行：

```bash
python3 scripts/benchmark_v31_vs_v22.py --repetitions 5
```

它会从 release tarball 解包到临时目录，分别运行 package health、repo context pack、live install drill 和 external component intake 任务，并更新 `docs/V3.1-BENCHMARK.md` 与 `docs/V3.1-BENCHMARK.json`。

需要重新生成 skill polish 量化对比时运行：

```bash
python3 scripts/benchmark_skill_polish.py
```

它会从 pre-polish release tarball 解包 `2026.06.12`，和当前 post-polish toolkit tree 对比，并更新 `docs/V3.1-SKILL-POLISH-BENCHMARK.md` 与 `docs/V3.1-SKILL-POLISH-BENCHMARK.json`。

落地到已有仓库时，优先使用 `--dry-run` 看冲突。脚本不会自动覆盖已有不同文件；如果目标仓库已经有大小写等价的架构文档，例如 `docs/ARCHITECTURE.md`，脚本会停止，要求人工合并引用，避免创建重复文档。

### 6. 个人 skills

`skills/` 包含 11 个个人 Codex skills：

- `repo-onboarding`：为仓库建立 context pack。
- `spec-kit-xl`：为 XL/正式规格任务沉淀需求、非目标、验收标准和风险边界。
- `debug-loop`：失败后按观察、假设、修复、复测循环收敛。
- `frontend-qa`：前端真实浏览器/截图/移动端/状态验证。
- `decision-record`：长期技术取舍沉淀成 ADR。
- `completion-review`：测试和验证之后、最终回复之前的交付闸门。
- `security-review`：安全敏感代码、配置、依赖、hooks、MCP/plugin、CI 或信任边界变化时做专项审查。
- `dependency-upgrade-review`：依赖、lockfile、runtime/base image、GitHub Actions、CVE/advisory、license 或供应链风险变更时做专项审查。
- `research-brief`：评估 GitHub 仓库、skills、MCP、hooks、subagents、模型/API 或工具选型时形成证据化 promote/hold/reject 结论。
- `skill-plugin-intake-review`：吸收外部 skill、plugin、MCP、hook、subagent prompt、workflow pack 前做 promote/pilot/repo-local/hold/reject 准入审查。
- `release-readiness`：准备可复用 artifact、portable toolkit、release archive、checksum bundle 或迁移包时做发布前证据门禁；当前为 pilot。

这些 skills 设计为补充 Superpowers：`spec-kit-xl` 只做 XL/正式规格，`security-review`、`dependency-upgrade-review`、`research-brief`、`skill-plugin-intake-review`、`release-readiness` 只做专项审查/研究/准入/发布证据门禁，计划、TDD、阶段推进和执行仍交给 Superpowers。

安装位置：

```text
~/.agents/skills/
```

复制后应确认 Codex 的 skill 列表能看到：

```text
repo-onboarding
spec-kit-xl
debug-loop
frontend-qa
decision-record
completion-review
security-review
dependency-upgrade-review
research-brief
skill-plugin-intake-review
release-readiness
```

## 新机器落地顺序

推荐按这个顺序执行：

```bash
cd codex-workflow-kit
python3 scripts/verify_toolkit.py
python3 scripts/build_release.py
./install.sh --dry-run
./install.sh
python3 scripts/verify_live_install.py
python3 scripts/codex_doctor.py
python3 scripts/codex_runtime_smoke.py
python3 scripts/audit_skill_contracts.py
```

如果还要给某个仓库安装 context pack：

```bash
./install.sh --repo /path/to/repo --dry-run
./install.sh --repo /path/to/repo --backup
cd /path/to/repo
python3 scripts/verify_context_pack.py
```

如果目标仓库没有 `python3` 或使用虚拟环境，把最后一条命令替换成项目真实入口，例如：

```bash
.venv/bin/python scripts/verify_context_pack.py
```

## 试跑和效果评估

给新仓库安装 context pack 后，不要立刻启用整套 hooks、MCP 或 memory。subagents 按全局协议主动评估：L/XL、已有实施计划、跨模块、多独立失败源、多文件审查和可并行调查要先做 suitability check；存在 2 个以上独立非重叠子任务时主动使用，不使用时说明原因。推荐先做 3-5 个真实 M/L/XL 任务，把结果写入：

```text
docs/codex-usage.md
```

每条记录只保留可复用信号：用了什么流程、跑了什么验证、减少了什么误判或返工、暴露了什么副作用或成本。

完成 3-5 条后做一次阶段复盘：

- 保留连续带来收益的规则或验证路径。
- 把一次性经验留在记录中观察，不晋升为全局规则。
- hooks、MCP、memory 和新脚本先作为文档化候选，只有在重复证明有收益、边界清晰、可回退后再启用；subagents 保持边界驱动，不做共享状态无条件并行。
- subagents 必须做 lifecycle check：记录本轮 agent id，结果集成后调用 `close_agent`；只读检查、竞品观察和 reviewer 不再需要时也要关闭。
- 如果流程只是弥补文档缺失，优先更新 `AGENTS.md`、`docs/testing.md`、`docs/quality-gates.md` 或 `docs/codex-playbook.md`。

## 复用检查清单

换机器或迁移到新 Codex 环境时，确认：

- `python3 scripts/verify_toolkit.py` 输出 `Workflow toolkit OK`。
- `python3 scripts/build_release.py` 已生成 `releases/codex-workflow-kit-<VERSION>.tar.gz` 和 `.sha256`。
- `./install.sh --dry-run` 的计划符合预期。
- `global/AGENTS.md` 已复制到 `~/.codex/AGENTS.md`。
- `skills/*` 已复制到 `~/.agents/skills/`。
- `python3 scripts/verify_live_install.py` 能确认安装内容没有 drift。
- `python3 scripts/codex_doctor.py` 能确认 live install 和 active plugin paths 正常。
- 新仓库已复制 `repo-template/AGENTS.md`、`repo-template/docs/`、`repo-template/scripts/`，以及可选的 `repo-template/tests/`；其中包含 `docs/codegraph-pilot.md` 和 `docs/memory-recall-pilot.md`。
- Codex 可发现 11 个个人 Codex skills。
- repo `AGENTS.md` 没有重复全局宪法，只保留项目事实和边界。
- repo `docs/subagents.md` 包含 lifecycle 收口规则：本轮派出的 agent id 必须在不再需要时 `close_agent`。
- 已检查目标仓库是否有同类文档或大小写等价文件，避免重复创建或覆盖人工文档。
- `docs/commands.md`、`docs/testing.md`、`docs/quality-gates.md` 已按项目真实命令填写。
- context pack verifier 已用目标仓库真实解释器运行通过。
- `docs/codex-usage.md` 已按真实任务记录效果信号，不记录一次性过程或敏感信息。
- `docs/specs/` 只用于 XL/正式规格任务。
- 没有把凭证、token、私钥、生产数据或一次性调试过程写入模板、docs 或 memory。

## 当前落地阶段

已完成：

- 个人 Codex 宪法和任务分级协议。
- repo context pack 模板。
- Superpowers/spec-kit 总控协议。
- 11 个自定义核心/专项 skills。
- V3.1 外部组件准入协议和只读审查脚本。
- Code graph、memory/recall、plugin/MCP trust、agent config lint 和 domain skill 的 repo-local pilot 边界。
- MCP、代码图谱和 memory 的使用边界协议。
- hooks 质量门禁协议和 repo 模板。
- subagents 并行协议和 repo 模板。
- usage/效果评估协议和 repo 模板。
- 真实仓库 5 个 M 级样本试跑，并将验证副作用分级回灌到 repo 模板。
- hooks 候选集策略：默认只文档化，不自动启用；默认阻断 hooks 只考虑 A 级无写入/低副作用命令。

当前盘点：

- 已启用插件：Browser、Chrome、Computer Use、Documents、Spreadsheets、Presentations、Superpowers。
- 显式 MCP server：内建 `node_repl`。
- memory：Codex 本地存在内建 memory 状态；当前不新增自定义 memory server。
- 代码图谱：当前不安装额外代码图谱服务；先使用 `rg`、语言工具、测试和 repo docs 构建临时图谱。

下一阶段：

- 在真实 repo 继续累计 V3.1 usage 证据：外部组件准入、codegraph、memory-recall、plugin/MCP trust、agent config lint、domain-pilot 都先记录为 pilot，不默认安装或启用。

## 已校准的复盘结论

- `scripts/verify_context_pack.py` 适合做 A 级低副作用文档/context pack 门禁。
- 静态扫描和覆盖率这类会写 `test-results/`、coverage、trace 或截图的命令属于 B 级报告门禁；只有输出目录已忽略且成本可控时才前移。
- 通过 TestClient、dev server、preview server 或 app startup 做 health check 的命令属于 C 级应用生命周期门禁；即使不连接外部服务，也可能初始化本地数据库、启动调度器、写缓存、占用端口或生成报告，不应默认放入 hooks。
- 外部服务、真实数据同步、数据库迁移、部署、权限、交易、支付、生产或凭证相关命令属于 D 级高风险门禁，执行前需要用户确认。
- Compile/typecheck/lint 也要先确认是否会写 bytecode、cache、coverage、build 产物或自动格式化文件；会写产物的命令不应标成严格无写入 hook。
