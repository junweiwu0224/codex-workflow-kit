# 2026-06-13 ghidra headless MCP `/bin/cat` 验证

## 场景分类
二进制分析 / Ghidra / Codex MCP 集成

## 目标概述
把 `ghidra` 从先前不稳定的 GUI 插件实验态切到低扰动的用户级 headless MCP，并验证 `gpt-5.4` 在 Codex 中能真实调用它对 `/bin/cat` 跑通 `xrefs / rename / exports / segments`。

## 完整执行链路

1. 读取 reverse skill 路由、`reverse-engineering/SKILL.md`、`tool-index.md` 与 field journal 索引，确认本轮目标是二进制分析链上的 `Ghidra (headless) + MCP`。
2. 复盘上一轮结论：官方 `GhidraMCP` GUI 插件链受 `ghidra 12.1.2` 兼容性和 Burp 占用 `8080` 双重阻塞，不再适合作为主路径。
3. 使用 `pyghidra` 在临时环境先打通 `open_program`、函数遍历、字符串读取、导入符号读取、入口函数反编译与反汇编，确认 headless 路线技术上可行。
4. 在 `/Users/junwei/.codex/reverse-skill/ghidra-mcp/headless/` 新建最小 `stdio MCP` bridge，先只实现 `open_binary`、`get_current_binary`、`list_functions`、`search_functions_by_name`、`decompile_function`、`decompile_function_by_address`、`disassemble_function`、`list_strings`、`list_imports`、`close_binary`。
5. 为 bridge 建独立运行时 `/Users/junwei/.codex/reverse-skill/ghidra-mcp/headless/.venv`，只安装 `pyghidra`，避免依赖 `/tmp` 试验环境。
6. 仅修改 `/Users/junwei/.codex/config.toml` 中 `ghidra` 一段，把 transport 从 `url=http://localhost:8765/mcp` 切到 `stdio command=/.../.venv/bin/python ghidra_headless_mcp.py`，并保留备份。
7. 首轮原始 JSON-RPC 自测失败，错误是 `Path element starting with '.' is not permitted`；根因不是 bridge 逻辑，而是 Ghidra 项目目录在 `.codex/...` 下，目录组件以点开头。
8. 将 Ghidra 项目目录改为 `/Users/junwei/CodexGhidraProjects` 后再次自测，`open -> list -> decompile -> disassemble -> strings -> imports -> close` 全链成功。
9. 运行 `codex exec -m gpt-5.4` 的真实案例，明确要求“只使用 `ghidra MCP` 分析 `/bin/cat`，不要退回别的工具”，并抓取完整事件流。
10. 检查 `gpt54-ghidra-events.jsonl`，确认模型实际调用了 `server:\"ghidra\"` 的 MCP 工具，再更新报告与日志。
11. 参考 `bethington/ghidra-mcp` 的 endpoint 设计，在现有 bridge 上增量实现 `get_xrefs_to`、`get_xrefs_from`、`get_function_xrefs`、`rename_function_by_address`、`rename_function`、`rename_data`、`list_exports`、`list_segments`，不切换到更重的 Java headless server。
12. 先跑扩展原始 JSON-RPC 自测，再单独验证 `rename_function_by_address` 可跨 reopen 持久化，最后跑扩展版 `codex exec -m gpt-5.4` 真实案例。

## 踩坑记录

| 问题 | 原因 | 解决方案 | 耗时 |
|------|------|---------|------|
| 官方 GUI 插件链一直不稳定 | `GhidraMCP 1.4` 与本机 `ghidra 12.1.2` 不匹配，且默认依赖 `8080` | 放弃 GUI 主路径，改为 `pyghidra` 用户级 headless MCP | 20min |
| 原始自测 `open_binary` 失败 | Ghidra `ProjectLocator` 不允许路径组件以 `.` 开头，`.codex` 正中坑位 | 将项目目录移到 `/Users/junwei/CodexGhidraProjects` | 8min |
| `codex exec` 过程中出现 HTTP 502 噪音 | 其他 HTTP 型 MCP 在启动时重试，不代表 `ghidra` 失败 | 以事件流里是否出现 `server:\"ghidra\"` 的成功调用作为真实判据 | 6min |
| 顶层直接 `import ghidra.*` 导致模块导入失败 | `pyghidra` 未 start 前，Java 包命名空间不存在 | 把 `SourceType` 改成延迟导入，只在 rename handler 内获取 | 3min |
| `rename` 看起来成功但必须确认是否持久化 | 仅 `flushEvents()` 不足以证明写入已保存到项目 | 改用 `program.save(...)`，并在独立 project 上做 rename→close→reopen→验证→改回 | 8min |

## 工具链发现

- `pyghidra 3.1.0` 足够支撑最小 headless 分析链，不需要继续硬拧官方 GUI MCP release。
- `pyghidra 3.1.0` 也足够支撑轻量写操作链，至少当前已验证函数 rename 与 data label rename 可用。
- `codex mcp list` / `codex mcp get ghidra` 很适合做“配置层已接入”的快速确认。
- Ghidra 的项目目录规则比普通脚本更严格，不能把实际工程目录放到带点前缀的路径组件下。
- `gpt-5.4` 在 Codex 中只要 MCP 真接上，就能稳定调用 `ghidra` 返回反编译、反汇编、字符串和导入表，不再停在解释层。
- 对真实逆向收益最高的增量是 `xrefs + rename`：前者让模型能追关系，后者让多轮分析能沉淀命名；`exports + segments` 是顺手但高性价比的补强。

## 关键代码/命令

```bash
codex mcp list
codex mcp get ghidra

source /Users/junwei/.codex/reverse-skill/ghidra-mcp/headless/.venv/bin/activate
GHIDRA_PROJECTS_DIR=/Users/junwei/CodexGhidraProjects \
python /Users/junwei/.codex/reverse-skill/ghidra-mcp/headless/ghidra_headless_mcp.py

codex exec -m gpt-5.4 --skip-git-repo-check --color never --json \
  -o .verification/ghidra/out/gpt54-ghidra-last-message.txt \
  -C /Users/junwei/Documents/逆向工程 - \
  < .verification/ghidra/out/gpt54-ghidra-prompt.txt \
  > .verification/ghidra/out/gpt54-ghidra-events.jsonl

codex exec -m gpt-5.4 --skip-git-repo-check --color never --json \
  -o .verification/ghidra/out/gpt54-ghidra-extended-last-message.txt \
  -C /Users/junwei/Documents/逆向工程 - \
  < .verification/ghidra/out/gpt54-ghidra-extended-prompt.txt \
  > .verification/ghidra/out/gpt54-ghidra-extended-events.jsonl
```

## 对本包的改进建议

- `tool-index` 里可以补充一条说明：Ghidra GUI 插件可用与否不等于 `ghidra` 能力不可用，headless MCP 是更稳的备用主路径。
- `reverse-engineering/tools.md` 可补一节“Codex headless Ghidra MCP 最小命令集”，方便后续 agent 直接走这条链。
- 如果后续要继续扩充工具面，可以逐步把 `xrefs`、`rename`、`exports`、`segments` 补到 headless bridge，而不必等 GUI 插件恢复。

## 可复用的模式/脚本片段

可复用的低扰动 Ghidra 集成模式：

```text
1. 不把主路径绑定到 GUI 插件和固定 HTTP 端口
2. 先用 pyghidra 打通 open/list/decompile/disassemble/strings/imports 最小集合
3. 再按实际收益把 xrefs / rename / exports / segments 增量补进来
4. 用 stdio MCP bridge 接入 Codex，避免额外端口冲突
5. Ghidra 项目目录避开 .dot-prefixed path component
6. 先做原始 JSON-RPC 自测，再做 gpt-5.4 的真实 Codex 案例
```

## 进化动作
- [ ] 更新了路由矩阵
- [ ] 更新了 tool-index
- [ ] 更新了 bootstrap-manifest
- [x] 更新了子 skill 文档
- [x] 新增了 pitfalls 记录
- [ ] 无需更新

## 本轮补充验证

- 扩展原始 JSON-RPC 自测：`raw-mcp-selftest-v3.jsonl`
- rename 持久化专项验证：函数名 `entry -> entry_tmp_persist -> reopen -> entry`
- 扩展真实案例：`gpt54-ghidra-extended-events.jsonl`

## 本轮结论

这条 headless Ghidra MCP 已经从“最小只读可用”升级成“可读 + 受控写 + 可真实追关系”的状态。

具体来说：

- `segments`、`exports`、`xrefs to`、`function xrefs`、`xrefs from` 都已在 raw selftest 和 `gpt-5.4` 真实案例里成功返回。
- `rename_function_by_address` 已验证可持久化，不是一次会话内假成功。
- `rename_data` 已验证能真实创建/修改 data label，并能恢复。
- 全部写操作都限制在临时 Ghidra project 中，未打乱既有 `burp` / `jshook` / `anything-analyzer` 工作流。

## 环境信息
- OS: macOS Darwin 24.6.0
- 工具版本: `ghidra 12.1.2`, `pyghidra 3.1.0`, `gpt-5.4`
- 目标平台/版本: macOS Mach-O `/bin/cat`

## 脱敏要求

本条目仅包含本地公开系统二进制路径、用户本机本地目录和公开工具版本，不包含账号、token、私有 URL、生产数据或敏感凭证。
