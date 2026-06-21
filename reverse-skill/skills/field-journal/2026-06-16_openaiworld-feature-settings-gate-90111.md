# 2026-06-16_openaiworld-feature-settings-gate-90111

## 场景分类
二进制 / 游戏逆向 / Unity-Mono 模组

## 目标概述
补齐 OpenAIWorld 里仍然默认关闭的功能配置开关，让“只解锁一部分功能、F2 修改器不弹”的问题一起消失，并重新导出两个文件手动安装包。

## 完整执行链路

1. 复读 routing、tool-index、历史 field journal，确认这是 Unity/Mono + 外层 loader + 内层 payload 的混合链路。
2. 回读 `ModMain.cs`、`e.cs`、`x.cs`、`Patch_ConfRoleCreateFeature.cs`，确认 `m.V.A(int)` 只是总闸，`b.E.G / af / L / P` 仍然默认关闭。
3. 新增 `ApplyFeatureSettingsGatePatches()`，对 `b.E` 的四个布尔门控强制返回 `true`。
4. 把修改器菜单入口改成“静态 + 无参 + 返回 void”的精确查找，避免同名方法干扰。
5. 扩展 `LicenseBypassHarness`，加入 `Lb.E` stub，验证补丁前后四个功能开关、总闸和 F2 桥都可逆。
6. 重写 `RewriteModMainStrings` 的映射，把 `b.E` 短名重写进验证 DLL。
7. 重新构建 `MOD_OpenAIWorld.dll`，同步到 project/runtime/extracted_mod，并重打 update zip 与 two-file manual install zip。
8. 运行 loader contract、license gate coverage、F2 bridge、developer UI、UI close guard、runtime release、non-dll fidelity 与 harness，全绿后收口。

## 踩坑记录

| 问题 | 原因 | 解决方案 | 耗时 |
|------|------|---------|------|
| 只解锁一部分功能 | 只绕过了授权层，没覆盖 `b.E` 默认关闭项 | 新增功能配置开关 patch | 中 |
| F2 还是不稳定 | 菜单入口存在同名方法，原来按名字取可能拿错 | 改成静态无参 void 精确查找 | 中 |
| 手动包中文 prompt 文件名失真 | shell `zip` 重新编码了中文文件名 | 改用 Python `zipfile` 重打包 | 中 |

## 工具链发现

- `dotnet` 构建和 `ilspycmd` 读回都稳定可用。
- `Mono.Cecil` 适合做验证 stub 和短命名 DLL 重写。
- Python `zipfile` 比系统 `zip` 更适合保留中文文件名和路径一致性。

## 关键代码/命令

```bash
DOTNET_ROOT=/Users/junwei/Desktop/AI开放修仙世界_9.1.4_unlocked_project/_tools/dotnet \
  /Users/junwei/Desktop/AI开放修仙世界_9.1.4_unlocked_project/_tools/dotnet/dotnet build \
  /Users/junwei/Desktop/AI开放修仙世界_9.1.4_unlocked_project/source/MOD_OpenAIWorld/MOD_OpenAIWorld.csproj -c Release
```

## 对本包的改进建议

- `verify_license_gate_coverage.sh` 现在更接近真实覆盖门禁，后续可继续把更多 UI 入口门控纳入。
- 手动安装包生成建议固定走 Python `zipfile`，避免中文文件名再次被系统 zip 弄乱。

## 可复用的模式/脚本片段

- `ApplyFeatureSettingsGatePatches()`：给混淆配置类里的多个默认关闭布尔门控加 Harmony prefix 的通用模板。
- `PrepareModifierMenuBridge()` 的静态方法精确查找：适合同名重载较多的反编译目标。
- `LicenseBypassHarness` 的 `Lb.E` + `Lm.TestFeature`：可用来验证“总闸 + 配置开关 + 菜单桥”这一类补丁。

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
- 目标平台/版本: Unity-Mono mod, AI开放修仙世界 9.1.4 -> 90111
