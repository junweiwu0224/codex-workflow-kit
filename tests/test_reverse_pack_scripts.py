import json
from pathlib import Path


def test_decode_sh_uses_portable_manifest_package_extraction() -> None:
    script = Path("reverse-skill/skills/apk-reverse/scripts/decode.sh").read_text(encoding="utf-8")

    assert "grep -oP" not in script
    assert "sed -n 's/.*package=\"\\([^\"]*\\)\".*/\\1/p'" in script


def test_bootstrap_sh_registers_mcp_for_codex_and_claude() -> None:
    script = Path("reverse-skill/skills/scripts/bootstrap-reverse.sh").read_text(encoding="utf-8")

    assert 'MCP_HOST_TARGET="${MCP_HOST_TARGET:-Both}"' in script
    assert 'CODEX_CONFIG_PATH="${CODEX_CONFIG_PATH:-$HOME/.codex/config.toml}"' in script
    assert 'write_codex_mcp_server()' in script
    assert 'write_claude_mcp_server()' in script
    assert 'for target in $(mcp_host_targets); do' in script


def test_bootstrap_sh_registers_headless_ghidra_bridge() -> None:
    script = Path("reverse-skill/skills/scripts/bootstrap-reverse.sh").read_text(encoding="utf-8")

    assert 'local ghidra_venv="$REPO_ROOT/ghidra-mcp/headless/.venv"' in script
    assert 'pyghidra_version="$(lock_value ghidra-release pyghidra_version || true)"' in script
    assert 'pyghidra_wheel_relative="$(lock_value ghidra-release pyghidra_wheel || true)"' in script
    assert 'pip install --no-index --find-links "$pyghidra_wheel_dir" "pyghidra==$pyghidra_version"' in script
    assert "pip install --upgrade pyghidra" not in script
    assert "pip install --upgrade pip" not in script
    assert 'write_mcp_server "ghidra"' in script
    assert 'GHIDRA_PROJECTS_DIR' in script


def test_bootstrap_sh_has_no_unlocked_pipx_or_binwalk_fallback() -> None:
    script = Path("reverse-skill/skills/scripts/bootstrap-reverse.sh").read_text(encoding="utf-8")

    assert "python3 -m pip install --user pipx" not in script
    assert "python3 -m pip install --user binwalk" not in script


def test_bootstrap_sh_blocks_unpinned_platform_packages_by_default() -> None:
    generic = Path("reverse-skill/skills/scripts/bootstrap-reverse.sh").read_text(encoding="utf-8")
    kali = Path("reverse-skill/kali/scripts/bootstrap-reverse.sh").read_text(encoding="utf-8")

    for script in (generic, kali):
        assert "REVERSE_ALLOW_UNPINNED_PLATFORM_PACKAGES" in script
        assert "unpinned apt" in script
    assert "install_brew ghidra || brew install --cask ghidra" not in generic


def test_bootstrap_sh_installs_portable_apktool_wrapper() -> None:
    script = Path("reverse-skill/skills/scripts/bootstrap-reverse.sh").read_text(encoding="utf-8")

    assert 'if [[ "$apktool_path" == "$TOOLS_ROOT/apktool/apktool" ]] && [[ -f "$TOOLS_ROOT/apktool/apktool.jar" ]] && apktool --version >/dev/null 2>&1; then' in script
    assert 'resolve_github_asset_url apktool-release' in script
    assert 'catalog/reverse-dependencies.lock.yaml' in script
    assert 'download_file_checked "$url" "$jar" "apktool jar"' in script
    assert 'apktool wrapper failed smoke check after install' in script
    assert 'exec java -jar "$SCRIPT_DIR/apktool.jar" "$@"' in script


def test_decode_sh_prefers_tool_index_paths() -> None:
    script = Path("reverse-skill/skills/apk-reverse/scripts/decode.sh").read_text(encoding="utf-8")

    assert 'TOOL_INDEX_JSON=' in script
    assert 'tool_path_from_index()' in script
    assert 'prefer_tool_from_index "apktool"' in script


def test_apk_shell_helpers_do_not_bootstrap_missing_tools_by_default() -> None:
    for relative in (
        "reverse-skill/skills/apk-reverse/scripts/decode.sh",
        "reverse-skill/skills/apk-reverse/scripts/rebuild-sign-install.sh",
    ):
        script = Path(relative).read_text(encoding="utf-8")
        assert 'REVERSE_ALLOW_TOOL_BOOTSTRAP:-0' in script
        assert '默认不安装' in script

    rebuild = Path(
        "reverse-skill/skills/apk-reverse/scripts/rebuild-sign-install.sh"
    ).read_text(encoding="utf-8")
    assert 'REVERSE_ALLOW_DEVICE_INSTALL:-0' in rebuild


def test_apk_powershell_helpers_require_explicit_side_effect_gates() -> None:
    decode = Path("reverse-skill/skills/apk-reverse/scripts/decode.ps1").read_text(
        encoding="utf-8"
    )
    rebuild = Path(
        "reverse-skill/skills/apk-reverse/scripts/rebuild-sign-install.ps1"
    ).read_text(encoding="utf-8")

    assert "REVERSE_ALLOW_TOOL_BOOTSTRAP" in decode
    assert "REVERSE_ALLOW_TOOL_BOOTSTRAP" in rebuild
    assert "REVERSE_ALLOW_DEVICE_INSTALL" in rebuild


def test_legacy_kali_quick_setup_is_explicit_and_uses_locked_cli_identities() -> None:
    script = Path("reverse-skill/kali/scripts/quick-setup.sh").read_text(encoding="utf-8")

    assert 'REVERSE_ALLOW_UNPINNED_PLATFORM_PACKAGES' in script
    assert 'exit 2' in script
    assert "frida-tools==14.10.4" in script
    assert "@jshookmcp/jshook@0.3.3" in script
    assert "@latest" not in script


def test_windows_reverse_bootstrap_is_fail_closed_by_default() -> None:
    script = Path("reverse-skill/skills/scripts/bootstrap-reverse.ps1").read_text(encoding="utf-8")

    assert "REVERSE_ALLOW_UNPINNED_WINDOWS_BOOTSTRAP" in script
    assert "Windows reverse bootstrap is disabled by default" in script
    assert "pnpm@11.12.0" in script
    assert "Get-LockedGitHubReleaseAsset" in script
    assert "Assert-LockedFileHash" in script
    assert "releases/latest" not in script


def test_windows_release_bootstrap_requires_fixed_asset_identities() -> None:
    manifest = json.loads(
        Path("reverse-skill/skills/scripts/bootstrap-manifest.json").read_text(encoding="utf-8")
    )
    by_name = {item["name"]: item for item in manifest["capabilities"]}

    for name in ("jadx", "apktool", "ghidra-mcp"):
        capability = by_name[name]
        assert capability["releaseTag"]
        assert capability["assetName"]
        assert len(capability["sha256"]) == 64

    for name in ("r2", "rabin2"):
        assert by_name[name]["canAutoInstall"] is False


def test_reverse_manifests_do_not_publish_latest_or_unverified_container_fallbacks() -> None:
    for relative in (
        "reverse-skill/skills/scripts/bootstrap-manifest.json",
        "reverse-skill/kali/scripts/bootstrap-manifest.json",
    ):
        value = json.loads(Path(relative).read_text(encoding="utf-8"))
        encoded = json.dumps(value, ensure_ascii=False)
        assert "@latest" not in encoded
        assert ":latest" not in encoded
    generic = json.loads(
        Path("reverse-skill/skills/scripts/bootstrap-manifest.json").read_text(encoding="utf-8")
    )
    pentestswarm = next(item for item in generic["capabilities"] if item["name"] == "pentestswarm")
    assert pentestswarm["canAutoInstall"] is False
    assert "dockerImage" not in pentestswarm
