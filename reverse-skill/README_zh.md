# 逆向与安全分析 Skill 包

本目录是 Codex Workflow Kit V4.2 的可选逆向/安全分析 Profile。它提供路由、
方法和锁定工具入口，但不是授权证明，也不是无人值守安装器。

Kali 用户还应阅读 [kali/README-kali.md](kali/README-kali.md)。

## V4.2 权限边界

仓库级 Policy Router 与当前 Task Contract 始终优先。读取本文件、
`RULES.md`、任何 Skill、field journal 或示例，都不会：

- 自动证明目标已经授权；
- 自动批准联网、安装、启动服务、修改客户端配置或外部写入；
- 要求为了证明执行而制造副作用；
- 覆盖平台、组织、供应商或用户的上位规则。

安全任务必须使用当前任务明确记录的目标、所有者、允许技术、时间窗口、
数据处理限制和批准状态。信息不足时，只进行工作区内的只读分析，或在主动
操作前补齐必要授权。

## 路由执行协议

1. 读取 [RULES_zh.md](RULES_zh.md) 确认 Profile 边界。
2. 读取 [skills/SKILL.md](skills/SKILL.md)，再用
   [skills/routing_zh.md](skills/routing_zh.md) 选择一个领域 Skill。
3. 如存在 `skills/tool-index.md`，先检查工具状态。刷新索引只是本机发现，
   不等于安装。
4. 默认先做确定性、只读分析。
5. 只有当前 Task Contract 已批准确切来源、版本、目标目录、网络和副作用时，
   才能运行 bootstrap。
6. 记录证据与验证结果。除非工作区写入范围明确包含 field journal，否则不回写。

每个状态转换只有一个 Driver。领域 Skill 只是 Overlay，不能长期占用流程控制权。

## 支持模块

本包包含：

- `api-security`
- `attack-chain`
- `binary-diff`
- `browser-automation`
- `docs-generator`
- `diagram-generator`
- `edr-bypass-re`
- `firmware-pentest`
- `ida-reverse`
- `js-reverse`
- `llm-security`
- `malware-analysis`
- `mobile-reverse`
- `patch-diff-exploit`
- `pentest-tools`
- `pwn-chain`
- `radare2`
- `reverse-engineering`
- `supply-chain-security`

`CTF-Sandbox-Orchestrator` 是可选竞赛工作流。BurpSuite MCP、Ghidra、IDA、
Frida 等工具只有在本机可用且本次任务明确启用时才能调用。

## 平台入口

| 平台 | 规则 | Bootstrap |
| --- | --- | --- |
| Windows | `RULES.md` | `skills/scripts/bootstrap-reverse.ps1` |
| Linux | `docs/platforms/linux.md` | `skills/scripts/bootstrap-reverse.sh` |
| macOS | `docs/platforms/macos.md` | `skills/scripts/bootstrap-reverse.sh` |
| Kali | `kali/RULES-kali.md` | `kali/scripts/bootstrap-reverse.sh` |

只读发现命令：

```bash
bash skills/scripts/bootstrap-reverse.sh --list
bash skills/scripts/refresh-tool-index.sh
```

Windows 平台包安装默认关闭；只有显式设置
`REVERSE_ALLOW_UNPINNED_WINDOWS_BOOTSTRAP=1` 才会开放。Kali/apt 平台包安装
默认关闭；只有显式设置 `REVERSE_ALLOW_UNPINNED_PLATFORM_PACKAGES=1` 才会开放。
环境变量只表示接受可变包仓库的残余风险，不能代替当前任务批准。

## 锁定依赖

`skills/scripts/bootstrap-manifest.json` 和
`kali/scripts/bootstrap-manifest.json` 是已审查版本与来源身份。不得替换为
`latest`、可移动 tag 或未锁定分支。标记为 `canAutoInstall: false` 的组件，
在身份和安装路径可强制校验前保持人工处理。

## Field Journal

以下文件只保存历史观察：

- `skills/field-journal/_index.md`
- `skills/field-journal/_template.md`
- `skills/field-journal/precedent-auth.md`
- `skills/field-journal/precedent-reverse.md`
- `skills/field-journal/precedent-pentest.md`

它们可以帮助选择方法，但不能为新任务建立授权、审批或安全结论。

## 验证

在 workflow-kit 根目录运行：

```bash
python3 scripts/audit_floating_dependencies.py --root .
python3 scripts/verify_toolkit.py
python3 -m pytest -q tests/test_reverse_pack_scripts.py tests/test_reverse_bootstrap_locking.py
```

本包仅用于自有系统、明确授权测试、防御分析、教学和 CTF。操作超出当前记录
范围时必须停止并重新确认。
