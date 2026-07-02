---
title: 安装指南
description: 在 Windows、macOS 和 Linux 上完整安装 SceneFab 的详细步骤。
---

# 安装指南

## 系统要求

| 组件 | 最低要求 | 推荐配置 |
|------|---------|---------|
| 操作系统 | Windows 10 / macOS 12 / Ubuntu 20.04 | 最新稳定版 |
| CPU | 4 核 | 8 核+ |
| 内存 | 8 GB | 16 GB+ |
| 显卡 | 集成显卡 | NVIDIA 4GB+（加速 AI 推理） |
| 磁盘 | 5 GB | 10 GB+ |
| Python | 3.10+ | 3.12 |
| FFmpeg | 6.x | 最新稳定版 |

## Windows

### 方式一：安装包（推荐）

1. 从 [GitHub Releases](https://github.com/Agions/scene-fab/releases) 下载 `.exe` 安装包
2. 运行安装程序，按照向导完成安装
3. 启动 SceneFab

### 方式二：pip

```powershell
### 确认 Python 版本
python --version   # 需 Python 3.10+

### 安装 SceneFab
pip install scenefab

### 启动
scenefab
```

## macOS

### 方式一：pip（推荐）

```bash
### 安装依赖
brew install python@3.12 ffmpeg

### 安装 SceneFab
pip3 install scenefab

### 启动
scenefab
```

### 方式二：源码安装

```bash
git clone https://github.com/Agions/scene-fab.git
cd scene-fab
pip install -e ".[dev]"
```

## Linux (Ubuntu/Debian)

```bash
### 安装系统依赖
sudo apt update
sudo apt install -y python3 python3-pip python3-venv ffmpeg \
  libsm6 libxext6 libgl1 libegl1 libxkbcommon0 libdbus-1-3

### 安装 SceneFab
pip install scenefab

### 启动
scenefab
```

## 依赖说明

| 依赖 | 版本 | 用途 | 安装方式 |
|------|------|------|---------|
| Python | 3.10+ | 运行时环境 | 系统包管理器 |
| FFmpeg | 6.x | 音视频处理 | 系统包管理器 |
| PySide6 | 6.9+ | Qt 桌面 UI | pip（自动安装） |
| OpenCV | 4.8+ | 视频帧处理 | pip（自动安装） |

## 验证安装

```bash
### 检查版本
scenefab --version
### 输出: scenefab 2.1.2

### 检查 FFmpeg
ffmpeg -version

### 检查 Python
python3 --version
```

## 可选依赖

### AI 完整模式（含 Whisper 语音识别）

```bash
pip install scenefab[ai-full]
```

此模式会安装 `faster-whisper` 和 `torch`（约 2GB+），支持本地语音识别。

### 翻译功能

```bash
pip install scenefab[translation]
```

### HTTP API 服务

```bash
pip install scenefab[api]
```

### 全部可选功能

```bash
pip install scenefab[all]
```

## 卸载

```bash
pip uninstall scenefab
```

卸载前请确保已导出所有项目文件。配置文件位于 `~/.scenefab/`，可手动删除。

## 相关文档

- [快速开始](/guide/quick-start) — 3 步上手
- [AI 配置](/guide/ai-configuration) — 配置 AI 服务商
