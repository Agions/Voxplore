---
title: 配置参考
description: Voxplore 配置文件详解和环境变量完整参考。
---

# 配置参考

Voxplore 支持灵活的配置文件和环境变量配置，所有配置均通过 `.env` 文件管理（项目根目录，已加入 `.gitignore`）。

---

## 环境变量

### 必需变量

| 变量 | 说明 | 获取地址 |
|------|------|----------|
| `DEEPSEEK_API_KEY` | DeepSeek V3.2 API Key（解说生成，默认） | [platform.deepseek.com](https://platform.deepseek.com) |
| `DASHSCOPE_API_KEY` | 阿里云百炼 API Key（Qwen2.5-VL 视频理解） | [bailian.console.aliyun.com](https://bailian.console.aliyun.com) |

### 可选变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `DEEPSEEK_BASE_URL` | `https://api.deepseek.com` | DeepSeek API 地址（可配置代理） |
| `DEEPSEEK_MODEL` | `deepseek-chat` | DeepSeek 模型（可选 deepseek-reasoner） |
| `DASHSCOPE_BASE_URL` | `https://dashscope.aliyuncs.com` | 阿里云 API 地址 |
| `DASHSCOPE_MODEL` | `qwen2.5-vl-7b-instruct` | 视频理解模型 |
| `TTS_ENGINE` | `edge-tts` | TTS 引擎：`edge-tts` / `f5-tts` / `openai` |
| `DEFAULT_EMOTION` | `heal` | 默认情感风格 |
| `OUTPUT_DIR` | `~/Videos/Voxplore` | 默认输出目录 |
| `FFMPEG_PATH` | `ffmpeg` | FFmpeg 可执行文件路径 |
| `HTTP_PROXY` | — | HTTP 代理地址（如需） |
| `HTTPS_PROXY` | — | HTTPS 代理地址 |

### 完整示例

```env
# AI API Keys
DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxx
DASHSCOPE_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxx

# DeepSeek 配置
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat

# 阿里云百炼配置
DASHSCOPE_BASE_URL=https://dashscope.aliyuncs.com
DASHSCOPE_MODEL=qwen2.5-vl-7b-instruct

# TTS 配置
TTS_ENGINE=edge-tts

# 默认情感风格（heal / mystery / inspiration / nostalgia / romance）
DEFAULT_EMOTION=heal

# 输出配置
OUTPUT_DIR=~/Videos/Voxplore

# FFmpeg（通常无需配置）
FFMPEG_PATH=ffmpeg

# 代理（如需要）
# HTTP_PROXY=http://127.0.0.1:7890
# HTTPS_PROXY=http://127.0.0.1:7890
```

---

## 配置文件

Voxplore 使用以下配置文件（位于 `~/.narrafiilm/`）：

| 文件 | 说明 |
|------|------|
| `config.yaml` | 主配置文件（应用级设置） |
| `credentials.enc` | 加密存储的 API Key（Keychain 不可用时降级） |
| `projects/` | 项目文件目录 |
| `logs/` | 应用日志 |

### config.yaml 结构

```yaml
# ~/.narrafiilm/config.yaml

app:
  version: "3.6.0"
  language: zh-CN
  theme: system          # system / light / dark
  auto_save_interval: 60  # 秒

video:
  default_format: mp4
  default_codec: h264    # h264 / h265
  ffmpeg_path: ffmpeg
  temp_dir: /tmp/narrafiilm

export:
  output_dir: ~/Videos/Voxplore
  quality_preset: high   # low / medium / high
  include_subtitles: true
```

---

## AI 提供商配置

### DeepSeek（解说生成 — 默认）

```env
DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxx
DEEPSEEK_MODEL=deepseek-chat
```

DeepSeek V3.2 成本约为 GPT-4o 的 **1/50**，中文理解能力强，为默认推荐。

### 阿里云百炼（视频理解 — 默认）

```env
DASHSCOPE_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxx
DASHSCOPE_MODEL=qwen2.5-vl-7b-instruct
```

Qwen2.5-VL（7B）为当前最优开源视频理解模型，也支持 72B 版本：

```env
DASHSCOPE_MODEL=qwen2.5-vl-72b-instruct
```

### OpenAI（全栈备选）

```env
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxx
OPENAI_MODEL=gpt-4.1
```

### Anthropic Claude

```env
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxxxxxxxxxxxxx
ANTHROPIC_MODEL=claude-opus-4.6-20260219
```

---

## TTS 引擎配置

### Edge-TTS（默认·无需安装）

```env
TTS_ENGINE=edge-tts
```

开箱即用，支持多音色，详见 [AI 工作流](./guide/ai-video-guide)。

### F5-TTS（可选·音色克隆）

```env
TTS_ENGINE=f5-tts
```

需要独立安装，详见[安装指南](./guide/installation#f5-tts-音色克隆)。

### OpenAI TTS

```env
TTS_ENGINE=openai
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxx
```

---

## 代理配置

如需通过代理访问 AI API：

```env
HTTP_PROXY=http://127.0.0.1:7890
HTTPS_PROXY=http://127.0.0.1:7890
```

DeepSeek 和阿里云通常无需代理（国内直连）。

---

## 故障排除

### 配置文件不生效

1. 确认 `.env` 文件在项目根目录
2. 验证 YAML 语法（YAML 对缩进敏感）
3. 使用 `--debug` 参数启动查看加载日志：

```bash
python app/main.py --debug
```

### API Key 安全存储

Voxplore 优先使用 OS Keychain 存储 Key：

| 系统 | 存储方式 |
|------|----------|
| macOS | Keychain Services |
| Windows | Credential Manager |
| Linux | Secret Service API (GNOME Keyring / KWallet) |

Keychain 不可用时，降级为 Fernet 加密文件 `~/.narrafiilm/credentials.enc`。

详见 [安全设计](./security)。
