---
title: CLI 参考
description: SceneFab 命令行工具的使用方法、参数和环境变量配置。
---

# CLI 参考

SceneFab 提供命令行入口，可直接启动 GUI，或在无 GUI 环境进入命令行模式。

## 基础命令

```bash
### 启动 GUI（默认）
scenefab

### 查看版本
scenefab --version

### 查看帮助
scenefab --help
```

## 命令行模式

当 PySide6 未安装或无法启动 GUI 时，SceneFab 自动进入命令行模式：

```bash
scenefab
```

可用功能：

```text
SceneFab 命令行模式
------------------------------
可用功能:
  1. AI 第一人称解说
  2. 剪映草稿导出
  3. 退出
```

### AI 第一人称解说

交互式生成视频解说：

1. 输入视频文件路径
2. 输入解说主题（可选）
3. 选择 AI 生成或自定义解说词
4. 自动生成配音和字幕
5. 导出剪映草稿

### 剪映草稿导出

将视频导出为剪映可导入的草稿格式：

1. 输入视频文件路径
2. 输入项目名称
3. 选择输出目录
4. 自动生成剪映草稿文件

## 环境变量

通过环境变量配置 API Key 和运行参数：

```bash
### LLM API Key
export DEEPSEEK_API_KEY="sk-your-deepseek-key"
export QWEN_API_KEY="sk-your-qwen-key"
export OPENAI_API_KEY="sk-your-openai-key"

### 调试模式
export SCENEFAB_DEBUG=true

### 缓存目录
export SCENEFAB_CACHE_DIR="~/.cache/scenefab"
```

或使用 `.env` 文件：

```bash
### .env
DEEPSEEK_API_KEY=sk-your-deepseek-key
QWEN_API_KEY=sk-your-qwen-key
SCENEFAB_DEBUG=false
```

## Python 模块调用

```bash
### 通过 python -m 调用
python -m scenefab
```

## 配置文件

配置文件位于项目根目录的 `config/` 目录：

```text
config/
├── app_config.yaml    # 应用配置（缓存、视频参数、TTS、LLM）
└── llm.yaml           # LLM 专用配置（API Key、模型）
```

## 常见问题

### FFmpeg 未找到

```bash
### 检查 FFmpeg
ffmpeg -version

### macOS 安装
brew install ffmpeg

### Ubuntu 安装
sudo apt install ffmpeg
```

### GUI 无法启动

如果 PySide6 未安装，SceneFab 会自动切换到命令行模式：

```bash
### 安装 PySide6
pip install PySide6

### 或使用命令行模式（无需 PySide6）
scenefab
```

### API Key 未配置

确保至少配置了一个 LLM 提供者的 API Key：

```bash
### 检查配置
cat config/llm.yaml
```

详见 [AI 配置](/guide/ai-configuration)。

## 相关文档

- [快速开始](/guide/quick-start) — 3 步上手
- [安装指南](/guide/installation) — 各平台安装步骤
- [疑难排查](/guide/troubleshooting) — 常见问题解决
