from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def install_script() -> str:
    return (ROOT / "install.ps1").read_text(encoding="utf-8")


def test_powershell_state_manager_forwards_transaction_and_scope_arguments() -> None:
    script = install_script()

    assert "ValidateSet('begin', 'preflight-copy', 'create-backup', 'copy-target', 'commit', 'abort', 'record', 'prune-preview', 'prune', 'uninstall', 'rollback')" in script
    for flag in ("'--repo-only'", "'--repo'", "'--with-pilots'", "'--with-reverse'", "'--backup'", "'--force'"):
        assert flag in script
    assert "[string]$Target" in script
    assert "@('--target', $Target)" in script


def test_powershell_install_uses_begin_commit_abort_transaction() -> None:
    script = install_script()

    begin = script.index("Invoke-InstallState -Mode 'begin'")
    copy = script.index("        Install-GlobalAgents", begin)
    commit = script.index("Invoke-InstallState -Mode 'commit'")
    finally_block = script.index("finally {")
    abort = script.index("Invoke-InstallState -Mode 'abort'")

    assert begin < copy < commit
    assert finally_block < abort
    assert "if (-not $DryRun) {\n        Invoke-InstallState -Mode 'begin'" in script
    assert "if (-not $DryRun) {\n        Invoke-InstallState -Mode 'commit'" in script
    assert "if ($transactionStarted) {\n        try {\n            Invoke-InstallState -Mode 'abort'" in script
    assert "catch {\n    Write-Log 'Install failed; restoring uncommitted managed files.'\n    throw\n}" in script


def test_powershell_management_modes_exit_before_install_transaction() -> None:
    script = install_script()

    management_exit = script.index("    exit 0\n}\n\n$transactionStarted = $false")
    begin = script.index("Invoke-InstallState -Mode 'begin'")

    assert management_exit < begin
    for mode in ("prune-preview", "prune", "uninstall", "rollback"):
        assert f"Invoke-InstallState -Mode '{mode}'" in script


def test_powershell_copy_uses_manager_owned_atomic_copy() -> None:
    script = install_script()

    copy_start = script.index("function Copy-ToolkitFile")
    copy_end = script.index("function Copy-ToolkitTree", copy_start)
    copy_function = script[copy_start:copy_end]

    assert ".bak-$(Get-Date" not in copy_function
    assert "$backupPath" not in copy_function

    manager_copy = copy_function.index("Invoke-InstallState -Mode 'copy-target' -Target $Target")
    dry_run = copy_function.index("if ($DryRun)")
    copy_item = copy_function.index("Copy-Item -LiteralPath $Source -Destination $Target -Force")

    assert dry_run < copy_item < manager_copy
    assert "Invoke-InstallState -Mode 'create-backup' -Target $Target" not in copy_function
