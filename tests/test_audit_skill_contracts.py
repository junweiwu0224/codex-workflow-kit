import json
from pathlib import Path

from scripts.audit_skill_contracts import build_report, main


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _skill(root: Path, name: str, body: str = "") -> None:
    _write(
        root / f"skills/{name}/SKILL.md",
        (
            "---\n"
            f"name: {name}\n"
            "description: Use when testing a skill contract.\n"
            "---\n"
            f"\n# {name}\n\n"
            "## 触发场景\n\nUse when the fixture applies.\n\n"
            "## 不要做\n\n- 不要越界。\n\n"
            "## 验证\n\nRun the local check.\n\n"
            "## Output Shape\n\n- Result\n"
            f"{body}\n"
        ),
    )


def _catalog(root: Path, name: str) -> None:
    _write(
        root / "catalog/components.yaml",
        (
            "schema_version: '4.2'\n"
            "repository:\n"
            "  name: fixture\n"
            "  commit: e76318c0e747ca9e3b6e5399499ab20a374056fc\n"
            "skills:\n"
            f"  - name: {name}\n"
            "    status: stable\n"
            "    metadata:\n"
            "      risk: low\n"
            "      source_repo: fixture\n"
            "      source_type: curated-local\n"
            "      date_added: '2026-07-12'\n"
            "      setup: none\n"
            "      write_surface: none\n"
            "      auth: none\n"
            "      network_policy: none\n"
        ),
    )


def test_build_report_accepts_current_skill_package():
    root = Path(__file__).resolve().parents[1]

    report = build_report(root)

    assert report["ok"] is True
    assert report["totals"]["skills"] == 14
    assert report["totals"]["ok"] == 14
    assert report["totals"]["with_output_shape"] == 14
    assert report["totals"]["with_boundaries"] == 14
    assert report["totals"]["with_validation"] == 14


def test_build_report_flags_missing_contract_parts(tmp_path):
    root = tmp_path / "kit"
    _write(
        root / "skills/thin-skill/SKILL.md",
        "---\nname: thin-skill\ndescription: Use when testing.\n---\n\n# thin-skill\n",
    )

    report = build_report(root)
    skill = report["skills"][0]

    assert report["ok"] is False
    assert skill["ok"] is False
    assert "risk" in skill["missing_catalog_metadata"]
    assert skill["has_output_shape"] is False
    assert skill["has_boundaries"] is False


def test_main_supports_json_markdown_and_text(tmp_path, capsys):
    root = tmp_path / "kit"
    _skill(root, "example", body="\nreferences/spec-template.md\nSuperpowers\n")
    _catalog(root, "example")
    _write(root / "skills/example/references/spec-template.md", "# Template\n")

    json_exit = main(["--root", str(root), "--json"])
    json_output = capsys.readouterr().out
    report = json.loads(json_output)

    markdown_exit = main(["--root", str(root), "--markdown"])
    markdown_output = capsys.readouterr().out

    text_exit = main(["--root", str(root)])
    text_output = capsys.readouterr().out

    assert json_exit == 0
    assert report["ok"] is True
    assert markdown_exit == 0
    assert "| example | yes | yes | yes | yes | yes | yes | yes | stable |" in markdown_output
    assert text_exit == 0
    assert "Skill contract audit OK" in text_output
