#!/usr/bin/env python3
"""Validate repository layout and the packaged Skill without extra dependencies."""

from __future__ import annotations

import re
import zipfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SKILL_NAME = "blur-video-faces"
VERSION = "1.0.3"
SKILL_DIR = REPO_ROOT / "skills" / SKILL_NAME
ARCHIVE = REPO_ROOT / "dist" / f"{SKILL_NAME}-skill-v{VERSION}.zip"
TEXT_SUFFIXES = {".md", ".py", ".yaml", ".yml"}
FIXED_TIME = (2026, 1, 1, 0, 0, 0)
REQUIRED = {
    "SKILL.md",
    "agents/openai.yaml",
    "references/upstream.md",
    "scripts/run_face_blur.py",
}


def package_bytes(relative: str, data: bytes) -> bytes:
    """Mirror the builder's cross-platform text normalization."""
    if Path(relative).suffix.lower() in TEXT_SUFFIXES:
        text = data.decode("utf-8")
        return text.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")
    return data


def source_files() -> dict[str, bytes]:
    files: dict[str, bytes] = {}
    for path in SKILL_DIR.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(SKILL_DIR).as_posix()
        if "__pycache__" in path.parts or path.suffix == ".pyc":
            raise AssertionError(f"Generated Python artifact found: {relative}")
        files[relative] = path.read_bytes()
    return files


def validate_skill(files: dict[str, bytes]) -> None:
    missing = REQUIRED - set(files)
    if missing:
        raise AssertionError(f"Missing required files: {sorted(missing)}")

    skill_text = files["SKILL.md"].decode("utf-8")
    match = re.match(r"^---\n(?P<frontmatter>.*?)\n---\n", skill_text, re.S)
    if not match:
        raise AssertionError("SKILL.md frontmatter is invalid")
    frontmatter = match.group("frontmatter")
    if not re.search(r"^name:\s*blur-video-faces\s*$", frontmatter, re.M):
        raise AssertionError("SKILL.md name is invalid")
    if not re.search(r"^description:\s*.+$", frontmatter, re.M):
        raise AssertionError("SKILL.md description is missing")
    if "TODO" in skill_text:
        raise AssertionError("SKILL.md contains TODO text")

    openai_yaml = files["agents/openai.yaml"].decode("utf-8")
    if "$blur-video-faces" not in openai_yaml:
        raise AssertionError("agents/openai.yaml does not mention the Skill")

    launcher = files["scripts/run_face_blur.py"].decode("utf-8")
    compile(launcher, "run_face_blur.py", "exec")


def validate_archive(files: dict[str, bytes]) -> None:
    if not ARCHIVE.is_file():
        raise AssertionError(f"Archive is missing: {ARCHIVE}")
    with zipfile.ZipFile(ARCHIVE) as package:
        names = set(package.namelist())
        expected = {f"{SKILL_NAME}/{name}" for name in files}
        if names != expected:
            raise AssertionError(
                f"Archive entries differ: missing={sorted(expected - names)} "
                f"extra={sorted(names - expected)}"
            )
        for relative, source_bytes in files.items():
            archive_name = f"{SKILL_NAME}/{relative}"
            info = package.getinfo(archive_name)
            if info.create_system != 3:
                raise AssertionError(f"Archive platform metadata differs: {relative}")
            if info.compress_type != zipfile.ZIP_STORED:
                raise AssertionError(f"Archive compression is not deterministic: {relative}")
            if info.date_time != FIXED_TIME:
                raise AssertionError(f"Archive timestamp differs: {relative}")
            packaged = package.read(archive_name)
            if packaged != package_bytes(relative, source_bytes):
                raise AssertionError(f"Archive content differs: {relative}")


def validate_repository_docs() -> None:
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    for required_text in (
        "$CODEX_HOME/skills/blur-video-faces",
        "pinxihao-code/-skill",
        "$blur-video-faces",
    ):
        if required_text not in readme:
            raise AssertionError(f"README is missing: {required_text}")
    for path in ("install.ps1", "install.sh", "AGENTS.md", "LICENSE"):
        if not (REPO_ROOT / path).is_file():
            raise AssertionError(f"Repository file is missing: {path}")


def main() -> None:
    files = source_files()
    validate_skill(files)
    validate_archive(files)
    validate_repository_docs()
    print(f"Validated {SKILL_NAME}: {len(files)} files, package matches source")


if __name__ == "__main__":
    main()
