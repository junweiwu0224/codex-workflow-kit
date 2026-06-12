---
name: release-readiness
description: Use when preparing, packaging, verifying, or handing off a reusable artifact, portable toolkit, local release archive, installable package, checksum bundle, migration bundle, or release evidence before delivery.
risk: medium
source_repo: personal-workflow-kit
source_type: curated-local
date_added: 2026-06-12
setup: none
write_surface: artifacts-and-docs
auth: none
network: none-by-default
status: pilot
---

# release-readiness

## 目标

在交付可复用 artifact、portable toolkit、release archive、安装包或迁移包前，确认“文件完整、版本一致、安装可跑、证据可复现、回滚路径清楚”。

这个 skill 是 artifact quality gate，不替代 Superpowers planning/TDD、`completion-review`、CI、正式 release manager 或生产发布审批。

## 触发场景

在以下情况触发：

- 构建或更新 `releases/*.tar.gz`、checksum、manifest、installer、portable toolkit、migration bundle。
- 用户要求“可复用到新机器”“打包”“发布包”“交付清单”“checksum”“安装验证”“release evidence”。
- 修改安装脚本、验证脚本、README/QUICKSTART、manifest、release archive 或 packaged skills/assets/references。
- 需要证明 output 包和本机 live install 一致。

不要在普通代码改动、单文件文档修正、未打包 artifact 的实现任务中触发。生产部署、外部发布、账号权限、包 registry 发布、真实用户流量或破坏性迁移仍必须先获得用户确认。

## 工作原则

- 先验证源码树，再构建 archive，再验证解包和安装。
- `VERSION`、manifest、archive name、checksum、README、QUICKSTART、evidence docs 和 benchmark docs 必须一致。
- 新增 skill、reference、script、asset、template 或 test 时，确认 archive listing 和 live install verifier 能覆盖它。
- release evidence 只写可复现事实：命令、输出、checksum、文件路径、通过/失败结果。
- 不把本地成功等同于生产可用；外部系统、真实账号、生产配置和发布渠道不在本 skill 默认权限内。

## Release Checklist

1. Source tree readiness
   - 运行 package verifier。
   - 检查 generated cache、临时文件、私有路径、secret pattern 和无关文件没有混入。
   - 如果不是 git repo，用 manifest、file list、targeted readback 替代 diff。

2. Version and docs alignment
   - `VERSION` 与 archive name 一致。
   - README / QUICKSTART / evidence docs 中的 skill count、checked file count、release version、checksum 命令一致。
   - 新增 skill 或脚本有触发边界、不要做、Output Shape 或等价输出契约。

3. Build artifact
   - 生成 manifest。
   - 构建 archive。
   - 生成 checksum。
   - 验证 archive top-level、manifest contents 和 checksum。

4. Install drill
   - 在临时 Codex/Agents home 做 dry-run。
   - 做真实临时安装。
   - 运行 live install verifier / doctor。
   - 如果包含 repo template，做 repo-only install drill 和 context pack verifier。

5. Evidence and rollback
   - 记录命令和关键输出。
   - 记录 archive path 和 checksum 验证。
   - 说明如何回滚：恢复 backup、重新安装上一版 archive、或删除临时安装目录。
   - 如果有未覆盖平台、权限、外部服务或手动步骤，明确列为 residual risk。

## Output Shape

最终交付或阶段汇报应包含：

- Artifact：release archive、checksum、manifest 或 install bundle 路径。
- Version：`VERSION`、archive name 和 docs 中的版本是否一致。
- Verification：package verifier、tests、build release、checksum、unpack drill、install drill、live install / doctor 的结果。
- Coverage：新增/变更的 skills、scripts、references、assets、docs 是否被 verifier 和 archive 覆盖。
- Rollback：备份、上一版 archive、临时目录或手动恢复路径。
- Gaps：未验证平台、外部发布、生产部署、账号权限或用户确认红线。

## 不要做

- 不要把 release-readiness 当成生产 deploy 批准。
- 不要只生成 archive 就声称可复用；必须验证 checksum、解包和安装路径。
- 不要遗漏新增 `references/`、assets、scripts、tests 或 agents metadata。
- 不要在 evidence 中写入 token、私钥、账号、生产数据或用户隐私。
- 不要因为时间紧跳过 `VERSION`、manifest、README/QUICKSTART、evidence docs 的一致性检查。
