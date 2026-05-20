# Voxplore 优化版本规格说明书

> 版本: 2.0.0 (优化版)  
> 日期: 2026-05-20  
> 定位: AI 影视解说工具 - 第一人称视角视频创作平台

---

## 1. 项目概述

### 1.1 核心定位
Voxplore 是一款专注于**第一人称视角视频解说**的 AI 工具。用户上传一段视频，AI 自动判断"我是谁"，从视频中提取该人物出现的片段，生成电影感配音解说。

### 1.2 目标用户
- 短剧创作者
- 影视解说博主
- Vlog 故事化改造者
- MCN 机构

### 1.3 核心优势
- **低成本**: < ¥0.01/视频 (DeepSeek-V4)
- **全本地**: 视频永不上传云端
- **高效率**: 全自动流程，端到端
- **可扩展**: 开源架构，插件系统

---

## 2. 技术架构

### 2.1 系统架构图
```
┌─────────────────────────────────────────────────────────────────────┐
│                        UI Layer (PySide6)                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌───────────┐ │
│  │ MainWindow  │  │ PreviewPane │  │ TaskManager │  │ Settings  │ │
│  └─────────────┘  └─────────────┘  └─────────────┘  └───────────┘ │
├─────────────────────────────────────────────────────────────────────┤
│                      Core Layer (Application)                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │
│  │ EventBus    │  │ ServiceContainer │  │ ConfigManager │            │
│  └──────────────┘  └──────────────┘  └──────────────┘              │
├───────────────────────────┬─────────────────────────────────────────┤
│     Video Pipeline        │           AI Services                    │
│  ┌───────────────────┐   │   ┌─────────────────────────────────┐   │
│  │ VideoSegmenter   │   │   │ LLM Services (DeepSeek/Qwen/GPT) │   │
│  │ SceneDetector    │   │   ├─────────────────────────────────┤   │
│  │ FirstPersonExtract│   │   │ Vision Services (Qwen2.5-VL)     │   │
│  │ EmotionPeakDetect │   │   ├─────────────────────────────────┤   │
│  │ SmartGrouper     │   │   │ ASR Services (SenseVoice/Whisper) │   │
│  │ AVSyncEngine     │   │   ├─────────────────────────────────┤   │
│  └───────────────────┘   │   │ TTS Services (Edge-TTS/F5-TTS)   │   │
│                          │   └─────────────────────────────────┘   │
│                          │                                             │
│  ┌───────────────────┐   │   ┌─────────────────────────────────┐   │
│  │ SubtitleGen     │   │   │ Export Services                  │   │
│  │ AudioMixer       │   │   │ - JianyingDraftExporter          │   │
│  │ VideoExporter    │   │   │ - MP4Exporter                   │   │
│  └───────────────────┘   │   │ - SubtitleExporter              │   │
│                          │   └─────────────────────────────────┘   │
├───────────────────────────┴─────────────────────────────────────────┤
│                        Infrastructure                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │
│  │ TaskManager  │  │ Checkpoint   │  │ CacheManager │              │
│  │ (暂停/恢复)   │  │ Manager      │  │ (Redis/File) │              │
│  └──────────────┘  └──────────────┘  └──────────────┘              │
└─────────────────────────────────────────────────────────────────────┘
```

### 2.2 核心模块

| 模块 | 职责 | 关键技术 |
|------|------|----------|
| `VideoSegmenter` | 视频分割、场景检测 | OpenCV, FFmpeg |
| `FirstPersonExtractor` | 第一人称视角提取 | Qwen2.5-VL, 视觉嵌入 |
| `EmotionPeakDetector` | 情感峰值检测 | 视觉复杂度 + 音频能量分析 |
| `SmartGrouper` | 智能分组（多视频） | 视觉嵌入(0.7) + 声纹(0.3) |
| `ScriptGenerator` | 解说文案生成 | DeepSeek-V4 / GPT-4o |
| `AVSyncEngine` | 音画同步 | 字幕时间戳对齐 |
| `TTSEngine` | 语音合成 | Edge-TTS / F5-TTS |
| `SubtitleGenerator` | 字幕生成 | Whisper word-level timing |
| `JianyingExporter` | 剪映草稿导出 | JSON Draft API |

### 2.3 数据流
```
输入视频 → 场景检测 → 第一人称提取 → 情感峰值 → 智能选段
    ↓                                              ↓
输入多视频 → 智能分组 → 分组选段 ─────────────→ 解说生成
                                                  ↓
                          TTS配音 ← → 字幕生成 ← → 脚本
                                                  ↓
                                              音画同步
                                                  ↓
                                              视频导出
```

---

## 3. 功能规格

### 3.1 核心功能

#### F1: 单视频第一人称解说
- 输入: MP4/MOV/AVI 视频文件
- 过程:
  1. 场景检测（SceneDetect）
  2. 第一人称帧识别（Qwen2.5-VL）
  3. 连续片段聚类
  4. 情感峰值排序
  5. 解说文案生成（DeepSeek-V4）
  6. TTS 配音（Edge-TTS）
  7. 字幕生成（50ms 精度）
  8. 音画同步
- 输出: MP4 / 剪映草稿

#### F2: 多视频智能混剪
- 输入: 文件夹 / 多选视频
- 过程:
  1. 视觉嵌入提取（Qwen2.5-VL）
  2. 声纹嵌入提取（Speaker Verification）
  3. 混合相似度计算（视觉 0.7 + 声纹 0.3）
  4. 分组聚类
  5. 组内选段
  6. 跨组叙事编排
- 输出: 合并版 MP4 + 高光片段

#### F3: 7 种情感风格
| 风格 | 语气 | 语速 | 场景 |
|------|------|------|------|
| 治愈 | 温暖 | 0.92x | 日常生活 |
| 悬疑 | 神秘 | 0.85x | 剧情紧张 |
| 励志 | 激昂 | 1.0x | 高光时刻 |
| 怀旧 | 平静 | 0.9x | 回忆场景 |
| 浪漫 | 温柔 | 0.95x | 情感戏 |
| 幽默 | 活泼 | 1.05x | 搞笑片段 |
| 纪录片 | 沉稳 | 0.88x | 说明性内容 |

#### F4: 剪映草稿导出
- 格式: 原生 JSON (draft_content.json)
- 支持:
  - 分辨率: 9:16 / 16:9 / 1:1
  - 视频轨道
  - 音频轨道
  - 字幕轨道
  - 素材引用

### 3.2 用户界面

#### 主窗口布局
```
┌─────────────────────────────────────────────────────────────────┐
│  Voxplore - AI 视频解说工具                    [—][□][×]        │
├──────────────┬──────────────────────────────────────────────────┤
│              │                                                   │
│  📁 视频列表  │              视频预览区                          │
│              │                                                   │
│  [+ 添加]    │                                                   │
│  [- 移除]    │                                                   │
│              │                                                   │
│  ──────────  │                                                   │
│  📊 任务进度  │                                                   │
│              ├──────────────────────────────────────────────────┤
│  ▶ 分析中... │              属性面板                             │
│  ████████░░ │  [情感风格] ▼ 治愈                              │
│              │  [输出格式] ▼ 9:16                               │
│  ──────────  │  [配音角色] ▼ 默认女声                           │
│  ⚙️ 设置     │                                                   │
├──────────────┴──────────────────────────────────────────────────┤
│  [▶ 开始创作]  [⏸ 暂停]  [⏹ 停止]  [📤 导出]                   │
└─────────────────────────────────────────────────────────────────┘
```

---

## 4. API 规格

### 4.1 内部服务 API

#### VideoSegmenter
```python
class VideoSegmenter:
    def detect_scenes(self, video_path: str) -> List[Scene]:
        """检测场景边界"""
        
    def extract_frames(self, video_path: str, timestamps: List[float]) -> List[np.ndarray]:
        """提取指定时间戳的帧"""
```

#### FirstPersonExtractor
```python
class FirstPersonExtractor:
    def extract(
        self, 
        video_path: str,
        use_cache: bool = True,
    ) -> List[VideoSegment]:
        """提取第一人称片段"""
        
    def set_vision_model(self, model: VisionModel):
        """设置视觉模型"""
```

#### EmotionPeakDetector
```python
class EmotionPeakDetector:
    def detect_peaks(
        self,
        segments: List[VideoSegment],
        parallel: bool = True,
    ) -> List[EmotionPeak]:
        """检测情感峰值"""
```

#### ScriptGenerator
```python
class ScriptGenerator:
    def generate(
        self,
        scenes: List[Scene],
        context: str,
        emotion: str,
        style: NarrationStyle,
    ) -> List[NarrationBlock]:
        """生成解说文案"""
```

### 4.2 外部 API (FastAPI)

```
POST /api/v1/commentary/generate
{
    "video_url": "string",
    "context": "string", 
    "emotion": "string",
    "style": "string",
    "callback_url": "string (optional)"
}

GET /api/v1/task/{task_id}/status
GET /api/v1/task/{task_id}/result
```

---

## 5. 配置规格

### 5.1 配置文件结构
```yaml
# config/app_config.yaml
app:
  name: "Voxplore"
  version: "2.0.0"
  
cache:
  enabled: true
  max_size: 100
  ttl: 3600

llm:
  default_provider: "deepseek"
  
  providers:
    qwen:
      enabled: true
      api_key: ""
      base_url: "https://dashscope.aliyuncs.com/compatible-mode/v1"
      model: "qwen-vl-plus"
      
    deepseek:
      enabled: true
      api_key: ""
      base_url: "https://api.deepseek.com"
      model: "deepseek-v4"
```

### 5.2 环境变量
```bash
# AI 服务
DEEPSEEK_API_KEY=sk-xxx
DASHSCOPE_API_KEY=xxx

# 本地模型（可选）
WHISPER_MODEL=large-v3
F5_TTS_MODEL=checkpoint.pth

# 路径配置
VOXPLORE_CACHE_DIR=~/.cache/voxplore
VOXPLORE_OUTPUT_DIR=./output
```

---

## 6. 性能规格

### 6.1 处理速度基准
| 视频时长 | 场景检测 | 第一人称提取 | 解说生成 | 总计 |
|---------|---------|-------------|---------|------|
| 1 分钟 | ~5s | ~30s | ~10s | ~45s |
| 10 分钟 | ~30s | ~120s | ~20s | ~170s |
| 1 小时 | ~3min | ~15min | ~60s | ~18min |

### 6.2 资源占用
- 内存: 2-8GB (取决于模型)
- GPU: 可选 (CUDA 加速)
- 磁盘: 10GB+ (模型缓存)

### 6.3 并行处理
- 帧分析: 4 线程 (自适应)
- 配音生成: 4 线程并行
- 视频导出: FFmpeg 单线程

---

## 7. 验收标准

### 7.1 功能验收
- [ ] 单视频第一人称解说生成成功
- [ ] 多视频智能分组准确
- [ ] 7 种情感风格可切换
- [ ] 剪映草稿可导入
- [ ] 任务暂停/恢复/取消正常
- [ ] 断点续传有效

### 7.2 性能验收
- [ ] 1 分钟视频处理 < 60s
- [ ] 内存占用 < 8GB
- [ ] GPU 加速生效 (如有)

### 7.3 稳定性验收
- [ ] API 限流保护生效
- [ ] 断路器在异常时正确开启
- [ ] 错误日志完整可查

---

## 8. 竞品对比

| 功能 | Voxplore | NarratoAI | 鬼手剪辑 |
|------|----------|-----------|----------|
| 第一人称解说 | ✅ | ❌ | ❌ |
| 多视频混剪 | ✅ | ✅ | ✅ |
| 情感风格 | 7种 | 有限 | 有限 |
| 本地处理 | ✅ | ❌ | ❌ |
| 剪映导出 | ✅ | ❌ | ✅ |
| 断点续传 | ✅ | ❌ | ❌ |
| 开源免费 | ✅ | ✅ | ❌ |

---

## 9. 路线图

### Phase 1: 核心优化 (当前)
- [x] 真实情感分析替代 Mock
- [x] 自适应采样替代固定间隔
- [x] AI 服务保护机制
- [x] 任务断点续传
- [ ] 完成代码实现

### Phase 2: 功能增强
- [ ] 批量处理优化
- [ ] 进度实时预览
- [ ] 插件系统

### Phase 3: 生态扩展
- [ ] Docker 一键部署
- [ ] API 服务化
- [ ] Web UI

---

*文档版本: 2.0.0*  
*最后更新: 2026-05-20*
