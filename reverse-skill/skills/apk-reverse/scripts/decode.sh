#!/usr/bin/env bash
# decode.sh — APK 解包（jadx 反编译 + apktool 解包）
# 等价于 Windows 版的 decode.ps1
#
# 用法:
#   bash decode.sh <apk_path> [--name <task_name>] [--out <output_dir>]
#                              [--skip-jadx] [--skip-apktool] [--clean]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
KALI_BOOTSTRAP="$(cd "$SCRIPT_DIR/../../../kali/scripts" 2>/dev/null && pwd)/bootstrap-reverse.sh"
TOOL_INDEX_JSON="$(cd "$SCRIPT_DIR/../../.." && pwd)/skills/tool-index.json"

# ─── 参数解析 ──────────────────────────────────────────────────────────────────────

APK_PATH=""
TASK_NAME=""
OUT_ROOT=""
SKIP_JADX=false
SKIP_APKTOOL=false
CLEAN=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --name) TASK_NAME="$2"; shift 2 ;;
        --out) OUT_ROOT="$2"; shift 2 ;;
        --skip-jadx) SKIP_JADX=true; shift ;;
        --skip-apktool) SKIP_APKTOOL=true; shift ;;
        --clean) CLEAN=true; shift ;;
        -*) echo "未知选项: $1"; exit 1 ;;
        *) APK_PATH="$1"; shift ;;
    esac
done

if [[ -z "$APK_PATH" ]]; then
    echo "用法: $0 <apk_path> [--name <name>] [--out <dir>] [--skip-jadx] [--skip-apktool] [--clean]"
    exit 1
fi

if [[ ! -f "$APK_PATH" ]]; then
    echo "ERR: APK 文件不存在: $APK_PATH"
    exit 1
fi

# ─── 工具检测与显式 Bootstrap ──────────────────────────────────────────────────────

ensure_tool() {
    local name="$1"
    if command -v "$name" &>/dev/null; then
        return 0
    fi
    if [[ "${REVERSE_ALLOW_TOOL_BOOTSTRAP:-0}" != "1" ]]; then
        echo "ERR: $name 未找到；默认不安装。批准锁定 bootstrap 后设置 REVERSE_ALLOW_TOOL_BOOTSTRAP=1。"
        return 1
    fi
    echo "INFO: $name 未找到，运行已批准的锁定 bootstrap..."
    if [[ -x "$KALI_BOOTSTRAP" ]]; then
        bash "$KALI_BOOTSTRAP" "$name" --skip-refresh 2>/dev/null || true
    fi
    if ! command -v "$name" &>/dev/null; then
        echo "ERR: $name bootstrap 失败，请审阅锁定来源和安装日志"
        return 1
    fi
    echo "INFO: $name bootstrap 成功"
}

tool_path_from_index() {
    local name="$1"
    [[ -f "$TOOL_INDEX_JSON" ]] || return 1
    python3 - "$TOOL_INDEX_JSON" "$name" <<'PY'
import json
import sys

index_path, tool_name = sys.argv[1:]
with open(index_path, 'r', encoding='utf-8') as handle:
    data = json.load(handle)
for item in data.get('tools', []):
    if item.get('name') == tool_name and item.get('available') and item.get('path') not in (None, '', '—'):
        print(item['path'])
        raise SystemExit(0)
raise SystemExit(1)
PY
}

prefer_tool_from_index() {
    local name="$1"
    local resolved=""
    resolved="$(tool_path_from_index "$name" 2>/dev/null || true)"
    if [[ -n "$resolved" ]]; then
        case "$resolved" in
            */apktool.jar)
                local wrapper_dir
                wrapper_dir="$(dirname "$resolved")"
                mkdir -p "$wrapper_dir"
                cat > "$wrapper_dir/apktool" <<'EOF'
#!/usr/bin/env bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec java -jar "$SCRIPT_DIR/apktool.jar" "$@"
EOF
                chmod +x "$wrapper_dir/apktool"
                export PATH="$wrapper_dir:$PATH"
                ;;
            *)
                export PATH="$(dirname "$resolved"):$PATH"
                ;;
        esac
    fi
}

prefer_tool_from_index "jadx"
prefer_tool_from_index "apktool"
[[ "$SKIP_JADX" != "true" ]] && ensure_tool "jadx"
[[ "$SKIP_APKTOOL" != "true" ]] && ensure_tool "apktool"

# ─── 路径计算 ──────────────────────────────────────────────────────────────────────

APK_BASENAME=$(basename "$APK_PATH" .apk | sed 's/[^A-Za-z0-9._-]/_/g')
TASK_NAME="${TASK_NAME:-$APK_BASENAME}"
OUT_ROOT="${OUT_ROOT:-$(dirname "$APK_PATH")}"
TASK_ROOT="$OUT_ROOT/$TASK_NAME"
JADX_OUT="$TASK_ROOT/jadx"
APKTOOL_OUT="$TASK_ROOT/apktool"

if [[ "$CLEAN" == "true" && -d "$TASK_ROOT" ]]; then
    rm -rf "$TASK_ROOT"
fi

mkdir -p "$TASK_ROOT"

# ─── jadx 反编译 ──────────────────────────────────────────────────────────────────

JADX_EXIT=0
if [[ "$SKIP_JADX" != "true" ]]; then
    rm -rf "$JADX_OUT"
    echo "=== jadx 反编译 ==="
    jadx -d "$JADX_OUT" "$APK_PATH" || JADX_EXIT=$?
fi

# ─── apktool 解包 ─────────────────────────────────────────────────────────────────

APKTOOL_EXIT=0
if [[ "$SKIP_APKTOOL" != "true" ]]; then
    rm -rf "$APKTOOL_OUT"
    echo "=== apktool 解包 ==="
    apktool d "$APK_PATH" -o "$APKTOOL_OUT" -f || APKTOOL_EXIT=$?
fi

# ─── 统计输出 ──────────────────────────────────────────────────────────────────────

PACKAGE=""
if [[ -f "$APKTOOL_OUT/AndroidManifest.xml" ]]; then
    PACKAGE=$(sed -n 's/.*package="\([^"]*\)".*/\1/p' "$APKTOOL_OUT/AndroidManifest.xml" 2>/dev/null | head -1)
fi

JAVA_COUNT=0
[[ -d "$JADX_OUT" ]] && JAVA_COUNT=$(find "$JADX_OUT" -name "*.java" | wc -l)

SMALI_DIRS=0
[[ -d "$APKTOOL_OUT" ]] && SMALI_DIRS=$(find "$APKTOOL_OUT" -maxdepth 1 -type d -name "smali*" | wc -l)

SO_COUNT=0
[[ -d "$APKTOOL_OUT" ]] && SO_COUNT=$(find "$APKTOOL_OUT" -name "*.so" | wc -l)

echo ""
echo "═══════════════════════════════════════════"
echo "  APK 解包完成"
echo "═══════════════════════════════════════════"
echo "  task_root=$TASK_ROOT"
echo "  jadx_out=$JADX_OUT"
echo "  apktool_out=$APKTOOL_OUT"
echo "  package=$PACKAGE"
echo "  jadx_exit_code=$JADX_EXIT"
echo "  apktool_exit_code=$APKTOOL_EXIT"
echo "  java_files=$JAVA_COUNT"
echo "  smali_dirs=$SMALI_DIRS"
echo "  so_files=$SO_COUNT"

if [[ "$SKIP_APKTOOL" != "true" && "$APKTOOL_EXIT" -ne 0 ]]; then
    exit "$APKTOOL_EXIT"
fi
