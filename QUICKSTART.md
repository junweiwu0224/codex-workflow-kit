# Quickstart

这是一份迁移清单，用于把 Codex Workflow Kit V4.2 迁移到新机器，并在 10 分钟内应用到第一个新 repo。工具包包含 14 个个人 Codex skills；默认安装仅包含薄全局规则和 Stable profile，Pilot、reverse、外部候选、网络服务及外部写入都需要显式启用或审批。

## 1. 新机器最短安装命令

从 release 包安装：

```bash
tar -xzf codex-workflow-kit-2026.07.19.1.tar.gz
cd codex-workflow-kit
python3 scripts/verify_toolkit.py
python3 scripts/validate_governance.py
python3 scripts/refresh_local_lock.py
python3 scripts/audit_floating_dependencies.py
./install.sh --dry-run
./install.sh
python3 scripts/verify_live_install.py
python3 scripts/codex_doctor.py
python3 scripts/codex_runtime_smoke.py
python3 scripts/audit_skill_contracts.py
python3 scripts/audit_external_component.py skills/skill-plugin-intake-review
python3 scripts/resolve_components.py --catalog catalog/components.yaml --lock catalog/upstreams.lock.json --root . --output /tmp/codex-workflow-v42-resolver.json
```

从已复制的目录安装：

```bash
cd codex-workflow-kit
python3 scripts/verify_toolkit.py
./install.sh --dry-run
./install.sh
python3 scripts/verify_live_install.py
python3 scripts/codex_doctor.py
python3 scripts/codex_runtime_smoke.py
python3 scripts/audit_skill_contracts.py
python3 scripts/audit_external_component.py skills/skill-plugin-intake-review
```

Windows 新机器：

```powershell
powershell -ExecutionPolicy Bypass -File .\install.ps1 -DryRun
powershell -ExecutionPolicy Bypass -File .\install.ps1
powershell -ExecutionPolicy Bypass -File .\install.ps1 -WithPilots
$env:REVERSE_ALLOW_UNPINNED_WINDOWS_BOOTSTRAP = '1'
powershell -ExecutionPolicy Bypass -File .\install.ps1 -WithReverseCore -VerifyReverseReady
python scripts/verify_live_install.py
python scripts/verify_reverse_ready.py
python scripts/verify_apk_decode_smoke.py --apk-fixture C:\path\to\app.apk
```

这组 PowerShell 命令是目标运行路径，不是已完成的 Windows 实机证据；V4.2 当前仍需要在真实 Windows 主机上补安装、冲突、卸载、rollback 和 reverse bootstrap 演练。Windows reverse bootstrap 默认 fail closed，不能把未设置环境变量时的失败写成安装通过。Ghidra 的大型 release asset/bootstrap 也必须在显式 reverse 环境中单独验证，不能由静态 lock 或其他小型 reverse smoke 代替。

普通安装只写入全局规则和 Stable skills，不会复制 Pilot skills、reverse router 或完整能力包。需要 Pilot skills 时使用 `./install.sh --with-pilots`。如果这台新机器的重点是 reverse-ready，直接使用：

Stable profile 包含 `completion-review`、`debug-loop`、`decision-record`、`dependency-upgrade-review`、`frontend-qa`、`junwei-frontend-design`、`repo-onboarding`、`research-brief`、`security-review` 和 `skill-plugin-intake-review`。

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
~/.codex/skills/              # reverse profile 启用后才包含 reverse-engineering/
~/.codex/reverse-skill/      # 仅 -WithReverse / -WithReverseCore
~/.agents/skills/
```

升级后先查看旧 profile，再决定是否清理：

```bash
./install.sh --prune-preview
./install.sh --prune
./install.sh --uninstall
./install.sh --rollback
```

安装在复制前建立私有 write-ahead journal；状态管理器统一校验 preimage、创建排他 nonce 备份并原子替换，成功后才提交受管状态。中途失败会自动恢复已覆盖文件并删除本次新建文件。PowerShell 对应 `-PrunePreview`、`-Prune`、`-Uninstall`、`-Rollback`。`prune`/`uninstall` 默认保护用户修改，显式 force 会改变这一行为；`rollback` 只撤销最近一次提交、恢复此前 Profile/ownership state，不会强制丢弃本次新建后又被修改的用户内容，也不会从残留 `.bak-*` 猜测归属。

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
python3 scripts/validate_task_contract.py path/to/task-contract.json --json
python3 scripts/policy_router.py path/to/task-contract.json --json
python3 scripts/runtime_policy.py route path/to/task-contract.json \
  --event-log path/to/events.jsonl \
  --event-anchor path/to/events.anchor.json \
  --json
python3 scripts/event_log.py validate path/to/events.jsonl \
  --anchor-path path/to/events.anchor.json \
  --json
PYTHONPATH=. python3 scripts/eval_harness.py --suite eval/fixtures/routing-demo.json --runner fixture --output /tmp/v42-eval.json
```

Governed 运行时必须同时具备独立的 event log 和 anchor，并由真实 tool broker 向 Python API 提供可信的审批/强制器 verifier 回调。`runtime_policy.py` CLI 只是诊断入口，不会自行认证审批文件或强制器，因此 Governed allow 会 fail closed。`event_log.py` 同时锁住 log 与 anchor；anchor 记录 canonical log identity、事件数与末尾 hash，禁止两个日志共享。验证时必须带 `--anchor-path`，这样才能检测截尾、替换或并发写入造成的链漂移。

repo-local lock 覆盖整个 Skill 目录树（相对路径、内容和可执行位），不是只覆盖 `SKILL.md`。reverse dependency lock 则按字段区分 `enforced`、`verified`、`metadata-only` 和 `blocked`；不要把“lock 中已记录”解释成“所有字段都已 exact enforcement”。当前除 anything-analyzer 的 Git identity 外均保守为 metadata-only；无可复现锁的 apt/Homebrew 安装默认禁用，只能通过单独的 `REVERSE_ALLOW_UNPINNED_PLATFORM_PACKAGES=1` 显式放开。

fixture Eval 只验证 harness，并永远保持 `promotion_decision: hold`。干净 HOME/worktree 不是系统级沙箱；非 fixture adapter 需要宿主提供可信 `isolation_verifier`，当前 `--runner command` CLI 因无法提供该回调而在执行前 fail closed。

发布候选时，先生成 paired/shadow fixture reports 作为发布管道 smoke，再把 archive、plugin 和全部 Eval reports 在 `write` 与 `verify` 两次调用中显式、原样绑定：

```bash
python3 scripts/build_plugin.py --root . --output /tmp/junwei-core --profile stable
python3 scripts/refresh_local_lock.py
PYTHONPATH=. python3 scripts/eval_harness.py \
  --suite eval/fixtures/routing-demo.json --runner fixture --mode paired \
  --output /tmp/v42-eval.json
PYTHONPATH=. python3 scripts/eval_harness.py \
  --suite eval/fixtures/routing-demo.json --runner fixture --mode shadow \
  --output /tmp/v42-shadow.json
python3 scripts/build_release.py --require-clean --output-dir /tmp/codex-workflow-kit-release
python3 scripts/build_release_evidence.py write \
  --root . --output /tmp/codex-workflow-kit-evidence \
  --archive /tmp/codex-workflow-kit-release/codex-workflow-kit-<VERSION>.tar.gz \
  --plugin /tmp/junwei-core \
  --eval-report /tmp/v42-eval.json \
  --eval-report /tmp/v42-shadow.json \
  --require-clean-source
python3 scripts/build_release_evidence.py verify \
  --root . --output /tmp/codex-workflow-kit-evidence \
  --archive /tmp/codex-workflow-kit-release/codex-workflow-kit-<VERSION>.tar.gz \
  --plugin /tmp/junwei-core \
  --eval-report /tmp/v42-eval.json \
  --eval-report /tmp/v42-shadow.json \
  --require-resolved --require-clean-source --require-eval
```

`verify` 会重算源码 manifest、release manifest、SBOM 和 notices，逐项确认工作树与 `HEAD` blob/mode/文件集合一致，要求归档是当前源码的逐字节可复现构建，并要求 plugin manifest、Profile 与锁定 Skill tree 一致。`--require-eval` 拒绝空报告集；fixture reports 不构成真实候选晋升证据。真实候选先用 `attest-eval` 和 `catalog/eval-trust-policy.json` 中预置的 key 指纹生成仓库外 registry，再使用 `--require-real-eval --eval-attestations /secure/path/attestations.json --eval-attestation-key /secure/path/eval-hmac.key`；report/suite/subject/source commit 必须全部匹配。公开门还会原子要求 Stable Profile Eval 与许可证。

验证 release 包 checksum：

```bash
cd releases
shasum -a 256 -c codex-workflow-kit-2026.07.19.1.tar.gz.sha256
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

`verify_toolkit.py`、`verify_live_install.py`、`verify_reverse_ready.py`、`verify_apk_decode_smoke.py`、`codex_doctor.py`、`codex_runtime_smoke.py`、`audit_skill_contracts.py` 和 `verify_context_pack.py` 都是只读验证：不联网、不安装外部工具、不启用 hooks、不启动 MCP、不写外部配置。`verify_live_install.py` 默认只检查全局规则和个人 skills；只有已安装 reverse profile 或显式传 `--with-reverse` 时才检查 reverse 资产。`verify_reverse_ready.py` 和 `verify_apk_decode_smoke.py` 仅在 reverse profile 已启用后运行。

`codex_runtime_smoke.py` 汇总 live install、local doctor、Codex CLI 和手动 agent checklist 证据；默认不运行 `codex debug prompt-input`。需要验证当前 profile 的模型可见 Skill 时加 `--check-prompt-input`，需要同时验证外部 Superpowers 时再加 `--require-superpowers`。

`audit_skill_contracts.py` 扫描 packaged skills 的 metadata、trigger、Output Shape、边界、验证条件和 progressive disclosure，确认 14 个个人 skills 的契约完整。

`audit_external_component.py` 也是只读审查：不安装外部 skill/plugin/MCP/hook，不启用外部工具，不写目标组件，只输出 `promote`、`pilot`、`repo-local`、`hold` 或 `reject` 建议。

需要安装并验证可选 reverse profile 时，单独执行：

```bash
./install.sh --with-reverse
python3 scripts/verify_live_install.py --with-reverse
python3 scripts/verify_reverse_ready.py
```

## 3. 首次应用到新 repo 的 10 分钟流程

第 0-2 分钟：安装前检查。

```bash
cd codex-workflow-kit
python3 scripts/verify_toolkit.py
./install.sh --dry-run
```

第 2-4 分钟：安装全局规则和 Stable skills。

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

- Codex 默认能看到 Stable profile 中的 10 个 skills；只有使用 `--with-pilots` 后，才额外看到 `spec-kit-xl`、`release-readiness`、`junwei-browser-automation` 和 `junwei-product-demo-video`。
- `python3 scripts/verify_live_install.py` 默认确认全局 AGENTS 和 10 个 Stable skill 入口；使用 `--with-pilots` 时要求全部 14 个，如果启用了 reverse profile，再使用 `--with-reverse` 检查 router 和能力树。
- `python3 scripts/codex_doctor.py` 输出 `Codex doctor OK`。
- `python3 scripts/codex_runtime_smoke.py` 输出 `Codex runtime smoke OK`；需要验证 prompt-input skill 可见性时可加 `--check-prompt-input`。
- `python3 scripts/audit_skill_contracts.py` 输出 `Skill contract audit OK`，并确认 14/14 skills 通过契约审计。
- 只有显式启用 reverse profile 后，Desktop 侧逆向/渗透类请求才经 `~/.codex/skills/reverse-engineering/` 路由到 `~/.codex/reverse-skill/skills/routing.md`。
- 目标 repo 有 `AGENTS.md`、`docs/commands.md`、`docs/testing.md`、`docs/quality-gates.md`、`docs/codex-usage.md`。
- 目标 repo 有 V3.1 试点文档：`docs/observability.md`、`docs/mcp-pilot.md`、`docs/codegraph-pilot.md`、`docs/memory-recall-pilot.md`，但没有默认安装外部工具、启用 hooks 或启动 MCP。
- 目标 repo 的 `docs/subagents.md` 有 Handoff Envelope、Return Envelope、History/Input Filter、Command/Tool Risk Policy、Step Budget / Stop Condition、Lifecycle Ledger 和 No-Dispatch Decision。
- `python3 scripts/verify_context_pack.py` 或项目真实入口能输出 `Context pack OK`。
- 小任务没有强行启用 XL/spec-kit 流程。
- M/L/XL 任务优先由 Superpowers 做计划、TDD、阶段推进和验证。
- usage 记录只沉淀可复用信号，不写一次性流水账。
- `pilot` usage row 只作为 observability、subagents、MCP/code graph、codegraph、memory-recall、external-component-intake、subagent-contract、agent-lifecycle-ledger 或 agent-eval-evidence 证据入口，不作为晋升默认行为的证明。
