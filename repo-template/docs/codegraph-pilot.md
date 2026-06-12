# Code Graph Pilot

本文件记录当前仓库是否、何时、如何试点 code graph。code graph 只作 orientation，不是真相源。

## 默认状态

- 默认使用 `rg`、`rg --files`、语言工具、测试、repo context pack 和源码回读。
- 不默认安装 code graph 工具。
- 不默认写 `.cartographer`、`.graph`、索引目录或 MCP 配置。
- 不默认启用 code graph MCP、后台索引或云服务。

## 适用场景

可以考虑 pilot：

- L/XL 任务跨多个模块、runtime、provider、adapter、schema 或 generated code。
- 删除旧模块、迁移架构、影响分析、调用链复杂。
- `rg + context pack` 多次不足以稳定找出影响范围。
- subagents 需要更清楚的只读分组和验证矩阵。

不要用于：

- XS/S 任务。
- 单文件或局部实现。
- 需要默认索引 secrets、`.env`、生产数据、私有用户数据或大生成产物的场景。
- 工具需要默认网络、云凭证、后台 daemon 或 external write。

## Pilot 准入

试点前记录：

- 目标任务：
- baseline 命令：
- 允许索引目录：
- 必须排除目录：
- 输出目录：
- 是否联网：
- 是否写本地产物：
- 如何删除索引：
- 如何回到 baseline：

## Baseline

先跑本地基线：

```bash
rg --files | sed -n '1,160p'
rg -n "<关键术语|函数|路由|schema|provider|adapter>" .
python3 scripts/verify_context_pack.py
```

## 使用规则

- graph 输出必须回读源码、测试或文档确认。
- graph 输出不能覆盖 repo `AGENTS.md`、`docs/architecture.md`、源码和测试。
- 任何 stale note、semantic note 或 generated map 都必须可删除。
- 有效事实应沉淀回 repo docs，而不是停留在工具缓存。

## 成功标准

至少满足两项才继续试点：

- 比 baseline 更快定位跨模块调用链。
- 发现 baseline 漏掉的关键文件、接口、schema、provider、adapter 或测试。
- 让 subagents 分工更清晰，减少重复探索。
- 让验证范围更准确，减少漏测或误测。

## 退出条件

- 索引范围不清或包含敏感文件。
- 工具输出无法被源码验证。
- 维护成本、安装成本、授权成本或延迟超过收益。
- 让普通任务变慢。
- 需要默认后台服务、默认网络访问或默认 external write。

## Usage 记录

```bash
python3 scripts/render_usage_row.py pilot --pilot codegraph
```

