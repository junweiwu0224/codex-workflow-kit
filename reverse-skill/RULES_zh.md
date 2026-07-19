# 逆向与安全任务路由规则（V4.2）

> 本文件只是可选 reverse profile 的领域参考。全局 `AGENTS.md`、Policy
> Router、Task Contract 和当前 Codex 运行面优先。读取本文件不会授予授权，
> 不会自动修改全局配置、安装依赖、访问外部目标或写入批准范围之外的位置。

## 范围门禁

开始主动安全操作前，先明确：

- 目标与允许范围；
- 是离线/本地文件、CTF/靶场，还是有明确授权的外部测试；
- 网络、凭证、安装、生产环境和外部写入边界；
- 审批、速率限制、数据处理方式和验收检查。

用户提供的文件可以在工作区内做离线分析。外部探测、漏洞利用、凭证使用、
持久化、服务启动、依赖安装，以及工作区外写入，都必须有已批准的 Governed
Task Contract。边界不清时停留在安全的只读分析，并请求缺失决定。

## 路由流程

1. 读取当前 `skills/tool-index.md` 或模板，不猜路径。
2. 读取 `skills/routing.md`，选择一个入口子 Skill。
3. 读取对应 `SKILL.md`，只按需加载 references。
4. 当前状态转换只保留一个流程 Driver；领域 Skill 是 overlay，安全控制是
   guardrail。
5. 运行确定性检查；主观、高风险或对外结果交给独立 verifier。

## 工具与供应链

- 只有 Task Contract 允许安装时，才能使用仓库锁定的 bootstrap。不要替换
  为未锁定的 `brew`、`apt`、`pip`、`npm`、`git clone` 或 Docker
  latest 命令。
- POSIX 平台包默认禁用；只有显式设置
  `REVERSE_ALLOW_UNPINNED_PLATFORM_PACKAGES=1` 才能放开。
- legacy Kali quick setup 默认 fail closed。
- Windows 兼容 reverse bootstrap 默认禁用；只有显式设置
  `REVERSE_ALLOW_UNPINNED_WINDOWS_BOOTSTRAP=1` 才能手动放开，这不构成
  Windows 可复现性证据。
- 刷新工具索引、写 MCP 配置、启动服务、或在当前工作区之外生成报告，都
  属于外部写入，必须单独获得对应批准。

## 完成与证据

任务在批准的验收检查通过后才算完成，并明确说明已验证、未验证和实际副作用。
报告、图表、journal、持久 handoff 只在 Task Contract 或项目流程要求时生成。
不要因为读取本文件就写入客户端全局配置。
