---
title: 架构概览
description: SceneFab 面向第一人称影视/短剧解说生产的系统架构与模块职责。
---

# 架构概览

SceneFab 的架构目标是让短剧/影视解说生产流程可重复、可验证、可扩展。核心不是手动剪辑时间线，而是围绕“素材理解 → 剧情上下文 → 第一人称脚本 → 配音字幕 → 导出发布”建立稳定的数据流。

## 分层结构

```text
PySide6 桌面工作台
  Home / Production / Assets / Settings
        |
        v
应用编排层
  pipeline_controller / project manager / task progress
        |
        v
第一人称解说流水线
  NarrationContext / NarrationStateMachine / NarrationEvaluator
        |
        v
业务服务层
  AI services / video services / video_understanding / export services
        |
        v
基础设施层
  EventBus / DIContainer / SafeFFmpeg / Audit / Settings / Resources
```

## 核心模块职责

| 模块 | 职责 |
| --- | --- |
| `ui/main` | 桌面工作台页面，承载生产流程、资产、设置和状态反馈 |
| `pipeline` | 第一人称解说状态机，管理理解、剧情图谱、脚本、评估、TTS 和装配 |
| `core` | 事件、任务、审计、安全 FFmpeg、短剧桥段等基础能力 |
| `services/ai` | LLM、视觉理解、ASR、TTS 等 AI 服务适配 |
| `services/video` | 帧提取、片段选择、分组、情绪峰值和视频处理 |
| `services/video_understanding` | 长视频/多场景剧情理解和 StoryGraph 构建 |
| `services/export` | MP4、字幕、剪映草稿和平台预设导出 |
| `resources` | 应用图标、主题 QSS 和运行时视觉资源 |

## 解说状态机

```text
INIT
  -> UNDERSTAND
  -> STORYGRAPH
  -> DRAFT
  -> EVALUATE
  -> HOOK_REWRITE
  -> TTS_LENGTH_ADJUST
  -> TTS
  -> ASSEMBLE
  -> DONE
```

状态机统一管理四类上下文：

| 上下文 | 内容 |
| --- | --- |
| 指令上下文 | 人设、风格、平台、目标时长、短剧风格 |
| 数据上下文 | StoryGraph、场景摘要、桥段识别结果 |
| 历史上下文 | 已讲过的人物、剧情点和桥段 |
| 工具上下文 | Few-shot、桥段模板、质量反馈 |

## 短剧生产字段

短剧模式在通用解说上下文上增加结构化字段：

| 字段 | 用途 |
| --- | --- |
| `content_tags` | 题材和爽点标签，用于 Hook、标题和脚本关键词 |
| `relationship_notes` | 人物关系备注，用于一致性控制 |
| `episode_index` | 连载集数，用于开头承接 |
| `previous_episode_summary` | 前情摘要，减少重复解释 |
| `next_hook_hint` | 下一集钩子，强化结尾悬念 |

## 数据流

```text
视频素材
  -> 场景分析
  -> 桥段检测
  -> StoryGraph
  -> NarrationContext
  -> ScriptConfig
  -> 解说稿
  -> 质量评估
  -> 配音与字幕
  -> 导出产物
```

## 设计原则

1. 生产字段优先结构化，避免依赖文件名和自由文本。
2. 脚本生成和质量评估使用同一套上下文。
3. AI 服务失败时可降级，不阻断基础流程。
4. 导出预设和文档标准保持一致。
5. UI 只承载生产决策，不复制业务规则。

## 目录结构

```text
src/scenefab/
├── core/                  # 事件、任务、安全、短剧桥段、审计
├── pipeline/              # 第一人称解说状态机和上下文
├── services/
│   ├── ai/                # LLM / Vision / ASR / TTS
│   ├── video/             # 视频分析、提取、选择、分组
│   ├── video_understanding/
│   └── export/            # 成片、字幕和剪映草稿导出
├── ui/
│   ├── main/              # Home / Production / Assets / Settings
│   └── theme/             # 设计令牌和主题加载
└── models/                # 稳定数据模型
```

## 相关文档

- [第一人称生产规范](./guide/first-person-narration-production.md)
- [AI 工作流](./guide/ai-video-guide.md)
- [导出发布](./guide/exporting.md)
