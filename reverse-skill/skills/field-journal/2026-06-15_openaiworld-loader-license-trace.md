# 2026-06-15 OpenAIWorld loader license trace

## 场景分类
二进制分析

## 目标概述
对 `AI开放修仙世界_9.1.4` 发布包完成 loader 解包，并沿 `license`、`UI license info`、本地授权文件路径三条线继续追踪离线授权落点。

## 完整执行链路

1. 从 RAR 发布包中提取 `MOD_OpenAIWorld.dll`，定位其嵌入资源 `Loader.bin` 与 `GGBH_OpenAIWorld.bin`。
2. 逆向 `Loader.bin`，确认其使用硬编码 key material 经 `SHA256` 派生 AES-256-CBC key，并以密文前 16 字节作为 IV。
3. 成功解密 `GGBH_OpenAIWorld.bin`，得到托管程序集 `GGBH_OpenAIWorld.dec.bin`。
4. 对明文 DLL 做字符串和 .NET 元数据扫描，确认存在 `OpenAIWorld.mod`、`OpenAIWorld.mod.data`、`OpenAIWorld.ui`、`ReadAllText`、`WriteAllText`、`GetModPathRoot`、`get_pathModExportData` 等业务符号。
5. 在发布包资源中发现明确的授权 UI 资源 `oaiw_uilicenseinfo.ab`。
6. 提取安装文档中的截图与文案，确认授权文件名固定为 `License`，并确认其放置目录为 `OpenAIWorldData` 根目录。
7. 从安装截图中确认授权 UI 至少包含 `SteamID` 展示、`点击复制`、`打开授权文件夹`、`刷新授权` 三类操作。

## 踩坑记录

| 问题 | 原因 | 解决方案 | 耗时 |
|------|------|---------|------|
| 直接扫 DLL 没命中 `license` 字符串 | .NET 程序集里授权文案不一定以明文字符串出现，可能在资源包或安装文档里 | 改走“程序集 + 资源包 + 安装文档截图”交叉取证 | 中 |
| 本机缺少现成 .NET 反编译链 | 无 `dotnet` / `mono` / `ilspycmd` | 先用 `dnfile` 做元数据扫描，再用发布包里的资源和文档补证据 | 中 |
| `oaiw_uilicenseinfo.ab` 二进制内容不易直接读文本 | Unity asset bundle 不是纯文本 | 转而利用文档截图和资源命名做 UI 语义确认 | 低 |

## 工具链发现

- `openssl` 足够完成这次 AES-256-CBC 解密验证。
- `dnfile` 在缺少完整 .NET 反编译器时，仍然能提供 TypeDef / MemberRef 级别的有效辅助。
- 对 Unity/模组发布包，安装文档与截图本身就是高价值证据源，尤其适合追 UI 文案与路径约定。

## 关键代码/命令

```bash
openssl enc -d -aes-256-cbc \
  -K 5a9bb825873d61e53e30f0f210e18189f980285ba5582f00e3aae5625923a384 \
  -iv 6d8373a113a334b6f89bc4a834d453d7 \
  -in ggbh_cipher.bin \
  -out GGBH_OpenAIWorld.dec.bin

/usr/bin/strings -a GGBH_OpenAIWorld.dec.bin | rg -in \
  "license|pathmodexportdata|getmodpathroot|openaiworld\\.mod|readalltext|writealltext"

find _work/ai-xiuxian-9.1.4 -iname '*license*' -o -iname '*授权*'
```

## 对本包的改进建议

- `reverse-engineering` 主 skill 可补一条轻量 .NET 反编译回退建议，覆盖“没有 dnSpy/ILSpy 时先用 `dnfile` 做 metadata triage”。
- `field-journal` 模板可以明确提醒：发布包附带的安装文档、截图、资源命名往往能作为路径/功能的直接证据。

## 可复用的模式/脚本片段

- 当授权字符串在程序集里不明显时，优先建立三条并行证据线：
  - 明文程序集符号
  - 资源包命名
  - 安装文档/截图/说明文字
- 对 Unity/模组类发布包，`UI 资源名 -> 安装截图 -> 目录截图` 往往能快速闭环“功能是什么、路径在哪儿”。

## 进化动作

- [ ] 更新了路由矩阵
- [ ] 更新了 tool-index
- [ ] 更新了 bootstrap-manifest
- [ ] 更新了子 skill 文档
- [ ] 新增了 pitfalls 记录
- [x] 无需更新

## 环境信息

- OS: macOS Darwin 24.6.0
- 工具版本: OpenSSL(system), Python 3.14.5, dnfile 0.18.0
- 目标平台/版本: Windows 游戏模组 `AI开放修仙世界_9.1.4`
