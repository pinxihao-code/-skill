#!/usr/bin/env python3
"""Cross-platform, pinned launcher for vorojar/face-blur."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import NamedTuple


UPSTREAM_REPO = "https://github.com/vorojar/face-blur"
UPSTREAM_COMMIT = "0c83fdce0ee206a0043cf00173a82f52ec1af81b"
RAW_BASE_URL = (
    "https://raw.githubusercontent.com/vorojar/face-blur/"
    f"{UPSTREAM_COMMIT}"
)
UPSTREAM_FILES = {
    "face_blur.py": "cb2ad472e425e922d1cfb043c2c248d5d9c429644f54dd2b768ddcae8f1b88b2",
    "face_landmarker.task": "64184e229b263107bc2b804c6625db1341ff2bb731874b0bcc2fe6544e0bc9ff",
    "blaze_face_short_range.tflite": "b4578f35940bf5a1a655214a1cce5cab13eba73c1297cd78e1a04c2380b0152f",
}
PYTHON_REQUIREMENTS = (
    "mediapipe==0.10.35",
    "opencv-contrib-python==4.14.0.94",
)
DEPS_MARKER = "deps-v2"
MIN_RUNTIME = (3, 10)
MAX_RUNTIME = (3, 12)


def configure_utf8_console() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure:
            reconfigure(encoding="utf-8", errors="replace")


configure_utf8_console()


class ToolError(RuntimeError):
    """Expected user-facing failure."""


class PythonRuntime(NamedTuple):
    executable: Path
    version: tuple[int, int, int]


def default_cache_dir() -> Path:
    override = os.environ.get("CODEX_FACE_BLUR_HOME")
    if override:
        return Path(override).expanduser().resolve()
    if os.name == "nt":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        return base / "Codex" / "blur-video-faces"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Caches" / "Codex" / "blur-video-faces"
    base = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache"))
    return base / "codex" / "blur-video-faces"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def source_dir(cache_dir: Path) -> Path:
    return cache_dir / "upstream" / UPSTREAM_COMMIT


def source_status(cache_dir: Path) -> str:
    root = source_dir(cache_dir)
    present = 0
    for name, expected_hash in UPSTREAM_FILES.items():
        path = root / name
        if not path.exists():
            continue
        present += 1
        if sha256_file(path) != expected_hash:
            return "corrupt"
    return "ready" if present == len(UPSTREAM_FILES) else "not prepared"


def download_verified(url: str, destination: Path, expected_hash: str) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_name(destination.name + ".part")
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "Codex-blur-video-faces/1.0"},
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            with partial.open("wb") as target:
                shutil.copyfileobj(response, target)
    except (OSError, urllib.error.URLError) as exc:
        if partial.exists():
            partial.unlink()
        raise ToolError(f"下载失败: {url}\n{exc}") from exc

    actual_hash = sha256_file(partial)
    if actual_hash != expected_hash:
        partial.unlink()
        raise ToolError(
            f"上游文件校验失败: {destination.name}\n"
            f"expected={expected_hash}\nactual={actual_hash}"
        )
    os.replace(partial, destination)


def ensure_upstream(cache_dir: Path) -> Path:
    root = source_dir(cache_dir)
    for name, expected_hash in UPSTREAM_FILES.items():
        destination = root / name
        if destination.exists() and sha256_file(destination) == expected_hash:
            continue
        print(f"下载固定上游文件: {name}", flush=True)
        download_verified(f"{RAW_BASE_URL}/{name}", destination, expected_hash)
    return root


def venv_dir(cache_dir: Path, runtime: PythonRuntime) -> Path:
    version = f"py{runtime.version[0]}{runtime.version[1]}"
    return cache_dir / f"venv-{version}-{DEPS_MARKER}"


def venv_python(cache_dir: Path, runtime: PythonRuntime) -> Path:
    root = venv_dir(cache_dir, runtime)
    return root / ("Scripts/python.exe" if os.name == "nt" else "bin/python3")


def marker_path(cache_dir: Path, runtime: PythonRuntime) -> Path:
    return venv_dir(cache_dir, runtime) / ".blur-video-faces-ready"


def run_quiet(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )


def inspect_python(path: Path) -> PythonRuntime | None:
    if not path.is_file():
        return None
    result = run_quiet(
        [
            str(path),
            "-c",
            (
                "import json,sys;"
                "print(json.dumps({'exe':sys.executable,'v':list(sys.version_info[:3])}))"
            ),
        ]
    )
    if result.returncode != 0:
        return None
    try:
        info = json.loads(result.stdout.strip())
        version = tuple(int(part) for part in info["v"])
        executable = Path(info["exe"]).resolve()
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        return None
    if not (MIN_RUNTIME <= version[:2] <= MAX_RUNTIME):
        return None
    return PythonRuntime(executable, version)


def compatible_python() -> PythonRuntime | None:
    candidates: list[Path] = [Path(sys.executable)]
    for executable_name in ("python3.12", "python3.11", "python3.10"):
        found = find_program(executable_name)
        if found:
            candidates.append(Path(found))

    if os.name == "nt" and find_program("py"):
        for version in ("3.12", "3.11", "3.10"):
            result = run_quiet(
                [
                    "py",
                    f"-{version}",
                    "-c",
                    "import sys; print(sys.executable)",
                ]
            )
            if result.returncode == 0 and result.stdout.strip():
                candidates.append(Path(result.stdout.strip()))

    runtime_root = Path.home() / ".cache" / "codex-runtimes"
    if runtime_root.exists():
        python_name = "python.exe" if os.name == "nt" else "python"
        candidates.extend(
            runtime_root.glob(f"*/dependencies/python/{python_name}")
        )

    runtimes: dict[Path, PythonRuntime] = {}
    for candidate in candidates:
        runtime = inspect_python(candidate.expanduser().resolve())
        if runtime:
            runtimes[runtime.executable] = runtime
    if not runtimes:
        return None
    return sorted(runtimes.values(), key=lambda item: item.version, reverse=True)[0]


def imports_ready(python_path: Path) -> bool:
    if not python_path.exists():
        return False
    result = run_quiet(
        [
            str(python_path),
            "-c",
            "import cv2, mediapipe; print(cv2.__version__, mediapipe.__version__)",
        ]
    )
    return result.returncode == 0


def dependency_status(cache_dir: Path, runtime: PythonRuntime | None) -> str:
    if runtime is None:
        return "no compatible Python"
    expected_marker = "\n".join(PYTHON_REQUIREMENTS) + "\n"
    marker = marker_path(cache_dir, runtime)
    if not venv_python(cache_dir, runtime).exists() or not marker.exists():
        return "not prepared"
    if marker.read_text(encoding="utf-8") != expected_marker:
        return "stale"
    return (
        "ready"
        if imports_ready(venv_python(cache_dir, runtime))
        else "broken"
    )


def prepare_dependencies(cache_dir: Path, runtime: PythonRuntime) -> Path:
    python_path = venv_python(cache_dir, runtime)
    expected_marker = "\n".join(PYTHON_REQUIREMENTS) + "\n"
    if dependency_status(cache_dir, runtime) == "ready":
        return python_path

    root = venv_dir(cache_dir, runtime)
    if not python_path.exists():
        print(f"创建隔离虚拟环境: {root}", flush=True)
        subprocess.run(
            [str(runtime.executable), "-m", "venv", str(root)],
            check=True,
        )

    print("安装/修复 MediaPipe 与 OpenCV 依赖（首次运行可能需要几分钟）...", flush=True)
    install_command = [
        str(python_path),
        "-m",
        "pip",
        "install",
        "--disable-pip-version-check",
        "--upgrade",
        *PYTHON_REQUIREMENTS,
    ]
    result = subprocess.run(install_command, check=False)
    if result.returncode != 0:
        raise ToolError("Python 依赖安装失败；请检查网络、Python 版本和 pip 输出。")
    if not imports_ready(python_path):
        raise ToolError("依赖已安装，但无法导入 cv2 或 mediapipe。")
    marker_path(cache_dir, runtime).write_text(
        expected_marker,
        encoding="utf-8",
    )
    return python_path


def require_compatible_python() -> PythonRuntime:
    runtime = compatible_python()
    if runtime:
        return runtime
    raise ToolError(
        "未找到可用于 MediaPipe 的 Python 3.10–3.12。"
        "请安装其中一个版本并确保它可被 py 启动器或 PATH 发现。"
    )


def find_program(name: str) -> str | None:
    return shutil.which(name)


def make_unique_default(input_path: Path) -> Path:
    candidate = input_path.with_name(f"{input_path.stem}_face_blurred.mp4")
    if not candidate.exists():
        return candidate
    index = 2
    while True:
        candidate = input_path.with_name(
            f"{input_path.stem}_face_blurred_{index}.mp4"
        )
        if not candidate.exists():
            return candidate
        index += 1


def resolve_output(input_path: Path, requested: str | None, overwrite: bool) -> Path:
    if requested is None:
        output = make_unique_default(input_path)
    else:
        output = Path(requested).expanduser().resolve()
    if input_path == output:
        raise ToolError("输入和输出不能是同一路径。")
    if output.exists() and not overwrite:
        raise ToolError(
            f"输出已存在: {output}\n"
            "如确需覆盖，请在用户明确同意后添加 --overwrite。"
        )
    return output


def ffprobe_path() -> str | None:
    found = find_program("ffprobe")
    if found:
        return found
    ffmpeg = find_program("ffmpeg")
    if not ffmpeg:
        return None
    sibling = Path(ffmpeg).with_name("ffprobe.exe" if os.name == "nt" else "ffprobe")
    return str(sibling) if sibling.exists() else None


def probe_media(path: Path, ffprobe: str) -> dict:
    command = [
        ffprobe,
        "-v",
        "error",
        "-show_entries",
        "format=duration:stream=index,codec_type,codec_name",
        "-of",
        "json",
        str(path),
    ]
    result = run_quiet(command)
    if result.returncode != 0:
        raise ToolError(f"FFprobe 无法读取 {path}:\n{result.stderr.strip()}")
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise ToolError(f"FFprobe 返回了无效 JSON: {path}") from exc


def duration_seconds(probe: dict) -> float | None:
    value = probe.get("format", {}).get("duration")
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def stream_count(probe: dict, stream_type: str) -> int:
    return sum(
        1 for stream in probe.get("streams", [])
        if stream.get("codec_type") == stream_type
    )


def verify_output(input_path: Path, output_path: Path) -> None:
    if not output_path.exists() or output_path.stat().st_size == 0:
        raise ToolError(f"未生成有效输出文件: {output_path}")

    probe = ffprobe_path()
    if not probe:
        print("警告: 未找到 ffprobe，仅验证了输出文件非空。", file=sys.stderr)
        return

    input_info = probe_media(input_path, probe)
    output_info = probe_media(output_path, probe)
    if stream_count(output_info, "video") < 1:
        raise ToolError("输出文件不含视频流。")
    if stream_count(input_info, "audio") > 0 and stream_count(output_info, "audio") < 1:
        raise ToolError("输入含音频，但输出音频流缺失。")

    input_duration = duration_seconds(input_info)
    output_duration = duration_seconds(output_info)
    if input_duration and output_duration:
        tolerance = max(1.0, input_duration * 0.02)
        if output_duration < input_duration - tolerance:
            raise ToolError(
                "输出时长明显短于输入，可能为不完整文件: "
                f"input={input_duration:.3f}s output={output_duration:.3f}s"
            )
        print(
            "媒体验证通过: "
            f"video={stream_count(output_info, 'video')} "
            f"audio={stream_count(output_info, 'audio')} "
            f"duration={output_duration:.3f}s",
            flush=True,
        )
    else:
        print("媒体验证通过: 输出含视频流。", flush=True)


def print_check(cache_dir: Path) -> int:
    ffmpeg = find_program("ffmpeg")
    ffprobe = ffprobe_path()
    runtime = compatible_python()
    print(f"启动器 Python: {sys.version.split()[0]} ({sys.executable})")
    if runtime:
        version = ".".join(str(part) for part in runtime.version)
        print(f"MediaPipe Python: OK {version} ({runtime.executable})")
    else:
        print("MediaPipe Python: MISSING (需要 3.10–3.12)")
    print(f"FFmpeg: {'OK ' + ffmpeg if ffmpeg else 'MISSING'}")
    print(f"FFprobe: {'OK ' + ffprobe if ffprobe else 'MISSING (验证将受限)'}")
    print(f"缓存目录: {cache_dir}")
    print(f"上游固定提交: {UPSTREAM_COMMIT}")
    print(f"上游文件: {source_status(cache_dir)}")
    print(f"Python 依赖: {dependency_status(cache_dir, runtime)}")
    return 0 if runtime and ffmpeg else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="使用固定版本 vorojar/face-blur 给视频中的人脸打码。"
    )
    parser.add_argument("input", nargs="?", help="输入视频路径")
    parser.add_argument("-o", "--output", help="输出路径；默认生成不冲突的 *_face_blurred.mp4")
    parser.add_argument(
        "--mode",
        choices=("gaussian", "mosaic"),
        default="gaussian",
        help="打码模式（默认 gaussian）",
    )
    parser.add_argument("--strength", type=int, default=80, help="模糊/马赛克强度")
    parser.add_argument("--padding", type=float, default=0.3, help="人脸轮廓外扩比例")
    parser.add_argument("--min-face-size", type=int, default=40, help="最小人脸边长（像素）")
    parser.add_argument("--detect-interval", type=int, default=3, help="每 N 帧检测一次")
    parser.add_argument("--min-confidence", type=float, default=0.3, help="最低检测置信度")
    parser.add_argument("--preview", action="store_true", help="打开实时预览窗口")
    parser.add_argument("--overwrite", action="store_true", help="允许覆盖指定输出")
    operation = parser.add_mutually_exclusive_group()
    operation.add_argument("--check", action="store_true", help="只检查系统和缓存状态")
    operation.add_argument("--prepare", action="store_true", help="只下载上游并准备隔离依赖")
    operation.add_argument("--dry-run", action="store_true", help="只显示计划，不下载或处理")
    parser.add_argument(
        "--cache-dir",
        help="覆盖缓存目录；也可设置 CODEX_FACE_BLUR_HOME",
    )
    return parser


def validate_args(args: argparse.Namespace) -> None:
    if args.strength < 1:
        raise ToolError("--strength 必须至少为 1。")
    if args.padding < 0:
        raise ToolError("--padding 不能为负数。")
    if args.min_face_size < 0:
        raise ToolError("--min-face-size 不能为负数。")
    if args.detect_interval < 1:
        raise ToolError("--detect-interval 必须至少为 1。")
    if not 0 <= args.min_confidence <= 1:
        raise ToolError("--min-confidence 必须在 0 到 1 之间。")


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    cache_dir = (
        Path(args.cache_dir).expanduser().resolve()
        if args.cache_dir
        else default_cache_dir()
    )

    if args.check:
        return print_check(cache_dir)

    runtime = require_compatible_python()
    validate_args(args)
    ffmpeg = find_program("ffmpeg")
    if not ffmpeg:
        raise ToolError("未找到 FFmpeg。请先安装并确保 ffmpeg 位于 PATH。")

    if args.prepare:
        root = ensure_upstream(cache_dir)
        python_path = prepare_dependencies(cache_dir, runtime)
        print(f"准备完成: {root}")
        print(f"VENV_PYTHON={python_path}")
        return 0

    if not args.input:
        parser.error("处理视频时必须提供 input；或使用 --check/--prepare。")

    input_path = Path(args.input).expanduser().resolve()
    if not input_path.is_file():
        raise ToolError(f"输入视频不存在或不是文件: {input_path}")
    output_path = resolve_output(input_path, args.output, args.overwrite)

    if args.dry_run:
        plan = {
            "input": str(input_path),
            "output": str(output_path),
            "mode": args.mode,
            "strength": args.strength,
            "padding": args.padding,
            "min_face_size": args.min_face_size,
            "detect_interval": args.detect_interval,
            "min_confidence": args.min_confidence,
            "preview": args.preview,
            "cache_dir": str(cache_dir),
            "upstream_commit": UPSTREAM_COMMIT,
            "upstream_status": source_status(cache_dir),
            "dependency_status": dependency_status(cache_dir, runtime),
            "runtime_python": str(runtime.executable),
        }
        print(json.dumps(plan, ensure_ascii=False, indent=2))
        return 0

    output_path.parent.mkdir(parents=True, exist_ok=True)
    root = ensure_upstream(cache_dir)
    python_path = prepare_dependencies(cache_dir, runtime)
    command = [
        str(python_path),
        str(root / "face_blur.py"),
        str(input_path),
        "--output",
        str(output_path),
        "--mode",
        args.mode,
        "--strength",
        str(args.strength),
        "--padding",
        str(args.padding),
        "--min-face-size",
        str(args.min_face_size),
        "--detect-interval",
        str(args.detect_interval),
        "--min-confidence",
        str(args.min_confidence),
    ]
    if args.preview:
        command.append("--preview")

    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    print(f"上游: {UPSTREAM_REPO}@{UPSTREAM_COMMIT}")
    print(f"输出: {output_path}", flush=True)
    result = subprocess.run(command, env=env, check=False)
    if result.returncode != 0:
        partial = "（存在部分输出）" if output_path.exists() else ""
        raise ToolError(
            f"人脸打码处理失败，退出码 {result.returncode} {partial}: {output_path}"
        )

    verify_output(input_path, output_path)
    print(f"OUTPUT_PATH={output_path}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ToolError as exc:
        print(f"错误: {exc}", file=sys.stderr)
        raise SystemExit(1)
    except subprocess.CalledProcessError as exc:
        print(f"错误: 命令执行失败（退出码 {exc.returncode}）", file=sys.stderr)
        raise SystemExit(exc.returncode or 1)
