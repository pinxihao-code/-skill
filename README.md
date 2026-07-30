# Blur Video Faces Skill

一个可供 Codex 和其他兼容 Agent 使用的视频人脸打码 Skill。它基于固定版本的 [`vorojar/face-blur`](https://github.com/vorojar/face-blur)，支持：

- 正脸、侧脸和多人脸检测
- 高斯模糊与马赛克
- 人脸轮廓外扩和羽化
- FFmpeg 硬件编码探测与 CPU 回退
- Windows、macOS、Linux 跨平台依赖启动
- 输出覆盖保护、音轨和时长验证
- 隐私敏感素材的视觉抽检流程

## 安装位置

| 环境 | 默认路径 |
|---|---|
| 通用 | `$CODEX_HOME/skills/blur-video-faces` |
| Windows（未设置 `CODEX_HOME`） | `%USERPROFILE%\.codex\skills\blur-video-faces` |
| macOS / Linux（未设置 `CODEX_HOME`） | `~/.codex/skills/blur-video-faces` |

安装后，新 Agent 回合会自动发现 `$blur-video-faces`。

## 安装方法

### 方法一：Codex Skill Installer

Windows PowerShell：

```powershell
$installer = if ($env:CODEX_HOME) {
  Join-Path $env:CODEX_HOME "skills\.system\skill-installer\scripts\install-skill-from-github.py"
} else {
  Join-Path $env:USERPROFILE ".codex\skills\.system\skill-installer\scripts\install-skill-from-github.py"
}
python $installer --repo pinxihao-code/-skill --path skills/blur-video-faces
```

macOS / Linux：

```bash
python "${CODEX_HOME:-$HOME/.codex}/skills/.system/skill-installer/scripts/install-skill-from-github.py" \
  --repo pinxihao-code/-skill \
  --path skills/blur-video-faces
```

### 方法二：使用仓库安装脚本

Windows：

```powershell
git clone https://github.com/pinxihao-code/-skill.git blur-video-faces-skill
powershell -ExecutionPolicy Bypass -File .\blur-video-faces-skill\install.ps1
```

macOS / Linux：

```bash
git clone https://github.com/pinxihao-code/-skill.git blur-video-faces-skill
bash ./blur-video-faces-skill/install.sh
```

安装脚本检测到目标目录已存在时会停止，不会覆盖现有 Skill。

### 方法三：下载打包文件

下载 [`dist/blur-video-faces-skill-v1.0.2.zip`](dist/blur-video-faces-skill-v1.0.2.zip)，把其中的 `blur-video-faces` 文件夹复制到上面的默认 Skill 目录。

## Agent 使用方法

在新任务中直接说：

```text
使用 $blur-video-faces 给 C:\视频\素材.mp4 中的所有人脸打马赛克，并检查是否漏脸。
```

或：

```text
Use $blur-video-faces to anonymize every face in /data/interview.mp4 and visually verify the result.
```

Agent 会：

1. 保留原视频并检查 Python、FFmpeg 和缓存。
2. 调用固定版本的人脸检测模型。
3. 生成独立的模糊或马赛克视频。
4. 验证视频流、音轨和时长。
5. 抽检开头、中段、结尾和主要镜头。
6. 对无法可靠自动识别的镜头报告限制，不用低置信度误检冒充成功。

## 直接运行

```powershell
python "<skill目录>\scripts\run_face_blur.py" "C:\path\input.mp4"
```

隐私优先参数：

```powershell
python "<skill目录>\scripts\run_face_blur.py" "C:\path\input.mp4" `
  --mode mosaic `
  --strength 80 `
  --padding 0.5 `
  --min-face-size 15 `
  --detect-interval 1 `
  --min-confidence 0.2
```

不要把整片置信度继续降到 `0.1` 或更低。真实视频测试表明，这会造成大范围误检；持续漏检应使用局部手动遮挡或跟踪补码。

## 系统要求

- Python 3.10–3.12（启动器也可由更高版本 Python 调用，并自动寻找兼容运行时）
- FFmpeg 和 FFprobe 位于 `PATH`
- 首次运行可访问 GitHub 和 Python 包索引

首次运行会把固定上游文件和隔离虚拟环境放入用户缓存，不会写入视频素材目录。

## 验证与打包

```bash
python scripts/build_package.py
python scripts/validate_package.py
```

GitHub Actions 会在 push 和 pull request 时重新生成压缩包并验证内容一致性。

## 来源与许可

- 上游：[`vorojar/face-blur`](https://github.com/vorojar/face-blur)
- 固定提交：`0c83fdce0ee206a0043cf00173a82f52ec1af81b`
- 本仓库代码：MIT License

自动检测不能保证绝对不漏脸。隐私敏感素材必须进行视觉抽检。
