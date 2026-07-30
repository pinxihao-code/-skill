---
name: blur-video-faces
description: "使用 vorojar/face-blur 自动检测并遮挡视频中的正脸、侧脸和多人脸，输出带高斯模糊或马赛克的人脸匿名化视频。用于用户要求视频人脸打码、人脸模糊、人脸马赛克、隐私脱敏、匿名化处理，或需要批量遮挡 MP4/MOV/MKV 等视频中的全部人脸时。"
---

# 视频人脸打码

使用固定版本的 `vorojar/face-blur` 完成双模型人脸检测、轮廓打码和 FFmpeg 编码。通过 `scripts/run_face_blur.py` 统一处理 Windows/macOS/Linux 的依赖、上游文件校验、输出保护和媒体验证。

## 执行流程

1. 确认输入视频的准确路径，并保留原文件。
2. 运行环境检查：

   ```powershell
   python "{skill_dir}\scripts\run_face_blur.py" --check
   ```

   将 `{skill_dir}` 替换为本 Skill 所在目录。缓存未准备属于正常状态；脚本会在首次正式处理时下载固定提交并创建隔离虚拟环境。若缺少兼容的 Python 3.10–3.12 或 FFmpeg，停止并向用户说明；不要擅自安装系统级软件。启动器会自动发现 Codex 随附的兼容 Python。

3. 根据需求选参数并运行。普通场景使用默认设置：

   ```powershell
   python "{skill_dir}\scripts\run_face_blur.py" "C:\path\input.mp4"
   ```

   指定输出和马赛克：

   ```powershell
   python "{skill_dir}\scripts\run_face_blur.py" "C:\path\input.mp4" -o "C:\path\output.mp4" --mode mosaic
   ```

   用户强调隐私、彻底遮挡、远处小脸或快速切镜时，优先使用：

   ```powershell
   python "{skill_dir}\scripts\run_face_blur.py" "C:\path\input.mp4" --mode mosaic --strength 80 --padding 0.5 --min-face-size 15 --detect-interval 1 --min-confidence 0.2
   ```

4. 读取脚本末尾的 `OUTPUT_PATH=...`。脚本会验证输出视频流、时长和原有音频是否存在；验证失败时不要宣称完成。
5. 做视觉抽检。至少对输入和输出的 10%、50%、90% 时间点提取同帧画面并对照检查；有多个镜头时覆盖每个主要镜头。检查正脸、侧脸、画面边缘、小脸和短暂入镜的人脸。若漏检，使用隐私优先参数重跑。
6. 返回输出视频的绝对路径，并说明使用的模式及视觉抽检范围。

## 参数选择

- 普通高斯模糊：保留默认 `--strength 80 --padding 0.3 --detect-interval 3`。
- 明显马赛克：使用 `--mode mosaic`；增大 `--strength` 会让像素块更粗。
- 小脸、侧脸、快速切镜：使用 `--detect-interval 1 --min-face-size 15 --min-confidence 0.2`。
- 隐私参数仍漏检：不要把整片 `--min-confidence` 继续降到 `0.1` 或更低；这会显著增加大范围误检。定位漏检时间段后，用局部手动遮挡/跟踪补码，或明确告知用户该模型不适合该镜头。
- 更大遮挡范围：将 `--padding` 提高到 `0.4`–`0.6`。
- 快速粗处理：保留 `--detect-interval 3`，但不得用于高风险隐私承诺。
- 实时窗口：仅当用户明确要求预览且当前环境支持 GUI 时添加 `--preview`。
- 覆盖已有指定输出：只有用户明确同意覆盖时添加 `--overwrite`。未指定输出时，脚本自动选择不冲突的 `*_face_blurred.mp4`。

## 安全与质量规则

- 不要把自动检测描述为绝对不会漏脸。隐私敏感素材必须视觉抽检。
- 不要用“检测次数增加”代替视觉验证；低置信度可能把衣服、手臂或背景识别成人脸。
- 不要原地修改输入文件。脚本拒绝输入输出为同一路径。
- 首次运行会从 GitHub 下载三个固定版本文件，并在用户缓存目录安装固定版本的 `mediapipe` 与 OpenCV contrib 包；向用户说明这一步需要网络且可能耗时。
- 默认输出为 H.264 MP4，复制原音轨。上游不会保留字幕、附件或数据流；用户要求保留这些流时，先读取 `references/upstream.md` 再设计后续封装。
- 处理失败后保留可能存在的部分输出，明确标为不完整，不要交付为成品。

## 参考

仅在需要审计来源、排查依赖/编码问题、保留字幕或理解已知限制时读取 [references/upstream.md](references/upstream.md)。
