# 2026-06-14 reverse-skill full verification

## Summary

- 对本机 `reverse-skill` 做了一轮补跑，把上一轮没通的主链继续补齐
- 已新增跑通：APK 重签名链、Frida 本机注入、anything-analyzer MCP、jshook 真页面链、nuclei 模板扫描、sqlmap 注入确认
- 当前仍未跑通的只剩 IDA MCP，阻塞点是本机缺少可工作的 IDA / idalib 前置条件

## Evidence

- 主报告：`/Users/junwei/Documents/逆向工程/.verification/reverse-skill/out/2026-06-14_reverse-skill-full-verification-report.md`
- APK 重签名：`/Users/junwei/Documents/逆向工程/.verification/reverse-skill/out/apk-rebuild-sign.txt`
- Frida：`/Users/junwei/Documents/逆向工程/.verification/reverse-skill/out/frida-local-hook.txt`
- Anything Analyzer：`/Users/junwei/Documents/逆向工程/.verification/reverse-skill/out/anything-local-capture.txt`
- gpt-5.4 + anything-analyzer：`/Users/junwei/Documents/逆向工程/.verification/reverse-skill/out/gpt54-anything-analyzer-events.jsonl`
- jshook：`/Users/junwei/Documents/逆向工程/.verification/reverse-skill/out/jshook-local.txt`
- gpt-5.4 + jshook：`/Users/junwei/Documents/逆向工程/.verification/reverse-skill/out/gpt54-jshook-events.jsonl`
- nuclei：`/Users/junwei/Documents/逆向工程/.verification/reverse-skill/out/nuclei-local.jsonl`
- sqlmap：`/Users/junwei/Documents/逆向工程/.verification/reverse-skill/out/sqlmap-local.txt`

## Reusable takeaways

- `anything-analyzer` 的 MCP 配置已正确时，最大概率问题是服务没起，不是注册没生效；前台 `pnpm dev` 很快能看出真状态
- `gpt-5.4` 在 Codex 里已经能真实调 `anything-analyzer` 和 `jshook`，所以“反编译/逆向被拦”不是简单等于模型面禁用，更多是具体 MCP/service/tool 链没起全
- Android `zipalign/apksigner` 不必强塞进 PATH，只要脚本会扫用户目录 build-tools 即可，扰动最小
- `refresh-tool-index.sh` 里 probe path 如果带 `*`，必须自己展开 glob，不然会出现“明明能用但索引还是 no”
- `frida-run.sh` 默认走远端 `-H 127.0.0.1:27042` 会把本机 smoke test 搞假失败；本机验证更适合 `frida-ps -a` + attach 本地 PID
- 当前 IDA MCP 的主要 blocker 是宿主前置条件，不是 reverse-skill 路由或 Codex Desktop 配置本身
