# Voxplore

> **AI 影视解说工具** — 第一人称视角视频创作平台，让你的故事更有电影感

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![Stars](https://img.shields.io/github/stars/Agions/Voxplore?style=social)](https://github.com/Agions/Voxplore)

---

## 🎯 项目简介

Voxplore 是一款专注于**第一人称视角视频解说**的 AI 工具。用户上传视频，AI 自动提取 POV 镜头，生成电影感解说配音。

**典型场景**：旅游 vlog、游戏集锦、运动相机 footage、生活记录

---

## ✨ 核心特性

| 特性 | 说明 |
|:----:|------|
| 🎬 **第一人称提取** | 自动识别并提取视频中的 POV / 主观镜头 |
| 🎭 **7 种情感风格** | 治愈 / 悬疑 / 励志 / 怀旧 / 浪漫 / 幽默 / 纪录片 |
| 🎙️ **智能配音** | Edge-TTS 高质量神经网络语音合成 |
| 📝 **精准字幕** | 50ms 精度时间轴对齐，支持 SRT/VTT/LRC |
| 📦 **剪映导出** | 原生草稿格式，一键导入剪映编辑 |
| 💾 **断点续传** | 任务暂停/恢复，无惧中途打断 |
| 🔒 **本地处理** | 视频永不上传，隐私安全无忧 |
| 💰 **低成本** | 集成 DeepSeek-V4 API，< ¥0.01 / 视频 |

---

## 🚀 快速开始

### 1. 安装依赖

```bash
git clone https://github.com/Agions/Voxplore.git
cd Voxplore
pip install -r requirements.txt
```

### 2. 配置 API Key

创建 `.env` 文件：

```bash
# AI 服务（必须）
DEEPSEEK_API_KEY=sk-your-deepseek-api-key
DASHSCOPE_API_KEY=your-dashscope-api-key

# 可选配置
VOXPLORE_CACHE_DIR=~/.cache/voxplore   # 缓存目录
VOXPLORE_OUTPUT_DIR=./output            # 输出目录
```

> 💡 API Key 申请：[DeepSeek](https://platform.deepseek.com/) · [阿里云 DashScope](https://dashscope.console.aliyun.com/)

### 3. 命令行使用

```bash
# 分析视频，查看第一人称片段
python -m voxplore analyze video.mp4

# 检测所有场景
python -m voxplore analyze video.mp4 --scenes

# 处理视频（生成解说）
python -m voxplore process video.mp4 --style documentary --emotion neutral

# 批量处理
python -m voxplore batch "*.mp4"

# 导出为剪映草稿
python -m voxplore process video.mp4 --export --format jianying
```

### 4. Python API

```python
from voxplore.pipeline import VoxplorePipeline, PipelineConfig
from voxplore.models import NarrationStyle, EmotionType

# 创建流水线
config = PipelineConfig(
    min_segment_duration=9.0,   # 最小片段（秒）
    max_segment_duration=60.0,  # 最大片段（秒）
)
pipeline = VoxplorePipeline(config)

# 处理视频
project = pipeline.process(
    video_path="video.mp4",
    context="这是一段关于云南旅行的记录",
    emotion=EmotionType.NEUTRAL,
    style=NarrationStyle.DOCUMENTARY,
    voice="zh-CN-XiaoxiaoNeural",
)

print(f"✅ 提取片段: {len(project.segments)}")
print(f"✅ 解说块:   {len(project.narration_blocks)}")
```

---

## 📁 项目结构

```
voxplore/
├── __init__.py
├── config.py           # 配置管理
├── core.py             # 核心模块（事件总线、服务容器）
├── models.py           # 数据模型定义
├── video.py            # 视频处理
├── ai_services.py      # AI 服务（LLM / 视觉 / TTS / ASR）
├── pipeline.py         # 处理流水线
├── exporters.py        # 导出服务（剪映 / 字幕）
├── task_manager.py     # 任务管理（断点续传）
└── cli.py              # 命令行界面
```

---

## ⚙️ 配置说明

编辑 `config/app_config.yaml`：

```yaml
app:
  name: "Voxplore"
  version: "2.0.0"

cache:
  enabled: true
  max_size: 100
  ttl: 3600

video:
  min_segment_duration: 9.0    # 最小片段时长（秒）
  max_segment_duration: 60.0   # 最大片段时长（秒）
  frame_sample_interval: 1.0   # 帧采样间隔（秒）
  min_confidence: 0.6         # 最低置信度

tts:
  provider: "edge"             # edge / f5
  voice: "zh-CN-XiaoxiaoNeural"
  rate: 1.0

llm_providers:
  deepseek:
    enabled: true
    api_key: "${DEEPSEEK_API_KEY}"
    base_url: "https://api.deepseek.com"
    model: "deepseek-v4"
```

---

## 🎨 情感风格

| 风格 | 语气 | 适用场景 |
|:----:|:----:|:---------|
| 治愈 | 🌡️ 温暖 | 日常生活记录 |
| 悬疑 | 🔍 神秘 | 剧情紧张片段 |
| 励志 | 💪 激昂 | 高光时刻 |
| 怀旧 | 📼 平静 | 回忆场景 |
| 浪漫 | 💕 温柔 | 情感戏 |
| 幽默 | 😂 活泼 | 搞笑片段 |
| 纪录片 | 🎙️ 沉稳 | 说明性内容 |

---

## 📦 导出格式

### 剪映草稿

导出为原生剪映草稿格式，可直接导入剪映编辑：

```python
from voxplore.exporters import JianyingExporter

exporter = JianyingExporter()
draft_path = exporter.export(project, output_dir="./output")
print(f"草稿已导出: {draft_path}")
```

### 字幕格式

```python
from voxplore.exporters import SubtitleExporter

# 多种格式一键导出
SubtitleExporter.export_srt(project.subtitles, "output.srt")
SubtitleExporter.export_vtt(project.subtitles, "output.vtt")
SubtitleExporter.export_lrc(project.subtitles, "output.lrc")
```

---

## 🛠️ 技术栈

| 领域 | 技术 |
|:----:|:-----|
| 🎬 视频处理 | OpenCV, FFmpeg |
| 🎤 语音识别 | Faster-Whisper |
| 👁️ 视觉模型 | Qwen2.5-VL |
| 🤖 LLM | DeepSeek-V4, GPT-4o, Qwen |
| 🔊 TTS | Edge-TTS, F5-TTS |
| 📝 字幕 | WhisperX 时间轴对齐 |

---

## 📄 许可证

本项目基于 [MIT License](https://opensource.org/licenses/MIT) 开源。

---

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！如果这个项目对你有帮助，请给我们一个 ⭐
