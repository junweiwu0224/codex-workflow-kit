# 2026-06-16 古韵 Steam 入库工具 / ManifestHub 样本源码恢复

## 场景分类
二进制分析 / Go GUI 逆向 / Wails 桌面应用源码恢复

## 目标概述
把 `古韵Steam入库工具 - v5.75New.exe` 的样本专属后端能力面继续还原回桌面源码树，并为后续 macOS 重构建立平台差距文档。

## 完整执行链路

1. 复用上一轮确认结果：样本是 `Go 1.26.3 + Wails 2.11.0 + WebView2`，公开同源仓库只覆盖了旧版底稿。
2. 回读 `redress source` 留下的 `go-source-projection.txt`，确认缺失模块仍然是 `steam_online.go`、`gbe_auth.go`、`cw_extract.go`、`screen_windows.go`。
3. 直接从样本字符串表和打包前端 RPC 面反推参数签名与返回结构：
   - `GBEOneClickAuth(exePath, appid, steamID, iniPath, useCW)`
   - `GBEGeneratePatch(...)`
   - `CWExtractStart(appid, outputDir)`
   - `DownloadSteamworksExample()`
   - `LaunchGameWithSpacewar(appid, exe)`
4. 发现样本的前端/配置面已经明显超过公开仓库：
   - 新增 `steam_path`
   - 新增 `kernel_type`
   - 新增 `enable_workshop`
5. 先补公共类型与配置字段，再把四个缺失模块写回桌面源码树。
6. 额外写一份 `docs/macos-port-gap-analysis.md`，把 Windows-only 能力和 macOS 替代方向分层。
7. 把旧底稿里直接写死在通用文件里的平台依赖拆开：
   - `steam_path_windows.go` / `steam_path_other.go`
   - `gbe_registry_windows.go` / `gbe_registry_other.go`

## 踩坑记录

| 问题 | 原因 | 解决方案 | 耗时 |
|------|------|---------|------|
| 公开仓库源码明显不等于样本版本 | 样本继续演进了前端 RPC 和配置面，GitHub 主仓库只保留旧版 | 不再把桌面工程当作“直接可编译的原始源码”，改为“高保真底稿 + 样本专属模块恢复” | 20m |
| `redress` 本轮不在 PATH | 本机 PATH 与上一轮不同 | 直接退回到已有 `go-source-projection.txt` 和二进制字符串证据 | 5m |
| 样本前端源码未直接拿到 | Wails 前端被嵌进二进制，当前仅能从字符串表读出压缩后的调用面 | 先恢复后端能力面和结构体，再把前端重建留到下一阶段 | 15m |
| 原仓库把 Windows 注册表逻辑散在通用文件里 | 旧版底稿本来就只面向 Windows | 先拆出平台文件，让恢复后的源码可继续作为 macOS 重构底稿演进 | 10m |

## 工具链发现

- `strings` + `rg` 仍然是恢复 Wails 打包前端 RPC 面的最高性价比组合。
- 当前这台机器上的 `radare2/rabin2` 可用，但这轮核心信息主要来自：
  - 上轮留存的 `go-source-projection.txt`
  - 样本字符串表
  - 公开同源仓库
  - `OpenSteamTool` 参考项目
- 当 `redress` 临时不在 PATH 时，仍可继续做源码层恢复，不必卡死在工具缺失。

## 关键代码/命令

```bash
strings -a "/Users/junwei/Downloads/古韵Steam入库工具 - v5.75New.exe" \
  | rg -n "GBEOneClickAuth|CWExtractStart|LaunchGameWithSpacewar|SwitchOpenKernelServer"

sed -n '1,260p' "/Users/junwei/Desktop/古韵Steam入库工具_v5.75New_源码还原/recovered/go-source-projection.txt"

sed -n '119980,120290p' <(strings -a "/Users/junwei/Downloads/古韵Steam入库工具 - v5.75New.exe")

cd "/Users/junwei/Desktop/古韵Steam入库工具_v5.75New_源码还原" && go test ./...
cd "/Users/junwei/Desktop/古韵Steam入库工具_v5.75New_源码还原" && GOOS=windows GOARCH=amd64 go test ./...
```

## 对本包的改进建议

- `reverse-engineering/go-reverse.md` 可补一条经验：
  - Wails 打包前端源码缺失时，优先从 `window.go.main.App.*` 的字符串面反推 RPC 签名。
- `field-journal/_index.md` 已有 Go 逆向条目，但可以新增一个“Wails 桌面二进制源码恢复”实体标签分组。

## 可复用的模式/脚本片段

- 恢复 Go/Wails 桌面样本时，优先补这些层：
  1. 配置结构和全局变量
  2. RPC 返回结构
  3. 缺失业务模块
  4. 平台差距文档
- 对于“无法百分百还原原始加密细节”的授权容器，可先构造一套可回环的恢复格式，把前后端链路打通，再继续替换为更高保真实现。

## 进化动作

- [ ] 更新了路由矩阵
- [ ] 更新了 tool-index
- [ ] 更新了 bootstrap-manifest
- [ ] 更新了子 skill 文档
- [x] 新增了 pitfalls 记录
- [ ] 无需更新

## 环境信息

- OS: macOS 15.x
- 工具版本: Go 1.26.3 样本 / Wails 2.11.0 / 本地 strings + rg + rabin2
- 目标平台/版本: Windows GUI 样本 `古韵Steam入库工具 - v5.75New.exe`
