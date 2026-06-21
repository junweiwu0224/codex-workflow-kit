from pathlib import Path
import json
import subprocess

from scripts.validate_v32_workflow_cases import (
    BROWSER,
    SECURITY,
    SUBAGENT_PROTOCOL,
    SUPERPOWERS_DISPATCH,
    build_report,
    evaluate_case,
    main,
    route_prompt,
    CASES,
)


def test_build_report_validates_current_v32_cases():
    root = Path(__file__).resolve().parents[1]

    report = build_report(root)

    assert report["ok"] is True
    assert report["totals"]["cases"] >= 10
    assert report["totals"]["passed"] == report["totals"]["cases"]
    assert report["totals"]["conflicts"] == 0
    assert report["totals"]["delta"] > 0


def test_csv_upload_tool_does_not_trigger_safety_stop_or_browser_workflow():
    route = route_prompt(
        "Build a browser-based CSV cleaning tool with upload, column profiling, filter chips, preview table, undo, and export."
    )

    assert route.stop_required is False
    assert SECURITY not in route.supporting
    assert BROWSER not in route.skills


def test_cloud_gpu_voice_cloning_video_does_not_trigger_browser_capture_workflow():
    route = route_prompt("Use cloud GPU and voice cloning to make the product video.")

    assert route.primary == "junwei-product-demo-video"
    assert BROWSER not in route.skills
    assert route.stop_required is True
    assert {"cloud GPU", "voice cloning", "paid/external service"}.issubset(set(route.blocked_actions))


def test_loaded_agents_subagent_authorization_does_not_require_repeat_permission():
    route = route_prompt(
        "Run an L-sized repo audit with loaded AGENTS long-term subagent authorization "
        "and two independent read-only explorer questions; do not ask again for current-turn permission."
    )

    assert route.primary == SUBAGENT_PROTOCOL
    assert SUPERPOWERS_DISPATCH in route.supporting
    assert route.stop_required is False


def test_every_case_has_positive_uplift_and_no_conflicts():
    root = Path(__file__).resolve().parents[1]

    for case in CASES:
        result = evaluate_case(root, case)
        assert result["ok"] is True, result
        assert result["delta"] > 0, result
        assert result["conflicts"] == [], result


def test_main_writes_json_and_markdown(tmp_path, capsys):
    root = Path(__file__).resolve().parents[1]
    json_out = tmp_path / "validation.json"
    markdown_out = tmp_path / "validation.md"

    exit_code = main(
        [
            "--root",
            str(root),
            "--json-out",
            str(json_out),
            "--markdown-out",
            str(markdown_out),
        ]
    )
    output = capsys.readouterr().out
    report = json.loads(json_out.read_text(encoding="utf-8"))
    markdown = markdown_out.read_text(encoding="utf-8")

    assert exit_code == 0
    assert report["ok"] is True
    assert "V3.2 Functional Validation" in markdown
    assert "Positive Effect" in markdown
    assert "V3.2 functional validation JSON" in output


def test_cli_json_output():
    root = Path(__file__).resolve().parents[1]

    result = subprocess.run(
        ["python3", "scripts/validate_v32_workflow_cases.py", "--json"],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    report = json.loads(result.stdout)

    assert result.returncode == 0
    assert report["ok"] is True
