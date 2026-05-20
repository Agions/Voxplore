# Voxplore

**AI 影视解说工具** - 第一人称视角视频创作平台

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)

## 🎯 项目简介

Voxplore 是一款专注于**第一人称视角视频解说**的 AI 工具。用户上传视频，AI 自动提取第一人称视角片段，生成电影感解说配音。

### 核心特性

- 🎬 **第一人称提取** - 自动识别并提取视频中的 POV/主观镜头
- 🎭 **7 种情感风格** - 治愈、悬疑、励志、怀旧、浪漫、幽默、纪录片
- 🎙️ **智能配音** - Edge-TTS 高质量语音合成
- 📝 **自动字幕** - 50ms 精度时间轴对齐
- 📦 **剪映导出** - 原生草稿格式导出，直接导入剪映
- 💾 **断点续传** - 任务暂停/恢复，再也不怕中途打断
- 🔒 **本地处理** - 视频永不上传，保护隐私
- 💰 **低成本** - 集成 DeepSeek-V4 API，< ¥0.01/视频

## 🚀 快速开始

### 安装依赖

```bash
pip install -r requirements.txt
```

### 配置 API Key

创建 `.env` 文件：

```bash
# AI 服务配置
DEEPSEEK_API_KEY=sk-your-deepseek-api-key
DASHSCOPE_API_KEY=your-dashscope-api-key

# 可选配置
VOXPLORE_CACHE_DIR=~/.cache/voxplore
VOXPLORE_OUTPUT_DIR=./output
```

### 命令行使用

```bash
# 分析视频
python -m voxplore analyze video.mp4

# 检测场景
python -m voxplore analyze video.mp4 --scenes

# 处理视频（生成解说）
python -m voxplore process video.mp4 --style documentary --emotion neutral

# 批量处理
python -m voxplore batch "*.mp4"

# 导出为剪映草稿
python -m voxplore process video.mp4 --export --format jianying
```

### Python API

```python
from voxplore.pipeline import VoxplorePipeline, PipelineConfig
from voxplore.models import NarrationStyle, EmotionType

# 创建流水线
config = PipelineConfig(
    min_segment_duration=9.0,
    max_segment_duration=60.0,
)
pipeline = VoxplorePipeline(config)

# 处理视频
project = pipeline.process(
    video_path="video.mp4",
    context="这是一个关于旅行的故事",
    emotion=EmotionType.NEUTRAL,
    style=NarrationStyle.DOCUMENTARY,
    voice="zh-CN-XiaoxiaoNeural",
)

print(f"提取片段: {len(project.segments)}")
print(f"解说块: {len(project.narration_blocks)}")
```

## 📁 项目结构

```
voxplore/
├── __init__.py
├── config.py          # 配置管理
├── core.py            # 核心模块（事件总线、服务容器）
├── models.py          # 数据模型
├── video.py           # 视频处理
├── ai_services.py     # AI 服务（LLM、视觉、TTS、ASR）
├── pipeline.py        # 处理流水线
├── exporters.py       # 导出服务（剪映、字幕）
├── task_manager.py    # 任务管理
└── cli.py             # 命令行界面
```

## ⚙️ 配置说明

### 配置文件

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
  min_segment_duration: 9.0   # 最小片段时长（秒）
  max_segment_duration: 60.0  # 最大片段时长（秒）
  frame_sample_interval: 1.0   # 帧采样间隔（秒）
  min_confidence: 0.6          # 最低置信度

tts:
  provider: "edge"            # edge, f5
  voice: "zh-CN-XiaoxiaoNeural"
  rate: 1.0

llm_providers:
  deepseek:
    enabled: true
    api_key: "${DEEPSEEK_API_KEY}"
    base_url: "https://api.deepseek.com"
    model: "deepseek-v4"
```

## 🎨 情感风格

| 风格 | 语气 | 适用场景 |
|------|------|----------|
| 治愈 | 温暖 | 日常生活 |
| 悬疑 | 神秘 | 剧情紧张 |
| 励志 | 激昂 | 高光时刻 |
| 怀旧 | 平静 | 回忆场景 |
| 浪漫 | 温柔 | 情感戏 |
| 幽默 | 活泼 | 搞笑片段 |
| 纪录片 | 沉稳 | 说明性内容 |

## 📦 导出格式

### 剪映草稿

导出为原生剪映草稿格式，可直接导入剪映编辑：

```python
from voxplore.exporters import JianyingExporter

exporter = JianyingExporter()
draft_path = exporter.export(project, output_dir="./output")
```

### 字幕格式

支持 SRT、VTT、LRC 等多种字幕格式：

```python
from voxplore.exporters import SubtitleExporter

SubtitleExporter.export_srt(project.subtitles, "output.srt")
SubtitleExporter.export_vtt(project.subtitles, "output.vtt")
SubtitleExporter.export_lrc(project.subtitles, "output.lrc")
```

## 🔧 技术栈

- **视频处理**: OpenCV, FFmpeg
- **语音识别**: Faster-Whisper
- **视觉模型**: Qwen2.5-VL
- **LLM**: DeepSeek-V4, GPT-4o, Qwen
- **TTS**: Edge-TTS, F5-TTS
- **字幕**: WhisperX 时间轴对齐

## 📄 许可证

MIT License

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！
