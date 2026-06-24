# SceneFab 使用示例

> **文档已迁移**：完整的使用说明和 API 文档已移至 [docs/](../docs/) 目录。

## 文档入口

- [快速开始](../docs/guide/quick-start.md) — 3 步上手
- [CLI 参考](../docs/guide/cli-reference.md) — 命令行使用说明
- [Python API](../docs/guide/python-api.md) — Python API 完整文档
- [AI 配置](../docs/guide/ai-configuration.md) — 多服务商配置详解
- [配置参考](../docs/config.md) — 配置文件结构

## 快速示例

### 启动 GUI

```bash
scenefab
```

### 命令行模式

```bash
scenefab
# 选择功能 1 (AI 第一人称解说) 或 2 (剪映草稿导出)
```

### Python API

```python
from scenefab.services.video import MonologueMaker

maker = MonologueMaker(voice_provider="edge")
project = maker.create_project(
    source_video="./movie.mp4",
    context="解说主题",
    emotion="平静",
)
maker.generate_script(project)
maker.generate_voice(project)
maker.generate_captions(project, style="cinematic")
draft_path = maker.export_to_jianying(project, "./output")
```

## 环境变量

```bash
export DEEPSEEK_API_KEY="sk-your-deepseek-key"
export QWEN_API_KEY="sk-your-qwen-key"
```

或使用 `.env` 文件（参考 [../.env.example](../.env.example)）。
