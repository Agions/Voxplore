---
title: 安装指南
description: 在 Windows、macOS 和 Linux 上完整安装 SceneFab 的详细步骤。
---

# 安装指南

## 系统要求

| 要求 | 最低配置 | 推荐配置 |
|------|----------|----------|
| 操作系统 | Windows 10 / macOS 11 / Ubuntu 20.04 | 最新稳定版 |
| Python | 3.10+ | 3.11+ |
| 内存 | 4 GB | 8 GB+ |
| 磁盘 | 2 GB 可用空间 | 5 GB 可用空间 |
| FFmpeg | 6.0+ | 最新版 |
| GPU | 可选（F5-TTS 需要） | NVIDIA CUDA / Apple Silicon |

## Windows

### 方式一：安装包（推荐）

1. 从 [Releases](https://github.com/Agions/scene-fab/releases) 下载最新 `.exe`
2. 双击运行安装程序
3. 安装完成后，桌面会出现 **SceneFab** 图标

### 方式二：pip

```bash
# 确认 Python 版本
python --version
# 应输出：Python 3.10.x 或更高

# 安装 SceneFab
pip install scenefab

# 验证安装
scenefab --version
```

## macOS

### 方式一：pip（推荐）

```bash
# 确认 Python 版本
python3 --version
# 应输出：Python 3.10.x 或更高

# 安装 SceneFab
pip3 install scenefab

# 验证安装
scenefab --version
```

### 方式二：Homebrew

```bash
# 安装依赖
brew install ffmpeg python@3.11

# 安装 SceneFab
pip3 install scenefab
```

## Linux（Ubuntu/Debian）

### 完整安装脚本

```bash
# 1. 更新系统
sudo apt update && sudo apt upgrade -y

# 2. 安装 Python 3.11
sudo apt install python3.11 python3.11-venv python3-pip -y

# 3. 安装 FFmpeg
sudo apt install ffmpeg -y

# 4. 安装 GUI 依赖（PySide6 需要）
sudo apt install libegl1 libgl1 libxkbcommon-x11-0 libxext6 libsm6 libxrender1 libdbus-1-3 -y

# 5. 创建虚拟环境
python3.11 -m venv ~/.venv/scenefab
source ~/.venv/scenefab/bin/activate

# 6. 安装 SceneFab
pip install --upgrade pip
pip install scenefab

# 7. 验证安装
scenefab --version
```

### 无头环境（无显示器）

```bash
# 使用 offscreen 模式启动
QT_QPA_PLATFORM=offscreen scenefab
```

## 验证安装

运行以下命令确认安装成功：

```bash
# 1. 检查 Python 版本
python --version

# 2. 检查 FFmpeg
ffmpeg -version | head -1

# 3. 检查 SceneFab
scenefab --version

# 4. 检查 GUI 依赖
python -c "from PySide6.QtCore import qVersion; print('Qt', qVersion())"
```

## 常见问题

### FFmpeg 未找到

```bash
# macOS
brew install ffmpeg

# Ubuntu
sudo apt install ffmpeg

# Windows
winget install ffmpeg
```

### GUI 依赖缺失

```bash
# Ubuntu
sudo apt install libegl1 libgl1 libxkbcommon-x11-0 libxext6 libsm6 libxrender1 libdbus-1-3
```

### 虚拟环境最佳实践

```bash
# 创建虚拟环境
python -m venv .venv

# 激活
source .venv/bin/activate  # Linux/macOS
.venv\Scripts\activate     # Windows

# 安装依赖
pip install scenefab
```

## 相关文档

- [快速开始](/guide/quick-start) — 3 步上手
- [界面介绍](/guide/interface) — 了解桌面界面
- [疑难排查](/guide/troubleshooting) — 常见问题解决