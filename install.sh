#!/usr/bin/env bash
set -euo pipefail

KIT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CODEX_HOME="${HOME}/.codex"
AGENTS_HOME="${HOME}/.agents"
TARGET_REPO=""
DRY_RUN=0
BACKUP=0
FORCE=0
REPO_ONLY=0
INSTALL_PILOTS=0
INSTALL_REVERSE=0
INSTALL_REVERSE_CORE=0
START_REVERSE_SERVICES=0
VERIFY_REVERSE_READY=0
REVERSE_BOOTSTRAP_CAPABILITIES=""
PRUNE_PREVIEW=0
PRUNE=0
UNINSTALL=0
ROLLBACK=0
REVERSE_BOOTSTRAP_SCRIPT_REL="reverse-skill/skills/scripts/bootstrap-reverse.sh"

usage() {
  cat <<'EOF'
Usage: ./install.sh [options]

Install the Codex workflow kit on this machine.

Options:
  --dry-run              Print actions without writing files.
  --codex-home PATH      Codex home for global AGENTS.md. Default: ~/.codex
  --agents-home PATH     Agents home for personal skills. Default: ~/.agents
  --repo PATH            Optional target repository for repo-template files.
  --repo-only            Install only repo-template files; skip global AGENTS.md and skills.
  --with-pilots          Add pilot skills to the default stable skill profile.
  --with-reverse         Install the optional reverse router and reverse capability pack.
  --with-reverse-core    Install the reverse profile and bootstrap reverse core tools (compatibility option).
  --start-reverse-services
                         With --with-reverse-core, also start supported local MCP services.
  --verify-reverse-ready Run reverse readiness verification; does not install the reverse profile.
  --reverse-capabilities CSV
                         Override reverse bootstrap capability list.
  --prune-preview        Show files from an older profile that can be pruned; do not write.
  --prune                Remove unchanged files from an older profile; modified files are kept.
  --uninstall            Remove files recorded by the last install; modified files are kept.
  --rollback             Restore the exact pre-install state recorded by the transaction.
  --backup               Back up conflicting existing files before replacing.
  --force                Replace conflicting existing files without backups.
  -h, --help             Show this help.

Default behavior installs the global guidance and stable personal skills only.
Pilot skills and the reverse profile are opt-in via --with-pilots,
--with-reverse, or --with-reverse-core. Existing different files are treated
as conflicts unless --backup or --force is provided.
EOF
}

log() {
  printf '%s\n' "$*"
}

run() {
  if [[ "${DRY_RUN}" == "1" ]]; then
    printf '[dry-run] %s\n' "$*"
  else
    "$@"
  fi
}

reverse_bootstrap_capabilities() {
  if [[ -n "${REVERSE_BOOTSTRAP_CAPABILITIES}" ]]; then
    printf '%s\n' "${REVERSE_BOOTSTRAP_CAPABILITIES}" | tr ',' '\n' | sed '/^$/d'
    return 0
  fi

  cat <<'EOF'
jadx
apktool
frida
r2
adb
nmap
sqlmap
ffuf
nuclei
binwalk
graphviz
jshookmcp
anything-analyzer
ghidra-mcp
EOF
}

run_reverse_bootstrap() {
  local bootstrap_script="${KIT_ROOT}/${REVERSE_BOOTSTRAP_SCRIPT_REL}"
  local installed_bootstrap_script="${CODEX_HOME}/reverse-skill/skills/scripts/bootstrap-reverse.sh"
  if [[ "${DRY_RUN}" != "1" && -f "${installed_bootstrap_script}" ]]; then
    bootstrap_script="${installed_bootstrap_script}"
  fi
  if [[ ! -f "${bootstrap_script}" ]]; then
    log "reverse bootstrap script missing: ${bootstrap_script}"
    return 1
  fi

  local args=()
  while IFS= read -r capability; do
    [[ -n "${capability}" ]] || continue
    args+=("${capability}")
  done < <(reverse_bootstrap_capabilities)

  if [[ "${#args[@]}" -eq 0 ]]; then
    log "reverse bootstrap capability list is empty"
    return 1
  fi

  if [[ "${START_REVERSE_SERVICES}" == "1" ]]; then
    args+=("--start-services")
  fi

  if [[ "${DRY_RUN}" == "1" ]]; then
    printf '[dry-run] bash %s' "${bootstrap_script}"
    local arg
    for arg in "${args[@]}"; do
      printf ' %s' "${arg}"
    done
    printf '\n'
    return 0
  fi

  log "bootstrap reverse core tools"
  CODEX_CONFIG_PATH="${CODEX_HOME}/config.toml" \
  CLAUDE_MCP_CONFIG="${HOME}/.claude/mcp.json" \
  bash "${bootstrap_script}" "${args[@]}"
}

run_reverse_ready_verifier() {
  local verify_script="${KIT_ROOT}/scripts/verify_reverse_ready.py"
  if [[ ! -f "${verify_script}" ]]; then
    log "reverse readiness verifier missing: ${verify_script}"
    return 1
  fi
  if [[ "${DRY_RUN}" == "1" ]]; then
    printf '[dry-run] python3 %s --user-home %s --codex-config %s\n' \
      "${verify_script}" "${HOME}" "${CODEX_HOME}/config.toml"
    return 0
  fi
  python3 "${verify_script}" --user-home "${HOME}" --codex-config "${CODEX_HOME}/config.toml"
}

manage_install_state() {
  local mode="$1"
  shift
  local state_script="${KIT_ROOT}/scripts/manage_install.py"
  if [[ ! -f "${state_script}" ]]; then
    log "install state manager missing: ${state_script}"
    return 1
  fi
  local args=("${state_script}" "${mode}" --kit-root "${KIT_ROOT}" --codex-home "${CODEX_HOME}" --agents-home "${AGENTS_HOME}")
  if [[ "${REPO_ONLY}" == "1" ]]; then
    args+=(--repo-only)
  fi
  if [[ -n "${TARGET_REPO}" ]]; then
    args+=(--repo "${TARGET_REPO}")
  fi
  if [[ "${INSTALL_PILOTS}" == "1" ]]; then
    args+=(--with-pilots)
  fi
  if [[ "${INSTALL_REVERSE}" == "1" ]]; then
    args+=(--with-reverse)
  fi
  if [[ "${FORCE}" == "1" ]]; then
    args+=(--force)
  fi
  if [[ "${BACKUP}" == "1" ]]; then
    args+=(--backup)
  fi
  if [[ "$#" -gt 0 ]]; then
    args+=("$@")
  fi
  python3 "${args[@]}"
}

INSTALL_TRANSACTION_ACTIVE=0

abort_install_transaction_on_exit() {
  local status=$?
  local abort_status=0
  trap - EXIT
  if [[ "${INSTALL_TRANSACTION_ACTIVE}" == "1" ]]; then
    set +e
    manage_install_state abort
    abort_status=$?
    set -e
    if [[ "${status}" == "0" && "${abort_status}" != "0" ]]; then
      status="${abort_status}"
    fi
  fi
  exit "${status}"
}

copy_file() {
  local source="$1"
  local target="$2"
  local target_dir
  target_dir="$(dirname "${target}")"

  if [[ -e "${target}" ]]; then
    if cmp -s "${source}" "${target}"; then
      log "skip identical: ${target}"
      return 0
    fi

    if [[ "${FORCE}" == "1" ]]; then
      log "replace: ${target}"
    elif [[ "${BACKUP}" == "1" ]]; then
      log "backup and replace: ${target}"
    else
      log "conflict: ${target}"
      log "  use --backup to preserve the current file, or --force to replace it"
      return 1
    fi
  else
    log "create: ${target}"
  fi

  if [[ "${DRY_RUN}" == "1" ]]; then
    run mkdir -p "${target_dir}"
    run cp -p "${source}" "${target}"
  else
    manage_install_state copy-target --target "${target}"
  fi
}

check_file() {
  local source="$1"
  local target="$2"

  if [[ ! -e "${target}" ]] || cmp -s "${source}" "${target}"; then
    return 0
  fi

  if [[ "${FORCE}" == "1" || "${BACKUP}" == "1" ]]; then
    return 0
  fi

  log "conflict: ${target}"
  log "  use --backup to preserve the current file, or --force to replace it"
  return 1
}

copy_tree_files() {
  local source_root="$1"
  local target_root="$2"

  while IFS= read -r -d '' source; do
    local relative
    local target
    relative="${source#${source_root}/}"
    target="${target_root}/${relative}"

    if [[ "${relative}" == "docs/architecture.md" && ! -e "${target}" && -d "${target_root}/docs" ]]; then
      local architecture_match
      architecture_match="$(find "${target_root}/docs" -maxdepth 1 -type f -iname 'architecture.md' -print -quit)"
      if [[ -n "${architecture_match}" ]]; then
        log "conflict: ${architecture_match}"
        log "  existing architecture doc differs by case; update references manually instead of creating a duplicate"
        return 1
      fi
    fi

    copy_file "${source}" "${target}"
  done < <(find "${source_root}" -type f -print0 | sort -z)
}

check_tree_files() {
  local source_root="$1"
  local target_root="$2"

  while IFS= read -r -d '' source; do
    local relative
    local target
    relative="${source#${source_root}/}"
    target="${target_root}/${relative}"

    if [[ "${relative}" == "docs/architecture.md" && ! -e "${target}" && -d "${target_root}/docs" ]]; then
      local architecture_match
      architecture_match="$(find "${target_root}/docs" -maxdepth 1 -type f -iname 'architecture.md' -print -quit)"
      if [[ -n "${architecture_match}" ]]; then
        log "conflict: ${architecture_match}"
        log "  existing architecture doc differs by case; update references manually instead of creating a duplicate"
        return 1
      fi
    fi

    check_file "${source}" "${target}"
  done < <(find "${source_root}" -type f -print0 | sort -z)
}

install_global_agents() {
  copy_file "${KIT_ROOT}/global/AGENTS.md" "${CODEX_HOME}/AGENTS.md"
}

check_global_agents() {
  check_file "${KIT_ROOT}/global/AGENTS.md" "${CODEX_HOME}/AGENTS.md"
}

install_reverse_router_skill() {
  copy_file \
    "${KIT_ROOT}/reverse-skill-router/reverse-engineering/SKILL.md" \
    "${CODEX_HOME}/skills/reverse-engineering/SKILL.md"
}

check_reverse_router_skill() {
  check_file \
    "${KIT_ROOT}/reverse-skill-router/reverse-engineering/SKILL.md" \
    "${CODEX_HOME}/skills/reverse-engineering/SKILL.md"
}

install_reverse_pack() {
  copy_tree_files "${KIT_ROOT}/reverse-skill" "${CODEX_HOME}/reverse-skill"
}

install_reverse_lock() {
  copy_file \
    "${KIT_ROOT}/catalog/reverse-dependencies.lock.yaml" \
    "${CODEX_HOME}/catalog/reverse-dependencies.lock.yaml"
}

check_reverse_pack() {
  check_tree_files "${KIT_ROOT}/reverse-skill" "${CODEX_HOME}/reverse-skill"
}

check_reverse_lock() {
  check_file \
    "${KIT_ROOT}/catalog/reverse-dependencies.lock.yaml" \
    "${CODEX_HOME}/catalog/reverse-dependencies.lock.yaml"
}

selected_skill_names() {
  local stable_profile="${KIT_ROOT}/catalog/profiles/stable.txt"
  local pilot_profile="${KIT_ROOT}/catalog/profiles/pilot.txt"
  if [[ ! -f "${stable_profile}" ]]; then
    log "skill profile missing: ${stable_profile}"
    return 1
  fi
  if [[ "${INSTALL_PILOTS}" == "1" && ! -f "${pilot_profile}" ]]; then
    log "skill profile missing: ${pilot_profile}"
    return 1
  fi
  {
    sed '/^[[:space:]]*#/d; /^[[:space:]]*$/d' "${stable_profile}"
    if [[ "${INSTALL_PILOTS}" == "1" ]]; then
      sed '/^[[:space:]]*#/d; /^[[:space:]]*$/d' "${pilot_profile}"
    fi
  } | sort -u
}

install_skills() {
  local skills_target="${AGENTS_HOME}/skills"
  while IFS= read -r skill_name; do
    [[ -n "${skill_name}" ]] || continue
    local source_dir="${KIT_ROOT}/skills/${skill_name}"
    if [[ ! -d "${source_dir}" ]]; then
      log "profile skill missing: ${source_dir}"
      return 1
    fi
    copy_tree_files "${source_dir}" "${skills_target}/${skill_name}"
  done < <(selected_skill_names)
}

check_skills() {
  local skills_target="${AGENTS_HOME}/skills"
  while IFS= read -r skill_name; do
    [[ -n "${skill_name}" ]] || continue
    local source_dir="${KIT_ROOT}/skills/${skill_name}"
    if [[ ! -d "${source_dir}" ]]; then
      log "profile skill missing: ${source_dir}"
      return 1
    fi
    check_tree_files "${source_dir}" "${skills_target}/${skill_name}"
  done < <(selected_skill_names)
}

install_repo_template() {
  if [[ -z "${TARGET_REPO}" ]]; then
    return 0
  fi
  if [[ ! -d "${TARGET_REPO}" ]]; then
    log "target repo does not exist: ${TARGET_REPO}"
    return 1
  fi

  copy_tree_files "${KIT_ROOT}/repo-template" "${TARGET_REPO}"
}

check_repo_template() {
  if [[ -z "${TARGET_REPO}" ]]; then
    return 0
  fi
  if [[ ! -d "${TARGET_REPO}" ]]; then
    log "target repo does not exist: ${TARGET_REPO}"
    return 1
  fi

  check_tree_files "${KIT_ROOT}/repo-template" "${TARGET_REPO}"
}

while [[ "$#" -gt 0 ]]; do
  case "$1" in
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    --codex-home)
      CODEX_HOME="$2"
      shift 2
      ;;
    --agents-home)
      AGENTS_HOME="$2"
      shift 2
      ;;
    --repo)
      TARGET_REPO="$2"
      shift 2
      ;;
    --repo-only)
      REPO_ONLY=1
      shift
      ;;
    --with-pilots)
      INSTALL_PILOTS=1
      shift
      ;;
    --with-reverse)
      INSTALL_REVERSE=1
      shift
      ;;
    --with-reverse-core)
      INSTALL_REVERSE=1
      INSTALL_REVERSE_CORE=1
      shift
      ;;
    --start-reverse-services)
      START_REVERSE_SERVICES=1
      shift
      ;;
    --verify-reverse-ready)
      VERIFY_REVERSE_READY=1
      shift
      ;;
    --reverse-capabilities)
      REVERSE_BOOTSTRAP_CAPABILITIES="$2"
      shift 2
      ;;
    --prune-preview)
      PRUNE_PREVIEW=1
      shift
      ;;
    --prune)
      PRUNE=1
      shift
      ;;
    --uninstall)
      UNINSTALL=1
      shift
      ;;
    --rollback)
      ROLLBACK=1
      shift
      ;;
    --backup)
      BACKUP=1
      shift
      ;;
    --force)
      FORCE=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      log "unknown option: $1"
      usage
      exit 2
      ;;
  esac
done

if [[ "${BACKUP}" == "1" && "${FORCE}" == "1" ]]; then
  log "--backup and --force cannot be used together"
  exit 2
fi

management_modes=$((PRUNE_PREVIEW + PRUNE + UNINSTALL + ROLLBACK))
if [[ "${management_modes}" -gt 1 ]]; then
  log "--prune-preview, --prune, --uninstall, and --rollback are mutually exclusive"
  exit 2
fi

if [[ "${REPO_ONLY}" == "1" && -z "${TARGET_REPO}" ]]; then
  log "--repo-only requires --repo PATH"
  exit 2
fi

if [[ "${START_REVERSE_SERVICES}" == "1" && "${INSTALL_REVERSE_CORE}" != "1" ]]; then
  log "--start-reverse-services requires --with-reverse-core"
  exit 2
fi

if [[ "${management_modes}" -eq 1 ]]; then
  if [[ "${REPO_ONLY}" == "1" && -z "${TARGET_REPO}" ]]; then
    log "management mode with --repo-only requires --repo PATH"
    exit 2
  fi
  if [[ "${PRUNE_PREVIEW}" == "1" ]]; then
    manage_install_state prune-preview
  elif [[ "${PRUNE}" == "1" ]]; then
    manage_install_state prune
  elif [[ "${UNINSTALL}" == "1" ]]; then
    manage_install_state uninstall
  else
    manage_install_state rollback
  fi
  exit $?
fi

if [[ "${REPO_ONLY}" != "1" ]]; then
  selected_skill_names >/dev/null
  check_global_agents
  if [[ "${INSTALL_REVERSE}" == "1" ]]; then
    check_reverse_router_skill
    check_reverse_pack
    check_reverse_lock
  fi
  check_skills
fi
check_repo_template

if [[ "${DRY_RUN}" != "1" ]]; then
  trap abort_install_transaction_on_exit EXIT
  manage_install_state begin
  INSTALL_TRANSACTION_ACTIVE=1
fi

if [[ "${REPO_ONLY}" != "1" ]]; then
  install_global_agents
  if [[ "${INSTALL_REVERSE}" == "1" ]]; then
    install_reverse_router_skill
    install_reverse_pack
    install_reverse_lock
  fi
  install_skills
fi
install_repo_template

if [[ "${REPO_ONLY}" != "1" && "${INSTALL_REVERSE_CORE}" == "1" ]]; then
  run_reverse_bootstrap
fi

if [[ "${REPO_ONLY}" != "1" && ( "${VERIFY_REVERSE_READY}" == "1" || "${INSTALL_REVERSE_CORE}" == "1" ) ]]; then
  run_reverse_ready_verifier
fi

if [[ "${DRY_RUN}" != "1" ]]; then
  manage_install_state commit
  INSTALL_TRANSACTION_ACTIVE=0
  trap - EXIT
fi

log "Install plan complete."
if [[ "${DRY_RUN}" == "1" ]]; then
  log "No files were written because --dry-run was used."
fi
