# 2026-06-19 Codex referral repos static analysis

## 场景分类

Web / API / 供应链静态审计

## 目标概述

静态分析两个开源 Codex referral/SSO 自动化仓库，梳理协议登录、邀请、激活、OIDC 适配和安全风险。

## 完整执行链路

1. 按 reverse-engineering router 读取路由、tool-index、field journal index。
2. 将两个 GitHub 仓库克隆到当前工作区 `work/research-repos/`，只读分析，不运行登录、邀请、激活或 Token 刷新流程。
3. 对比文件结构、README、依赖、commit hash、sha256 和同名脚本差异。
4. 重点阅读 `codex_protocol_login.py`、`codex_invitation_helper.py`、`codex_invitation_batch.py`、`codex_activation_helper.py`、`codex_activation_batch.py`、`codex_referral_flow.py`、Sentinel 相关脚本。
5. 输出正式报告到工作区 `outputs/2026-06-19_codex-referral-repos-static-analysis.md`，包含流程图、关键端点、文件行号证据和风险结论。
6. 对报告执行敏感词扫描，确认未写入真实邮箱密码、access token、refresh token、id token 或 API key。

## 踩坑记录

| 问题 | 原因 | 解决方案 | 耗时 |
|------|------|---------|------|
| `Codex_team_auto` 与 `codex-referral-risk-research` 高度相似 | 前者是后者基础上的包装和 OIDC 适配 | 先做 sha256/diff，再读新增的 `codex_referral_flow.py` 与 OIDC patch | 10m |
| README 容易让人误以为是普通浏览器自动化 | 核心其实是协议登录和 OAuth token exchange | 直接读 OpenAI/Auth/OIDC/Sentinel 调用链 | 20m |
| 敏感材料风险高 | 分析过程中同目录存在真实测试账号 CSV | 报告只引用仓库占位符与代码结构，最后用 `rg` 扫描输出 | 5m |

## 工具链发现

- `rg` 适合定位端点、token、代理、TLS 验证、subprocess、auth.json 写入点。
- `diff -u` 和 `shasum -a 256` 快速确认两个仓库同源关系。
- 对这种仓库不要运行脚本；`--dry-run` 也可能读取真实 auth 文件或触发外部请求，应坚持静态分析。

## 关键代码/命令

```bash
git clone --depth 1 https://github.com/Tyxy-R/codex-referral-risk-research.git work/research-repos/codex-referral-risk-research
git clone --depth 1 https://github.com/gakiyukr/Codex_team_auto.git work/research-repos/Codex_team_auto
rg -n "auth.openai|chatgpt|invite|referral|oauth|token|sentinel|api/|register|login|proxy|verify=False|auth\\.json" work/research-repos -S
diff -u work/research-repos/codex-referral-risk-research/codex_protocol_login.py work/research-repos/Codex_team_auto/codex_protocol_login.py
shasum -a 256 work/research-repos/*/*.py work/research-repos/*/*.js
```

## 对本包的改进建议

- 这类“开源自动化工具逻辑审计”更适合补一个 lightweight route：`supply-chain-security` + `api-security` + `docs-generator`，避免误走二进制 RE。
- 输出要求应允许“只读静态分析报告”，不强制运行目标代码，尤其当运行会触发认证、账号、邀请、风控或外部平台副作用。

## 可复用的模式/脚本片段

- 先 clone 到 workspace `work/`，不要安装依赖或执行目标脚本。
- 三层审计顺序：
  1. README/文件树/依赖/commit。
  2. `rg` 定位端点、凭证、外部写入、本地状态写入。
  3. `diff` 分析同源 fork 的新增能力和默认参数变化。

## 进化动作

- [ ] 更新了路由矩阵
- [ ] 更新了 tool-index
- [ ] 更新了 bootstrap-manifest
- [ ] 更新了子 skill 文档
- [x] 新增了 pitfalls 记录
- [ ] 无需更新

## 环境信息

- OS: macOS
- 工具版本: system git, rg, shasum
- 目标平台/版本: GitHub public repositories at commits `9426c47a5188d303816992af953d4ccd22bac4d3` and `52778519dd1bcc5708dbc8f4d97cd61c0a39a977`

## 脱敏要求

本日志未包含真实用户邮箱、密码、token、私有域名配置或账号数据。

## 索引同步

已在 `_index.md` 的 Web / API / 渗透测试分类追加本条。

---
<!-- [进化统计] 本包累计完成项目: 11 | 本次新增模式: 1 | 本次修复工具链问题: 0 -->
