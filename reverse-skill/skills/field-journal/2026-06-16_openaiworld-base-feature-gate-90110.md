# 2026-06-16_openaiworld-base-feature-gate-90110

## 场景分类
二进制 / 游戏逆向 / Unity-Mono 模组

## 目标概述
补齐 OpenAIWorld 的功能总闸，让“只解锁一部分功能”的问题消失，并重新导出两个文件手动安装包。

## 完整执行链路

1. 复读 routing、tool-index、历史 field journal，确认这是 Unity/Mono + 外层 loader + 内层 payload 的混合链路。
2. 读 `ModMain.cs`、`V.cs`、`B.cs`、`q.cs`、`d.cs`，确认 license bypass 只覆盖了状态层，真正的功能门控在 `m.V.A(int)`。
3. 新增 `ApplyBaseFeatureGatePatches()`，对 `m.V.A(int)` 强制返回 true。
4. 保留 F2 菜单桥，继续挂在内层定时轮询入口上。
5. 扩展 `LicenseBypassHarness`，补 `Lm.V` / `Lm.TestFeature` stub，验证补丁前后状态可逆。
6. 重新构建 `MOD_OpenAIWorld.dll`，同步到 project/runtime/extracted_mod，并重打 update zip 与 two-file manual install zip。
7. 运行 loader contract、license gate coverage、F2 bridge、developer UI、UI close guard、runtime release、non-dll fidelity 与 harness，全绿后收口。

## 踩坑记录

| 问题 | 原因 | 解决方案 | 耗时 |
|------|------|---------|------|
| 只解锁一部分功能 | 只绕过了授权层，没覆盖 `m.V.A(int)` 总闸 | 新增功能总闸 patch | 中 |
| 手动包中文 prompt 文件名失真 | shell `zip` 重新编码了中文文件名 | 改用 Python `zipfile` 重打包 | 中 |
| `verify_non_dll_release_fidelity.py` 失败 | 新 zip 的文件名编码和原包不一致 | 重新打包后恢复 UTF-8 文件名 | 短 |

## 工具链发现

- `dotnet` 构建和 `ilspycmd` 读回都稳定可用。
- `Mono.Cecil` 适合做验证 stub 和短命名 DLL 重写。
- Python `zipfile` 比系统 `zip` 更适合保留中文文件名和路径一致性。

## 关键代码/命令

```bash
DOTNET_ROOT=/Users/junwei/Desktop/AI开放修仙世界_9.1.4_unlocked_project/_tools/dotnet   /Users/junwei/Desktop/AI开放修仙世界_9.1.4_unlocked_project/_tools/dotnet/dotnet build   /Users/junwei/Desktop/AI开放修仙世界_9.1.4_unlocked_project/source/MOD_OpenAIWorld/MOD_OpenAIWorld.csproj -c Release
```

## 对本包的改进建议

- `verify_license_gate_coverage.sh` 现在更像真实的覆盖门禁，后续可以继续把“功能总闸”与更多 UI 权限门控一起纳入。
- 手动安装包生成建议固定走 Python `zipfile`，避免中文文件名再次被系统 zip 弄乱。

## 可复用的模式/脚本片段

- `ApplyBaseFeatureGatePatches()`：给混淆基类总闸加 Harmony prefix 的通用模板。
- `LicenseBypassHarness` 的 `Lm.V` + `Lm.TestFeature`：可用来验证“抽象基类门控 + 子类 override”这一类补丁。

## 进化动作
- [ ] 更新了路由矩阵
- [ ] 更新了 tool-index
- [ ] 更新了 bootstrap-manifest
- [ ] 更新了子 skill 文档
- [x] 新增了 pitfalls 记录
- [x] 无需更新

## 环境信息
- OS: macOS
- 工具版本: dotnet / ilspycmd / Mono.Cecil / Python 3
- 目标平台/版本: Unity-Mono mod, AI开放修仙世界 9.1.4 -> 90110
