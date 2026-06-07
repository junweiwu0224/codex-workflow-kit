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
  --backup               Back up conflicting existing files before replacing.
  --force                Replace conflicting existing files without backups.
  -h, --help             Show this help.

Default behavior is non-destructive: existing different files are treated as
conflicts unless --backup or --force is provided.
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
      local backup_path
      backup_path="${target}.bak-$(date +%Y%m%d%H%M%S)"
      log "backup: ${target} -> ${backup_path}"
      run cp -p "${target}" "${backup_path}"
    else
      log "conflict: ${target}"
      log "  use --backup to preserve the current file, or --force to replace it"
      return 1
    fi
  else
    log "create: ${target}"
  fi

  run mkdir -p "${target_dir}"
  run cp -p "${source}" "${target}"
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

install_skills() {
  local skills_target="${AGENTS_HOME}/skills"
  while IFS= read -r -d '' source_dir; do
    local skill_name
    skill_name="$(basename "${source_dir}")"
    copy_tree_files "${source_dir}" "${skills_target}/${skill_name}"
  done < <(find "${KIT_ROOT}/skills" -mindepth 1 -maxdepth 1 -type d -print0 | sort -z)
}

check_skills() {
  local skills_target="${AGENTS_HOME}/skills"
  while IFS= read -r -d '' source_dir; do
    local skill_name
    skill_name="$(basename "${source_dir}")"
    check_tree_files "${source_dir}" "${skills_target}/${skill_name}"
  done < <(find "${KIT_ROOT}/skills" -mindepth 1 -maxdepth 1 -type d -print0 | sort -z)
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

if [[ "${REPO_ONLY}" == "1" && -z "${TARGET_REPO}" ]]; then
  log "--repo-only requires --repo PATH"
  exit 2
fi

if [[ "${REPO_ONLY}" != "1" ]]; then
  check_global_agents
  check_skills
fi
check_repo_template

if [[ "${REPO_ONLY}" != "1" ]]; then
  install_global_agents
  install_skills
fi
install_repo_template

log "Install plan complete."
if [[ "${DRY_RUN}" == "1" ]]; then
  log "No files were written because --dry-run was used."
fi
