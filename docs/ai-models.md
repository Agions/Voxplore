---
title: AI 模型配置
description: Voxplore 支持的 AI 模型一览与配置指南。
---

# AI 模型配置

Voxplore 的 AI 模型分三层：**视频理解**、**解说生成**、**配音合成**。

---

## 视频理解模型

负责逐帧分析视频画面，识别主角、地点、动作、氛围。

| 模型 | 说明 | 推荐度 |
|------|------|--------|
| **Qwen2.5-VL (72B)** | 阿里开源，视频理解 SOTA，支持 Native 视频输入 | ⭐⭐⭐⭐⭐ |
| **Qwen3-VL (8B/32B)** | Qwen 2025 开源，推理比 2.5 更慢，准确度差异不大 | ⭐⭐⭐ |
| **GPT-4o** | OpenAI 旗舰多模态，能力强但费用高 | ⭐⭐⭐ |
| **Gemini 2.5 Flash** | Google 高性价比主力 | ⭐⭐⭐⭐ |

> **默认使用 Qwen2.5-VL (72B)**，平衡精度与速度。

---

## 解说生成模型

负责将画面分析结果转化为第一人称解说稿。

| 模型 | 说明 | 推荐度 |
|------|------|--------|
| **DeepSeek-V3** | 性价比最高，中文理解强，API 成本极低 | ⭐⭐⭐⭐⭐ |
| **GPT-4o** | OpenAI 旗舰，最强通用能力 | ⭐⭐⭐⭐ |
| **Claude Sonnet 4** | Anthropic 旗舰，超长上下文 | ⭐⭐⭐⭐ |
| **Qwen2.5-Max** | 阿里中文优化，API 稳定 | ⭐⭐⭐ |

> **默认使用 DeepSeek-V3**，成本约为 GPT-4o 的 **1/50**。

---

## 语音识别模型（ASR）

负责将原片音频转文字，辅助场景理解。

| 模型 | 说明 | 部署方式 |
|------|------|----------|
| **SenseVoice** | 阿里 FunAudioLLM，中文 ASR + 说话人分离 | 本地 |
| **Whisper** | OpenAI 开源，多语言识别 | 本地 |
| **云端 ASR** | API 调用第三方服务 | 云端 |

> **默认使用 SenseVoice**，完全本地运行，视频不上传。

---

## 配音合成模型（TTS）

负责将解说稿转化为自然语音。

| 模型 | 质量 | 费用 | 特点 |
|------|------|------|------|
| **Edge-TTS** | ⭐⭐⭐⭐⭐ | 免费 | 低延迟，多音色，Voxplore 默认 |
| **F5-TTS** | ⭐⭐⭐⭐ | 免费 | 零样本音色克隆，需 15–30s 参考音频 |
| **OpenAI TTS** | ⭐⭐⭐⭐⭐ | 付费 | 超自然，但需付费 |

---

## 快速配置

### DeepSeek（默认，推荐）

```bash
# 获取 Key：https://platform.deepseek.com
export DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxx
```

### OpenAI GPT-4o

```bash
export OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
```

### Claude Sonnet 4

```bash
export ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxxxxx
```

### 阿里云百炼（Qwen2.5-VL）

```bash
# https://bailian.console.aliyun.com
export DASHSCOPE_API_KEY=sk-xxxxxxxxxxxxxxxx
```

---

## 模型选择建议

| 预算 | 视频理解 | 解说生成 | 配音 |
|------|----------|----------|------|
| **免费** | Qwen2.5-VL 本地 | DeepSeek-V3 | Edge-TTS |
| **低 <¥50/月** | Qwen2.5-VL API | DeepSeek-V3 | Edge-TTS |
| **中 ¥50–300/月** | Qwen2.5-VL API | GPT-4o | Edge-TTS |
| **高 >¥300/月** | GPT-4o | Claude Sonnet 4 | OpenAI TTS |

---

## API Key 安全

::: warning 安全提示
- **不要** 将 API Key 提交到代码仓库
- 使用 `.env` 文件（已加入 .gitignore）或系统 Keychain 存储
- 定期检查用量异常
:::
