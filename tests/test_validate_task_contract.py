import json
from pathlib import Path

from scripts.validate_task_contract import main, validate_contract


def _base(**overrides):
    contract = {
        "lane": "fast",
        "state": "scoped",
        "transition": "scoped_to_planned",
        "transition_driver": "native",
        "write_scope": "workspace",
        "external_effects": [],
        "approvals": [],
        "required_artifacts": [],
        "acceptance_checks": ["run tests"],
        "verification_mode": "deterministic",
        "handoff": "none",
        "audit_record": False,
        "reversibility": "reversible",
    }
    contract.update(overrides)
    return contract


def test_fast_contract_is_valid():
    assert validate_contract(_base()) == []


def test_transition_source_must_match_state():
    errors = validate_contract(_base(state="planned"))
    assert "transition source must match state" in errors


def test_governed_external_work_requires_approval_record_but_not_a_grant():
    contract = _base(
        lane="governed",
        state="verified",
        transition="verified_to_released",
        transition_driver="release-readiness",
        write_scope="external",
        external_effects=["publish release"],
        audit_record=True,
        verification_mode="mixed",
        handoff="release",
        network_policy="allowlist",
        credential_refs=[],
        external_targets=["github-release"],
        package_install=False,
        production_access=False,
        policy_enforcement=[],
    )
    errors = validate_contract(contract)
    assert "governed external/irreversible work requires an approval record" in errors

    contract["approvals"] = [{"actor": "user", "decision": "pending"}]
    assert validate_contract(contract) == []


def test_cli_reports_json(tmp_path: Path, capsys):
    path = tmp_path / "contract.json"
    path.write_text(json.dumps(_base()), encoding="utf-8")
    assert main([str(path), "--json"]) == 0
    output = json.loads(capsys.readouterr().out)
    assert output["ok"] is True


def test_fast_lane_rejects_install_credentials_and_unrestricted_network():
    errors = validate_contract(
        _base(
            package_install=True,
            credential_refs=["release-token"],
            network_policy="unrestricted",
        )
    )
    assert "fast lane cannot declare external or irreversible effects" in errors


def test_optional_policy_fields_are_type_checked():
    errors = validate_contract(_base(external_targets="production", package_install="yes"))
    assert "external_targets must be a list of strings" in errors
    assert "package_install must be boolean" in errors


def test_project_only_install_is_standard_and_requires_workspace_scope():
    contract = _base(
        lane="standard",
        write_scope="workspace",
        package_install="project-only",
        verification_mode="mixed",
    )
    assert validate_contract(contract) == []
    errors = validate_contract({**contract, "write_scope": "none"})
    assert "project-only package installation requires workspace write_scope" in errors


def test_nested_network_policy_and_scoped_approval_shape_are_supported():
    contract = _base(
        lane="governed",
        write_scope="external",
        external_effects=["publish"],
        approvals=[
            {
                "actor": "user",
                "decision": "granted",
                "scope": ["external_write", "release.example"],
            }
        ],
        audit_record=True,
        verification_mode="mixed",
        network={"mode": "allowlist", "allowlist": ["release.example"]},
        credentials=[],
        external_targets=["release.example"],
        package_install=False,
        production_access=False,
        policy_enforcement=[],
    )
    assert validate_contract(contract) == []


def test_malformed_multiple_driver_and_unavailable_enforcement_do_not_crash():
    errors = validate_contract(
        _base(
            transition_driver=["native", "superpowers"],
            policy_enforcement=[{"field": "external_write", "status": "unknown"}],
        )
    )
    assert any("transition_driver" in error for error in errors)
    assert "policy_enforcement must contain field and a supported status" in errors
