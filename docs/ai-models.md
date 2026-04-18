---
title: AI 模型配置
description: Voxplore 支持的 AI 模型一览与配置指南。
---

# AI 模型配置

Voxplore 的 AI 模型分三层：视频理解、解说生成、配音合成。

---

## 视频理解模型（抽帧分析）

负责逐帧分析视频画面，识别主角、地点、动作、氛围。

| 模型 | 说明 | 推荐度 |
|------|------|--------|
| **Qwen2.5-VL (72B)** | 阿里开源，视频理解 SOTA，支持 Native 视频输入 | ⭐⭐⭐⭐⭐ |
| **Qwen3-VL (8B/32B)** | Qwen 2025 开源，Qwen3-VL 比 2.5 推理更慢，准确度差异不大 | ⭐⭐⭐ |
| **GPT-5.4** | OpenAI 最新旗舰，多模态，能力强但费用高 | ⭐⭐⭐ |
| **Gemini 2.5 Flash** | Google 最新主力，性价比高 | ⭐⭐⭐⭐ |

> **Voxplore 默认使用 Qwen2.5-VL (72B)**，平衡了精度与速度。

---

## 解说生成模型（文稿撰写）

负责将画面分析结果转化为第一人称解说稿。

| 模型 | 说明 | 推荐度 |
|------|------|--------|
| **DeepSeek-V3.2** | 性价比最高，中文理解强，API 成本极低 | ⭐⭐⭐⭐⭐ |
| **DeepSeek-V3** | V3.2 的前身，API 兼容 | ⭐⭐⭐⭐ |
| **GPT-5.4** | OpenAI 最新旗舰，最强通用能力 | ⭐⭐⭐⭐ |
| **Claude Opus 4.6** | Anthropic 最新旗舰（2026.02），超长上下文 | ⭐⭐⭐⭐ |
| **Qwen2.5-Max** | 阿里中文优化，API 稳定 | ⭐⭐⭐ |

> **Voxplore 默认使用 DeepSeek-V3.2**，成本约为 GPT-5.4 的 1/50。

---

## 语音识别模型（ASR）

负责将原片音频转文字，辅助场景理解。

| 模型 | 说明 | 部署方式 |
|------|------|----------|
| **SenseVoice** | 阿里 FunAudioLLM，中文 ASR + 说话人分离 | 本地 |
| **Whisper** | OpenAI 开源，多语言识别 | 本地 |
| **云端 ASR** | API 调用第三方服务 | 云端 |

> **Voxplore 默认使用 SenseVoice**，完全本地运行，视频不上传。

---

## 配音合成模型（TTS）

负责将解说稿转化为自然语音。

| 模型 | 版本 | 质量 | 费用 | 特点 |
|------|------|------|------|------|
| **Edge-TTS** | 7.2.8（2026.03） | ⭐⭐⭐⭐⭐ | 免费 | 低延迟，多音色，Voxplore 默认 |
| **F5-TTS** | latest | ⭐⭐⭐⭐ | 免费 | 零样本音色克隆，需 15–30s 参考音频 |
| **OpenAI TTS** | latest | ⭐⭐⭐⭐⭐ | 付费 | 超自然，但需付费 |

---

## 快速配置

### DeepSeek（默认，推荐）

```bash
# 获取 Key：https://platform.deepseek.com
export DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxx

# 应用内设置：设置 → AI 配置 → DeepSeek
```

### OpenAI GPT-5.4

```bash
export OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx

# 应用内设置：设置 → AI 配置 → OpenAI → GPT-5.4
```

### Claude Opus 4.6

```bash
export ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxxxxx

# 应用内设置：设置 → AI 配置 → Anthropic → Claude Opus 4.6
```

### 阿里云百炼（Qwen2.5-VL）

```bash
# https://bailian.console.aliyun.com
export DASHSCOPE_API_KEY=sk-xxxxxxxxxxxxxxxx

# 应用内设置：设置 → AI 配置 → 阿里云百炼
```

---

## 模型选择建议

| 预算 | 视频理解 | 解说生成 | 配音 |
|------|----------|----------|------|
| **免费** | Qwen2.5-VL（本地） | DeepSeek-V3.2 | Edge-TTS |
| **低预算 <$5/月** | Qwen2.5-VL（API） | DeepSeek-V3.2 | Edge-TTS |
| **中预算 $5-50/月** | Qwen2.5-VL（API） | GPT-5.4 | Edge-TTS |
| **高预算 >$50/月** | GPT-5.4 | Claude Opus 4.6 | OpenAI TTS |

---

## API Key 安全

::: warning 安全提示
- **不要** 将 API Key 提交到代码仓库
- 使用 `.env` 文件（已加入 .gitignore）或系统 Keychain 存储
- 定期检查用量异常
:::

---

## 更新日志

- **2026.04**: Edge-TTS 更新至 7.2.8（2026.03 最新）
- **2026.02**: Claude Opus 更新至 4.6，Gemini 3 Pro Preview 已停用
- **2026.01**: Qwen3-VL 开源（但 Qwen2.5-VL 仍为推荐选择）
