---
title: 配置参考
description: SceneFab 环境变量、配置文件与高级设置详解。
---

# 配置参考

所有配置通过 `.env` 文件管理（项目根目录，已加入 `.gitignore`）。

::: tip
API Key 安全存储优先使用 OS Keychain，降级为加密文件。详见 [安全设计](./security)。
:::

---

## 必需变量

| 变量 | 说明 | 获取方式 |
|------|------|----------|
| `DEEPSEEK_API_KEY` | DeepSeek V4 API Key（解说生成） | [platform.deepseek.com](https://platform.deepseek.com) |
| `DASHSCOPE_API_KEY` | 阿里云百炼 API Key（Qwen2.5-VL 视频理解） | [bailian.console.aliyun.com](https://bailian.console.aliyun.com) |

---

## 可选变量

### AI 服务配置

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `DEEPSEEK_BASE_URL` | `https://api.deepseek.com` | API 地址（可配置代理） |
| `DEEPSEEK_MODEL` | `deepseek-chat` | DeepSeek 模型 |
| `DEEPSEEK_MAX_TOKENS` | `4096` | 最大生成 token 数 |
| `DEEPSEEK_TEMPERATURE` | `0.7` | 生成温度（0-2） |
| `DASHSCOPE_BASE_URL` | `https://dashscope.aliyuncs.com` | 阿里云 API 地址 |
| `DASHSCOPE_MODEL` | `qwen2.5-vl-7b-instruct` | 视频理解模型 |

### TTS 配置

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `TTS_ENGINE` | `edge-tts` | TTS 引擎：`edge-tts` / `f5-tts` / `openai` |
| `TTS_VOICE` | `zh-CN-XiaoxiaoNeural` | 默认音色 |
| `TTS_RATE` | `+0%` | 语速调整（-50% ~ +50%） |
| `TTS_PITCH` | `+0Hz` | 音调调整 |

### 视频处理配置

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `FFMPEG_PATH` | `ffmpeg` | FFmpeg 路径 |
| `FRAME_INTERVAL` | `1` | 抽帧间隔（秒） |
| `MIN_SCENE_LENGTH` | `5` | 最小场景长度（秒） |
| `CONFIDENCE_THRESHOLD` | `0.6` | 置信度阈值 |

### 导出配置

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `OUTPUT_DIR` | `~/Videos/SceneFab` | 默认输出目录 |
| `EXPORT_FORMAT` | `mp4` | 导出格式：`mp4` / `mov` / `jianying` |
| `VIDEO_CODEC` | `h264` | 视频编码：`h264` / `h265` |
| `VIDEO_QUALITY` | `high` | 视频质量：`low` / `medium` / `high` |

### 情感风格配置

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `DEFAULT_EMOTION` | `heal` | 默认情感风格 |
| `NARRATION_STYLE` | `first_person` | 解说视角：`first_person` / `third_person` |

### 网络配置

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `HTTP_PROXY` | — | HTTP 代理地址 |
| `HTTPS_PROXY` | — | HTTPS 代理地址 |
| `REQUEST_TIMEOUT` | `30` | 请求超时时间（秒） |
| `MAX_RETRIES` | `3` | 最大重试次数 |

---

## 完整示例

```env
# ═══════════════════════════════════════════════════════════
# AI API Keys
# ═══════════════════════════════════════════════════════════
DEEPSEEK_API_KEY=sk-xxx...xxxx
DASHSCOPE_API_KEY=sk-xxx...xxxx

# ═══════════════════════════════════════════════════════════
# DeepSeek 配置
# ═══════════════════════════════════════════════════════════
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat
DEEPSEEK_MAX_TOKENS=4096
DEEPSEEK_TEMPERATURE=0.7

# ═══════════════════════════════════════════════════════════
# 阿里云百炼配置
# ═══════════════════════════════════════════════════════════
DASHSCOPE_BASE_URL=https://dashscope.aliyuncs.com
DASHSCOPE_MODEL=qwen2.5-vl-7b-instruct

# ═══════════════════════════════════════════════════════════
# TTS 配置
# ═══════════════════════════════════════════════════════════
TTS_ENGINE=edge-tts
TTS_VOICE=zh-CN-XiaoxiaoNeural
TTS_RATE=+0%
TTS_PITCH=+0Hz

# ═══════════════════════════════════════════════════════════
# 视频处理配置
# ═══════════════════════════════════════════════════════════
FFMPEG_PATH=ffmpeg
FRAME_INTERVAL=1
MIN_SCENE_LENGTH=5
CONFIDENCE_THRESHOLD=0.6

# ═══════════════════════════════════════════════════════════
# 导出配置
# ═══════════════════════════════════════════════════════════
OUTPUT_DIR=~/Videos/SceneFab
EXPORT_FORMAT=mp4
VIDEO_CODEC=h264
VIDEO_QUALITY=high

# ═══════════════════════════════════════════════════════════
# 情感风格配置
# ═══════════════════════════════════════════════════════════
DEFAULT_EMOTION=heal
NARRATION_STYLE=first_person

# ═══════════════════════════════════════════════════════════
# 网络配置
# ═══════════════════════════════════════════════════════════
HTTP_PROXY=http://127.0.0.1:7890
HTTPS_PROXY=http://127.0.0.1:7890
REQUEST_TIMEOUT=30
MAX_RETRIES=3
```

---

## 配置文件

SceneFab 使用以下配置文件（位于 `~/.scenefab/`）：

| 文件 | 说明 | 格式 |
|------|------|------|
| `config.yaml` | 主配置文件（应用级设置） | YAML |
| `credentials.enc` | 加密 API Key（Keychain 不可用时降级） | 二进制 |
| `projects/` | 项目文件目录 | — |
| `logs/` | 日志文件目录 | — |

### config.yaml 示例

```yaml
# ~/.scenefab/config.yaml
app:
  version: "3.0.0"
  language: zh-CN
  theme: dark
  log_level: INFO

video:
  default_format: mp4
  default_codec: h264
  ffmpeg_path: ffmpeg
  temp_dir: /tmp/scenefab
  max_concurrent: 2

ai:
  provider_priority:
    - deepseek
    - openai
    - claude
  cache_enabled: true
  cache_ttl: 3600

export:
  output_dir: ~/Videos/SceneFab
  quality_preset: high
  include_subtitles: true
  include_audio: true

tts:
  engine: edge-tts
  voice: zh-CN-XiaoxiaoNeural
  rate: "+0%"
  pitch: "+0Hz"
```

---

## 代理配置

```env
# HTTP 代理
HTTP_PROXY=http://127.0.0.1:7890
HTTPS_PROXY=http://127.0.0.1:7890

# SOCKS5 代理
HTTP_PROXY=socks5://127.0.0.1:1080
HTTPS_PROXY=socks5://127.0.0.1:1080
```

DeepSeek 和阿里云通常国内直连，无需代理。

---

## 环境变量优先级

```
命令行参数 > 环境变量 > .env 文件 > config.yaml > 默认值
```

---

## 故障排除

### 配置文件不生效

1. 确认 `.env` 文件在项目根目录
2. 验证 YAML 语法
3. 使用 `--debug` 参数启动：
```bash
scenefab --debug
```

### API Key 无效（401）

确认 Key 格式正确（`sk-` 开头）且未过期或被删除。

### 触发限流（429）

降低并发请求数，或在服务商控制台升级套餐。

### 配置冲突

```bash
# 查看当前生效的配置
scenefab --show-config

# 重置为默认配置
scenefab --reset-config
```
