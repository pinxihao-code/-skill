#!/usr/bin/env python3
"""Build a deterministic ZIP containing only the distributable Skill."""

from __future__ import annotations

import zipfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SKILL_NAME = "blur-video-faces"
VERSION = "1.0.0"
SKILL_DIR = REPO_ROOT / "skills" / SKILL_NAME
DIST_DIR = REPO_ROOT / "dist"
ARCHIVE = DIST_DIR / f"{SKILL_NAME}-skill-v{VERSION}.zip"
FIXED_TIME = (2026, 1, 1, 0, 0, 0)


def included_files() -> list[Path]:
    return sorted(
        path
        for path in SKILL_DIR.rglob("*")
        if path.is_file()
        and "__pycache__" not in path.parts
        and path.suffix != ".pyc"
    )


def main() -> None:
    if not (SKILL_DIR / "SKILL.md").is_file():
        raise SystemExit(f"Missing {SKILL_DIR / 'SKILL.md'}")
    DIST_DIR.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(
        ARCHIVE,
        "w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=9,
    ) as package:
        for path in included_files():
            relative = path.relative_to(SKILL_DIR)
            archive_name = (Path(SKILL_NAME) / relative).as_posix()
            info = zipfile.ZipInfo(archive_name, FIXED_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            package.writestr(info, path.read_bytes())
    print(f"Built {ARCHIVE} ({ARCHIVE.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
