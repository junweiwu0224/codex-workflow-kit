# 2026-06-16 OpenAIWorld F2 modifier menu bridge

## 场景分类
Unity / Mono game reverse, Harmony runtime patching, mod import packaging

## 目标概述
用户反馈 AI开放修仙世界已能导入但按 F2 无法调出修改器菜单；需要把运行时菜单入口接到可用热键上，并保持安装包只含 `Mods/` 和 `OpenAIWorldData/`。

## 完整执行链路
1. 先区分“授权已解锁”与“菜单入口未接通”，避免把问题误判成 license 仍受限。
2. 从截图和反编译源码确认“修改器”对应的真实入口是 `...Y.o.C()` 打开 `OAIW_UIModMenu`，不是傀儡系统或 hack mode。
3. 发现外层 `ModMain` 不是 `MonoBehaviour`，不能直接写 Unity `Update()` 指望自动回调。
4. 进一步确认模板工程是靠 `g.timer.Frame(new Action(OnUpdate), 1, true)` 或内层循环做每帧回调，因此 F2 桥应挂在现成内层循环上。
5. 在外层 `MOD_OpenAIWorld.dll` 里给内层 `...f.d.d()` 增加 Harmony postfix，利用反射调用 `UnityEngine.Input.GetKeyDown(KeyCode.F2)`。
6. F2 命中时反射调用 `...Y.o.C()` 打开修改器菜单；保留原来的 license bypass 和 UI CloseUI 兼容补丁。
7. 重建 DLL、回填到 `extracted_mod`、`runtime` 和 90108 更新包，并导出只含 `Mods/`、`OpenAIWorldData/` 的手动安装包。
8. 新增 `verification/verify_f2_modifier_menu_bridge.sh`，用反编译文本验证 F2 桥、菜单入口和日志字符串；避免依赖 `strings` 读取中文 UTF-16 文本。

## 踩坑记录

| 问题 | 原因 | 解决方案 | 耗时 |
|------|------|---------|------|
| 以为给 `ModMain` 加 `OnUpdate()` 就够了 | 这个 MOD 的模板/宿主实际是通过 timer/内层循环回调，不是普通 Unity MonoBehaviour 生命周期 | 改成给内层主循环 `...f.d.d()` 打 Harmony postfix | short |
| `strings` 验证中文日志失败 | DLL 里的中文多为 UTF-16/混合编码，ASCII `strings` 不稳定 | 改为用 `ilspycmd` 反编译读回文本验证 | short |
| 生成手动包路径时误用了 `Path.with_suffix()` | 目录名包含 `.4`，被当成“扩展名”处理 | 改为显式目标路径 `/Users/junwei/Desktop/AI开放修仙世界_9.1.4_unlocked_manual_install_90108.zip` | short |

## 工具链发现
- 这类 Unity/Mono MOD 入口问题，先看实际菜单方法名，再找每帧回调点，别只盯 `Update()`。
- 手动安装包最好只保留 `Mods/` 和 `OpenAIWorldData/` 顶层，避免把工作区 docs/verification/extracted 混进去。
- 验证中文日志时，反编译读回比 `strings` 更稳。

## 关键代码/命令

```bash
DOTNET_ROOT=/Users/junwei/Desktop/AI开放修仙世界_9.1.4_unlocked_project/_tools/dotnet \
DOTNET_ROOT_ARM64=/Users/junwei/Desktop/AI开放修仙世界_9.1.4_unlocked_project/_tools/dotnet \
/Users/junwei/Desktop/AI开放修仙世界_9.1.4_unlocked_project/_tools/dotnet/dotnet \
build /Users/junwei/Desktop/AI开放修仙世界_9.1.4_unlocked_project/source/MOD_OpenAIWorld/MOD_OpenAIWorld.csproj -c Release -nologo
```

```text
MOD_OpenAIWorld.dll SHA256: 18818aba29e270ebb55f0a7058bea4cb1afd70a05357341f8d8af26ec26c0b24
90108 update ZIP SHA256: aedd5ef4354a95e3c9483e6542f61039b7b99c030dd80783f3d1464ac4ff3cad
90108 manual ZIP SHA256: 8a8bf781c27a79765ef9a49e177032db4c54b037daf5138ac9a3161d509e0a4c
```

## 可复用的模式/脚本片段
- `Harmony postfix + reflection + Input.GetKeyDown(KeyCode.F2)` 适合给混淆/封装 MOD 补热键入口。
- 对中文日志和混淆字符串，优先用反编译器读回验证，不要只靠 `strings`。
- 手动安装包要先清理旧版本，再显式重打版本号一致的 ZIP，避免缓存命中旧包。

## 进化动作
- [ ] 更新了路由矩阵
- [ ] 更新了 tool-index
- [ ] 更新了 bootstrap-manifest
- [ ] 更新了子 skill 文档
- [x] 新增了 pitfalls 记录
- [ ] 无需更新

## 环境信息
- OS: macOS local analysis; target runtime is Windows GuiGuBaHuang / MelonLoader
- 工具版本: bundled dotnet 10.0.301, Harmony 2.4.2, ilspycmd, Python zipfile
- 目标平台/版本: AI开放修仙世界 9.1.4, package version `90108`

## 脱敏要求
No credentials, tokens, or private network targets recorded.
