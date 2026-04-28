---
title: 模型更新日志
description: Voxplore AI 模型版本变更历史、TTS/ASR/LLM 更新追踪。
---

# 模型更新日志

本文档追踪 Voxplore 各 AI 模型层的版本变更，帮助你了解每个版本的能力变化和配置差异。

---

## 2026-04 模型版本总览

| 模型层 | 当前版本 | 状态 |
|--------|----------|------|
| **LLM（解说生成）** | DeepSeek-V4.2 | ✅ 推荐 |
| **视频理解** | Qwen2.5-VL (7B) | ✅ 推荐 |
| **ASR（语音识别）** | SenseVoice | ✅ 推荐 |
| **TTS（配音合成）** | Edge-TTS 7.2.8 | ✅ 推荐 |
| **音色克隆** | F5-TTS | 🔶 可选 |

---

## v3.6.0 — 2026-04-11

### 架构升级

| 变更类型 | 内容 |
|----------|------|
| **类型安全** | `models.py` Any: 89→0，Pydantic v2 替换 dataclass，7个新子类型 |
| **Provider 抽象** | 新建 `provider_models.py`（Pydantic 模型），统一 LLM Provider 接口 |
| **Bug 修复** | Hunyuan / Doubao `usage` 字段缺失问题修复 |

> **Voxplore v3.6.0 推荐默认配置不变**：DeepSeek-V4.2 + Qwen2.5-VL + Edge-TTS。

---

## v3.5.0 — 2026-04-10

### UI 全面重构

| 变更类型 | 内容 |
|----------|------|
| **OKLCH 色彩系统** | UI 全面迁移至 OKLCH 色彩空间，设计一致性提升 |
| **OutCubic 缓动动画** | 动画曲线规范化，交互体验更专业 |
| **创作向导重构** | 3 步向导页面全新设计，StageCard 组件动画修复 |
| **WizardPage 信号管理** | 修复信号重复绑定、StepPipeline 断开旧连接问题 |

> 设计规范与 Voxplore Design System v2 对齐。

---

## v3.4.0 — 2026-04-09

### 品牌与产品定位重构

| 变更类型 | 内容 |
|----------|------|
| **品牌重命名** | Voxplore → **Voxplore**，视觉识别系统全面更新 |
| **产品定位聚焦** | 裁剪全部冗余功能（MashupMaker / BeatSyncMaker / CommentaryMaker / BatchProcessor），只保留 **MonologueMaker** 核心——AI 第一人称视频解说 |
| **OKLCH 设计系统** | 首次引入 OKLCH 色彩系统，替代原有 HSL 配色 |

---

## v3.3.0 — 2026-04-08

### 性能优化

| 变更类型 | 内容 |
|----------|------|
| **Scene Detection** | 视频场景检测算法优化，处理速度提升 |

---

## TTS 引擎版本详情

### Edge-TTS

| 版本 | 日期 | 变更 |
|------|------|------|
| 7.2.8 | 2026-03 | **当前版本**，多音色优化，中文自然度提升 |
| 7.0.0 | 2026-01 | 正式支持情感控制参数 |

**推荐音色配置：**

| 场景 | 音色 | 风格 |
|------|------|------|
| 治愈风格 | `zh-CN-Xiaoxiao` | 女声，温暖清晰 |
| 悬疑风格 | `zh-CN-Yunxi` | 男声，低沉留白 |
| 励志风格 | `zh-CN-Yunyang` | 男声，专业有力 |
| 浪漫风格 | `zh-CN-Xiaoyi` | 女声，细腻柔和 |

### F5-TTS（可选·音色克隆）

| 版本 | 日期 | 变更 |
|------|------|------|
| latest | 2026-03 | 零样本音色克隆，15-30秒参考音频即可克隆任意音色 |

> ⚠️ F5-TTS 需要独立安装，详见[安装指南](./guide/installation#f5-tts-音色克隆)。

---

## ASR 模型对比

| 模型 | 部署 | 中文精度 | 说话人分离 | 推荐场景 |
|------|------|----------|------------|----------|
| **SenseVoice** | 本地 | ⭐⭐⭐⭐⭐ | ✅ | Voxplore 默认，精度的中文 ASR |
| Whisper | 本地 | ⭐⭐⭐⭐ | ❌ | 多语言内容 |
| 云端 ASR | API | ⭐⭐⭐⭐⭐ | ✅ | 需要最高精度且不介意上传 |

---

## 模型选择快速参考

| 预算 | LLM（解说生成） | 视频理解 | TTS | ASR |
|------|----------------|----------|-----|-----|
| 免费 | DeepSeek-V4.2 | Qwen2.5-VL（本地） | Edge-TTS | SenseVoice |
| <$5/月 | DeepSeek-V4.2 | Qwen2.5-VL（API） | Edge-TTS | SenseVoice |
| $5-50/月 | GPT-5.4 | GPT-5.4 Vision | Edge-TTS | SenseVoice |
| >$50/月 | Claude Opus 4.6 | GPT-5.4 Vision | OpenAI TTS | SenseVoice |

---

## 相关文档

- [AI 模型配置](./ai-models.md) — 各模型详细说明与配置指南
- [安装配置](./guide/installation.md) — F5-TTS 等可选模型安装步骤
- [疑难排查](./guide/troubleshooting.md) — 模型相关问题解决方案
