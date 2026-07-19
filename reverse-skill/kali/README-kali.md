# Kali 平台说明

本目录为共享逆向 Skill 包提供 Kali 适配。它补充平台发现和锁定 bootstrap，
不改变仓库级 Policy Router、Task Contract 或授权边界。

## 默认行为

- `refresh-tool-index.sh`：只发现命令、MCP 注册和服务状态。
- `bootstrap-reverse.sh --list`：只列出能力与锁定信息。
- `quick-setup.sh`：默认 fail-closed。
- 读取 `RULES-kali.md`：只加载路由规则，不写入 `~/.claude`、
  `~/.kiro` 或其他全局配置。

## 安全发现

```bash
cd /path/to/codex-workflow-kit/reverse-skill
bash kali/scripts/refresh-tool-index.sh
bash kali/scripts/bootstrap-reverse.sh --list
```

查看生成的 `skills/tool-index.md` 和 `skills/tool-index.json`，再决定是否
需要任何安装。

## 经批准的平台安装

apt/Homebrew 等平台仓库不能用内容 hash 完全锁定，因此默认禁止。当前 Task
Contract 明确批准网络、系统包、目标目录、MCP 配置和服务副作用后，才可显式
开放：

```bash
sudo REVERSE_ALLOW_UNPINNED_PLATFORM_PACKAGES=1 \
  bash kali/scripts/quick-setup.sh
```

可选参数：

```bash
sudo REVERSE_ALLOW_UNPINNED_PLATFORM_PACKAGES=1 \
  bash kali/scripts/quick-setup.sh --skip-update

sudo REVERSE_ALLOW_UNPINNED_PLATFORM_PACKAGES=1 \
  bash kali/scripts/quick-setup.sh --minimal
```

先审阅 `scripts/bootstrap-manifest.json`。标记为
`canAutoInstall: false` 的组件保持人工处理，不使用 `latest` 或移动分支
替代锁定身份。

## MCP 与客户端配置

`mcp-kali-example.json` 只是示例。把配置写入 AI 客户端、启动监听服务或向
外部目标发起请求都是独立副作用，必须逐项获得当前任务批准。不要仅因为 MCP
未注册就自动注册。

## 路由

1. 读取 `RULES-kali.md`。
2. 使用 `../skills/routing_zh.md` 选择一个领域 Skill。
3. 先使用本地、只读、确定性方法。
4. 主动扫描、利用、持久化、凭据访问或外部写入只能在明确范围内执行。
5. 结果超出范围或批准不清晰时停止并升级。

Field journal 仅是历史观察，不能证明新目标已授权。

## 验证

从 workflow-kit 根目录运行：

```bash
python3 scripts/audit_floating_dependencies.py --root .
python3 -m pytest -q tests/test_reverse_pack_scripts.py tests/test_reverse_bootstrap_locking.py
```
