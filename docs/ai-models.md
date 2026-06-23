---
title: AI 模型
description: SceneFab 在视频理解、解说生成、语音识别和配音合成中的模型选择与配置。
---

# AI 模型

SceneFab 的模型层服务于第一人称影视/短剧解说生产。当前策略是只保留最新、质量优先的模型栈：中文剧情理解优先，长上下文可用。所有模型名称、参数和能力声明由 `services.ai.model_catalog` 统一管理，配置文件和 Provider 不得各自硬编码。

## 模型总览

| Provider | 模型 | 上下文长度 | 最大输出 | 视觉能力 | 开源 |
| --- | --- | --- | --- | --- | --- |
| Qwen | qwen3.7-max | 1,000K | 32,768 | 是 | 否 |
| Qwen | qwen3.7-plus | 1,000K | 16,384 | 是 | 否 |
| DeepSeek | deepseek-v4-pro | 1,000K | 32,768 | 否 | 否 |
| DeepSeek | deepseek-v4-flash | 1,000K | 16,384 | 否 | 否 |
| OpenAI | gpt-5 | 1,000K | 32,768 | 是 | 否 |
| OpenAI | gpt-5-mini | 1,000K | 16,384 | 是 | 否 |
| Claude | claude-opus-4-6 | 200K | 16,384 | 是 | 否 |
| Claude | claude-sonnet-4-5 | 200K | 16,384 | 是 | 否 |
| Gemini | gemini-3.1-pro | 2,000K | 8,192 | 是 | 否 |
| Gemini | gemini-3.1-flash | 1,000K | 8,192 | 是 | 否 |
| Kimi | moonshot-v1-128k | 128K | 8,000 | 否 | 否 |
| GLM | glm-5-plus | 128K | 16,384 | 否 | 否 |
| GLM | glm-5-flash | 128K | 8,192 | 否 | 否 |
| Doubao | doubao-pro-128k | 128K | 64,000 | 否 | 否 |
| Hunyuan | hunyuan-pro | 128K | 8,000 | 否 | 否 |
| 本地 | qwen3:32b | 128K | 8,192 | 否 | 是 |
| 本地 | deepseek-r1:32b | 128K | 8,192 | 否 | 是 |

## 模型分层

| 层级 | 主要职责 | 默认模型 | 备选模型 |
| --- | --- | --- | --- |
| 视频理解 | 分析画面、人物、动作、场景和冲突 | Qwen3.7 Max | Gemini 3.1 Pro / Qwen3.7 Plus |
| 解说生成 | 生成第一人称脚本、Hook、桥段和结尾钩子 | DeepSeek V4 Pro | Qwen3.7 Max / GPT-5 |
| 质量评估 | 一致性校验、桥段回灌、结构审稿 | Qwen3.7 Max | Claude Opus 4.6 |
| 语音识别 | 提取原片对白和声音线索 | SenseVoice | Whisper |
| 配音合成 | 生成解说音频和时间戳 | Edge-TTS | F5-TTS |

## 推荐配置

### 视频理解

| 场景 | 推荐模型 | 说明 |
| --- | --- | --- |
| 中文短剧/影视片段 | qwen3.7-max | 默认主力，中文语境和桥段识别最佳 |
| 长片/复杂剧情校验 | gemini-3.1-pro | 2M 上下文，适合长视频多模态交叉复核 |
| 批量短剧分析 | qwen3.7-plus | 高吞吐，适合批量素材预处理 |
| 隐私敏感素材 | qwen3:32b (本地) | 开源本地部署，素材不上传 |

### 解说生成

| 场景 | 推荐模型 | 说明 |
| --- | --- | --- |
| 第一人称解说/短剧脚本 | deepseek-v4-pro | 默认主力，中文叙事能力强 |
| Hook 快速迭代 | deepseek-v4-flash | 低延迟，适合批量草稿和改写 |
| 剧情一致性评估 | qwen3.7-max | 与视频理解共享语义上下文 |
| 高价值成片质检 | claude-opus-4-6 / gpt-5 | 跨模型复核，长结构审稿 |

### 配音合成

| 场景 | 推荐方案 | 说明 |
| --- | --- | --- |
| 快速出片 | Edge-TTS | 免费、低门槛、多音色 |
| 音色一致/人设声线 | F5-TTS | 支持音色克隆，声线更稳定 |

## 组合方案

| 目标 | 视频理解 | 解说生成 | 配音 | 适用场景 |
| --- | --- | --- | --- | --- |
| 快速出片 | qwen3.7-max | deepseek-v4-pro | Edge-TTS | 日常生产，性价比最高 |
| 本地优先 | qwen3:32b | deepseek-v4-pro | Edge-TTS | 隐私敏感素材 |
| 音色一致 | qwen3.7-max | deepseek-v4-pro | F5-TTS | 需要统一人设声线 |
| 长片理解 | gemini-3.1-pro | deepseek-v4-pro | Edge-TTS | 电影/剧集长片 |
| 最高质量 | qwen3.7-max | deepseek-v4-pro + claude-opus-4-6 复核 | F5-TTS | 高价值成片 |

## 本地模型

SceneFab 支持通过 Ollama 或 LM Studio 运行本地模型，适用于隐私敏感场景：

| 模型 | 参数量 | 用途 | 说明 |
| --- | --- | --- | --- |
| qwen3:32b | 32B | 视频理解/脚本初稿 | 推荐本地部署首选 |
| deepseek-r1:32b | 32B | 推理/评估 | 开源推理模型 |

本地模型需要在 `config/llm.yaml` 中配置 `local` 提供商的 `base_url`（默认 `http://localhost:11434`）。

## 安全提示

API Key 只应保存在系统 Keychain、加密配置或受控环境变量中。不要把密钥写入截图、公开文档、项目备注或共享素材包。

## 相关文档

- [配置参考](/config) — 两文件配置结构与 API Key 设置
- [架构概览](/architecture) — ModelCatalog 单源真相机制
