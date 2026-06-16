---
title: 完整安装指南
description: 在 Windows macOS Linux 上完整安装 SceneFab 的详细步骤。
---

# 完整安装指南

## 系统要求

| 组件 | 最低要求 | 推荐配置 |
|------|---------|---------|
| CPU | 4 核 | 8 核+ |
| 内存 | 8 GB | 16 GB+ |
| 显卡 | 集成 | NVIDIA 4GB+（加速 AI 推理） |
| 磁盘 | 5 GB | 10 GB+ |

## Windows

### 方式一：安装包（推荐）

1. 从 [GitHub Releases](https://github.com/Agions/scene-fab/releases) 下载 `.exe` 安装包
2. 运行安装程序，启动 SceneFab

### 方式二：pip

```powershell
python --version   # 需 Python 3.10+
pip install scenefab
scenefab
```

## macOS

### 方式一：Homebrew（推荐）

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
brew install scenefab
scenefab
```

### 方式二：pip

```bash
brew install python@3.11 ffmpeg
pip3 install scenefab
scenefab
```

## Linux (Ubuntu/Debian)

```bash
sudo apt update
sudo apt install -y python3.10 python3-pip python3.10-venv ffmpeg libsm6 libxext6 libgl1
pip install scenefab
scenefab
```

## 依赖说明

| 依赖 | 版本 | 用途 | 安装方式 |
|------|------|------|---------|
| Python | 3.10+ | 运行语言 | 系统 |
| FFmpeg | latest | 音视频处理 | 系统包 |
| PySide6 | 6.5+ | Qt 桌面 UI | pip |
| DeepSeek SDK | — | API 调用 | pip |

## 验证安装

```bash
scenefab --version
# 输出: scenefab 2.2.0
```

## 卸载

```bash
pip uninstall scenefab
# 或 Homebrew:
brew uninstall scenefab
```

::: warning
卸载前请确保已导出所有项目文件！
:::
