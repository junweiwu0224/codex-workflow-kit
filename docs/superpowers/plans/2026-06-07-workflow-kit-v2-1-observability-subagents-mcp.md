# Workflow Kit V2.1 Observability, Subagents, and MCP Pilot Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a conservative V2.1 layer that improves Codex usage visibility, subagent dispatch quality, and MCP/code graph experimentation without changing V2 defaults.

**Architecture:** Keep the portable kit document-first and non-destructive. Add optional repo-template guidance, a print-only usage row helper extension, verifier checks, tests, and release metadata; do not install external tools, enable hooks, or make MCP/memory/subagents unconditional. This is a no default automation layer.

**Tech Stack:** Bash installer, Python verifier/tests, Markdown repo templates, release tarball manifest/checksum.

---

### Task 1: Lock V2.1 Requirements With Failing Tests

**Files:**
- Modify: `tests/test_verify_toolkit.py`
- Modify: `tests/test_render_usage_row.py`
- Modify: `scripts/verify_toolkit.py`
- Modify: `scripts/render_usage_row.py`

- [ ] **Step 1: Add failing verifier tests**

Add tests that fail until V2.1 docs and verifier terms exist:

```python
def test_check_toolkit_requires_v2_1_observability_docs(tmp_path):
    shadow = _clean_package_copy(tmp_path)
    (shadow / "repo-template/docs/observability.md").unlink(missing_ok=True)

    issues = check_toolkit(shadow)

    assert any(issue.code == "missing-required-file" and issue.path == "repo-template/docs/observability.md" for issue in issues)


def test_check_toolkit_requires_v2_1_mcp_pilot_docs(tmp_path):
    shadow = _clean_package_copy(tmp_path)
    (shadow / "repo-template/docs/mcp-pilot.md").unlink(missing_ok=True)

    issues = check_toolkit(shadow)

    assert any(issue.code == "missing-required-file" and issue.path == "repo-template/docs/mcp-pilot.md" for issue in issues)
```

- [ ] **Step 2: Add failing usage row tests**

Add tests for a new `pilot` usage row and the `render_usage_row pilot` command path:

```python
def test_build_pilot_row_uses_defaults():
    row = build_pilot_row(date="2026-06-07", pilot="subagents")

    assert "| 2026-06-07 | subagents pilot | L | subagents, pilot evidence |" in row
    assert "Keep documented; promote only after repeated positive signals" in row
```

- [ ] **Step 3: Run tests and verify RED**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 <trial-repo-ai-quant-trading>/.venv/bin/python -m pytest -p no:cacheprovider tests/test_verify_toolkit.py tests/test_render_usage_row.py -q
```

Expected: failure for missing docs/terms or missing `build_pilot_row`.

### Task 2: Add V2.1 Repo Template Guidance

**Files:**
- Create: `repo-template/docs/observability.md`
- Create: `repo-template/docs/mcp-pilot.md`
- Modify: `repo-template/docs/subagents.md`
- Modify: `repo-template/AGENTS.md`
- Modify: `repo-template/scripts/verify_context_pack.py`
- Modify: `repo-template/tests/test_verify_context_pack.py`

- [ ] **Step 1: Create observability guide**

Document optional local-only tools, privacy boundaries, verification commands, and when to record signals in `docs/codex-usage.md`.

- [ ] **Step 2: Create MCP/code graph pilot guide**

Document pilot entry criteria, baseline comparison against `rg + context pack`, privacy exclusions, success/failure criteria, and rollback.

- [ ] **Step 3: Add subagent prompt cards**

Add five copy-ready cards: read-only code mapper, test/debug investigator, frontend QA reviewer, docs/content-contract reviewer, and architecture/migration reviewer.

- [ ] **Step 4: Extend context pack verifier**

Require `docs/observability.md` and `docs/mcp-pilot.md`; add tests that fail when either is missing.

### Task 3: Extend Usage Row Helper

**Files:**
- Modify: `scripts/render_usage_row.py`
- Modify: `tests/test_render_usage_row.py`

- [ ] **Step 1: Implement `build_pilot_row`**

Add a Markdown row builder that prints evidence rows for optional pilots without writing files.

- [ ] **Step 2: Add CLI subcommand**

Add:

```bash
python3 scripts/render_usage_row.py pilot --pilot subagents
python3 scripts/render_usage_row.py pilot --pilot observability
python3 scripts/render_usage_row.py pilot --pilot mcp-code-graph
```

- [ ] **Step 3: Run usage row tests**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 <trial-repo-ai-quant-trading>/.venv/bin/python -m pytest -p no:cacheprovider tests/test_render_usage_row.py -q
```

Expected: all tests pass.

### Task 4: Wire V2.1 Into Toolkit Verification and Docs

**Files:**
- Modify: `scripts/verify_toolkit.py`
- Modify: `tests/test_verify_toolkit.py`
- Modify: `README.md`
- Modify: `QUICKSTART.md`
- Modify: `WORKFLOW-REVIEW.md`
- Modify: `docs/V2-ADOPTION-EVIDENCE.md`
- Modify: `VERSION`

- [ ] **Step 1: Require V2.1 files and terms**

Update toolkit verifier to require observability, MCP pilot, prompt cards, pilot usage rows, V2.1 review/evidence terms, and current release evidence.

- [ ] **Step 2: Update portable docs**

Document V2.1 as optional experience/observability additions, not new defaults.

- [ ] **Step 3: Bump version**

Set `VERSION` to `2026.06.07.11`.

### Task 5: Build and Verify Release

**Files:**
- Modify: `MANIFEST.sha256`
- Create: `releases/codex-workflow-kit-2026.06.07.11.tar.gz`
- Create: `releases/codex-workflow-kit-2026.06.07.11.tar.gz.sha256`

- [ ] **Step 1: Run package self-checks**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 scripts/verify_toolkit.py
cd repo-template && PYTHONDONTWRITEBYTECODE=1 python3 scripts/verify_context_pack.py
```

- [ ] **Step 2: Run test suites**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 <trial-repo-ai-quant-trading>/.venv/bin/python -m pytest -p no:cacheprovider tests/test_verify_toolkit.py tests/test_audit_repo_adoption.py tests/test_render_usage_row.py -q
cd repo-template
PYTHONDONTWRITEBYTECODE=1 <trial-repo-ai-quant-trading>/.venv/bin/python -m pytest -p no:cacheprovider tests/test_verify_context_pack.py -q
```

- [ ] **Step 3: Build release and verify checksum**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 scripts/build_release.py
cd releases
env LC_ALL=C LANG=C LC_CTYPE=C shasum -a 256 -c codex-workflow-kit-2026.06.07.11.tar.gz.sha256
```

Expected: toolkit OK, context pack OK, tests pass, checksum OK.
