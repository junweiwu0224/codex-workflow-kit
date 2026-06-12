#!/usr/bin/env python3
"""Build a versioned release archive for the Codex workflow kit."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import io
import os
import shutil
import stat
import sys
import tarfile
import tempfile
from pathlib import Path


EXCLUDE_DIRS = {
    ".git",
    "__pycache__",
    ".pytest_cache",
    "releases",
}
EXCLUDE_SUFFIXES = {
    ".pyc",
}
EXCLUDE_FILES = {
    ".DS_Store",
}
MANIFEST_PATH = "MANIFEST.sha256"


def _load_verify_toolkit(root: Path):
    script = root / "scripts/verify_toolkit.py"
    spec = importlib.util.spec_from_file_location("verify_toolkit_release", script)
    if spec is None or spec.loader is None:
        raise RuntimeError("Could not load scripts/verify_toolkit.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    old_dont_write_bytecode = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        spec.loader.exec_module(module)
    finally:
        sys.dont_write_bytecode = old_dont_write_bytecode
    return module


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _hash_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _iter_package_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for current_root, dir_names, file_names in os.walk(root):
        dir_names[:] = sorted(name for name in dir_names if name not in EXCLUDE_DIRS)
        current = Path(current_root)
        for file_name in sorted(file_names):
            if file_name in EXCLUDE_FILES:
                continue
            path = current / file_name
            relative = path.relative_to(root).as_posix()
            if any(relative.endswith(suffix) for suffix in EXCLUDE_SUFFIXES):
                continue
            if relative == MANIFEST_PATH:
                continue
            files.append(path)
    return files


def build_manifest(root: Path) -> str:
    lines = []
    for path in _iter_package_files(root):
        relative = path.relative_to(root).as_posix()
        lines.append(f"{_hash_file(path)}  {relative}")
    return "\n".join(lines) + "\n"


def write_manifest(root: Path) -> Path:
    manifest_path = root / MANIFEST_PATH
    manifest_path.write_text(build_manifest(root), encoding="utf-8")
    return manifest_path


def _copy_package(root: Path, staging_root: Path) -> Path:
    package_root = staging_root / root.name
    package_root.mkdir(parents=True, exist_ok=True)
    for path in _iter_package_files(root):
        relative = path.relative_to(root)
        target = package_root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
    shutil.copy2(root / MANIFEST_PATH, package_root / MANIFEST_PATH)
    return package_root


def _normalize_tar_info(info: tarfile.TarInfo) -> tarfile.TarInfo:
    info.uid = 0
    info.gid = 0
    info.uname = ""
    info.gname = ""
    info.mtime = 0
    if info.isfile():
        executable = bool(info.mode & stat.S_IXUSR)
        info.mode = 0o755 if executable else 0o644
    elif info.isdir():
        info.mode = 0o755
    return info


def build_archive(root: Path, output_dir: Path) -> Path:
    version = (root / "VERSION").read_text(encoding="utf-8").strip()
    output_dir.mkdir(parents=True, exist_ok=True)
    archive_path = output_dir / f"{root.name}-{version}.tar.gz"

    with tempfile.TemporaryDirectory() as temp_name:
        staging_root = Path(temp_name)
        package_root = _copy_package(root, staging_root)
        buffer = io.BytesIO()
        with tarfile.open(fileobj=buffer, mode="w:gz", format=tarfile.PAX_FORMAT) as tar:
            tar.add(package_root, arcname=package_root.name, filter=_normalize_tar_info)
        archive_path.write_bytes(buffer.getvalue())

    checksum_path = archive_path.with_suffix(archive_path.suffix + ".sha256")
    checksum_path.write_text(f"{_hash_file(archive_path)}  {archive_path.name}\n", encoding="utf-8")
    return archive_path


def verify_archive(archive_path: Path) -> None:
    checksum_path = archive_path.with_suffix(archive_path.suffix + ".sha256")
    expected = checksum_path.read_text(encoding="utf-8").split()[0]
    actual = _hash_file(archive_path)
    if actual != expected:
        raise RuntimeError(f"Archive checksum mismatch: expected {expected}, got {actual}")

    with tarfile.open(archive_path, mode="r:gz") as tar:
        members = tar.getmembers()
        if not members:
            raise RuntimeError("Archive is empty.")
        top_levels = {member.name.split("/", 1)[0] for member in members}
        if top_levels != {"codex-workflow-kit"}:
            raise RuntimeError(f"Archive top level must be codex-workflow-kit, got {sorted(top_levels)}")

        manifest_member = tar.getmember("codex-workflow-kit/MANIFEST.sha256")
        manifest_file = tar.extractfile(manifest_member)
        if manifest_file is None:
            raise RuntimeError("Archive manifest could not be read.")
        manifest_lines = manifest_file.read().decode("utf-8").splitlines()
        member_by_name = {member.name: member for member in members if member.isfile()}
        for line in manifest_lines:
            digest, relative = line.split(maxsplit=1)
            member_name = f"codex-workflow-kit/{relative}"
            member = member_by_name.get(member_name)
            if member is None:
                raise RuntimeError(f"Manifest file missing from archive: {relative}")
            extracted = tar.extractfile(member)
            if extracted is None:
                raise RuntimeError(f"Could not read archive member: {relative}")
            if _hash_bytes(extracted.read()) != digest:
                raise RuntimeError(f"Manifest checksum mismatch in archive: {relative}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build a Codex workflow kit release archive.")
    parser.add_argument("--root", default=".", help="Toolkit root. Default: current directory.")
    parser.add_argument("--output-dir", default="releases", help="Release output directory.")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    output_dir = (root / args.output_dir).resolve()

    write_manifest(root)

    verify_toolkit = _load_verify_toolkit(root)
    after_report = verify_toolkit.build_report(root)
    if not after_report["ok"]:
        verify_toolkit._print_report(after_report)
        return 1

    archive_path = build_archive(root, output_dir)
    verify_archive(archive_path)

    print(f"Release archive: {archive_path}")
    print(f"Checksum file: {archive_path.with_suffix(archive_path.suffix + '.sha256')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
