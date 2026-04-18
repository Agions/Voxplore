---
title: 快速开始
description: Voxplore 安装与首次使用的完整指南。
---

# 快速开始

本文档是 Voxplore 的完整安装与配置指南。如果你想快速上手，推荐阅读 [5 分钟快速开始](./quick-start)。

---

## 环境要求

| 要求 | 最低配置 | 推荐配置 |
|------|----------|----------|
| 操作系统 | Windows 10 / macOS 11 / Ubuntu 20.04 | Windows 11 / macOS 13 / Ubuntu 22.04 |
| CPU | Intel i5 / Apple M1 | Intel i7 / Apple M2+ |
| 内存 | 8 GB | 16 GB+ |
| 显卡 | NVIDIA 4GB / 集成显卡 | NVIDIA 8GB+ |
| 磁盘 | 10 GB 可用空间 | 20 GB SSD |

::: tip GPU 加速
NVIDIA 显卡配合 CUDA 可显著加速 AI 处理。如无独显，Voxplore 会在 CPU 模式下运行（速度较慢但功能完整）。
:::

---

## 安装步骤

### 方式一：下载安装包（推荐）

1. 访问 [GitHub Releases](https://github.com/Agions/Voxplore/releases)
2. 下载对应平台的最新版本：

| 平台 | 安装包 | 说明 |
|------|--------|------|
| Windows | `Voxplore-Setup-x.x.x.exe` | 运行安装程序 |
| macOS | `Voxplore-x.x.x.dmg` | 拖入 Applications |
| Linux | `Voxplore-x.x.x.AppImage` | 添加执行权限后运行 |

### 方式二：Homebrew（macOS / Linux）

```bash
brew install narrafiilm
```

### 方式三：从源码构建

```bash
# 克隆项目
git clone https://github.com/Agions/Voxplore.git
cd Voxplore

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate   # Windows

# 安装依赖
pip install -r requirements.txt

# 复制环境配置
cp .env.example .env

# 运行应用
python app/main.py
```

---

## 首次配置

### 1. 安装 FFmpeg

Voxplore 需要 FFmpeg 进行视频处理。安装方式：

```bash
# macOS
brew install ffmpeg

# Ubuntu / Debian
sudo apt update && sudo apt install ffmpeg

# Windows
# 访问 https://ffmpeg.org/download.html 下载并添加到 PATH
```

验证安装：

```bash
ffmpeg -version
```

### 2. 配置 AI 模型

启动应用后，进入 **设置 → AI 配置** 配置 API Key。

或在 `.env` 文件中配置（项目根目录）：

```env
# 推荐配置（免费额度）
DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxx

# 备选配置
# OPENAI_API_KEY=sk-your-key
# DASHSCOPE_API_KEY=your-key
```

支持的 AI 提供商和获取方式：

| 提供商 | 获取地址 | 免费额度 |
|--------|----------|----------|
| DeepSeek | [platform.deepseek.com](https://platform.deepseek.com) | ✅ 有免费额度 |
| OpenAI | [platform.openai.com](https://platform.openai.com) | $5 新用户 |
| 通义千问 | [dashscope.console.aliyun.com](https://dashscope.console.aliyun.com) | ✅ 有免费额度 |
| Kimi | [platform.moonshot.cn](https://platform.moonshot.cn) | ✅ 有免费额度 |
| Ollama | [ollama.ai](https://ollama.ai) | 🔒 完全免费（本地） |

### 3. 验证配置

进入 **设置 → AI 配置**，点击 **连接测试**。

看到 `✅ AI 服务连接正常` 即配置成功。

---

## 快速教程

### 1. 创建新项目

1. 点击 **新建项目**
2. 选择项目保存位置
3. 输入项目名称
4. 选择创作模式

### 2. 导入视频素材

- 点击 **导入素材** 或直接拖拽文件到窗口
- 支持格式：`MP4`, `MOV`, `AVI`, `MKV`, `WebM`

### 3. 配置创作参数

| 参数 | 选项 | 说明 |
|------|------|------|
| 情感风格 | 治愈 / 悬疑 / 励志 / 怀旧 / 浪漫 | 解说语气风格 |
| 解说长度 | 简洁版 / 标准版 / 详细版 | 每段解说字数 |
| 配音音色 | XiaoXiao / Yunxi / Xiaoyi / Yunyang | Edge-TTS 内置音色 |
| 字幕样式 | 电影黑底白字 / 透明覆盖 / 卡片式 | ASS 字幕样式 |
| 是否保留原音 | 是 / 否 | 保留原片音频作为背景音 |

### 4. 调整参数

根据需要调整：

| 参数 | 说明 |
|------|------|
| 剪辑风格 | 电影感 / 快节奏 / 轻松随意 |
| 输出格式 | MP4 / MOV / WebM |
| 画质 | 高质量 / 标准 / 快速预览 |
| 字幕样式 | 电影字幕 / 解说字幕 / 无字幕 |

### 5. 导出成片

1. 点击 **导出**
2. 选择格式和保存位置
3. 等待处理完成
4. 预览导出结果

---

## 常见问题

### 启动报错 "Module not found"

```bash
pip install -r requirements.txt
```

### FFmpeg 报错 "FFmpeg not found"

确保 FFmpeg 已安装并添加到系统 PATH，然后重启应用。

### AI 功能不工作

1. 检查 API Key 是否配置正确
2. 确认网络连接正常
3. 查看 **帮助 → 查看日志** 获取详细错误

---

## 下一步

- [5 分钟快速开始](./quick-start) — 更精简的上手指南
- [功能详细介绍](../features) — 深入了解 AI 第一人称解说全流程
- [AI 模型配置](../ai-models) — 选择和优化 AI 提供商
- [常见问题](../faq) — 更多问题解答
- [疑难排查](./troubleshooting) — 详细的问题解决指南
