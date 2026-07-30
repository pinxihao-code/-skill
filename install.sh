#!/usr/bin/env bash
set -euo pipefail

skill_name="blur-video-faces"
version="1.0.0"
package_url="https://raw.githubusercontent.com/pinxihao-code/-skill/main/dist/blur-video-faces-skill-v${version}.zip"
repo_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
codex_root="${CODEX_HOME:-${HOME}/.codex}"
destination_root="${1:-${codex_root}/skills}"
destination="${destination_root}/${skill_name}"

if [[ -e "${destination}" ]]; then
  printf 'Skill already exists: %s\n' "${destination}" >&2
  exit 1
fi

mkdir -p "${destination_root}"
staging="${destination_root}/.${skill_name}.installing-$$"
download_root="$(mktemp -d)"

cleanup() {
  rm -rf -- "${staging}"
  rm -rf -- "${download_root}"
}
trap cleanup EXIT

mkdir -p "${staging}"
local_source="${repo_dir}/skills/${skill_name}"

if [[ -f "${local_source}/SKILL.md" ]]; then
  cp -R "${local_source}/." "${staging}/"
else
  archive="${download_root}/skill.zip"
  extract="${download_root}/extract"
  if command -v curl >/dev/null 2>&1; then
    curl -fsSL "${package_url}" -o "${archive}"
  elif command -v wget >/dev/null 2>&1; then
    wget -q "${package_url}" -O "${archive}"
  else
    printf 'curl or wget is required\n' >&2
    exit 1
  fi
  mkdir -p "${extract}"
  unzip -q "${archive}" -d "${extract}"
  if [[ ! -f "${extract}/${skill_name}/SKILL.md" ]]; then
    printf 'Downloaded package is invalid\n' >&2
    exit 1
  fi
  cp -R "${extract}/${skill_name}/." "${staging}/"
fi

if [[ ! -f "${staging}/SKILL.md" ]]; then
  printf 'Staged Skill is invalid: SKILL.md is missing\n' >&2
  exit 1
fi

mv "${staging}" "${destination}"
printf 'Installed %s to %s\n' "${skill_name}" "${destination}"
printf 'The Skill will be available on the next Agent turn.\n'
