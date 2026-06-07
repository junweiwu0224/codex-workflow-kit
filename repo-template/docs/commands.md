# Commands

本文件记录当前项目常用命令。命令变化时请同步更新。

## 环境要求

- Node/Python/Go/Rust/Java/其他版本：
- 包管理器：
- 必需环境变量：
- 外部服务依赖：

## 安装

```bash
# 示例
```

## 本地开发

```bash
# 示例
```

## 测试

### 全量测试

```bash
# 示例
```

### 针对性测试

```bash
# 示例：按文件、目录、测试名运行
```

### Watch 模式

```bash
# 示例
```

## 质量检查

### Context pack / 文档门禁

```bash
python3 scripts/verify_context_pack.py
```

模板自带 `scripts/verify_context_pack.py`。落地到具体仓库后，如果项目使用 `.venv/bin/python`、`python3` 或其他解释器，请先探测真实可用入口并同步更新本命令、`docs/testing.md` 和 `docs/quality-gates.md`。

### 快速无副作用门禁

```bash
# 示例：只读/无网络/不写业务数据的快速检查
```

优先把这类命令放入 hooks 或默认 Codex 验证。

### 报告型门禁

```bash
# 示例：生成 ignored 报告，例如 test-results/、coverage/、playwright-report/
```

报告型命令可以很有价值，但要明确输出目录是否已被 `.gitignore` 忽略。

### 应用生命周期门禁

```bash
# 示例：通过 TestClient、dev server、preview server 或 app startup 做健康检查
```

这类命令可能启动调度器、连接本地数据库、写缓存、生成报告或短暂占用端口。不要默认放入无副作用 hooks；执行前先确认副作用边界。

详见 `docs/quality-gates.md`。

### 类型检查

```bash
# 示例
```

### Lint

```bash
# 示例
```

### 格式化

```bash
# 示例
```

## 构建

```bash
# 示例
```

## 数据库 / 迁移

```bash
# 示例
```

## 前端 / 浏览器验证

```bash
# 示例：启动 dev server、运行 e2e、打开 storybook
```

如命令会写 `test-results/`、截图、trace、coverage、缓存或本地数据库，请在本文件和 `docs/quality-gates.md` 明确说明。

## 常见失败

- 失败现象：
  - 可能原因：
  - 处理方式：

## Codex 使用建议

- 小改动优先运行：
- 涉及共享逻辑时运行：
- 发布/CI 前运行：
- 需要凭证或外部服务的命令：
