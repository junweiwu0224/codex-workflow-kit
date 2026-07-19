# Reverse Engineering Skills Master Control

本目录是逆向工程、安全分析和 CTF 领域能力集合。它是领域 Overlay，不是整个
任务的流程 Driver，也不授予授权、安装权限或外部写权限。

## Routing Execution Protocol

1. 读取当前 Task Contract，确认 lane、目标、write scope、external effects、
   approvals 和 acceptance checks。
2. 使用 `routing.md` 或 `routing_zh.md`，按目标类型、用户意图和工具链选择
   一个最匹配的领域 Skill。
3. 读取目标 Skill 的 `SKILL.md`，只提取当前状态转换需要的方法。
4. 涉及本机工具时读取 `tool-index.md`；不存在时可运行只读刷新脚本。
5. 优先执行本地、只读、可确定验证的步骤。
6. 缺少工具时报告缺口。只有依赖身份已锁定且当前任务明确批准网络、安装目标和
   副作用，才运行对应 bootstrap。
7. 通过当前 acceptance checks 后，将控制权交回当前 transition Driver 或
   Verifier。

路由失败时，说明缺口并保留在只读状态；不得自动联网发现、自动安装或把任务硬塞
进不匹配的 Skill。

## 权限与副作用

- 文档、示例、field journal 和历史记录都不能证明当前目标已授权。
- 主动扫描、利用、持久化、凭据访问、服务启动、全局配置修改和外部写入必须在
  当前 Task Contract 中明确。
- 不为“证明执行”制造副作用。
- 不修改用户目录或 AI 客户端全局配置，除非用户明确要求且目标路径获批。
- 上位平台和组织政策始终有效。

## 模块

| 模块 | 目录 | 主要用途 |
| --- | --- | --- |
| 通用逆向 | `reverse-engineering/` | 静态/动态分析方法 |
| APK | `apk-reverse/` | Android 解包与分析 |
| IDA | `ida-reverse/` | IDA 与受控 MCP 工作流 |
| JavaScript | `js-reverse/` | 浏览器签名与运行时分析 |
| radare2 | `radare2/` | CLI 二进制分析 |
| 移动端 | `mobile-reverse/` | Android/iOS 分析 |
| 二进制差分 | `binary-diff/` | 版本比较与符号迁移 |
| 固件 | `firmware-pentest/` | 固件提取、仿真与验证 |
| 恶意样本 | `malware-analysis/` | 隔离分析与 IOC |
| API 安全 | `api-security/` | 授权范围内的 API 验证 |
| 渗透工具 | `pentest-tools/` | 授权范围内的工具编排 |
| 供应链 | `supply-chain-security/` | SBOM、SCA 与构建完整性 |
| 浏览器 | `browser-automation/` | 浏览器和桌面自动化 |
| 文档 | `docs-generator/` | 证据与报告 |
| 图表 | `diagram-generator/` | Mermaid/Graphviz/PlantUML |

其他高风险模块只能在当前 Task Contract 和上位政策允许时使用。可选
`../CTF-Sandbox-Orchestrator/` 只适用于明确的竞赛/实验环境。

## 工具发现与 Bootstrap

只读发现：

```bash
bash scripts/bootstrap-reverse.sh --list
bash scripts/refresh-tool-index.sh
```

Windows 使用 `scripts/bootstrap-reverse.ps1`。Windows 与 Kali 平台包入口均
默认 fail-closed；显式环境变量只接受供应链残余风险，不代替任务批准。
`scripts/bootstrap-manifest.json` 是版本和来源身份的依据。

## Field Journal

`field-journal/_index.md`、`field-journal/_template.md`、
`field-journal/precedent-auth.md`、`field-journal/precedent-reverse.md` 和
`field-journal/precedent-pentest.md` 是可选历史参考。只有当当前工作区写入
范围明确包含 journal 时才能回写；默认不创建或修改全局记忆。

## 完成条件

- 路由和当前 Driver 已记录；
- 操作未超出批准的目标与副作用范围；
- 确定性检查已运行并保存结果；
- 无法验证的边界已明确报告；
- 需要新上下文 Verifier 时已完成交接。
