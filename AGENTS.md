# Agent Instructions

## Purpose

Treat `skills/blur-video-faces` as the distributable Skill. Keep repository-level installation, release, and contributor documentation outside that directory.

## Install

Prefer the standard Codex Skill Installer:

```text
repo: pinxihao-code/-skill
path: skills/blur-video-faces
ref: main
```

The installed directory must be:

```text
${CODEX_HOME:-~/.codex}/skills/blur-video-faces
```

On Windows without `CODEX_HOME`, use:

```text
%USERPROFILE%\.codex\skills\blur-video-faces
```

Tell the user the Skill becomes available on the next Agent turn.

## Use

1. Read `skills/blur-video-faces/SKILL.md` completely before processing video.
2. Run `scripts/run_face_blur.py --check`.
3. Preserve the input and use a distinct output path.
4. Use default Gaussian settings for ordinary requests.
5. Use the privacy preset only when the user asks for stronger anonymization or when small/fast faces are expected.
6. Compare input and output frames at 10%, 50%, and 90% of duration and across major cuts.
7. Never claim complete anonymization solely from a higher detection count.
8. If confidence `0.2` still misses a face, use a localized manual/tracked mask or report the limitation. Do not lower the full video to `0.1` or below.

## Validate changes

Run:

```text
python scripts/build_package.py
python scripts/validate_package.py
```

Do not commit videos, generated QA frames, virtual environments, model caches, or `__pycache__`.
