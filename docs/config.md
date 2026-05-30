---
title: 配置参考
description: SceneFab 环境变量配置详解。
---

# 配置参考

所有配置通过 `.env` 文件管理（项目根目录，已加入 `.gitignore`）。

::: tip
API Key 安全存储优先使用 OS Keychain，降级为加密文件。详见 [安全设计](./security)。
:::

---

## 必需变量

| 变量 | 说明 | 获取 |
|------|------|------|
| `DEEPSEEK_API_KEY` | DeepSeek V4 API Key（解说生成） | [platform.deepseek.com](https://platform.deepseek.com) |
| `DASHSCOPE_API_KEY` | 阿里云百炼 API Key（Qwen2.5-VL 视频理解） | [bailian.console.aliyun.com](https://bailian.console.aliyun.com) |

---

## 可选变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `DEEPSEEK_BASE_URL` | `https://api.deepseek.com` | API 地址（可配置代理） |
| `DEEPSEEK_MODEL` | `deepseek-chat` | DeepSeek 模型 |
| `DASHSCOPE_BASE_URL` | `https://dashscope.aliyuncs.com` | 阿里云 API 地址 |
| `DASHSCOPE_MODEL` | `qwen2.5-vl-7b-instruct` | 视频理解模型 |
| `TTS_ENGINE` | `edge-tts` | TTS 引擎：`edge-tts` / `f5-tts` / `openai` |
| `DEFAULT_EMOTION` | `heal` | 默认情感风格 |
| `OUTPUT_DIR` | `~/Videos/SceneFab` | 默认输出目录 |
| `FFMPEG_PATH` | `ffmpeg` | FFmpeg 路径 |
| `HTTP_PROXY` / `HTTPS_PROXY` | — | 代理地址（如需） |

---

## 完整示例

```env
# AI API Keys
DEEPSEEK_API_KEY=sk-xxx...xxxx
DASHSCOPE_API_KEY=sk-xxx...xxxx

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
OUTPUT_DIR=~/Videos/SceneFab
```

---

## 配置文件

SceneFab 使用以下配置文件（位于 `~/.scenefab/`）：

| 文件 | 说明 |
|------|------|
| `config.yaml` | 主配置文件（应用级设置） |
| `credentials.enc` | 加密 API Key（Keychain 不可用时降级） |
| `projects/` | 项目文件目录 |

### config.yaml 示例

```yaml
# ~/.scenefab/config.yaml
app:
  version: "3.0.0"
  language: zh-CN
  theme: dark

video:
  default_format: mp4
  default_codec: h264
  ffmpeg_path: ffmpeg
  temp_dir: /tmp/scenefab

export:
  output_dir: ~/Videos/SceneFab
  quality_preset: high
  include_subtitles: true
```

---

## 代理配置

```env
HTTP_PROXY=http://127.0.0.1:7890
HTTPS_PROXY=http://127.0.0.1:7890
```

DeepSeek 和阿里云通常国内直连，无需代理。

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