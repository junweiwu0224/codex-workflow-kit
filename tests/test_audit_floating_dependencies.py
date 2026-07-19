import json
from pathlib import Path

from scripts.audit_floating_dependencies import (
    TARGET_FILES,
    build_report,
    main,
    refresh_baseline,
    scan_floating_dependencies,
    validate_reverse_lock,
)


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _fixture_root(tmp_path: Path) -> Path:
    root = tmp_path / "kit"
    for relative in TARGET_FILES:
        _write(root / relative, "#!/usr/bin/env bash\n")
    _write(
        root / TARGET_FILES[0],
        "#!/usr/bin/env bash\n"
        "npm install -g pnpm@9.15.0\n"
        "git clone --branch v1.2.3 https://github.com/example/tool.git \"$HOME/tool\"\n",
    )
    return root


def test_current_baseline_passes(tmp_path):
    root = _fixture_root(tmp_path)

    refresh_baseline(root)
    report = build_report(root)

    assert report["ok"] is True
    assert report["errors"] == []
    assert report["drift"] == {"added": [], "changed": [], "removed": []}
    payload = json.loads((root / "catalog/floating-dependencies-baseline.json").read_text(encoding="utf-8"))
    assert payload["kind"] == "zero-floating-reference-baseline"
    assert "zero-finding baseline" in payload["description"]
    assert "reverse-dependencies.lock.yaml" in payload["description"]


def test_repository_has_no_floating_references_and_valid_reverse_lock():
    root = Path(__file__).resolve().parents[1]

    report = build_report(root)
    lock_report = validate_reverse_lock(root)

    assert report["ok"] is True
    assert report["findings"] == []
    assert lock_report["ok"] is True
    assert lock_report["dependencies"] >= 17
    assert "pnpm-npm.integrity" in lock_report["enforcement_summary"]["metadata-only"]
    assert "frida-tools-pypi.sha256" in lock_report["enforcement_summary"]["metadata-only"]
    assert "anything-analyzer-git.commit" in lock_report["enforcement_summary"]["enforced"]


def test_packaged_checkout_fails_closed_without_reverse_lock(tmp_path):
    root = _fixture_root(tmp_path)
    _write(root / "catalog/components.yaml", "schema_version: '4.2'\n")
    refresh_baseline(root)

    report = build_report(root)

    assert report["ok"] is False
    assert "reverse-lock-missing" in report["errors"]


def test_new_floating_reference_fails(tmp_path, capsys):
    root = _fixture_root(tmp_path)
    refresh_baseline(root)
    install_script = root / "install.sh"
    install_script.write_text(
        install_script.read_text(encoding="utf-8") + "npx playwright install chromium\n",
        encoding="utf-8",
    )

    exit_code = main(["--root", str(root), "--json"])
    report = json.loads(capsys.readouterr().out)

    assert exit_code == 1
    assert report["ok"] is False
    assert any(entry["kind"] == "npx-unpinned" for entry in report["drift"]["added"])


def test_nonzero_baseline_can_never_be_grandfathered(tmp_path):
    root = _fixture_root(tmp_path)
    refresh_baseline(root)
    baseline = root / "catalog/floating-dependencies-baseline.json"
    payload = json.loads(baseline.read_text(encoding="utf-8"))
    payload["findings"] = [{
        "path": "install.sh",
        "kind": "npm-unpinned",
        "reference": "example",
        "signature": "npm install <floating-ref>",
        "count": 1,
        "lines": [1],
    }]
    baseline.write_text(json.dumps(payload), encoding="utf-8")

    report = build_report(root)

    assert report["ok"] is False
    assert "baseline-must-remain-zero" in report["errors"]


def test_refresh_refuses_to_normalize_floating_references(tmp_path):
    root = _fixture_root(tmp_path)
    refresh_baseline(root)
    target = root / TARGET_FILES[0]
    target.write_text("#!/usr/bin/env bash\nnpm install -g unpinned\n", encoding="utf-8")

    try:
        refresh_baseline(root)
    except ValueError as exc:
        assert "cannot refresh a zero-finding baseline" in str(exc)
    else:
        raise AssertionError("floating references must never be normalized into the baseline")


def test_scanner_recognizes_required_floating_reference_families(tmp_path):
    root = _fixture_root(tmp_path)
    _write(
        root / "install.ps1",
        "go install example.invalid/tool@latest\n"
        "npm install -g pnpm\n"
        "git clone https://github.com/acme/clone.git tool\n"
        "docker pull example.invalid/tool:latest\n"
        "$url = 'https://api.github.com/repos/acme/tool/releases/latest'\n"
        "pipx install git+https://github.com/acme/tool.git\n"
        "pip install requests\n"
        "pip3 install flask\n"
        "python -m pip install urllib3\n"
        "python3 -m pip install rich\n"
        "python3 -m pip install django==5.*\n"
        '"$venv/bin/python" -m pip install pyghidra\n',
    )

    kinds = {finding.kind for finding in scan_floating_dependencies(root)}

    assert {
        "container-latest",
        "git-clone-unpinned",
        "git-plus-unpinned",
        "go-install-latest",
        "npm-unpinned",
        "pip-unpinned",
        "pipx-unpinned",
        "release-latest",
    }.issubset(kinds)


def test_scanner_accepts_explicit_git_tag_and_package_versions(tmp_path):
    root = _fixture_root(tmp_path)
    _write(
        root / "install.sh",
        "git clone --branch v1.2.3 https://github.com/acme/tool.git tool\n"
        "npm install -g pnpm@9.15.0\n"
        "npx playwright@1.52.0 install chromium\n"
        "pipx install sqlmap==1.9.0\n"
        "pip install requests==2.32.4\n"
        "python3 -m pip install git+https://github.com/acme/tool.git@aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\n"
        '"$venv/bin/python" -m pip install --no-index --find-links "$wheel_dir" "pyghidra==$version"\n',
    )

    install_findings = [
        finding for finding in scan_floating_dependencies(root) if finding.path == "install.sh"
    ]

    assert install_findings == []


def test_scanner_reports_each_direct_unpinned_pip_form(tmp_path):
    root = _fixture_root(tmp_path)
    _write(
        root / "install.sh",
        "pip install requests\n"
        "pip3 install flask\n"
        "python -m pip install urllib3\n"
        "python3 -m pip install rich\n"
        "python3 -m pip install django==5.*\n"
        '"$venv/bin/python" -m pip install pyghidra\n',
    )

    findings = [
        finding for finding in scan_floating_dependencies(root)
        if finding.path == "install.sh" and finding.kind == "pip-unpinned"
    ]

    assert {finding.reference for finding in findings} == {
        "requests", "flask", "urllib3", "rich", "django==5.*", "pyghidra"
    }


def test_kali_locked_variable_helper_is_not_a_false_positive():
    root = Path(__file__).resolve().parents[1]
    findings = [
        finding for finding in scan_floating_dependencies(root)
        if finding.path == "reverse-skill/kali/scripts/bootstrap-reverse.sh"
        and finding.kind == "pip-unpinned"
    ]
    script = (root / "reverse-skill/kali/scripts/bootstrap-reverse.sh").read_text(encoding="utf-8")

    assert findings == []
    assert 'install_pip_package "frida-tools==$(lock_value frida-tools-pypi version)"' in script
    assert 'git+$(lock_value ida-pro-mcp-git repository)@$(lock_value ida-pro-mcp-git commit)' in script


def test_refresh_rejects_baseline_outside_repository(tmp_path):
    root = _fixture_root(tmp_path)

    exit_code = main(
        [
            "--root",
            str(root),
            "--baseline",
            str(tmp_path / "outside.json"),
            "--refresh-baseline",
            "--json",
        ]
    )

    assert exit_code == 1
    assert not (tmp_path / "outside.json").exists()
