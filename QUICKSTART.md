# Quickstart / 快速开始

## 中文

### 1. 安装到当前机器

```bash
git clone https://github.com/junweiwu0224/codex-workflow-kit.git
cd codex-workflow-kit
python3 scripts/verify_toolkit.py
./install.sh --dry-run
./install.sh --backup
python3 scripts/verify_live_install.py
```

默认安装位置：

```text
~/.codex/AGENTS.md
~/.agents/skills/
```

### 2. 验证

```bash
python3 scripts/verify_toolkit.py
python3 scripts/verify_live_install.py
python3 -m pytest tests/test_verify_toolkit.py tests/test_verify_live_install.py tests/test_audit_repo_adoption.py tests/test_render_usage_row.py -q
cd repo-template
python3 scripts/verify_context_pack.py
python3 -m pytest tests/test_verify_context_pack.py -q
```

期望关键输出：

```text
Workflow toolkit OK
Live install OK (12 files checked)
Context pack OK
```

### 3. 10 分钟流程：应用到新 repo

第 0-2 分钟：只读审计。

```bash
python3 scripts/audit_repo_adoption.py /path/to/repo
```

第 2-5 分钟：如果审计建议为 `repo-only-install`，安装 context pack。

```bash
./install.sh --repo-only --repo /path/to/repo --dry-run
./install.sh --repo-only --repo /path/to/repo --backup
```

第 5-8 分钟：验证目标 repo。

```bash
cd /path/to/repo
python3 scripts/verify_context_pack.py
```

第 8-10 分钟：追加 baseline usage 行。

```bash
/path/to/codex-workflow-kit/scripts/render_usage_row.py baseline >> docs/codex-usage.md
```

首次任务建议选择一个 M 级真实小任务：先读 repo context pack，再做最小实现，运行 targeted verification，最后只把可复用流程信号记录到 `docs/codex-usage.md`。

## English

### 1. Install on this machine

```bash
git clone https://github.com/junweiwu0224/codex-workflow-kit.git
cd codex-workflow-kit
python3 scripts/verify_toolkit.py
./install.sh --dry-run
./install.sh --backup
python3 scripts/verify_live_install.py
```

Default install locations:

```text
~/.codex/AGENTS.md
~/.agents/skills/
```

### 2. Verify

```bash
python3 scripts/verify_toolkit.py
python3 scripts/verify_live_install.py
python3 -m pytest tests/test_verify_toolkit.py tests/test_verify_live_install.py tests/test_audit_repo_adoption.py tests/test_render_usage_row.py -q
cd repo-template
python3 scripts/verify_context_pack.py
python3 -m pytest tests/test_verify_context_pack.py -q
```

Expected key output:

```text
Workflow toolkit OK
Live install OK (12 files checked)
Context pack OK
```

### 3. Apply to a new repo in 10 minutes

Minute 0-2: run a read-only audit.

```bash
python3 scripts/audit_repo_adoption.py /path/to/repo
```

Minute 2-5: if the recommendation is `repo-only-install`, install the context pack.

```bash
./install.sh --repo-only --repo /path/to/repo --dry-run
./install.sh --repo-only --repo /path/to/repo --backup
```

Minute 5-8: verify the target repo.

```bash
cd /path/to/repo
python3 scripts/verify_context_pack.py
```

Minute 8-10: append a baseline usage row.

```bash
/path/to/codex-workflow-kit/scripts/render_usage_row.py baseline >> docs/codex-usage.md
```

For the first real task, choose a small M-level change: read the repo context pack, implement the smallest safe change, run targeted verification, and record only reusable workflow signals in `docs/codex-usage.md`.
