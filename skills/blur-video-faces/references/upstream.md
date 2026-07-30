# 上游实现与限制

## 来源固定

- 仓库：<https://github.com/vorojar/face-blur>
- 固定提交：`0c83fdce0ee206a0043cf00173a82f52ec1af81b`
- 提交日期：2026-04-18
- 仓库 README 声明：MIT

启动器只下载该提交中的三个运行文件，并逐个校验 SHA-256：

| 文件 | SHA-256 |
|---|---|
| `face_blur.py` | `cb2ad472e425e922d1cfb043c2c248d5d9c429644f54dd2b768ddcae8f1b88b2` |
| `face_landmarker.task` | `64184e229b263107bc2b804c6625db1341ff2bb731874b0bcc2fe6544e0bc9ff` |
| `blaze_face_short_range.tflite` | `b4578f35940bf5a1a655214a1cce5cab13eba73c1297cd78e1a04c2380b0152f` |

## 工作方式

1. OpenCV 逐帧读取视频。
2. MediaPipe FaceLandmarker 用 468 个关键点生成脸部轮廓。
3. MediaPipe FaceDetector 用椭圆区域补充侧脸和极端角度。
4. 对重叠结果去重，对检测间隔内的后续帧复用轮廓。
5. 对轮廓内区域应用高斯模糊或马赛克，并羽化边缘。
6. 将原始帧管道送入 FFmpeg，自动尝试 VideoToolbox、NVENC、AMF、QSV，最后回退到 libx264；复制原音轨。

## 为什么使用启动器

上游 `_ensure_venv()` 固定查找 `.venv/bin/python3` 和 `.venv/bin/pip`，Windows 虚拟环境实际位于 `.venv/Scripts/`。启动器自动寻找 Python 3.10–3.12（包括 Codex 随附运行时），在用户缓存目录创建跨平台虚拟环境，先保证 `mediapipe` 与 `cv2` 可导入，再调用未经修改的固定上游脚本，因此不会触发该 Windows 路径问题。启动器本身可由更新版本的 Python 启动。

为避免两个发行包同时提供 `cv2` 命名空间，启动器固定安装 `mediapipe==0.10.35` 与 `opencv-contrib-python==4.14.0.94`，不再额外安装 `opencv-python`。MediaPipe 所需的 OpenCV 功能由 contrib 包完整提供。

缓存默认位置：

- Windows：`%LOCALAPPDATA%\Codex\blur-video-faces`
- macOS：`~/Library/Caches/Codex/blur-video-faces`
- Linux：`${XDG_CACHE_HOME:-~/.cache}/codex/blur-video-faces`

可用环境变量 `CODEX_FACE_BLUR_HOME` 或启动器参数 `--cache-dir` 覆盖。

## 上游参数

| 参数 | 默认值 | 作用 |
|---|---:|---|
| `--mode` | `gaussian` | `gaussian` 或 `mosaic` |
| `--strength` | `80` | 模糊核/马赛克粗细 |
| `--padding` | `0.3` | 人脸轮廓外扩比例 |
| `--min-face-size` | `40` | 小于该边长的人脸不处理 |
| `--detect-interval` | `3` | 每 N 帧重新检测 |
| `--min-confidence` | `0.3` | 最低检测置信度 |
| `--preview` | 关闭 | 打开 OpenCV 实时窗口 |

## 已知限制与处理

- 自动检测可能漏掉严重遮挡、极小、运动模糊、背面或极端角度的人脸。高风险场景使用 `--detect-interval 1 --min-face-size 15 --min-confidence 0.2 --padding 0.5`，并逐镜头抽检。
- 实测表明，把整片置信度从 `0.2` 降到 `0.1` 可能同时增加真实检测和大面积误检，不能仅凭“检测次数更多”判断效果。若 `0.2` 仍漏检，优先对已定位的时间段做固定区域、关键帧或目标跟踪补码。
- 检测间隔大于 1 时，切镜后的 1–2 帧可能短暂复用上一镜头轮廓。快速切镜或严格隐私处理使用间隔 1。
- FaceLandmarker 配置最多 10 张脸；密集人群不能假定完全覆盖。
- 输出视频会重新编码为 H.264 `yuv420p`。原始画质、码率、HDR、透明度和可变帧率特征不保证保持。
- 上游只映射处理后的视频流和原文件的音频流，不保留字幕、附件、数据流或完整元数据。
- 音频使用 stream copy。原音频编码与 MP4 不兼容时 FFmpeg 可能失败。先告知用户，再考虑将音频转为 AAC 或改用兼容容器；不要静默改变音频。
- `--preview` 中按 `q` 会提前结束，可能产生短视频；启动器的时长验证会将其标为不完整。
- FFmpeg 硬件编码器探测失败时回退至 CPU `libx264`，属于正常但速度较慢。

## 字幕/元数据保留思路

需要保留字幕时，先完成人脸打码，再用 FFmpeg 从原文件映射字幕和元数据到一个新文件。必须先用 `ffprobe` 检查字幕编码与目标容器兼容性；例如 ASS 字幕通常不能直接复制进 MP4。保留原打码输出作为中间文件，禁止覆盖输入。
