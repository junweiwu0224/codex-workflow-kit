#!/usr/bin/env bash
# bootstrap-reverse.sh — Kali Linux 版经批准工具安装/补齐
# 等价于 Windows 版的 bootstrap-reverse.ps1
#
# 用法:
#   bash bootstrap-reverse.sh <capability1> [capability2] ... [--start-services] [--skip-refresh]
#
# 示例:
#   bash bootstrap-reverse.sh jadx apktool frida
#   bash bootstrap-reverse.sh idapro --start-services
#   bash bootstrap-reverse.sh jshookmcp anything-analyzer

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ "${BOOTSTRAP_REVERSE_LIB_ONLY:-0}" != "1" ]]; then
    source "$SCRIPT_DIR/lib/tool-discovery.sh"
fi
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
WORKFLOW_ROOT="$(cd "$REPO_ROOT/.." && pwd)"
LOCK_FILE="${REVERSE_DEPENDENCY_LOCK:-$WORKFLOW_ROOT/catalog/reverse-dependencies.lock.yaml}"

lock_value() {
    local dependency_id="$1"
    local field="$2"
    [[ -f "$LOCK_FILE" ]] || return 1
    awk -v wanted="$dependency_id" -v wanted_field="$field" '
        $1 == "-" && $2 == "id:" {
            current=$3
            gsub(/^"|"$/, "", current)
            next
        }
        current == wanted && $1 == wanted_field ":" {
            sub(/^[^:]+:[[:space:]]*/, "")
            gsub(/^"|"$/, "")
            print
            exit
        }
    ' "$LOCK_FILE"
}

require_locked_dependency() {
    local dependency_id="$1"
    local status
    status="$(lock_value "$dependency_id" status || true)"
    if [[ "$status" != "resolved" ]]; then
        log_warn "MANUAL_INSTALL_REQUIRED: $dependency_id is not resolved in $LOCK_FILE"
        return 1
    fi
}

verify_sha256() {
    local expected="$1"
    local file="$2"
    if command -v sha256sum >/dev/null 2>&1; then
        printf '%s  %s\n' "$expected" "$file" | sha256sum -c - >/dev/null
    else
        printf '%s  %s\n' "$expected" "$file" | shasum -a 256 -c - >/dev/null
    fi
}

fetch_locked_repo() {
  local dependency_id="$1"
  local destination="$2"
  require_locked_dependency "$dependency_id" || return 1
  local repository commit origin_url checkout_status actual_commit
  repository="$(lock_value "$dependency_id" repository)"
  commit="$(lock_value "$dependency_id" commit)"
  [[ "$repository" =~ ^https://.+\.git$ ]] && [[ "$commit" =~ ^[0-9a-f]{40}$ ]] || {
    log_warn "MANUAL_INSTALL_REQUIRED: $dependency_id requires an HTTPS repository and full commit in $LOCK_FILE"
    return 1
  }
  if [[ -d "$destination/.git" ]]; then
    origin_url="$(git -C "$destination" remote get-url origin 2>/dev/null || true)"
    if [[ "$origin_url" != "$repository" ]]; then
      log_err "Refusing $dependency_id checkout with unexpected origin: ${origin_url:-missing}"
      return 1
    fi
    if ! checkout_status="$(git -C "$destination" status --porcelain --untracked-files=all)"; then
      log_err "Refusing $dependency_id checkout whose worktree state cannot be verified: $destination"
      return 1
    fi
    if [[ -n "$checkout_status" ]]; then
      log_err "Refusing dirty $dependency_id checkout: $destination"
      return 1
    fi
    git -C "$destination" fetch --depth=1 origin "$commit"
  elif [[ -e "$destination" ]]; then
    log_err "Refusing non-Git checkout path for $dependency_id: $destination"
    return 1
  else
    mkdir -p "$destination"
    git -C "$destination" init -q
    git -C "$destination" remote add origin "$repository"
    git -C "$destination" fetch --depth=1 origin "$commit"
  fi
  git -C "$destination" cat-file -e "${commit}^{commit}"
  git -C "$destination" checkout --detach -q "$commit"
  actual_commit="$(git -C "$destination" rev-parse HEAD)"
  if [[ "$actual_commit" != "$commit" ]]; then
    log_err "Refusing $dependency_id checkout: expected $commit, got $actual_commit"
    return 1
  fi
}

verify_go_tag_commit() {
    local dependency_id="$1"
    require_locked_dependency "$dependency_id" || return 1
    if ! command -v git >/dev/null 2>&1; then
        log_warn "MANUAL_INSTALL_REQUIRED: Git is required to verify the locked Go tag commit"
        return 1
    fi
    local repository version commit actual_commit
    repository="$(lock_value "$dependency_id" repository || true)"
    version="$(lock_value "$dependency_id" version || true)"
    commit="$(lock_value "$dependency_id" commit || true)"
    [[ "$repository" =~ ^https://.+\.git$ ]] && [[ -n "$version" ]] && [[ "$commit" =~ ^[0-9a-f]{40}$ ]] || {
        log_warn "MANUAL_INSTALL_REQUIRED: $dependency_id requires repository, version, and full commit in $LOCK_FILE"
        return 1
    }
    actual_commit="$(git ls-remote "$repository" "refs/tags/${version}^{}" "refs/tags/${version}" | awk -v direct="refs/tags/${version}" -v peeled="refs/tags/${version}^{}" '
        $2 == peeled { print $1; found=1; exit }
        $2 == direct { candidate=$1 }
        END { if (!found && candidate != "") print candidate }
    ')"
    if [[ "$actual_commit" != "$commit" ]]; then
        log_err "Refusing $dependency_id: tag $version resolved to ${actual_commit:-missing}, not $commit"
        return 1
    fi
}

install_locked_go_package() {
    local dependency_id="$1"
    local module version
    require_locked_dependency "$dependency_id" || return 1
    module="$(lock_value "$dependency_id" module || true)"
    version="$(lock_value "$dependency_id" version || true)"
    [[ -n "$module" && -n "$version" ]] || {
        log_warn "MANUAL_INSTALL_REQUIRED: $dependency_id has no module/version in $LOCK_FILE"
        return 1
    }
    verify_go_tag_commit "$dependency_id" || return 1
    go install "${module}@${version}"
}

install_pnpm_dependencies_frozen() {
    local project_dir="$1"
    if [[ ! -f "$project_dir/pnpm-lock.yaml" ]]; then
        log_err "Refusing to start without pnpm-lock.yaml: $project_dir"
        return 1
    fi
    (cd "$project_dir" && pnpm install --frozen-lockfile)
}

# Test-only library mode exposes the lock helpers without invoking bootstrap.
if [[ "${BOOTSTRAP_REVERSE_LIB_ONLY:-0}" == "1" ]]; then
    return 0 2>/dev/null || exit 0
fi

# ─── 参数解析 ──────────────────────────────────────────────────────────────────────

CAPABILITIES=()
START_SERVICES=false
SKIP_REFRESH=false

for arg in "$@"; do
    case "$arg" in
        --start-services) START_SERVICES=true ;;
        --skip-refresh) SKIP_REFRESH=true ;;
        --list|-l)
            echo "jadx apktool frida frida-ps idalib-mcp jshookmcp anything-analyzer idapro r2 rabin2 adb agent-browser ghidra-mcp seclists proxycat burpsuite-mcp nmap pentestswarm"
            echo "mcp-kali-server metasploitmcp hexstrike-ai adaptixc2 atomic-operator sstimap xsstrike wpprobe fluxion gef coercer evil-winrm-py netexec responder bloodhound certipy"
            exit 0
            ;;
        -*) echo "未知选项: $arg"; exit 1 ;;
        *) CAPABILITIES+=("$arg") ;;
    esac
done

if [[ ${#CAPABILITIES[@]} -eq 0 ]]; then
    echo "用法: $0 <capability1> [capability2] ... [--start-services] [--skip-refresh]"
    echo ""
    echo "可用能力:"
    echo ""
    echo "  [逆向分析]"
    echo "    jadx apktool frida frida-ps idalib-mcp r2 rabin2 adb gef"
    echo ""
    echo "  [渗透测试 - 经典工具]"
    echo "    nmap sqlmap hashcat hydra gobuster ffuf msfconsole nuclei"
    echo "    netexec responder crackmapexec bloodhound certipy wfuzz"
    echo "    aircrack-ng coercer evil-winrm-py"
    echo ""
    echo "  [渗透测试 - Kali 2026.1 新增]"
    echo "    adaptixc2 atomic-operator sstimap xsstrike wpprobe fluxion"
    echo ""
    echo "  [MCP 服务]"
    echo "    jshookmcp anything-analyzer idapro agent-browser"
    echo "    mcp-kali-server metasploitmcp hexstrike-ai pentestswarm"
    echo ""
    echo "  [其他]"
    echo "    ghidra-mcp seclists proxycat burpsuite-mcp"
    echo ""
    echo "示例:"
    echo "  $0 mcp-kali-server metasploitmcp hexstrike-ai pentestswarm  # 全部渗透 MCP"
    echo "  $0 adaptixc2 sstimap xsstrike wpprobe          # 安装 2026.1 新工具"
    echo "  $0 pentestswarm --start-services               # 安装 Swarm AI"
    echo "  $0 idapro --start-services                     # 安装并启动 IDA MCP"
    exit 1
fi

# ─── 辅助函数 ──────────────────────────────────────────────────────────────────────

log_info() { echo -e "\033[36m[INFO]\033[0m $*"; }
log_ok() { echo -e "\033[32m[OK]\033[0m $*"; }
log_warn() { echo -e "\033[33m[WARN]\033[0m $*"; }
log_err() { echo -e "\033[31m[ERR]\033[0m $*"; }

require_unpinned_platform_opt_in() {
    if [[ "${REVERSE_ALLOW_UNPINNED_PLATFORM_PACKAGES:-0}" != "1" ]]; then
        log_warn "MANUAL_INSTALL_REQUIRED: unpinned apt installs are disabled by default"
        log_warn "Install manually, or explicitly set REVERSE_ALLOW_UNPINNED_PLATFORM_PACKAGES=1"
        return 1
    fi
}

# 检查是否有 sudo 权限
check_sudo() {
    if [[ $EUID -eq 0 ]]; then
        return 0
    fi
    if sudo -n true 2>/dev/null; then
        return 0
    fi
    log_warn "部分操作需要 sudo 权限"
    return 1
}

# apt 安装
install_apt_package() {
    local package="$1"
    require_unpinned_platform_opt_in || return 1
    log_info "apt install $package ..."
    if [[ $EUID -eq 0 ]]; then
        apt-get update -qq && apt-get install -y -qq "$package"
    else
        sudo apt-get update -qq && sudo apt-get install -y -qq "$package"
    fi
}

# pip 安装
install_pip_package() {
    local package="$1"
    local source="${2:-}"
    local target="${source:-$package}"
    log_info "pip3 install $target ..."
    pip3 install --upgrade "$target" --break-system-packages 2>/dev/null \
        || pip3 install --upgrade "$target"
}

# npm 全局安装
install_npm_global() {
    local package="$1"
    local version="${2:-}"
    log_info "install locked npm package $package ..."
    [[ -n "$version" ]] || {
        log_warn "MANUAL_INSTALL_REQUIRED: $package has no locked npm version"
        return 1
    }
    if [[ $EUID -eq 0 ]]; then
        npm install -g "${package}@${version}"
    else
        sudo npm install -g "${package}@${version}" 2>/dev/null || npm install -g "${package}@${version}"
    fi
}

# GitHub Release 下载并解压
install_github_release() {
    local dependency_id="$1"
    local install_dir="$2"

    require_locked_dependency "$dependency_id" || return 1
    log_info "从锁定 GitHub Release 下载: $dependency_id ..."

    local download_url expected_sha
    download_url="$(lock_value "$dependency_id" url || true)"
    expected_sha="$(lock_value "$dependency_id" sha256 || true)"
    if [[ -z "$download_url" || ! "$expected_sha" =~ ^[0-9a-f]{64}$ ]]; then
        log_err "锁中缺少 $dependency_id 的固定 URL 或 SHA-256"
        return 1
    fi

    local filename
    filename=$(basename "$download_url")
    local tmp_file="/tmp/bootstrap-$$-${filename}"

    log_info "下载: $download_url"
    curl -sL -o "$tmp_file" "$download_url"
    if ! verify_sha256 "$expected_sha" "$tmp_file"; then
        rm -f "$tmp_file"
        log_err "校验失败: $dependency_id"
        return 1
    fi

    # 创建安装目录
    mkdir -p "$install_dir"

    # 根据文件类型解压
    case "$filename" in
        *.tar.gz|*.tgz)
            tar -xzf "$tmp_file" -C "$install_dir" --strip-components=1 2>/dev/null \
                || tar -xzf "$tmp_file" -C "$install_dir"
            ;;
        *.zip)
            local tmp_extract="/tmp/bootstrap-extract-$$"
            mkdir -p "$tmp_extract"
            unzip -qo "$tmp_file" -d "$tmp_extract"
            # 如果只有一个顶层目录，strip 它
            local top_dirs
            top_dirs=$(find "$tmp_extract" -maxdepth 1 -mindepth 1 -type d)
            if [[ $(echo "$top_dirs" | wc -l) -eq 1 ]]; then
                cp -a "$top_dirs"/* "$install_dir/" 2>/dev/null || mv "$top_dirs"/* "$install_dir/"
            else
                cp -a "$tmp_extract"/* "$install_dir/"
            fi
            rm -rf "$tmp_extract"
            ;;
        *.deb)
            require_unpinned_platform_opt_in || return 1
            if [[ $EUID -eq 0 ]]; then
                dpkg -i "$tmp_file" || apt-get install -f -y
            else
                sudo dpkg -i "$tmp_file" || sudo apt-get install -f -y
            fi
            ;;
        *)
            cp "$tmp_file" "$install_dir/"
            ;;
    esac

    rm -f "$tmp_file"

    # 把 bin 目录加入 PATH（当前 session）
    if [[ -d "$install_dir/bin" ]]; then
        export PATH="$install_dir/bin:$PATH"
    else
        export PATH="$install_dir:$PATH"
    fi

    log_ok "已安装到 $install_dir"
}

# 注册 MCP server 到 Claude 配置
register_mcp_server() {
    local server_name="$1"
    local config_json="$2"  # JSON 格式的 server 配置

    local config_path
    config_path=$(get_claude_mcp_config_path)
    local config_dir
    config_dir=$(dirname "$config_path")

    mkdir -p "$config_dir"

    if [[ ! -f "$config_path" ]]; then
        echo '{"mcpServers":{}}' > "$config_path"
    fi

    if command -v jq &>/dev/null; then
        local tmp_file="/tmp/mcp-config-$$.json"
        jq ".mcpServers.\"${server_name}\" = ${config_json}" "$config_path" > "$tmp_file"
        mv "$tmp_file" "$config_path"
        log_ok "MCP server '$server_name' 已注册到 $config_path"
    else
        log_warn "未安装 jq，无法自动注册 MCP server。请手动编辑 $config_path"
    fi
}

# 等待端口就绪
wait_for_port() {
    local port="$1"
    local timeout="${2:-90}"
    local elapsed=0

    while [[ $elapsed -lt $timeout ]]; do
        if test_tcp_port "$port" 2>/dev/null; then
            return 0
        fi
        sleep 2
        elapsed=$((elapsed + 2))
    done
    return 1
}

# ─── 能力安装逻辑 ──────────────────────────────────────────────────────────────────

ensure_capability() {
    local name="$1"

    # 先检查是否已可用
    if command -v "$name" &>/dev/null; then
        log_ok "$name 已可用: $(command -v "$name")"
        return 0
    fi

    log_info "开始安装: $name"

    case "$name" in
        # ─── apt 预装/可装的工具 ───
        nmap|sqlmap|hashcat|hydra|gobuster|ffuf|adb)
            install_apt_package "$name"
            ;;
        msfconsole)
            install_apt_package "metasploit-framework"
            ;;
        r2|rabin2|rasm2|radiff2|rahash2|rax2)
            if ! command -v r2 &>/dev/null; then
                install_apt_package "radare2"
            fi
            ;;
        apktool)
            install_apt_package "apktool"
            ;;
        seclists)
            install_apt_package "seclists"
            ;;
        # ─── Kali 2026.1 新增工具（全部 apt 直装） ───
        adaptixc2)
            install_apt_package "adaptixc2"
            ;;
        atomic-operator)
            install_apt_package "atomic-operator"
            ;;
        fluxion)
            install_apt_package "fluxion"
            ;;
        gef)
            install_apt_package "gef"
            log_info "GEF 已安装。启动 gdb 时自动加载 GEF 增强功能。"
            ;;
        sstimap)
            install_apt_package "sstimap"
            ;;
        xsstrike)
            install_apt_package "xsstrike"
            ;;
        wpprobe)
            install_apt_package "wpprobe"
            ;;
        evil-winrm-py)
            install_apt_package "evil-winrm-py"
            ;;
        coercer)
            install_apt_package "coercer"
            ;;
        netexec)
            install_apt_package "netexec"
            ;;
        responder)
            install_apt_package "responder"
            ;;
        crackmapexec)
            install_apt_package "crackmapexec"
            ;;
        bloodhound)
            install_apt_package "bloodhound"
            ;;
        certipy)
            install_apt_package "certipy-ad"
            ;;
        wfuzz)
            install_apt_package "wfuzz"
            ;;
        aircrack-ng)
            install_apt_package "aircrack-ng"
            ;;
        # ─── Kali 原生 MCP 工具（apt 安装 + MCP 注册） ───
        mcp-kali-server)
            install_apt_package "mcp-kali-server"
            register_mcp_server "kali-server" '{
                "command": "kali-server-mcp",
                "args": ["--port", "5000"]
            }'
            log_info "启动方式: kali-server-mcp --port 5000"
            log_info "然后用 mcp-server 连接 AI 客户端到 API server"
            ;;
        metasploitmcp)
            install_apt_package "metasploitmcp"
            register_mcp_server "metasploit-mcp" '{
                "command": "metasploitmcp",
                "args": ["--transport", "stdio"]
            }'
            log_info "MetasploitMCP 支持 stdio 和 HTTP 两种模式"
            log_info "  stdio: metasploitmcp --transport stdio"
            log_info "  HTTP:  metasploitmcp --transport http --port 8085"
            ;;
        hexstrike-ai)
            install_apt_package "hexstrike-ai"
            register_mcp_server "hexstrike" '{
                "command": "hexstrike-ai",
                "args": []
            }'
            log_info "HexStrike AI 已安装。150+ 安全工具通过 MCP 暴露给 AI agent。"
            ;;
        # ─── Pentest Swarm AI（群体智能渗透框架） ───
        pentestswarm)
            if command -v pentestswarm &>/dev/null; then
                log_ok "pentestswarm 已可用"
            elif command -v go &>/dev/null; then
                log_info "go install pentestswarm ..."
                require_locked_dependency pentestswarm-go || return 1
                install_locked_go_package pentestswarm-go
            else
                log_warn "需要 Go 1.24+ 或 Docker 来安装 pentestswarm"
                log_info "安装 Go: apt install golang-go"
                log_info "然后使用 $LOCK_FILE 中的固定版本安装 Pentest-Swarm-AI"
                return 1
            fi
            register_mcp_server "pentestswarm" '{
                "command": "pentestswarm",
                "args": ["mcp", "serve"]
            }'
            log_info "Pentest Swarm AI 已配置"
            log_info "  MCP 模式: pentestswarm mcp serve"
            log_info "  扫描模式: pentestswarm scan <target> --scope <scope> --swarm"
            log_info "  需要设置: export PENTESTSWARM_ORCHESTRATOR_API_KEY=<your-claude-key>"
            ;;

        # ─── pip 安装 ───
        frida|frida-ps)
            require_locked_dependency frida-tools-pypi || return 1
            install_pip_package "frida-tools==$(lock_value frida-tools-pypi version)"
            ;;
        idalib-mcp)
            require_locked_dependency ida-pro-mcp-git || return 1
            install_pip_package "ida-pro-mcp" "git+$(lock_value ida-pro-mcp-git repository)@$(lock_value ida-pro-mcp-git commit)"
            log_info "运行 ida-pro-mcp --install 完成 IDA 插件安装"
            ;;
        proxycat)
            require_locked_dependency proxycat-git || return 1
            install_pip_package "proxycat" "git+$(lock_value proxycat-git repository)@$(lock_value proxycat-git commit)"
            ;;

        # ─── GitHub Release ───
        jadx)
            install_github_release jadx-release "$HOME/tools/jadx"
            chmod +x "$HOME/tools/jadx/bin/jadx" 2>/dev/null || true
            ;;
        ghidra-mcp)
            if command -v ghidra &>/dev/null; then
                log_ok "ghidra 已通过 apt 安装"
            else
                install_apt_package "ghidra" 2>/dev/null \
                    || install_github_release ghidra-release "$HOME/tools/ghidra"
            fi
            log_warn "GhidraMCP 插件需手动安装: https://github.com/LaurieWired/GhidraMCP/releases"
            ;;
        nuclei)
            if command -v go &>/dev/null; then
                log_info "go install nuclei ..."
                require_locked_dependency nuclei-go || return 1
                install_locked_go_package nuclei-go
            else
                install_github_release nuclei-release "$HOME/tools/nuclei"
            fi
            ;;

        # ─── npm/MCP ───
        jshookmcp)
            if ! command -v node &>/dev/null; then
                install_apt_package "nodejs"
            fi
            if ! command -v npm &>/dev/null; then
                install_apt_package "npm"
            fi
            require_locked_dependency jshookmcp-npm || return 1
            local jshook_version
            jshook_version="$(lock_value jshookmcp-npm version)"
            register_mcp_server "jshook" "{\"command\":\"npx\",\"args\":[\"-y\",\"@jshookmcp/jshook@$jshook_version\"],\"env\":{\"JSHOOK_BASE_PROFILE\":\"search\"}}"
            ;;
        agent-browser)
            if ! command -v node &>/dev/null; then
                install_apt_package "nodejs"
            fi
            require_locked_dependency agent-browser-npm || return 1
            require_locked_dependency playwright-npm || return 1
            install_npm_global "agent-browser" "$(lock_value agent-browser-npm version)"
            npx --yes "playwright@$(lock_value playwright-npm version)" install chromium 2>/dev/null || true
            ;;

        # ─── 本地 HTTP MCP 服务 ───
        anything-analyzer)
            if [[ "$START_SERVICES" == "true" ]]; then
                start_anything_analyzer
            else
                ensure_anything_analyzer_checkout
            fi
            register_mcp_server "anything-analyzer" "{\"url\": \"http://localhost:23816/mcp\"}"
            ;;
        idapro)
            # 先确保 idalib-mcp 已安装
            ensure_capability "idalib-mcp"
            register_mcp_server "idapro" "{\"url\": \"http://127.0.0.1:13337/mcp\"}"
            if [[ "$START_SERVICES" == "true" ]]; then
                start_idapro_service
            fi
            ;;

        # ─── 手动安装 ───
        burpsuite-mcp)
            log_warn "MANUAL_INSTALL_REQUIRED: burpsuite-mcp"
            log_warn "Kali 预装 BurpSuite，在扩展市场搜索 MCP 插件安装"
            register_mcp_server "burpsuite" "{\"url\": \"http://localhost:9876/mcp\"}"
            ;;

        *)
            log_err "未知能力: $name"
            return 1
            ;;
    esac
}

# ─── 服务启动 ──────────────────────────────────────────────────────────────────────

ensure_anything_analyzer_checkout() {
    local repo_dir="$HOME/tools/anything-analyzer"
    if ! command -v git &>/dev/null; then
        install_apt_package git || return 1
    fi
    fetch_locked_repo anything-analyzer-git "$repo_dir"
}

start_anything_analyzer() {
    local repo_dir="$HOME/tools/anything-analyzer"

    ensure_anything_analyzer_checkout || return 1

    if test_tcp_port 23816 2>/dev/null; then
        log_err "Refusing to reuse an already-running anything-analyzer service whose checkout cannot be verified"
        return 1
    fi

    if ! command -v pnpm &>/dev/null; then
        require_locked_dependency pnpm-npm || return 1
        install_npm_global pnpm "$(lock_value pnpm-npm version)"
    fi

    install_pnpm_dependencies_frozen "$repo_dir" || return 1
    (cd "$repo_dir" && nohup pnpm dev > /tmp/anything-analyzer.log 2>&1 &)

    log_info "等待 anything-analyzer 启动 (port 23816) ..."
    if wait_for_port 23816 120; then
        log_ok "anything-analyzer 已启动"
    else
        log_err "anything-analyzer 启动超时，查看日志: /tmp/anything-analyzer.log"
        return 1
    fi
}

start_idapro_service() {
    if test_tcp_port 13337 2>/dev/null; then
        log_ok "IDA Pro MCP 已在运行 (port 13337)"
        return 0
    fi

    local ida_start_script="$SCRIPT_DIR/ida-start.sh"
    if [[ -x "$ida_start_script" ]]; then
        bash "$ida_start_script"
    else
        log_warn "IDA 启动脚本不存在: $ida_start_script"
        log_warn "请手动启动 IDA Pro，插件会自动监听 13337 端口"
        return 1
    fi
}

# ─── 主流程 ────────────────────────────────────────────────────────────────────────

RESULTS=()

for cap in "${CAPABILITIES[@]}"; do
    if ensure_capability "$cap"; then
        RESULTS+=("{\"name\":\"$cap\",\"status\":\"ready\"}")
    else
        RESULTS+=("{\"name\":\"$cap\",\"status\":\"failed\"}")
    fi
done

# 刷新工具索引
if [[ "$SKIP_REFRESH" != "true" ]]; then
    log_info "刷新工具索引 ..."
    bash "$SCRIPT_DIR/refresh-tool-index.sh" >/dev/null 2>&1 || true
fi

# 输出结果
echo ""
echo "═══════════════════════════════════════════"
echo "  Bootstrap 完成"
echo "═══════════════════════════════════════════"
for r in "${RESULTS[@]}"; do
    name=$(echo "$r" | jq -r '.name' 2>/dev/null || echo "$r")
    status=$(echo "$r" | jq -r '.status' 2>/dev/null || echo "unknown")
    if [[ "$status" == "ready" ]]; then
        echo "  ✓ $name"
    else
        echo "  ✗ $name (failed)"
    fi
done
echo ""
