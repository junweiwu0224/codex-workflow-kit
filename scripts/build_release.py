#!/usr/bin/env python3
"""Build a versioned release archive for the Codex workflow kit."""
from __future__ import annotations

import argparse
import gzip
import hashlib
import importlib.util
import io
import os
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path
from pathlib import PurePosixPath


EXCLUDE_DIRS = {
    ".git",
    "__pycache__",
    ".pytest_cache",
    "releases",
}
EXCLUDE_SUFFIXES = {
    ".pyc",
    ".bak",
}
EXCLUDE_FILES = {
    ".DS_Store",
}
EXCLUDE_PREFIXES = (
    "reverse-skill/burp-mcp-full/build/libs/",
    "reverse-skill/reports/",
)
MANIFEST_PATH = "MANIFEST.sha256"


def _relative_is_excluded(relative: str) -> bool:
    path = PurePosixPath(relative)
    if any(part in EXCLUDE_DIRS for part in path.parts):
        return True
    if path.name in EXCLUDE_FILES:
        return True
    if any(relative.startswith(prefix) for prefix in EXCLUDE_PREFIXES):
        return True
    if any(relative.endswith(suffix) for suffix in EXCLUDE_SUFFIXES):
        return True
    return ".bak-" in relative or relative == MANIFEST_PATH


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
        current = Path(current_root)
        retained_dirs: list[str] = []
        for name in sorted(dir_names):
            if name in EXCLUDE_DIRS:
                continue
            path = current / name
            if path.is_symlink():
                raise RuntimeError(f"Release source must not contain symlink directories: {path.relative_to(root)}")
            retained_dirs.append(name)
        dir_names[:] = retained_dirs
        for file_name in sorted(file_names):
            if file_name in EXCLUDE_FILES:
                continue
            path = current / file_name
            relative = path.relative_to(root).as_posix()
            if _relative_is_excluded(relative):
                continue
            if path.is_symlink():
                raise RuntimeError(f"Release source must not contain symlink files: {relative}")
            if not path.is_file():
                raise RuntimeError(f"Release source contains a non-regular file: {relative}")
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
    info.pax_headers = {}
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
        tar_buffer = io.BytesIO()
        with tarfile.open(fileobj=tar_buffer, mode="w", format=tarfile.PAX_FORMAT) as tar:
            tar.add(package_root, arcname=package_root.name, filter=_normalize_tar_info)
        gzip_buffer = io.BytesIO()
        with gzip.GzipFile(filename="", mode="wb", fileobj=gzip_buffer, mtime=0) as compressed:
            compressed.write(tar_buffer.getvalue())
        archive_path.write_bytes(gzip_buffer.getvalue())

    checksum_path = archive_path.with_suffix(archive_path.suffix + ".sha256")
    checksum_path.write_text(f"{_hash_file(archive_path)}  {archive_path.name}\n", encoding="utf-8")
    return archive_path


def require_clean_worktree(root: Path, phase: str) -> None:
    """Fail closed when a release input is not a clean Git worktree."""
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain", "--untracked-files=all"],
            cwd=root,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
    except OSError as exc:
        raise RuntimeError(f"Cannot verify clean worktree during {phase}: {exc}") from exc
    if result.returncode != 0:
        detail = result.stderr.strip() or "not a Git worktree"
        raise RuntimeError(f"Cannot verify clean worktree during {phase}: {detail}")
    if result.stdout.strip():
        raise RuntimeError(f"Release requires a clean worktree during {phase}.")
    try:
        ignored = subprocess.run(
            ["git", "ls-files", "-z", "--others", "--ignored", "--exclude-standard"],
            cwd=root,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
    except OSError as exc:
        raise RuntimeError(f"Cannot inspect ignored release inputs during {phase}: {exc}") from exc
    if ignored.returncode != 0:
        detail = ignored.stderr.decode("utf-8", errors="replace").strip() or "git ls-files failed"
        raise RuntimeError(f"Cannot inspect ignored release inputs during {phase}: {detail}")
    hidden_inputs = sorted(
        value.decode("utf-8", errors="surrogateescape")
        for value in ignored.stdout.split(b"\0")
        if value and not _relative_is_excluded(value.decode("utf-8", errors="surrogateescape"))
    )
    if hidden_inputs:
        raise RuntimeError(
            f"Release input is hidden by Git ignore rules during {phase}: {hidden_inputs[0]}"
        )

    def git_output(*arguments: str, binary: bool = False) -> str | bytes:
        completed = subprocess.run(
            ["git", *arguments],
            cwd=root,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if completed.returncode != 0:
            detail = completed.stderr.decode("utf-8", errors="replace").strip() or "git command failed"
            raise RuntimeError(f"Cannot bind release inputs to HEAD during {phase}: {detail}")
        return completed.stdout if binary else completed.stdout.decode("utf-8").strip()

    if git_output("rev-parse", "HEAD^{tree}") != git_output("write-tree"):
        raise RuntimeError(f"Release index does not match HEAD during {phase}.")

    tagged = git_output("ls-files", "-v", "-z", binary=True)
    assert isinstance(tagged, bytes)
    unsafe_flags = [entry for entry in tagged.split(b"\0") if entry and entry[:1] != b"H"]
    if unsafe_flags:
        path = unsafe_flags[0][2:].decode("utf-8", errors="surrogateescape")
        raise RuntimeError(f"Release tracked file has assume-unchanged/skip-worktree state during {phase}: {path}")

    staged = git_output("ls-files", "--stage", "-z", binary=True)
    assert isinstance(staged, bytes)
    index: dict[str, tuple[str, str]] = {}
    for raw in staged.split(b"\0"):
        if not raw:
            continue
        metadata, separator, raw_path = raw.partition(b"\t")
        fields = metadata.decode("ascii").split()
        if not separator or len(fields) != 3 or fields[2] != "0":
            raise RuntimeError(f"Release index contains an unsupported entry during {phase}.")
        mode, object_id, _stage = fields
        relative = raw_path.decode("utf-8", errors="surrogateescape")
        if not _relative_is_excluded(relative):
            index[relative] = (mode, object_id)

    packaged = {
        path.relative_to(root).as_posix(): path
        for path in _iter_package_files(root)
    }
    if set(packaged) != set(index):
        difference = sorted(set(packaged) ^ set(index))
        raise RuntimeError(f"Release filesystem does not match tracked package inputs during {phase}: {difference[0]}")
    for relative, path in packaged.items():
        mode, expected_object = index[relative]
        if mode not in {"100644", "100755"}:
            raise RuntimeError(f"Release contains an unsupported tracked mode during {phase}: {relative} ({mode})")
        actual_mode = "100755" if path.stat().st_mode & stat.S_IXUSR else "100644"
        if actual_mode != mode:
            raise RuntimeError(f"Release executable mode differs from HEAD during {phase}: {relative}")
        actual_object = git_output("hash-object", "--no-filters", "--", relative)
        if actual_object != expected_object:
            raise RuntimeError(f"Release file bytes differ from HEAD during {phase}: {relative}")


def verify_archive(archive_path: Path, *, expected_manifest: str | None = None) -> None:
    checksum_path = archive_path.with_suffix(archive_path.suffix + ".sha256")
    checksum_parts = checksum_path.read_text(encoding="utf-8").split()
    if len(checksum_parts) != 2 or checksum_parts[1] != archive_path.name:
        raise RuntimeError("Archive checksum file must contain exactly '<sha256> <archive-name>'.")
    expected = checksum_parts[0]
    if len(expected) != 64 or any(character not in "0123456789abcdef" for character in expected):
        raise RuntimeError("Archive checksum file contains an invalid SHA-256 digest.")
    actual = _hash_file(archive_path)
    if actual != expected:
        raise RuntimeError(f"Archive checksum mismatch: expected {expected}, got {actual}")

    with tarfile.open(archive_path, mode="r:gz") as tar:
        members = tar.getmembers()
        if not members:
            raise RuntimeError("Archive is empty.")
        names: set[str] = set()
        for member in members:
            candidate = PurePosixPath(member.name)
            if candidate.is_absolute() or ".." in candidate.parts or not candidate.parts:
                raise RuntimeError(f"Archive contains an unsafe path: {member.name}")
            if member.name in names:
                raise RuntimeError(f"Archive contains a duplicate member: {member.name}")
            names.add(member.name)
            if not (member.isdir() or member.isfile()):
                raise RuntimeError(f"Archive contains an unsupported member type: {member.name}")
            expected_mode = 0o755 if member.isdir() or (member.isfile() and member.mode & 0o111) else 0o644
            pax_path = member.name + "/" if member.isdir() else member.name
            allowed_pax = not member.pax_headers or member.pax_headers == {"path": pax_path}
            if (
                member.uid != 0
                or member.gid != 0
                or member.uname != ""
                or member.gname != ""
                or member.mtime != 0
                or member.mode != expected_mode
                or not allowed_pax
            ):
                raise RuntimeError(f"Archive member metadata is not normalized: {member.name}")
        top_levels = {member.name.split("/", 1)[0] for member in members}
        if top_levels != {"codex-workflow-kit"}:
            raise RuntimeError(f"Archive top level must be codex-workflow-kit, got {sorted(top_levels)}")

        manifest_member = tar.getmember("codex-workflow-kit/MANIFEST.sha256")
        manifest_file = tar.extractfile(manifest_member)
        if manifest_file is None:
            raise RuntimeError("Archive manifest could not be read.")
        manifest_text = manifest_file.read().decode("utf-8")
        if expected_manifest is not None and manifest_text != expected_manifest:
            raise RuntimeError("Archive manifest does not match the expected source manifest.")
        manifest_lines = manifest_text.splitlines()
        member_by_name = {member.name: member for member in members if member.isfile()}
        expected_members: set[str] = set()
        for line in manifest_lines:
            parts = line.split(maxsplit=1)
            if len(parts) != 2:
                raise RuntimeError("Archive manifest contains a malformed line.")
            digest, relative = parts
            relative_path = PurePosixPath(relative)
            if (
                len(digest) != 64
                or any(character not in "0123456789abcdef" for character in digest)
                or relative_path.is_absolute()
                or ".." in relative_path.parts
                or relative == MANIFEST_PATH
            ):
                raise RuntimeError(f"Archive manifest contains an unsafe entry: {relative}")
            member_name = f"codex-workflow-kit/{relative}"
            if member_name in expected_members:
                raise RuntimeError(f"Archive manifest contains a duplicate entry: {relative}")
            expected_members.add(member_name)
            member = member_by_name.get(member_name)
            if member is None:
                raise RuntimeError(f"Manifest file missing from archive: {relative}")
            extracted = tar.extractfile(member)
            if extracted is None:
                raise RuntimeError(f"Could not read archive member: {relative}")
            if _hash_bytes(extracted.read()) != digest:
                raise RuntimeError(f"Manifest checksum mismatch in archive: {relative}")
        actual_members = set(member_by_name) - {"codex-workflow-kit/MANIFEST.sha256"}
        unexpected = sorted(actual_members - expected_members)
        if unexpected:
            raise RuntimeError(f"Archive contains files not covered by its manifest: {unexpected[0]}")
        missing = sorted(expected_members - actual_members)
        if missing:
            raise RuntimeError(f"Archive manifest references missing files: {missing[0]}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build a Codex workflow kit release archive.")
    parser.add_argument("--root", default=".", help="Toolkit root. Default: current directory.")
    parser.add_argument("--output-dir", default="releases", help="Release output directory.")
    parser.add_argument(
        "--require-clean",
        action="store_true",
        help="Fail unless the Git worktree is clean before and after manifest refresh.",
    )
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    output_dir = (root / args.output_dir).resolve()

    try:
        if args.require_clean:
            require_clean_worktree(root, "preflight")

        write_manifest(root)

        if args.require_clean:
            require_clean_worktree(root, "manifest refresh")
    except RuntimeError as exc:
        parser.error(str(exc))

    verify_toolkit = _load_verify_toolkit(root)
    after_report = verify_toolkit.build_report(root)
    if not after_report["ok"]:
        verify_toolkit._print_report(after_report)
        return 1

    if args.require_clean:
        try:
            require_clean_worktree(root, "archive build")
        except RuntimeError as exc:
            parser.error(str(exc))

    archive_path = build_archive(root, output_dir)
    verify_archive(archive_path)

    print(f"Release archive: {archive_path}")
    print(f"Checksum file: {archive_path.with_suffix(archive_path.suffix + '.sha256')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
