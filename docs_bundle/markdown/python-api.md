---
title: Python API
description: 使用 SceneFab Python API 进行视频解说生成、场景分析和导出。
---

# Python API

SceneFab 提供完整的 Python API，支持在脚本或项目中调用核心功能。

## 快速示例

```python
from scenefab.services.video import MonologueMaker

### 创建解说器
maker = MonologueMaker(voice_provider="edge")

### 创建项目
project = maker.create_project(
    source_video="./input/movie.mp4",
    context="分析这段视频的精彩瞬间",
    emotion="平静",
)

### 生成解说
maker.generate_script(project)
maker.generate_voice(project)
maker.generate_captions(project, style="cinematic")

### 导出剪映草稿
draft_path = maker.export_to_jianying(project, "./output")
print(f"草稿路径: {draft_path}")
```

## 核心类

### MonologueMaker

第一人称视频解说的核心类，封装了从视频分析到导出的完整流程。

```python
from scenefab.services.video import MonologueMaker

maker = MonologueMaker(voice_provider="edge")
```

**参数：**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `voice_provider` | `str` | `"edge"` | TTS 引擎：`"edge"` / `"openai"` |

**主要方法：**

#### `create_project(source_video, context, emotion)`

创建视频解说项目。

```python
project = maker.create_project(
    source_video="./movie.mp4",
    context="解说主题或背景描述",
    emotion="平静",  # 平静/紧张/激动/幽默
)
```

#### `generate_script(project, custom_script=None)`

生成解说脚本。传入 `custom_script` 使用自定义文案，否则由 AI 生成。

```python
### AI 自动生成
maker.generate_script(project)

### 使用自定义文案
maker.generate_script(project, custom_script="这是我的自定义解说词...")
```

#### `generate_voice(project)`

生成配音音频。

```python
maker.generate_voice(project)
```

#### `generate_captions(project, style="cinematic")`

生成字幕文件。

```python
maker.generate_captions(project, style="cinematic")
```

#### `export_to_jianying(project, output_dir)`

导出剪映草稿。

```python
draft_path = maker.export_to_jianying(project, "./output/jianying_drafts")
```

#### `set_progress_callback(callback)`

设置进度回调函数。

```python
def on_progress(stage, progress):
    print(f"[{stage}] {progress * 100:.0f}%")

maker.set_progress_callback(on_progress)
```

---

### SceneAnalyzer

场景分析器，用于检测视频场景、提取关键帧和计算重要性评分。

```python
from scenefab.services.ai import SceneAnalyzer

analyzer = SceneAnalyzer()
```

**主要方法：**

#### `analyze(video_path)`

分析视频场景，返回场景列表。

```python
scenes = analyzer.analyze("./movie.mp4")

for scene in scenes:
    print(f"场景 {scene.index}: {scene.start:.1f}s - {scene.end:.1f}s")
    print(f"  类型: {scene.type.value}")
    print(f"  评分: {scene.suitability_score:.0f}/100")
```

#### `analyze_with_importance(video_path)`

分析场景并计算重要性评分（含叙事重要性）。

```python
scenes = analyzer.analyze_with_importance("./movie.mp4")
```

#### `extract_key_moments(scenes, top_k=5)`

提取关键时刻（评分最高的场景）。

```python
key_moments = analyzer.extract_key_moments(scenes, top_k=5)
```

#### `generate_scene_context_prompt(scenes)`

生成场景上下文提示（用于脚本生成）。

```python
prompt = analyzer.generate_scene_context_prompt(scenes)
print(prompt)
```

---

### JianyingExporter

剪映草稿导出器。

```python
from scenefab.services.export import JianyingExporter, JianyingConfig

exporter = JianyingExporter(
    JianyingConfig(
        canvas_ratio="9:16",
        copy_materials=True,
    )
)
```

**导出流程：**

```python
from scenefab.services.export import (
    JianyingExporter, JianyingConfig,
    Track, TrackType, Segment, TimeRange, VideoMaterial,
)

### 创建导出器
exporter = JianyingExporter(JianyingConfig(canvas_ratio="9:16"))

### 创建草稿
draft = exporter.create_draft("我的项目")

### 添加视频轨道
video_track = Track(type=TrackType.VIDEO, attribute=1)
draft.add_track(video_track)

### 添加视频素材
video_material = VideoMaterial(path="./movie.mp4")
draft.add_video(video_material)

### 添加片段
segment = Segment(
    material_id=video_material.id,
    source_timerange=TimeRange.from_seconds(0, 30),
    target_timerange=TimeRange.from_seconds(0, 30),
)
video_track.add_segment(segment)

### 导出
draft_path = exporter.export(draft, "./output")
```

---

### ConfigManager

配置管理器（单例），用于加载和管理应用配置。

```python
from scenefab.settings import ConfigManager, get_config, get_llm_config

### 获取配置管理器
config = ConfigManager()

### 获取应用配置
app_config = get_config()
print(f"应用名: {app_config.name}")
print(f"版本: {app_config.version}")

### 获取 LLM 配置
llm_config = get_llm_config("deepseek")
if llm_config and llm_config.is_valid():
    print(f"模型: {llm_config.model}")
```

---

## 数据模型

### SceneInfo

场景信息，由 `SceneAnalyzer.analyze()` 返回。

| 属性 | 类型 | 说明 |
|------|------|------|
| `index` | `int` | 场景序号 |
| `start` | `float` | 开始时间（秒） |
| `end` | `float` | 结束时间（秒） |
| `duration` | `float` | 时长（秒） |
| `type` | `SceneType` | 场景类型 |
| `avg_brightness` | `float` | 平均亮度 (0-1) |
| `motion_level` | `float` | 运动程度 (0-1) |
| `audio_level` | `float` | 音频音量 (0-1) |
| `suitability_score` | `float` | 适用性评分 (0-100) |
| `description` | `str` | 场景描述 |

### SceneType

场景类型枚举。

| 值 | 说明 |
|------|------|
| `LANDSCAPE` | 风景画面 |
| `B_ROLL` | 素材画面 |
| `ACTION` | 动作场景 |
| `TALKING_HEAD` | 人物讲话 |
| `TRANSITION` | 转场 |
| `TITLE` | 标题画面 |
| `PRODUCT` | 产品展示 |
| `UNKNOWN` | 未知 |

### LLMConfig

LLM 提供者配置。

| 属性 | 类型 | 说明 |
|------|------|------|
| `name` | `str` | 提供者名称 |
| `enabled` | `bool` | 是否启用 |
| `api_key` | `str` | API 密钥 |
| `base_url` | `str` | API 地址 |
| `model` | `str` | 模型名称 |
| `max_tokens` | `int` | 最大 token 数 |
| `temperature` | `float` | 温度参数 |

---

## 相关文档

- [快速开始](/guide/quick-start) — 3 步上手
- [AI 配置](/guide/ai-configuration) — 多服务商配置详解
