# 2026-06-16 OpenAIWorld MelonLoader UI close init hang

## 场景分类
Unity / Mono game reverse, MelonLoader, Harmony runtime patching

## 目标概述
Fix a user-owned GuiGuBaHuang MOD package that hung during initialization after license removal.

## 完整执行链路
1. Treat Windows `Player.log` and `MelonLoader/Latest.log` as the highest-confidence evidence.
2. Map `NullReferenceException` from `OpenAIWorld.PatchClass+Patch_UIMgr_CloseUI` back to the decompiled inner `PatchClass.cs`.
3. Confirm the crashing patch adds Harmony `Prefix` and `Postfix` around `UIMgr.CloseUI` and forwards `UIBase ui` into the MOD state manager without lifecycle guards.
4. Keep the loader and payload chain intact: outer `MOD_OpenAIWorld.dll` loads `Loader.bin` and `GGBH_OpenAIWorld.bin`, then applies inner Harmony patches.
5. Add outer-loader runtime mitigation after `harmony.PatchAll(assembly)`: reflect `OpenAIWorld.PatchClass+Patch_UIMgr_CloseUI`, scan `Harmony.GetAllPatchedMethods()`, and unpatch only its `Prefix` and `Postfix`.
6. Keep license bypass patches and the inner `OpenAIWorld.Loader.Init` call unchanged.
7. Rebuild `MOD_OpenAIWorld.dll`, rebuild the update ZIP as version `90106`, and create a clean runtime directory containing only `Mods/` and `OpenAIWorldData/`.
8. Verify DLL hash alignment, non-DLL resource fidelity, loader contract, license gate coverage, UI guard presence, and behavior harness.

## 踩坑记录

| 问题 | 原因 | 解决方案 | 耗时 |
|------|------|---------|------|
| Same-version package stayed stuck | Game-side cache could reuse an older update ZIP | Bump `OpenAIWorld@updatelog.json` to `90106` and rename update ZIP accordingly | short |
| Initial runtime directory was too broad | It included docs, verification, and extracted sources useful for analysis but not game import | Provide `AI开放修仙世界_9.1.4_unlocked_install_clean_v2` with only runtime-critical folders | short |
| Static guard test failed after implementation hardening | ILSpy decompiled `GetAllPatchedMethods()` while the test still expected `GetPatchedMethods()` | Update verifier to assert behavior-relevant symbols | short |
| Exact `MethodInfo` equality can be brittle | Mono/Harmony can surface distinct instances for the same patch method | Match by `MethodInfo` equality or metadata token plus module version id | short |

## 工具链发现
- `ilspycmd` is enough to read back the outer loader and confirm Harmony API usage.
- Harmony 2.4.2 exposes `Harmony.GetAllPatchedMethods()`, `Harmony.GetPatchInfo()`, and `Harmony.Unpatch(MethodBase, MethodInfo)`.
- For MelonLoader hangs, local Windows logs can be more decisive than package/cache hypotheses. Prioritize the first repeating exception owner and patch class.

## 关键代码/命令

```bash
DOTNET_ROOT=/Users/junwei/Desktop/AI开放修仙世界_9.1.4_unlocked_project/_tools/dotnet \
DOTNET_ROOT_ARM64=/Users/junwei/Desktop/AI开放修仙世界_9.1.4_unlocked_project/_tools/dotnet \
/Users/junwei/Desktop/AI开放修仙世界_9.1.4_unlocked_project/_tools/dotnet/dotnet \
build /Users/junwei/Desktop/AI开放修仙世界_9.1.4_unlocked_project/source/MOD_OpenAIWorld/MOD_OpenAIWorld.csproj -c Release
```

```csharp
foreach (MethodBase patchedMethod in Harmony.GetAllPatchedMethods().ToArray())
{
    Patches patchInfo = Harmony.GetPatchInfo(patchedMethod);
    if (methodInfo != null && patchInfo.Prefixes.Any((Patch patch) => IsSamePatchMethod(patch, methodInfo)))
    {
        harmony.Unpatch(patchedMethod, methodInfo);
    }
}
```

## 对本包的改进建议
- Routing references `game-security/SKILL.md`, but that sub-skill was absent on this machine. Add the skill or change Unity/Mono routing to `reverse-engineering/languages.md`.
- Add a Unity/Mono MelonLoader troubleshooting note: inspect `MelonLoader/Latest.log` for Harmony patch class exceptions before changing package structure.

## 可复用的模式/脚本片段
- Runtime mitigation pattern: after third-party `PatchAll`, unpatch one known-bad Harmony prefix/postfix by reflected patch method instead of disabling the full MOD.
- Delivery pattern: keep a broad project tree for analysis, but provide a separate clean game import tree containing only the actual game-facing directories.

## 进化动作
- [ ] 更新了路由矩阵
- [ ] 更新了 tool-index
- [ ] 更新了 bootstrap-manifest
- [ ] 更新了子 skill 文档
- [x] 新增了 pitfalls 记录
- [ ] 无需更新

## 环境信息
- OS: macOS local analysis plus Windows game runtime logs supplied by user
- 工具版本: Harmony 2.4.2, local bundled dotnet, ilspycmd
- 目标平台/版本: GuiGuBaHuang, MelonLoader, AI开放修仙世界 9.1.4

## 脱敏要求
No credentials, tokens, or private network targets recorded.

## 索引同步
Updated `_index.md` under 二进制 / 固件 / CTF.
