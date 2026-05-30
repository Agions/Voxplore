---
title: 架构概览
description: SceneFab 整体架构与模块设计（v3.0.0 重构版）。
---

# 架构概览

## 产品定位

**SceneFab ≠ 传统剪辑软件！** 核心能力是 AI 全自动理解与生成，而非手动轨道剪辑。

SceneFab 的使命：**让影视解说创作从「几天一条」变成「一天十条」**。

---

## 核心工作流（5 步流水线）

```
Step 1 · 语义拆条          Step 2 · 情感峰值选段
Qwen2.5-VL                 视觉 0.6 + 音频 0.4
场景边界检测 + 语义聚类       叙事完整优先 + 情感排序
        ↓                            ↓
        ┌──────────────────────────────┐
        │   Step 3 · 解说稿生成         │
        │   DeepSeek-V4                │
        │   7 种情感风格                │
        │   多版本备选                  │
        └──────────────────────────────┘
                      ↓
        ┌──────────────────────────────┐
        │   Step 4 · 配音合成           │
        │   Edge-TTS / F5-TTS          │
        │   50ms 精度字幕对齐           │
        └──────────────────────────────┘
                      ↓
        ┌──────────────────────────────┐
        │   Step 5 · 视频合成导出        │
        │   FFmpeg H.264/H.265         │
        │   MP4 直出 / 剪映草稿 JSON   │
        └──────────────────────────────┘
```

---

## 系统架构

```
┌──────────────────────────────────────────────────────────────┐
│                      SceneFab App (PySide6)                  │
├────────────────────────────┬─────────────────────────────────┤
│  UI Layer                  │  CLI Layer (Agent-ready)         │
│  · MainWindow / Step Pages │  · Command-first interface      │
│  · 步骤式引导（4 步）        │  · SKILL.md for Agent workflows│
├────────────────────────────┴─────────────────────────────────┤
│                  Business Logic Layer                         │
│  Pipeline · Orchestration · VideoMgr · ExportEngine         │
├─────────────────────────────────────────────────────────────┤
│                    AI Service Layer                          │
│  LLMService · VisionService · TTSService · ASRService      │
├─────────────────────────────────────────────────────────────┤
│                  Platform Layer (FFmpeg / OS)               │
└─────────────────────────────────────────────────────────────┘
```

---

## 五大核心模块

### 1. 语义拆条引擎（Semantic Slicer）

**输入**：原始视频文件（mp4/mov/avi/webm）
**输出**：按语义切分的场景片段列表

| 组件 | 技术 | 职责 |
|------|------|------|
| 帧提取器 | OpenCV + FFmpeg | 定时抽帧，构造帧序列 |
| 视觉理解器 | **Qwen2.5-VL** | 逐帧理解画面内容与语义 |
| 场景边界检测 | 帧间差异 + 语义相似度 | 自动发现场景切换点 |
| 语义聚类器 | 向量化 + 聚类算法 | 将同类场景归组 |

### 2. 情感峰值选段引擎（Emotion Peak Selector）

**输入**：所有场景片段
**输出**：按情感强度排序的高光片段

评分公式：
```
情感得分 = 视觉信息密度 × 0.6 + 音频语调变化 × 0.4
```

优先保留：叙事核心片段（起承转合完整）> 情感峰值片段

### 3. 解说生成引擎（Narration Generator）

**输入**：选定的片段 + 情感风格
**输出**：结构化解说稿（多版本备选）

| 组件 | 技术 | 职责 |
|------|------|------|
| Prompt 工程 | DeepSeek-V4 | 构建解说 prompt |
| 多版本生成 | Temperature 调优 | 每段生成 2-3 个版本供选择 |
| 风格注入 | 角色设定 + 情感标签 | 精确控制解说语气 |

### 4. 配音合成引擎（TTS Synthesizer）

**输入**：解说稿文字
**输出**：配音 WAV/MP3 + 词级时间戳

| 组件 | 技术 | 职责 |
|------|------|------|
| 主流配音 | Edge-TTS | 免费低延迟，50+ 音色 |
| 音色克隆 | F5-TTS | 15-30 秒参考音频克隆任意音色 |
| 时间戳对齐 | Edge-TTS word-level | 逐字时间戳 → ASS 字幕 |

### 5. 视频合成引擎（Video Composer）

**输入**：原片片段 + 配音 + 字幕
**输出**：最终 MP4 / 剪映草稿 JSON

| 组件 | 技术 | 职责 |
|------|------|------|
| 音画合成 | FFmpeg | 配音+字幕+原片精确对齐 |
| 编码器 | H.264 / H.265 | 自适应码率，质量优先 |
| 草稿导出 | 剪映 JSON 格式 | 保留时间轴+字幕+配音轨道 |

---

## LLM 多 Provider 架构

SceneFab 内置统一 LLM 管理器，支持自动切换：

```
AIServiceManager
├── DeepSeek Provider（主力，解说生成）
├── Qwen Provider（通义千问，视觉理解）
├── Kimi Provider（月之暗面）
├── GLM-5 Provider（智谱）
├── Claude Provider（Anthropic）
├── Gemini Provider（Google）
├── Doubao Provider（字节豆包）
└── Hunyuan Provider（腾讯混元）
```

自动故障转移：某 Provider 超时/限流时自动切换下一个。

---

## 配置管理

使用 `pydantic-settings` 进行配置校验：

- 环境变量优先
- `.env` 文件支持
- API Key 存入 OS Keychain，永不写入代码

:::tip
详细模块说明请参考 [AI 工作流详解](/guide/ai-video-guide)。
:::

---

## 目录结构（v3.0.0 重构版）

```
src/scenefab/
├── core/                       # 核心基础设施（非业务）
│   ├── state.py                # ApplicationState 状态机
│   ├── context.py              # ApplicationContext 应用上下文
│   ├── events/                 # 事件系统（EventBus）
│   ├── container/              # ServiceContainer 依赖注入容器
│   ├── exceptions.py           # 统一异常体系
│   ├── patterns.py             # 单例/装饰器等设计模式
│   └── callbacks.py            # 公共回调定义
│
├── models/                      # 数据模型（按域拆分）
│   ├── narration.py            # NarrationStyle, EmotionType, NarrationBlock
│   ├── video.py                # TimeRange, VideoSegment, EmotionPeak
│   ├── media.py                # SubtitleItem, AudioTrack
│   └── project.py              # VideoProject, VideoGroup, TaskProgress
│
├── services/                     # 业务服务
│   ├── ai/                     # AI 服务（已拆分）
│   │   ├── infra/              # RateLimiter, CircuitBreaker, LRUCache, PersistentCache
│   │   ├── base.py            # BaseAIService 基类
│   │   ├── llm.py             # LLMService（DeepSeek/Claude/GPT 等）
│   │   ├── vision.py         # VisionService（Qwen2.5-VL）
│   │   ├── tts.py             # TTSService（Edge-TTS / F5-TTS）
│   │   ├── asr.py            # ASRService（SenseVoice / Whisper）
│   │   └── manager.py        # AIServiceManager 单例
│   │
│   ├── video/                  # 视频服务（已拆分）
│   │   ├── cache/             # VideoFrameCache, VideoCache（适配器）
│   │   ├── session.py        # FFmpegSession 单例
│   │   ├── analyzer.py       # VideoAnalyzer 场景检测
│   │   └── processor.py     # VideoProcessor 剪切/合并
│   │
│   ├── audio/                  # 音频处理
│   ├── export/                 # 导出器（MP4 / 剪映 / 字幕）
│   └── orchestration/         # 工作流编排
│
├── config/                      # 配置层（合并后单一入口）
│   ├── defs.py                 # dataclass 配置定义
│   ├── loader.py               # YAML / ENV 加载器
│   └── validator.py            # 配置校验器
│
├── utils/                       # 工具函数
│   ├── time.py                 # 时间格式化
│   ├── file.py                 # 文件操作
│   └── path.py                 # 路径处理
│
├── ui/                          # PySide6 桌面 UI
│   ├── main/                   # MainWindow + 组件
│   └── settings/               # 设置页
│
├── cli/                         # 命令行入口
│   └── commands.py             # CLI 命令定义
│
├── pipeline.py                 # 核心 5 步流水线
├── application.py             # Application 生命周期管理
├── settings.py               # ConfigManager 单一配置入口
├── service_container.py      # ServiceContainer（代理至 core/container/）
├── engine.py                 # engine 兼容层（→ core/events/）
├── event_bus.py              # EventBus 事件总线
└── exceptions.py             # 顶层异常导出
```

### 模块职责速查

| 模块 | 职责 | 关键类 |
|------|------|--------|
| `core/state` | 应用状态机 | `ApplicationState` |
| `core/events` | 事件驱动 | `EventBus`, `EventEmitter` |
| `core/container` | 依赖注入 | `ServiceContainer` |
| `models/narration` | 解说风格/情感 | `NarrationStyle`, `NarrationBlock` |
| `models/video` | 视频片段 | `VideoSegment`, `TimeRange` |
| `services/ai/llm` | LLM 调用 | `LLMService` |
| `services/ai/vision` | 视频视觉理解 | `VisionService` |
| `services/ai/tts` | 配音合成 | `TTSService` |
| `services/video/analyzer` | 场景检测 | `VideoAnalyzer` |
| `services/video/processor` | 视频处理 | `VideoProcessor` |

---

## 关键设计决策

### 1. 依赖注入容器

`ServiceContainer` 统一管理所有服务生命周期，支持：
- 按需延迟初始化
- 单例模式（AI Services）
- 线程安全

### 2. 事件驱动架构

`EventBus` 解耦各模块，通过事件通知状态变化：
- `VideoAnalyzed`, `NarrationGenerated`, `TTSCompleted` 等
- 各服务无需直接引用 Pipeline

### 3. 配置单一入口

`settings.py` 的 `ConfigManager` 是唯一配置出口：
- 所有配置文件统一由 `ConfigManager` 读取
- 其他模块禁止直接读 YAML/ENV

:::tip
详细使用说明请参考 [配置参考](/config)。
:::