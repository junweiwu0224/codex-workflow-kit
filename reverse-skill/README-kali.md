# 逆向 Skill 包：Kali 入口

这是顶层 Kali 快速入口；详细规则见
[kali/RULES-kali.md](kali/RULES-kali.md)，平台说明见
[kali/README-kali.md](kali/README-kali.md)。

## V4.2 边界

- 阅读文档不会授予目标权限，也不会批准安装、联网、服务启动、MCP 注册、
  全局配置修改或外部写入。
- 当前 Task Contract 必须明确目标、允许技术、写入范围和批准状态。
- 默认仅做本机发现和只读分析；缺少批准时保持 fail-closed。
- field journal 是历史参考，不是授权先例。

## 只读初始化

```bash
bash kali/scripts/refresh-tool-index.sh
bash kali/scripts/bootstrap-reverse.sh --list
```

这两条命令用于发现工具状态，不安装包、不启动服务，也不修改 AI 客户端配置。

## 平台包安装

`quick-setup.sh` 涉及 apt、pip、npm、MCP 配置和可能的服务状态。只有在当前
任务明确批准这些副作用，并接受可变 OS 包仓库风险时才运行：

```bash
sudo REVERSE_ALLOW_UNPINNED_PLATFORM_PACKAGES=1 \
  bash kali/scripts/quick-setup.sh
```

该环境变量不是授权证明。运行前仍需审阅
`kali/scripts/bootstrap-manifest.json` 和脚本将修改的目标。

## 路由

读取 `kali/RULES-kali.md` 后，使用 `skills/routing_zh.md` 选择一个领域
Skill。路由本身不触发安装或主动扫描；所有主动安全操作仍受 Task Contract
和上位政策限制。

本包支持 `reverse-engineering`、`ida-reverse`、`apk-reverse`、
`js-reverse`、`mobile-reverse`、`firmware-pentest`、
`pentest-tools`、`api-security`、`malware-analysis` 和其他共享模块。

## 验证

```bash
python3 scripts/audit_floating_dependencies.py --root .
python3 -m pytest -q tests/test_reverse_pack_scripts.py
```
