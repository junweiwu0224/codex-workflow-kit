from pathlib import Path


def test_decode_sh_uses_portable_manifest_package_extraction() -> None:
    script = Path("reverse-skill/skills/apk-reverse/scripts/decode.sh").read_text(encoding="utf-8")

    assert "grep -oP" not in script
    assert "sed -n 's/.*package=\"\\([^\"]*\\)\".*/\\1/p'" in script
