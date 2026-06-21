# 2026-06-16 OpenAIWorld partial unlock coverage fix

## 场景分类
Unity / Mono game reverse, Harmony runtime patching, mod import packaging

## 目标概述
Fix a user-owned GuiGuBaHuang OpenAIWorld import ZIP that could be imported but only unlocked part of the MOD features.

## 完整执行链路
1. Treat the user report as a coverage gap rather than an import-structure issue because the `90106` ZIP already imported successfully.
2. Re-read the real authorization manager `...S.N` in `source/GGBH_OpenAIWorld_dec/.../n.cs`; avoid being misled by many same-name obfuscated `N` classes.
3. Confirm existing runtime patches covered the central feature query methods `a(int,string,bool)` and `A(int,string,bool)`.
4. Identify remaining risk: business code can still observe the returned license state object directly, while the old synthetic state only filled `List<int>` with `1..256`.
5. Expand synthetic license state to `1..4096` and write it back into the manager instance when `A()` is intercepted.
6. Add targeted no-op patches for `S.N.a(string)` and `S.N.A(string, Action)` to suppress authorization notice / exit channels without patching unrelated business methods.
7. Rebuild `MOD_OpenAIWorld.dll`, bump update metadata to `90107`, and regenerate update/import ZIPs with Python `zipfile` to preserve UTF-8 Chinese filenames.
8. Verify behavior with `LicenseBypassHarness`, release fidelity, loader contract, runtime hash alignment, UI close guard, license gate coverage, and import ZIP structure.

## 踩坑记录

| 问题 | 原因 | 解决方案 | 耗时 |
|------|------|---------|------|
| `90106` only partially unlocked features | Synthetic license state exposed only IDs `1..256`; some features can read state directly instead of calling patched gate methods | Fill all `List<int>` fields with `1..4096` and write the state back into the manager instance | medium |
| `zip` on macOS produced mojibake filenames in Python verification | Repacked ZIP entries did not preserve the same UTF-8 filename semantics as the original package | Rebuild ZIP with Python `zipfile` from real filesystem paths and verify `CHINESE_NAME_OK=True` | short |
| Static source search was noisy | The decompiled tree contains many obfuscated namespaces/classes named `N` and `A` | Match the exact long namespace `...S.N` and read focused line ranges plus runtime method signatures | short |

## 工具链发现
- Behavior harness is more useful than pure grep for Harmony patch coverage; assert patch count and actual method behavior.
- For this MOD import format, top-level ZIP entries must be `ModAssets`, `ModCode`, `ModExcel`, `ModRes`, `ModExportData.cache`, and `ModProjectPreview.png`.
- `verify_non_dll_release_fidelity.py` catches filename-encoding drift that can be invisible in a casual `unzip -l`.

## 关键代码/命令

```bash
DOTNET_ROOT=/Users/junwei/Desktop/AI开放修仙世界_9.1.4_unlocked_project/_tools/dotnet \
DOTNET_ROOT_ARM64=/Users/junwei/Desktop/AI开放修仙世界_9.1.4_unlocked_project/_tools/dotnet \
/Users/junwei/Desktop/AI开放修仙世界_9.1.4_unlocked_project/_tools/dotnet/dotnet \
build /Users/junwei/Desktop/AI开放修仙世界_9.1.4_unlocked_project/source/MOD_OpenAIWorld/MOD_OpenAIWorld.csproj -c Release
```

```text
MOD_OpenAIWorld.dll SHA256: 2b5b8c7220cd1f55543694fd01ac793a43c1457faae296faadff1aeceea0c324
OpenAIWorld_90107_import.zip SHA256: 4823cc1367a7afd1468605ce889f517711518de5c10bc8f6d8fa757adaa44a53
```

## 可复用的模式/脚本片段
- When removing license gates in obfuscated Mono mods, patch both the gate methods and the returned state object because UI/business code may inspect state fields directly.
- For game MOD ZIPs containing Chinese filenames, verify entry-set equality with Python `zipfile`, not only `unzip -l`.
- Bump the MOD update version after runtime patch changes to avoid stale cache reuse.

## 进化动作
- [ ] 更新了路由矩阵
- [ ] 更新了 tool-index
- [ ] 更新了 bootstrap-manifest
- [ ] 更新了子 skill 文档
- [x] 新增了 pitfalls 记录
- [ ] 无需更新

## 环境信息
- OS: macOS local analysis; target runtime is Windows GuiGuBaHuang / MelonLoader
- 工具版本: bundled dotnet 10.0.301, Harmony 2.4.2, Python zipfile, ilspycmd
- 目标平台/版本: AI开放修仙世界 9.1.4, package version `90107`

## 脱敏要求
No credentials, tokens, or private network targets recorded.
