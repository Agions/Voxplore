---
title: AI 服务配置
description: 配置 SceneFab 所使用的 AI 服务（DeepSeek / Qwen3.7 / Edge-TTS）。
---

# AI 服务配置

SceneFab 支持配置多个 AI 服务商，所有配置在本地存储，绝不外传。

---

## DeepSeek（解说稿生成）

### 获取 API Key

1. 访问 [platform.deepseek.com](https://platform.deepseek.com) → API Keys → Create
2. 推荐使用 **DeepSeek-V4** 模型（性价比最高）

### 配置项

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| API Key | 你的 DeepSeek API Key | — |
| 模型 | DeepSeek-V4 / DeepSeek-Coder | DeepSeek-V4 |
| Base URL | API 端点 | https://api.deepseek.com |
| Max Tokens | 单次最大输出 | 4096 |
| Temperature | 创造性（0=确定输出，1=最大随机） | 0.7 |

### 费用估算

| 操作 | tokens 消耗 | 费用 |
|------|------------|------|
| 5 分钟视频解说生成 | ~50K tokens | ~0.05 元 |
| 2 小时电影解说生成 | ~500K tokens | ~0.5 元 |

---

## Qwen3.7（视频语义分析）

### 获取 API Key

1. 访问 [阿里云百炼](https://bailian.console.aliyun.com/) → API Keys → 创建
2. 选择 `qwen3.7-max` 模型

### 配置项

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| API Key | 你的阿里云 API Key | — |
| 模型 | qwen3.7-max / qwen3.7-plus | qwen3.7-max |
| Base URL | API 端点 | https://dashscope.aliyuncs.com |

### 费用估算

| 操作 | 调用次数 | 费用 |
|------|---------|------|
| 5 分钟视频分析 | ~300 次 | ~0.03 元 |
| 2 小时电影分析 | ~2000 次 | ~0.2 元 |

---

## Edge TTS（配音合成）

**免费使用，无需 API Key！**

微软官方 TTS 引擎，50+ 音色，支持中文。

### 推荐音色

| 音色 ID | 名称 | 适用风格 |
|--------|------|---------|
| zh-CN-XiaoxiaoNeural | 晓晓 | 治愈、浪漫、怀旧 |
| zh-CN-YunxiNeural | 云希 | 悬疑、励志 |
| zh-CN-YunyangNeural | 云扬 | 纪录片、正式 |
| zh-CN-XiaoyiNeural | 小艺 | 幽默、轻松 |

### 高级参数

| 参数 | 范围 | 说明 |
|------|------|------|
| 语速 | 0.5x – 2.0x | 默认 1.0x |
| 音调 | -50% – +50% | 默认 0 |
| 音量 | -50% – +50% | 默认 0 |

---

## F5-TTS（音色克隆，可选）

### 安装

```bash
pip install f5-tts
```

### 使用方式

1. 准备参考音频（MP3/WAV，15–30 秒，说话清晰）
2. 设置 → 配音配置 → F5-TTS → 上传参考音频
3. AI 自动克隆音色，后续配音使用克隆音色

### 费用

完全本地运行，GPU 加速，无 API 费用。

---

## 一键配置

在项目根目录创建 `.env`：

```bash
# DeepSeek（解说稿生成）
DEEPSEEK_API_KEY=sk-xxx...xxxx

# 阿里云 Qwen3.7（视频分析）
DASHSCOPE_API_KEY=sk-xxx...xxxx
```

---

## 多服务商支持

| 服务 | 支持状态 | 说明 |
|------|---------|------|
| DeepSeek | ✅ 正式支持 | 推荐，性价比最高 |
| OpenAI GPT-4 | ✅ 可配置 | 需自行修改端点 |
| Qwen3.7 | ✅ 正式支持 | 视频理解必选 |
| Edge TTS | ✅ 内置免费 | 配音合成 |
| F5-TTS | ✅ 本地运行 | 音色克隆 |

---

## 故障排查

### 401 Unauthorized

API Key 无效或已过期，检查 Key 是否正确复制。

### 429 Rate Limit

触发了 API 限流，1 分钟后重试，或在服务商控制台升级套餐。

### 视频分析超时

长视频（1 小时+）建议分段处理，或降低抽帧频率（设置 → AI 配置 → 抽帧间隔改为 2 秒）。
