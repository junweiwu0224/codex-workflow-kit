import os
import hashlib
import io
import subprocess
import tarfile
from pathlib import Path

import pytest

from scripts.build_release import build_archive, require_clean_worktree, verify_archive, write_manifest


def test_release_archive_is_byte_reproducible_and_has_normalized_gzip_header(tmp_path):
    root = tmp_path / "codex-workflow-kit"
    root.mkdir()
    (root / "VERSION").write_text("4.2.0\n", encoding="utf-8")
    script = root / "scripts" / "run.sh"
    script.parent.mkdir()
    script.write_text("#!/bin/sh\nprintf 'ok\\n'\n", encoding="utf-8")
    script.chmod(0o755)
    (root / "payload.txt").write_text("release payload\n", encoding="utf-8")
    long_path = root / "docs" / (("long-name-" * 14) + ".md")
    long_path.parent.mkdir()
    long_path.write_text("deterministic PAX path\n", encoding="utf-8")
    write_manifest(root)

    first = build_archive(root, tmp_path / "first")
    os.utime(script, (2_000_000_000, 2_000_000_000))
    second = build_archive(root, tmp_path / "second")

    assert first.read_bytes() == second.read_bytes()
    header = first.read_bytes()[:10]
    assert header[:3] == b"\x1f\x8b\x08"
    assert header[3] & 0x08 == 0  # No source filename in the gzip header.
    assert header[4:8] == b"\x00\x00\x00\x00"
    verify_archive(first)
    verify_archive(second)
    with pytest.raises(RuntimeError, match="expected source manifest"):
        verify_archive(first, expected_manifest="forged\n")


def test_clean_worktree_gate_rejects_tracked_and_untracked_changes(tmp_path):
    root = tmp_path / "repository"
    root.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.name", "Release Test"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.email", "release-test@example.invalid"], cwd=root, check=True)
    tracked = root / "tracked.txt"
    tracked.write_text("clean\n", encoding="utf-8")
    subprocess.run(["git", "add", "tracked.txt"], cwd=root, check=True)
    subprocess.run(["git", "commit", "-qm", "initial"], cwd=root, check=True)

    require_clean_worktree(root, "test")
    tracked.write_text("dirty\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="clean worktree"):
        require_clean_worktree(root, "test")

    tracked.write_text("clean\n", encoding="utf-8")
    (root / "untracked.txt").write_text("untracked\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="clean worktree"):
        require_clean_worktree(root, "test")


def test_clean_worktree_gate_fails_closed_outside_git(tmp_path):
    with pytest.raises(RuntimeError, match="Cannot verify clean worktree"):
        require_clean_worktree(tmp_path, "test")


def test_clean_worktree_rejects_ignored_file_that_would_be_packaged(tmp_path):
    root = tmp_path / "repository"
    root.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.name", "Release Test"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.email", "release-test@example.invalid"], cwd=root, check=True)
    (root / "tracked.txt").write_text("clean\n", encoding="utf-8")
    subprocess.run(["git", "add", "tracked.txt"], cwd=root, check=True)
    subprocess.run(["git", "commit", "-qm", "initial"], cwd=root, check=True)
    (root / ".git/info/exclude").write_text("secret.env\n__pycache__/\n", encoding="utf-8")
    (root / "secret.env").write_text("credential material\n", encoding="utf-8")
    cache = root / "__pycache__/ignored.pyc"
    cache.parent.mkdir()
    cache.write_bytes(b"ignored cache")

    assert subprocess.check_output(["git", "status", "--porcelain"], cwd=root) == b""
    with pytest.raises(RuntimeError, match="hidden by Git ignore.*secret.env"):
        require_clean_worktree(root, "test")


def test_clean_worktree_rejects_assume_unchanged_content_drift(tmp_path):
    root = tmp_path / "repository"
    root.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.name", "Release Test"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.email", "release-test@example.invalid"], cwd=root, check=True)
    tracked = root / "payload.txt"
    tracked.write_text("committed\n", encoding="utf-8")
    subprocess.run(["git", "add", "payload.txt"], cwd=root, check=True)
    subprocess.run(["git", "commit", "-qm", "initial"], cwd=root, check=True)
    subprocess.run(["git", "update-index", "--assume-unchanged", "payload.txt"], cwd=root, check=True)
    tracked.write_text("hidden drift\n", encoding="utf-8")

    assert subprocess.check_output(["git", "status", "--porcelain"], cwd=root) == b""
    with pytest.raises(RuntimeError, match="assume-unchanged/skip-worktree"):
        require_clean_worktree(root, "test")


def test_release_source_rejects_symlink_escape(tmp_path):
    root = tmp_path / "codex-workflow-kit"
    root.mkdir()
    (root / "VERSION").write_text("4.2.0\n", encoding="utf-8")
    outside = tmp_path / "outside.txt"
    outside.write_text("private\n", encoding="utf-8")
    try:
        (root / "escaped.txt").symlink_to(outside)
    except OSError as exc:  # pragma: no cover - platform policy may forbid symlinks
        pytest.skip(f"symlinks unavailable: {exc}")

    with pytest.raises(RuntimeError, match="symlink"):
        write_manifest(root)


def test_archive_rejects_unmanifested_payload(tmp_path):
    archive = tmp_path / "codex-workflow-kit-4.2.0.tar.gz"
    manifest = hashlib.sha256(b"4.2.0\n").hexdigest().encode() + b"  VERSION\n"
    with tarfile.open(archive, mode="w:gz") as handle:
        for name, payload in (
            ("codex-workflow-kit/MANIFEST.sha256", manifest),
            ("codex-workflow-kit/VERSION", b"4.2.0\n"),
            ("codex-workflow-kit/untracked.sh", b"echo unsafe\n"),
        ):
            info = tarfile.TarInfo(name)
            info.size = len(payload)
            handle.addfile(info, io.BytesIO(payload))
    checksum = hashlib.sha256(archive.read_bytes()).hexdigest()
    archive.with_suffix(archive.suffix + ".sha256").write_text(
        f"{checksum}  {archive.name}\n", encoding="utf-8"
    )

    with pytest.raises(RuntimeError, match="not covered"):
        verify_archive(archive)


def test_archive_rejects_non_normalized_member_metadata(tmp_path):
    archive = tmp_path / "codex-workflow-kit-4.2.0.tar.gz"
    payload = b"4.2.0\n"
    manifest = hashlib.sha256(payload).hexdigest().encode() + b"  VERSION\n"
    with tarfile.open(archive, mode="w:gz") as handle:
        manifest_info = tarfile.TarInfo("codex-workflow-kit/MANIFEST.sha256")
        manifest_info.size = len(manifest)
        manifest_info.mode = 0o644
        handle.addfile(manifest_info, io.BytesIO(manifest))
        payload_info = tarfile.TarInfo("codex-workflow-kit/VERSION")
        payload_info.size = len(payload)
        payload_info.mode = 0o4755
        payload_info.uid = 12345
        payload_info.gid = 12345
        handle.addfile(payload_info, io.BytesIO(payload))
    checksum = hashlib.sha256(archive.read_bytes()).hexdigest()
    archive.with_suffix(archive.suffix + ".sha256").write_text(
        f"{checksum}  {archive.name}\n", encoding="utf-8"
    )

    with pytest.raises(RuntimeError, match="metadata is not normalized"):
        verify_archive(archive, expected_manifest=manifest.decode())
