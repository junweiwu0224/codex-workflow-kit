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
    assert 'pip install --upgrade pyghidra' in script
    assert 'write_mcp_server "ghidra"' in script
    assert 'GHIDRA_PROJECTS_DIR' in script


def test_bootstrap_sh_installs_portable_apktool_wrapper() -> None:
    script = Path("reverse-skill/skills/scripts/bootstrap-reverse.sh").read_text(encoding="utf-8")

    assert 'if [[ "$apktool_path" == "$TOOLS_ROOT/apktool/apktool" ]] && [[ -f "$TOOLS_ROOT/apktool/apktool.jar" ]] && apktool --version >/dev/null 2>&1; then' in script
    assert 'resolve_github_asset_url iBotPeaches/Apktool' in script
    assert 'download_file_checked "$url" "$jar" "apktool jar"' in script
    assert 'apktool wrapper failed smoke check after install' in script
    assert 'exec java -jar "$SCRIPT_DIR/apktool.jar" "$@"' in script


def test_decode_sh_prefers_tool_index_paths() -> None:
    script = Path("reverse-skill/skills/apk-reverse/scripts/decode.sh").read_text(encoding="utf-8")

    assert 'TOOL_INDEX_JSON=' in script
    assert 'tool_path_from_index()' in script
    assert 'prefer_tool_from_index "apktool"' in script
