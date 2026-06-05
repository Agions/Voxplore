# SceneFab 技术规格说明书

> 版本: 3.0.0 (架构重构版)
> 日期: 2026-05-23
> 定位: **AI 影视/短剧解说创作工具** — 专注影视解说、短剧解说、知识视频创作

---

## 1. 产品定位

### 1.1 核心差异：SceneFab ≠ 传统剪辑软件

| | 剪映/PR/FCP | SceneFab |
|---|---|---|
| 核心方式 | 手动轨道剪辑 | **AI 自动理解 + 生成** |
| 操作方式 | 时间轴 + 关键帧 | **上传 → 全自动** |
| 输出形态 | 原始素材重组 | **AI 解说 + 配音 + 成片** |
| 学习成本 | 高（需数月掌握） | **低（5 分钟上手）** |
| 定位 | 通用剪辑工具 | **垂直：影视/短剧解说** |

### 1.2 目标用户
- 影视解说博主（电影/电视剧/纪录片）
- 短剧解说创作者
- 知识类视频创作者（科普/历史/财经）
- MCN 机构批量生产

### 1.3 核心优势
- **低成本**：DeepSeek-V4 < ¥0.01/视频
- **全本地**：视频永不上传云端
- **一键成片**：5-15 分钟/条
- **Agent 接入**：命令行原生，支持 Skill 文件接入 Agent 工作流

---

## 2. 核心工作流（5 步流水线）

```
Step 1 · 语义拆条     Step 2 · 情感峰值选段
Qwen3.7              视觉 0.6 + 音频 0.4
场景边界检测           叙事完整优先
语义聚类               情感强度排序
    ↓                      ↓
    ┌──────────────────────────┐
    │  Step 3 · 解说稿生成    │
    │  DeepSeek-V4            │
    │  7 种情感风格           │
    │  多版本备选             │
    └──────────────────────────┘
              ↓
    ┌──────────────────────────┐
    │  Step 4 · 配音合成       │
    │  Edge-TTS / F5-TTS      │
    │  50ms 精度字幕对齐       │
    └──────────────────────────┘
              ↓
    ┌──────────────────────────┐
    │  Step 5 · 视频合成导出   │
    │  FFmpeg H.264/H.265     │
    │  MP4 直出 / 剪映草稿    │
    └──────────────────────────┘
```

---

## 3. 系统架构

```
┌──────────────────────────────────────────────────────────────┐
│                      SceneFab App (PySide6)                  │
├────────────────────────────┬─────────────────────────────────┤
│  UI Layer                  │  CLI Layer (Agent-ready)         │
│  · MainWindow / Step Pages │  · Command-first interface     │
│  · 步骤式引导（4 步）        │  · SKILL.md for Agent workflows│
├────────────────────────────┴─────────────────────────────────┤
│                  Business Logic Layer                         │
│  ┌────────────┐  ┌────────────┐  ┌────────────────────────┐│
│  │ VideoMgr   │  │ Pipeline   │  │ Orchestration Layer     ││
│  │ 视频管理    │  │ 5步流水线  │  │ 工作流编排 + 批量处理    ││
│  └────────────┘  └────────────┘  └────────────────────────┘│
├─────────────────────────────────────────────────────────────┤
│                    AI Service Layer                          │
│  ┌──────────────┐  ┌──────────────┐  ┌─────────────────┐  │
│  │ Vision       │  │ LLM          │  │ TTS             │  │
│  │ Qwen3.7      │  │ DeepSeek-V4  │  │ Edge-TTS/F5-TTS │  │
│  │ 语义拆条      │  │ 解说稿生成    │  │ 配音合成         │  │
│  └──────────────┘  └──────────────┘  └─────────────────┘  │
├─────────────────────────────────────────────────────────────┤
│                  Platform Layer                              │
│  FFmpeg · OS Keychain · Local File System                   │
└─────────────────────────────────────────────────────────────┘
```

---

## 4. 五大核心模块

### 4.1 语义拆条引擎（Semantic Slicer）

**职责**：输入视频 → AI 理解 → 按语义/情节切分片段

| 组件 | 技术 | 职责 |
|------|------|------|
| 帧提取器 | OpenCV + FFmpeg | 定时抽帧，构建帧序列 |
| 视觉理解器 | **Qwen3.7** | 逐帧理解画面内容与语义 |
| 场景边界检测 | 帧间差异 + 语义相似度 | 自动发现场景切换点 |
| 语义聚类器 | 向量化 + 聚类 | 将同类场景归组 |

**输出**：`List[SceneInfo]` — 每个场景含时间戳、场景类型、氛围、叙事重要性

### 4.2 情感峰值选段引擎（Emotion Peak Selector）

**职责**：对所有片段按情感强度排序，优先选取叙事高潮

评分公式：
```
情感得分 = 视觉信息密度 × 0.6 + 音频语调变化 × 0.4
```

优先级：叙事核心片段（起承转合完整）> 情感峰值片段

### 4.3 解说生成引擎（Narration Generator）

**职责**：DeepSeek-V4 生成结构化解说稿

| 组件 | 技术 | 职责 |
|------|------|------|
| Prompt 工程 | DeepSeek-V4 | 构建解说 prompt |
| 7 种情感风格 | 角色设定 + 情感标签 | 精确控制解说语气 |
| 多版本生成 | Temperature 调优 | 每段生成 2-3 个版本供选择 |

### 4.4 配音合成引擎（TTS Synthesizer）

**职责**：解说稿 → 配音音频 + 词级时间戳

| 组件 | 技术 | 职责 |
|------|------|------|
| 主流配音 | **Edge-TTS** | 免费低延迟，50+ 音色 |
| 音色克隆 | F5-TTS | 15-30 秒参考音频克隆 |
| 时间戳对齐 | Edge-TTS word-level | 逐字时间戳 → ASS/SRT 字幕 |

### 4.5 视频合成引擎（Video Composer）

**职责**：原片片段 + 配音 + 字幕 → 最终成片

| 组件 | 技术 | 职责 |
|------|------|------|
| 音画合成 | FFmpeg | 配音 + 字幕 + 原片精确对齐 |
| 编码器 | H.264 / H.265 | 自适应码率 |
| 草稿导出 | 剪映 JSON 格式 | 保留时间轴 + 字幕 + 配音轨道 |

---

## 5. 数据流

```
视频输入 → 帧提取 → Qwen3.7 语义理解
    ↓
场景边界检测 → 语义聚类 → 场景片段列表
    ↓
情感评分（视觉 0.6 + 音频 0.4）→ 峰值排序
    ↓
DeepSeek 生成解说稿（多风格）→ 用户选择 / 编辑
    ↓
Edge-TTS 配音合成 + 词级时间戳
    ↓
FFmpeg 音画合并 → ASS 字幕压制
    ↓
输出 MP4 / 剪映草稿 JSON
```

---

## 6. 目录结构

```
src/scenefab/
├── cli/                    # 命令行入口（Agent-ready）
├── services/
│   ├── ai/                 # AI 服务层
│   │   ├── providers/      # LLM/Vision/TTS Provider 实现
│   │   ├── llm_manager.py  # LLM 统一管理器
│   │   ├── vision_providers.py
│   │   ├── script_generator.py  # 解说稿生成
│   │   ├── tts_providers.py
│   │   ├── scene_analyzer.py    # 语义拆条
│   │   ├── scene_analyzer_v2.py # 重要性评分
│   │   └── cache.py
│   ├── video/              # 视频处理
│   │   ├── extraction/     # 片段提取
│   │   ├── grouping/       # 智能分组
│   │   ├── selection/      # 峰值选段
│   │   └── models/
│   ├── audio/              # 音频处理
│   ├── export/             # 导出（MP4 / 剪映）
│   └── orchestration/     # 流程编排
├── ui/                     # PySide6 桌面 UI
├── pipeline.py             # 核心 5 步流水线
└── plugins/                # 插件系统
```

---

## 7. API 规格

### 7.1 内部 Pipeline API

```python
from scenefab.pipeline import SceneFabPipeline, PipelineConfig

config = PipelineConfig(
    min_segment_duration=9.0,
    max_segment_duration=60.0,
    emotion_style="纪录片",  # 7 种之一
)
pipeline = SceneFabPipeline(config)

# 完整流水线
result = pipeline.run(
    video_path="input.mp4",
    output_dir="output/",
    style="纪录片",
)

# 分步执行
scenes = pipeline.semantic_slice("input.mp4")
peaks = pipeline.emotion_select(scenes)
script = pipeline.generate_script(peaks, style="悬疑")
audio = pipeline.synthesize_voice(script)
final = pipeline.compose_video(scenes, peaks, audio)
```

### 7.2 CLI 命令行

```bash
# 核心命令
scenefab commentary create-movie ./movie.mp4 --style 纪录片 --output ./output/
scenefab commentary create-drama ./drama.mp4 --style 悬疑 --voice zh-CN-YunxiNeural

# Agent 模式（输出 JSON）
scenefab commentary create-movie ./video.mp4 --style 纪录片 --format json

# 批量模式
scenefab batch ./videos/ --style 悬疑 --parallel 4
```

---

## 8. 性能规格

| 视频时长 | 语义拆条 | 解说生成 | 配音合成 | 总计 |
|---------|---------|---------|---------|------|
| 1 分钟 | ~5s | ~10s | ~8s | ~25s |
| 10 分钟 | ~30s | ~20s | ~15s | ~70s |
| 1 小时 | ~3min | ~60s | ~3min | ~9min |

---

## 9. 竞品对比

| 功能 | SceneFab | NarratoAI | AI解说大师 |
|------|---------|-----------|-----------|
| 语义拆条 | ✅ Qwen3.7 | ⚠️ 基础 | ⚠️ 基础 |
| 影视解说 | ✅ 7种风格 | ✅ | ✅ |
| 短剧解说 | ✅ | ❌ | ⚠️ |
| 命令行原生 | ✅ | ❌ | ✅ |
| Agent Skill 接入 | ✅ SKILL.md | ❌ | ✅ |
| 剪映草稿导出 | ✅ | ❌ | ❌ |
| 完全本地 | ✅ | ❌ | ❌ |
| 开源 | ✅ MIT | ✅ | ❌ |

---

## 10. 路线图

### Phase 1: 架构重构（当前）
- [x] 语义拆条引擎（Qwen3.7）
- [x] 解说生成引擎（DeepSeek-V4）
- [x] TTS 配音合成（Edge-TTS）
- [x] 剪映草稿导出
- [x] 完成 CLI commentary 命令（create-movie / create-drama）
- [x] 完成批量处理（batch 命令）

### Phase 2: 功能增强
- [ ] F5-TTS 音色克隆
- [ ] 多轨字幕样式
- [ ] 进度实时预览
- [ ] 插件系统

### Phase 3: 生态扩展
- [ ] Docker 一键部署
- [ ] SKILL.md 完善（Agent 接入）
- [ ] API 服务化

---

*文档版本: 3.0.0*
*最后更新: 2026-05-23*
