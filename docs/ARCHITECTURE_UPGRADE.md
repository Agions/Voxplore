# Voxplore 架构升级方案

## 一、现状分析

### 当前架构
```
┌──────────────────────────────────────────────────────────────┐
│                         UI 层 (PySide6)                      │
├──────────────────────────────────────────────────────────────┤
│                        服务层 (Services)                     │
│   AI服务 · 视频处理服务 · 音频服务 · 导出服务                  │
├──────────────────────────────────────────────────────────────┤
│                         核心层 (Core)                         │
│   配置管理 · 事件总线 · 依赖注入 · 安全密钥管理                 │
├──────────────────────────────────────────────────────────────┤
│                        外部依赖层                              │
│        FFmpeg · OpenCV · Qwen2.5-VL · DeepSeek-V4 · Edge-TTS │
└──────────────────────────────────────────────────────────────┘
```

### 当前痛点
| 问题 | 影响 |
|------|------|
| 无插件系统 | 无法扩展功能 |
| 无 Web API | 无法远程调用/二次开发 |
| AI Provider 硬编码 | 新增模型需改源码 |
| 视频穿插逻辑缺失 | 核心功能不完整 |
| 无视角映射 | 第一人称代入感弱 |
| 缓存策略简单 | 多实例无法共享 |

---

## 二、升级后架构

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            表 现 层 (Presentation)                            │
│  ┌─────────────────┐  ┌──────────────────────┐  ┌────────────────────────┐  │
│  │   PySide6       │  │   FastAPI + Vue3     │  │   CLI (TUI/Pure)       │  │
│  │   桌面客户端     │  │   Web 界面            │  │   命令行工具            │  │
│  └─────────────────┘  └──────────────────────┘  └────────────────────────┘  │
├─────────────────────────────────────────────────────────────────────────────┤
│                            OpenAPI / GraphQL 网关                            │
│                    认证 · 限流 · 缓存 · 监控                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                            应 用 层 (Application)                            │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────────────┐   │
│  │  Pipeline        │  │  Plugin Manager  │  │  Task Queue (Celery)     │   │
│  │  Orchestrator    │  │  插件生命周期管理  │  │  后台异步任务             │   │
│  └──────────────────┘  └──────────────────┘  └──────────────────────────┘   │
├─────────────────────────────────────────────────────────────────────────────┤
│                            服 务 层 (Services)                               │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────┐  ┌────────────────┐  │
│  │ Scene       │  │ Perspective  │  │ Video        │  │ Subtitle       │  │
│  │ Analyzer    │  │ Mapper ⭐NEW  │  │ Interleaver  │  │ Generator      │  │
│  │ 场景分析     │  │ 视角映射     │  │ ⭐NEW穿插逻辑 │  │ 字幕生成       │  │
│  └─────────────┘  └──────────────┘  └──────────────┘  └────────────────┘  │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────┐  ┌────────────────┐  │
│  │ Script      │  │ Voice        │  │ Export       │  │ Cache          │  │
│  │ Generator   │  │ Synthesizer  │  │ Manager      │  │ (Redis)        │  │
│  └─────────────┘  └──────────────┘  └──────────────┘  └────────────────┘  │
├─────────────────────────────────────────────────────────────────────────────┤
│                            核 心 层 (Domain)                                 │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────────────────┐    │
│  │ Event Bus      │  │ Service        │  │ Security                   │    │
│  │ (内存+MQ可选)   │  │ Container (DI) │  │ Key Manager               │    │
│  └────────────────┘  └────────────────┘  └────────────────────────────┘    │
├─────────────────────────────────────────────────────────────────────────────┤
│                            基 础 层 (Infrastructure)                         │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │ FFmpeg      │  │ Redis        │  │ SQLite       │  │ File System  │   │
│  │ 视频处理     │  │ 缓存层       │  │ 项目存储     │  │ 素材管理     │   │
│  └─────────────┘  └──────────────┘  └──────────────┘  └──────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 三、核心模块设计

### 3.1 Perspective Mapper（视角映射器）⭐ 新增

**职责**：建立"解说-画面"的视角映射关系

```python
# app/services/video/perspective_mapper.py

from dataclasses import dataclass
from enum import Enum
from typing import List, Dict, Optional
from .models.perspective_models import (
    SubjectRole, PerspectiveShot, ViewpointAnchor
)

class PerspectiveMapper:
    """
    第一人称视角映射器
    
    将画面中的主体与解说视角建立映射关系：
    - 识别画面中的主角位置（我/他/旁观者）
    - 建立"我"的视觉坐标系
    - 决定何时切入第一人称画面
    """
    
    def map_scenes_to_perspective(
        self,
        scenes: List[SceneSegment],
        script: str,
        video_keyframes: List[KeyFrame]
    ) -> List[PerspectiveShot]:
        """
        将场景与第一人称视角映射
        
        Args:
            scenes: 场景分段列表
            script: 解说文本
            video_keyframes: 视频关键帧
            
        Returns:
            PerspectiveShot 列表，每个片段的视角信息
        """
        ...
        
    def determine_viewpoint_anchor(
        self,
        frame,
        subject_positions: List[SubjectPosition]
    ) -> ViewpointAnchor:
        """
        确定视角锚点——"我"在画面中的位置
        
        Returns:
            ViewpointAnchor: 包含空间位置和情感倾向
        """
        ...
        
    def should_show_original_clip(
        self,
        narration_segment: NarrationSegment,
        emotional_intensity: float
    ) -> InterleaveDecision:
        """
        决定是否展示原片画面
        
        规则：
        - 高情绪强度 → 展示原片刻画沉浸感
        - 关键信息 → 画中画/高亮放大
        - 叙事留白 → 纯解说无画面
        """
        ...
```

### 3.2 Video Interleaver（视频穿插器）⭐ 新增

**职责**：智能决定何时展示原片、如何与解说穿插

```python
# app/services/video/video_interleaver.py

from dataclasses import dataclass
from enum import Enum
from typing import List, Tuple, Optional
from .models.interleave_models import (
    InterleaveMode, InterleaveDecision, ClipSegment
)

class VideoInterleaver:
    """
    视频穿插逻辑处理器
    
    核心算法：解说与原片的穿插策略
    - 解说为主模式：原片作为解说佐证
    - 原片为主模式：解说作为画外音
    - 交织模式：解说与原片交替出现
    """
    
    def decide_interleave(
        self,
        narration_timeline: List[NarrationSegment],
        original_clips: List[ClipSegment],
        perspective_shots: List[PerspectiveShot],
        emotion_curve: List[float]
    ) -> InterleaveTimeline:
        """
        生成最终穿插时间线
        
        Args:
            narration_timeline: 解说时间轴
            original_clips: 原片片段
            perspective_shots: 视角映射结果
            emotion_curve: 情感强度曲线
            
        Returns:
            InterleaveTimeline: 包含所有片段的排列和转场
        """
        ...
        
    def apply_interleave_mode(
        self,
        mode: InterleaveMode,
        context: InterleaveContext
    ) -> InterleaveDecision:
        """
        根据模式应用穿插策略
        
        Modes:
        - NARRATION_PRIORITY: 解说优先，原片点缀
        - ORIGINAL_PRIORITY: 原片优先，解说为辅
        - EMOTIONAL_BURST: 情绪高潮时切入原片
        - MINIMALIST: 纯解说，最小化原片
        """
        ...
        
    def generate_transition(
        self,
        from_clip: Optional[ClipSegment],
        to_clip: Optional[ClipSegment],
        transition_type: TransitionType
    ) -> TransitionEffect:
        """
        生成转场效果
        
        Types:
        - CUT: 硬切
        - FADE: 淡入淡出
        - DISSOLVE: 叠化
        - ZOOM_HIGHLIGHT: 放大高亮
        """
        ...
```

### 3.3 Plugin System（插件系统）⭐ 新增

**职责**：支持插件扩展核心功能

```
voxplore/
├── plugins/
│   ├── __init__.py
│   ├── manifest.schema.json       # 插件清单规范
│   ├── loader.py                  # 插件加载器
│   ├── registry.py                # 插件注册表
│   └── interfaces/
│       ├── __init__.py
│       ├── base.py                # BasePlugin 基类
│       ├── ai_generator.py        # AI 生成器接口
│       ├── export_plugin.py       # 导出插件接口
│       └── ui_extension.py         # UI 扩展接口
│   └── examples/
│       ├── wordstrike_plugin/     # 示例：字幕效果插件
│       └── custom_voice_plugin/     # 示例：自定义音色
```

```python
# app/plugins/interfaces/base.py

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Any, Optional
from enum import Enum

class PluginType(Enum):
    AI_GENERATOR = "ai_generator"
    EXPORT = "export"
    UI_EXTENSION = "ui_extension"
    VOICE_CLONE = "voice_clone"
    SUBTITLE_STYLE = "subtitle_style"

@dataclass
class PluginManifest:
    id: str
    name: str
    version: str
    author: str
    description: str
    plugin_type: PluginType
    dependencies: Dict[str, str]  # package: version_spec
    entry_point: str  # module.path:class_name
    permissions: list[str]

class BasePlugin(ABC):
    """所有插件的基类"""
    
    def __init__(self, manifest: PluginManifest):
        self.manifest = manifest
        self._enabled = False
        
    @abstractmethod
    def initialize(self, app_context: "AppContext") -> None:
        """初始化插件"""
        ...
        
    @abstractmethod
    def enable(self) -> None:
        """启用插件"""
        self._enabled = True
        
    @abstractmethod
    def disable(self) -> None:
        """禁用插件"""
        self._enabled = False
        
    def is_enabled(self) -> bool:
        return self._enabled
        
    @abstractmethod
    def get_metadata(self) -> Dict[str, Any]:
        """获取插件元数据"""
        ...
```

### 3.4 Web API Layer（Web API 层）⭐ 新增

**职责**：提供 REST API 支持远程调用

```python
# app/api/
# ├── __init__.py
# ├── main.py                 # FastAPI 入口
# ├── deps.py                 # 依赖注入
# ├── routers/
# │   ├── projects.py         # 项目管理
# │   ├── pipeline.py          # 流水线
# │   ├── export.py            # 导出
# │   └── health.py            # 健康检查
# └── schemas/                 # Pydantic 模型

# app/api/main.py 示例
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Voxplore API",
    description="AI 第一人称视频解说 API",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/v1/pipeline/narrate")
async def create_narration(request: NarrationRequest):
    """
    创建视频解说任务
    
    上传视频文件，AI 生成第一人称解说
    """
    task_id = await pipeline.submit(
        source_video=request.video_url,
        emotion=request.emotion,
        style=request.style,
    )
    return {"task_id": task_id, "status": "processing"}

@app.get("/v1/pipeline/{task_id}/status")
async def get_task_status(task_id: str):
    """获取任务状态"""
    return pipeline.get_status(task_id)
```

### 3.5 AI Provider Adapter（AI 适配器）⭐ 重构

**现状**：硬编码 10 个 Provider
**改进**：插件化 Adapter 模式

```python
# app/services/ai/adapters/
# ├── __init__.py
# ├── base.py              # BaseLLMAdapter
# ├── openai_adapter.py
# ├── deepseek_adapter.py
# ├── qwen_adapter.py
# └── local_adapter.py     # Ollama/LM Studio

class BaseLLMAdapter(ABC):
    """LLM 适配器基类"""
    
    @property
    @abstractmethod
    def provider_name(self) -> str:
        ...
        
    @abstractmethod
    async def complete(self, prompt: str, **kwargs) -> str:
        ...
        
    @abstractmethod
    async def analyze_video(self, video_path: str) -> VideoAnalysis:
        ...
        
    @abstractmethod
    async def generate_script(
        self, 
        context: str, 
        emotion: str,
        **kwargs
    ) -> ScriptOutput:
        ...

class LLMProviderRegistry:
    """LLM Provider 注册中心"""
    
    def __init__(self):
        self._adapters: Dict[str, BaseLLMAdapter] = {}
        
    def register(self, adapter: BaseLLMAdapter) -> None:
        self._adapters[adapter.provider_name] = adapter
        
    def get(self, name: str) -> Optional[BaseLLMAdapter]:
        return self._adapters.get(name)
        
    def list_providers(self) -> List[str]:
        return list(self._adapters.keys())
        
    async def complete(self, provider: str, prompt: str, **kwargs) -> str:
        adapter = self.get(provider)
        if not adapter:
            raise ValueError(f"Unknown provider: {provider}")
        return await adapter.complete(prompt, **kwargs)
```

---

## 四、技术栈确认

| 层级 | 技术选型 | 说明 |
|------|----------|------|
| **桌面 GUI** | PySide6 | 现有，保留 |
| **Web 界面** | FastAPI + Vue3 | 新增 |
| **任务队列** | Celery + Redis | 新增 |
| **消息总线** | EventBus（内存）<br>+ RabbitMQ（可选） | 增强 |
| **缓存** | Redis | 新增 |
| **数据库** | SQLite（本地）<br>+ PostgreSQL（远程 API） | 增强 |
| **AI 分析** | Qwen2.5-VL | 现有 |
| **AI 文案** | DeepSeek-V4 / Qwen-Plus | 现有 |
| **语音合成** | Edge-TTS / F5-TTS | 现有 |
| **视频处理** | FFmpeg | 现有 |

---

## 五、实施路线图

### Phase 1: 基础重构（1-2 周）
- [ ] Plugin System 框架搭建
- [ ] AI Adapter 重构为注册模式
- [ ] EventBus 增强（支持插件订阅）
- [ ] 本地缓存层抽象

### Phase 2: 核心功能（2-3 周）
- [ ] Perspective Mapper 实现
- [ ] Video Interleaver 实现
- [ ] Pipeline Orchestrator 重构
- [ ] 多轨字幕增强

### Phase 3: Web API（2 周）
- [ ] FastAPI 框架搭建
- [ ] 项目管理 API
- [ ] 流水线触发 API
- [ ] 导出 API
- [ ] Web 前端原型

### Phase 4: UI/UX 升级（2-3 周）
- [ ] 视觉风格全面升级
- [ ] 解说编辑器组件
- [ ] 时间线穿梭器
- [ ] 情感调节器

### Phase 5: 生态完善（持续）
- [ ] 插件市场文档
- [ ] SDK (Python / JS)
- [ ] Docker 部署
- [ ] CI/CD 优化

---

## 六、文件变更清单

### 新增文件
```
app/
├── plugins/
│   ├── __init__.py
│   ├── manifest.schema.json
│   ├── loader.py
│   ├── registry.py
│   └── interfaces/
│       ├── __init__.py
│       ├── base.py
│       ├── ai_generator.py
│       ├── export_plugin.py
│       └── ui_extension.py
├── api/
│   ├── __init__.py
│   ├── main.py
│   ├── deps.py
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── projects.py
│   │   ├── pipeline.py
│   │   ├── export.py
│   │   └── health.py
│   └── schemas/
│       ├── __init__.py
│       └── models.py
└── services/
    └── video/
        ├── perspective_mapper.py    # ⭐ 新增
        ├── perspective_models.py     # ⭐ 新增
        ├── video_interleaver.py      # ⭐ 新增
        └── interleave_models.py      # ⭐ 新增
```

### 修改文件
```
app/
├── core/
│   ├── service_container.py        # 插件支持
│   └── event_bus.py                # 分布式支持
├── services/
│   ├── ai/
│   │   ├── llm_manager.py          # Adapter 模式重构
│   │   └── providers/              # 适配器迁移
│   └── video/
│       └── monologue_maker.py      # 集成 Interleaver
└── ui/
    └── ...                         # UI 优化
```

### 删除文件
```
app/
├── plugins/                        # 空目录，待实现
```

---

## 七、向后兼容性

- 所有新增接口均通过 `@abstractmethod` 定义
- 现有 Provider 通过 Adapter 封装，不影响现有代码
- Plugin System 通过 opt-in 方式启用，不影响默认行为
- API 通过 `/v1/` 版本前缀，与现有 CLI 模式共存
