#!/usr/bin/env bash
# free-binary-workflow.sh — 免费二进制分析链：radare2 快速侦察 + Ghidra headless MCP 深挖
#
# 默认只做低风险只读分析；如需验证 rename，可显式加 --rename-smoke。
#
# 用法：
#   bash free-binary-workflow.sh /bin/cat --analyze --rename-smoke --label bin-cat-free-chain

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
REPO_ROOT="$(cd "$SKILL_DIR/../.." && pwd)"
TOOL_INDEX_JSON="$REPO_ROOT/skills/tool-index.json"
R2_RECON_SCRIPT="$REPO_ROOT/skills/radare2/scripts/recon.sh"
CODEX_CONFIG_PATH="${CODEX_CONFIG_PATH:-$HOME/.codex/config.toml}"

TARGET=""
LABEL=""
OUT_DIR="${PWD}/.verification/reverse-skill/out"
PROJECT_NAME=""
GHIDRA_PROJECT_ROOT="${GHIDRA_PROJECTS_DIR:-}"
RUN_R2=true
RUN_GHIDRA=true
RUN_ANALYSIS=false
RENAME_SMOKE=false
STRINGS_LIMIT=40
IMPORTS_LIMIT=80

usage() {
    cat <<'EOF'
用法:
  bash free-binary-workflow.sh <target_file> [options]

选项:
  --label <name>                 输出文件标签；默认用目标文件名
  --out-dir <dir>                输出目录；默认 <cwd>/.verification/reverse-skill/out
  --project-name <name>          固定 Ghidra project 名称；默认自动生成临时项目名
  --ghidra-project-root <dir>    覆盖 Ghidra project 根目录
  --strings-limit <n>            r2 字符串截断条数，默认 40
  --imports-limit <n>            r2 导入截断条数，默认 80
  --analyze                      让 recon.sh 额外跑 r2 自动分析
  --rename-smoke                 在临时 Ghidra project 中做一次 rename 并自动恢复
  --no-r2                        跳过 radare2 侦察
  --no-ghidra                    跳过 Ghidra MCP 深挖
  -h, --help                     显示帮助
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --label) LABEL="$2"; shift 2 ;;
        --out-dir) OUT_DIR="$2"; shift 2 ;;
        --project-name) PROJECT_NAME="$2"; shift 2 ;;
        --ghidra-project-root) GHIDRA_PROJECT_ROOT="$2"; shift 2 ;;
        --strings-limit) STRINGS_LIMIT="$2"; shift 2 ;;
        --imports-limit) IMPORTS_LIMIT="$2"; shift 2 ;;
        --analyze) RUN_ANALYSIS=true; shift ;;
        --rename-smoke) RENAME_SMOKE=true; shift ;;
        --no-r2) RUN_R2=false; shift ;;
        --no-ghidra) RUN_GHIDRA=false; shift ;;
        -h|--help) usage; exit 0 ;;
        -*) echo "未知选项: $1" >&2; usage; exit 1 ;;
        *) TARGET="$1"; shift ;;
    esac
done

if [[ -z "$TARGET" ]]; then
    usage
    exit 1
fi

if [[ ! -f "$TARGET" ]]; then
    echo "ERR: 目标文件不存在: $TARGET" >&2
    exit 1
fi

if [[ ! -f "$TOOL_INDEX_JSON" ]]; then
    echo "ERR: tool-index.json 不存在: $TOOL_INDEX_JSON" >&2
    echo "请先执行: bash $REPO_ROOT/skills/scripts/refresh-tool-index.sh" >&2
    exit 1
fi

if [[ ! -f "$R2_RECON_SCRIPT" ]]; then
    echo "ERR: recon.sh 不存在: $R2_RECON_SCRIPT" >&2
    exit 1
fi

TARGET_ABS="$(cd "$(dirname "$TARGET")" && pwd)/$(basename "$TARGET")"
if [[ -z "$LABEL" ]]; then
    LABEL="$(basename "$TARGET_ABS" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9._-]/-/g')"
fi
mkdir -p "$OUT_DIR"

R2_LOG="$OUT_DIR/${LABEL}-r2-recon.log"
GHIDRA_JSONL="$OUT_DIR/${LABEL}-ghidra-free-chain.jsonl"
GHIDRA_STDERR="$OUT_DIR/${LABEL}-ghidra-free-chain.stderr"
SUMMARY_JSON="$OUT_DIR/${LABEL}-free-chain-summary.json"

resolve_tool_path() {
    local tool_name="$1"
    python3 - "$TOOL_INDEX_JSON" "$tool_name" <<'PY'
import json
import sys

tool_index_path, tool_name = sys.argv[1], sys.argv[2]
with open(tool_index_path, 'r', encoding='utf-8') as handle:
    data = json.load(handle)
for item in data.get("tools", []):
    if item.get("name") == tool_name and item.get("available") and item.get("path"):
        print(item["path"])
        raise SystemExit(0)
raise SystemExit(1)
PY
}

if [[ "$RUN_R2" == "true" ]]; then
    R2_PATH="$(resolve_tool_path r2)"
    RABIN2_PATH="$(resolve_tool_path rabin2)"
    export PATH="$(dirname "$R2_PATH"):$(dirname "$RABIN2_PATH"):$PATH"

    R2_ARGS=("$TARGET_ABS" "--strings-limit" "$STRINGS_LIMIT" "--imports-limit" "$IMPORTS_LIMIT")
    if [[ "$RUN_ANALYSIS" == "true" ]]; then
        R2_ARGS+=("--analyze")
    fi

    bash "$R2_RECON_SCRIPT" "${R2_ARGS[@]}" >"$R2_LOG"
fi

if [[ "$RUN_GHIDRA" == "true" ]]; then
    if [[ ! -f "$CODEX_CONFIG_PATH" ]]; then
        echo "ERR: Codex 配置不存在，无法解析 ghidra MCP: $CODEX_CONFIG_PATH" >&2
        exit 1
    fi

    if [[ -z "$PROJECT_NAME" ]]; then
        PROJECT_NAME="free_chain_${LABEL}_$(date +%Y%m%d_%H%M%S)"
    fi

    python3 - "$CODEX_CONFIG_PATH" "$TARGET_ABS" "$PROJECT_NAME" "$GHIDRA_PROJECT_ROOT" "$GHIDRA_JSONL" "$GHIDRA_STDERR" "$SUMMARY_JSON" "$RENAME_SMOKE" <<'PY'
import json
import os
import subprocess
import sys
import tomllib
from pathlib import Path

config_path = Path(sys.argv[1])
target_path = str(Path(sys.argv[2]).resolve())
project_name = sys.argv[3]
project_root = sys.argv[4]
jsonl_path = Path(sys.argv[5])
stderr_path = Path(sys.argv[6])
summary_path = Path(sys.argv[7])
rename_smoke = sys.argv[8].lower() == "true"

with config_path.open("rb") as handle:
    config = tomllib.load(handle)

server = config.get("mcp_servers", {}).get("ghidra")
if not server:
    raise SystemExit(f"ghidra MCP 未注册在 {config_path}")

command = server.get("command")
args = list(server.get("args", []))
if not command:
    raise SystemExit("ghidra MCP 配置缺少 command")

env = os.environ.copy()
for key, value in (server.get("env") or {}).items():
    env[str(key)] = str(value)
if project_root:
    env["GHIDRA_PROJECTS_DIR"] = project_root

proc = subprocess.Popen(
    [command, *args],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
    bufsize=1,
    env=env,
)

stderr = ""

def parse_text_payload(response):
    items = response["result"]["content"]
    return json.loads(items[0]["text"])

def send(message, expect_response=True):
    proc.stdin.write(json.dumps(message) + "\n")
    proc.stdin.flush()
    if not expect_response:
        return None
    line = proc.stdout.readline()
    if not line:
        raise RuntimeError("ghidra MCP 未返回响应")
    jsonl_path.parent.mkdir(parents=True, exist_ok=True)
    with jsonl_path.open("a", encoding="utf-8") as handle:
        handle.write(line)
    response = json.loads(line)
    if "error" in response:
        raise RuntimeError(response["error"]["message"])
    return response

summary = {
    "target": target_path,
    "project_name": project_name,
    "project_root": env.get("GHIDRA_PROJECTS_DIR"),
    "rename_smoke": rename_smoke,
}

try:
    send({
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "free-binary-workflow", "version": "0.1.0"},
        },
    })
    send({"jsonrpc": "2.0", "method": "notifications/initialized"}, expect_response=False)
    send({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})

    open_result = parse_text_payload(send({
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {
            "name": "open_binary",
            "arguments": {
                "binary_path": target_path,
                "analyze": True,
                "project_name": project_name,
                **({"project_root": project_root} if project_root else {}),
            },
        },
    }))
    summary["open_binary"] = open_result

    current_binary = parse_text_payload(send({
        "jsonrpc": "2.0",
        "id": 4,
        "method": "tools/call",
        "params": {"name": "get_current_binary", "arguments": {}},
    }))
    summary["current_binary"] = current_binary

    segments = parse_text_payload(send({
        "jsonrpc": "2.0",
        "id": 5,
        "method": "tools/call",
        "params": {"name": "list_segments", "arguments": {"offset": 0, "limit": 10}},
    }))
    summary["segments_preview"] = segments.get("items", [])
    summary["segments_total"] = segments.get("total")

    exports = parse_text_payload(send({
        "jsonrpc": "2.0",
        "id": 6,
        "method": "tools/call",
        "params": {"name": "list_exports", "arguments": {"offset": 0, "limit": 10}},
    }))
    summary["exports_preview"] = exports.get("items", [])
    summary["exports_total"] = exports.get("total")

    functions = parse_text_payload(send({
        "jsonrpc": "2.0",
        "id": 7,
        "method": "tools/call",
        "params": {"name": "list_functions", "arguments": {"offset": 0, "limit": 10}},
    }))
    summary["functions_preview"] = functions.get("items", [])
    summary["functions_total"] = functions.get("total")

    xref_target = None
    for item in exports.get("items", []):
        if item.get("address"):
            xref_target = item["address"]
            if item.get("name") == "entry":
                break
    if not xref_target and functions.get("items"):
        xref_target = functions["items"][0]["address"]
    if not xref_target:
        raise RuntimeError("无法从 exports/functions 中解析 xref 目标地址")

    xrefs_to = parse_text_payload(send({
        "jsonrpc": "2.0",
        "id": 8,
        "method": "tools/call",
        "params": {"name": "get_xrefs_to", "arguments": {"address": xref_target, "offset": 0, "limit": 10}},
    }))
    function_xrefs = parse_text_payload(send({
        "jsonrpc": "2.0",
        "id": 9,
        "method": "tools/call",
        "params": {"name": "get_function_xrefs", "arguments": {"address": xref_target, "offset": 0, "limit": 10}},
    }))
    xrefs_from = parse_text_payload(send({
        "jsonrpc": "2.0",
        "id": 10,
        "method": "tools/call",
        "params": {"name": "get_xrefs_from", "arguments": {"address": xref_target, "offset": 0, "limit": 10}},
    }))
    summary["xref_target"] = xref_target
    summary["xrefs_to"] = xrefs_to
    summary["function_xrefs"] = function_xrefs
    summary["xrefs_from"] = xrefs_from

    if rename_smoke:
        if not functions.get("items"):
            raise RuntimeError("rename smoke 需要至少一个函数")
        rename_address = functions["items"][0]["address"]
        original_name = functions["items"][0]["name"]
        temporary_name = f"{original_name}_codex_free_chain_tmp"

        rename_forward = parse_text_payload(send({
            "jsonrpc": "2.0",
            "id": 11,
            "method": "tools/call",
            "params": {
                "name": "rename_function_by_address",
                "arguments": {"address": rename_address, "new_name": temporary_name},
            },
        }))
        rename_search = parse_text_payload(send({
            "jsonrpc": "2.0",
            "id": 12,
            "method": "tools/call",
            "params": {
                "name": "search_functions_by_name",
                "arguments": {"query": temporary_name, "offset": 0, "limit": 5},
            },
        }))
        rename_restore = parse_text_payload(send({
            "jsonrpc": "2.0",
            "id": 13,
            "method": "tools/call",
            "params": {
                "name": "rename_function_by_address",
                "arguments": {"address": rename_address, "new_name": original_name},
            },
        }))
        summary["rename_smoke_result"] = {
            "address": rename_address,
            "original_name": original_name,
            "temporary_name": temporary_name,
            "rename_forward": rename_forward,
            "rename_search": rename_search,
            "rename_restore": rename_restore,
        }

    close_result = parse_text_payload(send({
        "jsonrpc": "2.0",
        "id": 14,
        "method": "tools/call",
        "params": {"name": "close_binary", "arguments": {}},
    }))
    summary["close_binary"] = close_result
finally:
    if proc.stdin:
        proc.stdin.close()
    if proc.stdout:
        proc.stdout.close()
    stderr = proc.stderr.read() if proc.stderr else ""
    if proc.stderr:
        proc.stderr.close()
    proc.wait(timeout=30)
    stderr_path.write_text(stderr, encoding="utf-8")

summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
print(json.dumps(summary, indent=2, ensure_ascii=False))
PY
fi

echo "输出目录: $OUT_DIR"
[[ -f "$R2_LOG" ]] && echo "r2 侦察日志: $R2_LOG"
[[ -f "$GHIDRA_JSONL" ]] && echo "ghidra RPC 输出: $GHIDRA_JSONL"
[[ -f "$GHIDRA_STDERR" ]] && echo "ghidra STDERR: $GHIDRA_STDERR"
[[ -f "$SUMMARY_JSON" ]] && echo "汇总 JSON: $SUMMARY_JSON"
