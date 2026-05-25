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
| 系统 | Win10/macOS12/Ubuntu20 | 同左 |
| 磁盘 | 5 GB | 10 GB+ |

## Windows

### 方式一：安装包（推荐）

1. 从 [GitHub Releases](https://github.com/Agions/scene-fab/releases) 下载 `.exe` 安装包
2. 运行安装程序
3. 安装完成后，在开始菜单找到 **SceneFab** 并启动

### 方式二：pip

```powershell
# 确保已安装 Python 3.10+
python --version

pip install scenefab
scenefab
```

### 方式三：WSL + 源码

```bash
# WSL2 Ubuntu
sudo apt update && sudo apt upgrade -y
sudo apt install python3.10-venv ffmpeg libsm6 libxext6 libgl1
git clone https://github.com/Agions/scene-fab.git
cd scene-fab
python3 -m venv venv
source venv/bin/activate
pip install -e .
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
# 需要先安装 python3.10+ 和 ffmpeg
brew install python@3.11 ffmpeg
pip3 install scenefab
scenefab
```

## Linux (Ubuntu/Debian)

```bash
# 安装系统依赖
sudo apt update
sudo apt install -y python3.10 python3-pip python3.10-venv ffmpeg libsm6 libxext6 libgl1

# 克隆并安装
git clone https://github.com/Agions/scene-fab.git
cd scene-fab
python3 -m venv venv
source venv/bin/activate
pip install -e .

# 运行
scenefab
```

## 依赖说明

| 依赖 | 版本 | 用途 | 安装方式 |
|------|------|------|---------|
| Python | 3.10+ | 运行语言 | 系统 |
| FFmpeg | latest | 音视频处理 | 系统包 |
| PySide6 | 6.5+ | Qt 桌面 UI | pip |
| DeepSeek SDK | - | API 调用 | pip |

## 验证安装

```bash
scenefab --version
# 输出: scenefab 2.0.0
```

## 卸载

```bash
pip uninstall scenefab
# 或 Homebrew:
brew uninstall scenefab
```

:::warning
卸载前请确保已导出所有项目文件！
:::
