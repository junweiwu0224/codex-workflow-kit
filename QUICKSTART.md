# Quickstart

这是一份迁移清单，用于把 Codex Workflow Kit 迁移到新机器，并在 10 分钟内应用到第一个新 repo。当前包是 v3.2 口径：保留全局规则、11 个个人 Codex skills、repo context pack、完整 `reverse-skill`、reverse router、live install 校验、doctor 巡检、runtime smoke、skill contract audit、外部组件准入、release-readiness pilot、codegraph/memory pilot、V3.1 证据和 baseline/pilot usage 记录。

## 1. 新机器最短安装命令

从 release 包安装：

```bash
tar -xzf codex-workflow-kit-2026.06.14.1.tar.gz
cd codex-workflow-kit
python3 scripts/verify_toolkit.py
./install.sh --dry-run
./install.sh
python3 scripts/verify_live_install.py
python3 scripts/verify_reverse_ready.py
python3 scripts/verify_apk_decode_smoke.py --apk-fixture /path/to/app.apk
python3 scripts/codex_doctor.py
python3 scripts/codex_runtime_smoke.py
python3 scripts/audit_skill_contracts.py
python3 scripts/audit_external_component.py skills/skill-plugin-intake-review
```

从已复制的目录安装：

```bash
cd codex-workflow-kit
python3 scripts/verify_toolkit.py
./install.sh --dry-run
./install.sh
python3 scripts/verify_live_install.py
python3 scripts/verify_reverse_ready.py
python3 scripts/verify_apk_decode_smoke.py --apk-fixture /path/to/app.apk
python3 scripts/codex_doctor.py
python3 scripts/codex_runtime_smoke.py
python3 scripts/audit_skill_contracts.py
python3 scripts/audit_external_component.py skills/skill-plugin-intake-review
```

Windows 新机器：

```powershell
powershell -ExecutionPolicy Bypass -File .\install.ps1 -DryRun
powershell -ExecutionPolicy Bypass -File .\install.ps1
powershell -ExecutionPolicy Bypass -File .\install.ps1 -WithReverseCore -VerifyReverseReady
python scripts/verify_live_install.py
python scripts/verify_reverse_ready.py
python scripts/verify_apk_decode_smoke.py --apk-fixture C:\path\to\app.apk
```

如果这台新机器的重点是 reverse-ready，而不是只把文件装进去，直接使用：

```bash
./install.sh --with-reverse-core
python3 scripts/verify_reverse_ready.py
python3 scripts/verify_apk_decode_smoke.py --apk-fixture /path/to/app.apk
```

若要把支持自动启动的本地 MCP 服务也一并拉起：

```bash
./install.sh --with-reverse-core --start-reverse-services
python3 scripts/verify_reverse_ready.py
```

如果希望把 readiness 校验直接绑定到安装流程：

```bash
./install.sh --with-reverse-core --verify-reverse-ready
```

如果只想补一部分 reverse core capability：

```bash
./install.sh --with-reverse-core --reverse-capabilities jadx,apktool,frida,r2,nmap
python3 scripts/verify_reverse_ready.py
```

如果机器上已有个人配置，先用备份模式安装：

```bash
./install.sh --backup
```

默认安装位置：

```text
~/.codex/AGENTS.md
~/.codex/skills/reverse-engineering/
~/.codex/reverse-skill/
~/.agents/skills/
```

## 2. 最短验证命令

验证 toolkit 包完整：

```bash
python3 scripts/verify_toolkit.py
python3 scripts/verify_live_install.py
python3 scripts/verify_reverse_ready.py
python3 scripts/verify_apk_decode_smoke.py --apk-fixture /path/to/app.apk
python3 scripts/codex_doctor.py
python3 scripts/codex_runtime_smoke.py
python3 scripts/audit_skill_contracts.py
python3 scripts/render_usage_row.py baseline
python3 scripts/render_usage_row.py pilot --pilot observability
python3 scripts/render_usage_row.py pilot --pilot external-component-intake
python3 scripts/render_usage_row.py pilot --pilot subagent-contract
python3 scripts/render_usage_row.py pilot --pilot agent-lifecycle-ledger
python3 scripts/render_usage_row.py pilot --pilot agent-eval-evidence
python3 scripts/render_usage_row.py trial --task "Runtime smoke evidence" --level M --tools "codex_runtime_smoke" --verification "runtime smoke OK" --effect "drift found early" --friction "manual agent cases remain HITL" --decision "keep package/runtime split"
python3 scripts/render_usage_row.py trial --preset trial-preset-helper
python3 scripts/audit_external_component.py skills/skill-plugin-intake-review
```

验证 release 包 checksum：

```bash
cd releases
shasum -a 256 -c codex-workflow-kit-2026.06.14.1.tar.gz.sha256
```

验证 toolkit 自身测试：

```bash
python3 -m pytest tests/test_verify_toolkit.py tests/test_verify_live_install.py tests/test_render_usage_row.py tests/test_codex_doctor.py tests/test_codex_runtime_smoke.py tests/test_audit_skill_contracts.py tests/test_audit_repo_adoption.py tests/test_audit_external_component.py tests/test_benchmark_skill_polish.py tests/test_benchmark_agent_contract.py -q
```

验证 repo context pack 模板：

```bash
cd repo-template
python3 scripts/verify_context_pack.py
python3 -m pytest tests/test_verify_context_pack.py -q
```

期望关键输出：

```text
Workflow toolkit OK
Live install OK
Reverse ready OK
APK decode smoke OK
Codex doctor OK
Codex runtime smoke OK
Skill contract audit OK
Context pack OK
```

`verify_toolkit.py`、`verify_live_install.py`、`verify_reverse_ready.py`、`verify_apk_decode_smoke.py`、`codex_doctor.py`、`codex_runtime_smoke.py`、`audit_skill_contracts.py` 和 `verify_context_pack.py` 都是只读验证：不联网、不安装外部工具、不启用 hooks、不启动 MCP、不写外部配置。`verify_live_install.py` 会额外检查 `~/.codex/skills/reverse-engineering/` 和 `~/.codex/reverse-skill/` 是否与包内 reverse 资产一致。`verify_reverse_ready.py` 则专门确认 reverse-ready core 是否真的在当前机器可执行。`verify_apk_decode_smoke.py` 会真实调用已安装的 `decode.sh` 跑一遍 APK 解包主链，确认 fresh install 下 `apktool` 不是假成功。`codex_doctor.py` 只汇总 live install drift 和活跃插件/native-host/plugin-cache 路径是否指向其他 macOS 用户目录。

`codex_runtime_smoke.py` 汇总 live install、local doctor、Codex CLI 和手动 agent checklist 证据；默认不运行 `codex debug prompt-input`，需要验证模型可见 skill 时加 `--check-prompt-input`。

`audit_skill_contracts.py` 扫描 packaged skills 的 metadata、trigger、Output Shape、边界、验证条件和 progressive disclosure，确认 11 个个人 skills 的契约完整。

`audit_external_component.py` 也是只读审查：不安装外部 skill/plugin/MCP/hook，不启用外部工具，不写目标组件，只输出 `promote`、`pilot`、`repo-local`、`hold` 或 `reject` 建议。

## 3. 首次应用到新 repo 的 10 分钟流程

第 0-2 分钟：安装前检查。

```bash
cd codex-workflow-kit
python3 scripts/verify_toolkit.py
./install.sh --dry-run
```

第 2-4 分钟：安装全局规则和个人 skills。

```bash
./install.sh
python3 scripts/verify_live_install.py
python3 scripts/codex_doctor.py
python3 scripts/codex_runtime_smoke.py
python3 scripts/audit_skill_contracts.py
```

第 4-6 分钟：给目标 repo 安装 context pack 模板。

```bash
./install.sh --repo-only --repo /path/to/repo --dry-run
./install.sh --repo-only --repo /path/to/repo --backup
```

第 6-8 分钟：在目标 repo 验证模板。

```bash
cd /path/to/repo
python3 scripts/verify_context_pack.py
```

如果项目使用虚拟环境，改用项目真实 Python：

```bash
.venv/bin/python scripts/verify_context_pack.py
```

第 8-10 分钟：让 Codex 首次读取并校准 repo context pack。

```bash
cd /path/to/repo
/path/to/codex-workflow-kit/scripts/render_usage_row.py baseline >> docs/codex-usage.md
```

如首次任务包含 V2.1 试点，例如 usage/session 观测、subagent prompt cards 或 MCP/code graph pilot，先只记录候选试用，不启用默认自动化：

```bash
/path/to/codex-workflow-kit/scripts/render_usage_row.py pilot --pilot observability >> docs/codex-usage.md
/path/to/codex-workflow-kit/scripts/render_usage_row.py pilot --pilot subagents >> docs/codex-usage.md
/path/to/codex-workflow-kit/scripts/render_usage_row.py pilot --pilot mcp-code-graph >> docs/codex-usage.md
/path/to/codex-workflow-kit/scripts/render_usage_row.py pilot --pilot codegraph >> docs/codex-usage.md
/path/to/codex-workflow-kit/scripts/render_usage_row.py pilot --pilot memory-recall >> docs/codex-usage.md
/path/to/codex-workflow-kit/scripts/render_usage_row.py pilot --pilot external-component-intake >> docs/codex-usage.md
/path/to/codex-workflow-kit/scripts/render_usage_row.py pilot --pilot subagent-contract >> docs/codex-usage.md
/path/to/codex-workflow-kit/scripts/render_usage_row.py pilot --pilot agent-lifecycle-ledger >> docs/codex-usage.md
/path/to/codex-workflow-kit/scripts/render_usage_row.py pilot --pilot agent-eval-evidence >> docs/codex-usage.md
```

首次打开目标 repo 后，给 Codex 的启动提示可以是：

```text
请先做 repo onboarding：阅读 AGENTS.md、docs/commands.md、docs/testing.md、docs/quality-gates.md、docs/architecture.md，确认当前仓库的验证命令和风险边界。
```

首次任务建议选择一个 M 级真实任务，要求 Codex：

```text
按当前 workflow 执行一个真实小改动：先读 repo context pack，再做最小实现，运行 targeted verification，最后把流程收益和问题记录到 docs/codex-usage.md。
```

## 4. 首次落地检查点

完成第一次 repo 应用后，确认：

- Codex 能看到 `repo-onboarding`、`spec-kit-xl`、`debug-loop`、`frontend-qa`、`decision-record`、`completion-review`、`security-review`、`dependency-upgrade-review`、`research-brief`、`skill-plugin-intake-review`、`release-readiness`。
- `python3 scripts/verify_live_install.py` 能确认当前机器的全局 AGENTS、11 个 skill 入口、`~/.codex/skills/reverse-engineering/` router 和 `~/.codex/reverse-skill/` 能力树与 output 包一致，并确认活跃 Codex/Chrome 插件、native host 和 plugin cache symlink 没有指向其他 macOS 用户目录。
- `python3 scripts/codex_doctor.py` 输出 `Codex doctor OK`。
- `python3 scripts/codex_runtime_smoke.py` 输出 `Codex runtime smoke OK`；需要验证 prompt-input skill 可见性时可加 `--check-prompt-input`。
- `python3 scripts/audit_skill_contracts.py` 输出 `Skill contract audit OK`，并确认 11/11 skills 通过契约审计。
- Desktop 侧逆向/渗透类请求能经 `~/.codex/skills/reverse-engineering/` 路由到 `~/.codex/reverse-skill/skills/routing.md`。
- 目标 repo 有 `AGENTS.md`、`docs/commands.md`、`docs/testing.md`、`docs/quality-gates.md`、`docs/codex-usage.md`。
- 目标 repo 有 V3.1 试点文档：`docs/observability.md`、`docs/mcp-pilot.md`、`docs/codegraph-pilot.md`、`docs/memory-recall-pilot.md`，但没有默认安装外部工具、启用 hooks 或启动 MCP。
- 目标 repo 的 `docs/subagents.md` 有 Handoff Envelope、Return Envelope、History/Input Filter、Command/Tool Risk Policy、Step Budget / Stop Condition、Lifecycle Ledger 和 No-Dispatch Decision。
- `python3 scripts/verify_context_pack.py` 或项目真实入口能输出 `Context pack OK`。
- 小任务没有强行启用 XL/spec-kit 流程。
- M/L/XL 任务优先由 Superpowers 做计划、TDD、阶段推进和验证。
- usage 记录只沉淀可复用信号，不写一次性流水账。
- `pilot` usage row 只作为 observability、subagents、MCP/code graph、codegraph、memory-recall、external-component-intake、subagent-contract、agent-lifecycle-ledger 或 agent-eval-evidence 证据入口，不作为晋升默认行为的证明。
