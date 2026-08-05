# 01 · Python 实现 8 大子系统深度审计

> 📌 本章对 `src/app/` 下的 57,050 行 Python 实现做系统性审计，识别所有需要迁移的模块、依赖关系、技术债务与风险点。

## 1. 全局模块拓扑

```
src/app/                                    57,050 行 / 249 文件
├── __init__.py · main.py · application.py · __main__.py
│
├── api/                                     1,200 行 / 7 文件
│   ├── main.py (202)                        # FastAPI 应用 + 中间件 + 异常处理
│   ├── routers/                             # 5 个 REST 路由
│   │   ├── health.py                        # GET /api/v1/health{ready,live}
│   │   ├── projects.py (96)                 # CRUD 项目
│   │   ├── pipeline.py (262)                # 5 步流水线异步任务
│   │   ├── export.py                        # 视频/草稿导出
│   │   └── plugins.py                       # 插件管理
│   ├── middleware/
│   │   ├── auth.py (212)                    # API Key 鉴权 (Bearer/X-API-Key)
│   │   └── rate_limit.py                    # 速率限制
│   └── schemas/models.py (107)              # Pydantic 模式
│
├── core/                                    4,800 行 / 15 文件
│   ├── di_container.py (200)                # 命名+类型服务容器，3 种生命周期
│   ├── unified_event_bus.py (311)           # 同步/异步/通配/统计
│   ├── task_store.py (407)                  # 3 后端：内存/SQLite/Redis
│   ├── audit.py (428)                       # 审计日志
│   ├── security_keys.py (414)               # 加密密钥管理（keyring 包装）
│   ├── ffmpeg_safe.py (702)                 # FFmpeg 安全包装
│   ├── base_worker.py                       # 异步/取消/进度基类
│   ├── stream_worker.py                     # LLM 流式 Worker
│   ├── settings_store.py                    # 设置门面
│   ├── signals.py                           # Qt 信号助手
│   ├── metrics.py                           # 指标聚合
│   ├── exceptions.py                        # 领域异常
│   ├── event_types.py                       # 事件枚举 + DomainEvent
│   └── task_model.py                        # 任务数据模型
│
├── config/                                  1,200 行 / 5 文件
│   ├── config.py                            # ConfigManager 强类型入口
│   ├── manager.py (581)                     # ProjectSettingsManager（5 个 profile）
│   ├── definitions.py                       # ConfigDefinition 表
│   ├── types.py                             # ConfigDefinition / SettingType / Profile
│   └── settings_data.py                     # 内置设置默认值
│
├── models/                                  906 行 / 9 文件
│   ├── project.py (325)                     # VideoProject / VideoSource / MultiVideoSource
│   ├── project_models.py (178)              # Project/ProjectMetadata/ProjectSettings/ProjectTimeline
│   ├── narration.py (79)                    # NarrationBlock/EmotionType/NarrationStyle
│   ├── video.py (83)                        # VideoSegment/EmotionPeak
│   ├── media.py (52)                        # AudioTrack/SubtitleItem
│   ├── file_metadata.py (52)                # FileMetadata
│   ├── constants.py (51)                    # 枚举常量
│   ├── serialization.py (20)                # SerializableDataclass mixin
│   └── __init__.py                          # 公共导出
│
├── services/                                23,000+ 行 / 60+ 文件
│   ├── ai/                                  8,500 行 / 22 文件
│   │   ├── base_llm_provider.py (535)       # LLM 基类 + ProviderType 枚举
│   │   ├── llm_manager.py                   # Provider 路由 + 失败切换
│   │   ├── script_generator/                # 脚本生成器子模块
│   │   │   ├── script_generator.py          # 主生成器
│   │   │   ├── _prompt_builder.py           # Prompt 模板
│   │   │   ├── _response_parser.py          # 响应解析
│   │   │   └── _style_prompts.py            # 7 种第一人称风格
│   │   ├── providers/                       # 11 个 LLM Provider
│   │   │   ├── openai_compat.py             # OpenAI 兼容
│   │   │   ├── claude.py                    # Anthropic Claude
│   │   │   ├── deepseek.py                  # DeepSeek
│   │   │   ├── doubao.py                    # 字节豆包
│   │   │   ├── gemini.py                    # Google Gemini
│   │   │   ├── glm5.py                      # 智谱 GLM-5
│   │   │   ├── hunyuan.py                   # 腾讯混元
│   │   │   ├── kimi.py                      # Moonshot Kimi
│   │   │   ├── local.py                     # Ollama
│   │   │   ├── qwen.py                      # 阿里通义千问
│   │   │   └── qwen37.py                    # 通义 3.7 增强版
│   │   ├── scene_analyzer.py (515)          # 视频场景分析
│   │   ├── tts_providers.py (574)           # TTS 多实现
│   │   ├── voice_generator.py               # 配音生成
│   │   ├── voice_models.py                  # VoiceConfig/VoiceStyle
│   │   ├── vision_base.py / vision_providers.py  # 视觉分析
│   │   ├── script_models.py / scene_models.py / script_stream.py
│   │   ├── subtitle_*.py (5 个)             # 字幕相关
│   │   ├── retry.py                         # 重试策略
│   │   └── model_catalog.py                 # 模型目录
│   │
│   ├── video/                               11,000 行 / 18 文件
│   │   ├── monologue_maker.py (754) ★       # 第一人称独白制作器（核心）
│   │   ├── pipeline_integrator.py (503)     # 5 步流水线整合
│   │   ├── base_maker.py (159)              # Maker 基类
│   │   ├── analyzer.py                      # 视频分析
│   │   ├── caption_gen.py                   # 字幕生成
│   │   ├── ffmpeg_tool.py                   # FFmpeg 命令包装
│   │   ├── hardware.py                      # 硬件加速检测
│   │   ├── highlight_detector.py            # 亮点检测
│   │   ├── perspective_mapper.py            # 视角映射
│   │   ├── processor.py                     # 视频处理
│   │   ├── probe.py                         # ffprobe 包装
│   │   ├── scene_converter.py               # 场景转换
│   │   ├── session.py                       # 会话管理
│   │   ├── tool_base.py                     # 工具基类
│   │   ├── track_builder.py                 # 轨道构建
│   │   ├── video_interleaver.py             # 视频穿插
│   │   ├── extraction/                      # 视频抽帧子模块
│   │   │   ├── first_person.py (309)        # 第一人称抽帧 ★
│   │   │   └── ...                          # 其它抽帧策略
│   │   ├── cache/                           # 抽帧缓存子模块
│   │   ├── models/                          # 视频相关数据模型
│   │   │   ├── monologue.py
│   │   │   └── perspective.py
│   │   └── __init__.py
│   │
│   ├── export/                              3,000 行 / 8 文件
│   │   ├── export_manager.py                # 导出管理
│   │   ├── video_exporter.py                # 视频导出
│   │   ├── jianying_exporter.py             # 剪映草稿导出
│   │   ├── jianying_adapter.py              # 剪映适配
│   │   ├── subtitle_exporter.py             # 字幕导出
│   │   ├── batch_export.py                  # 批量导出
│   │   ├── presets.py                       # 预设（高质量/标准/省资源）
│   │   └── export_utils.py
│   │
│   ├── monitor/system_monitor.py            # 1Hz 系统监控（psutil 软依赖）
│   ├── orchestration/                       # 编排（pipe_models.py/enums.py）
│   ├── series_context_store.py              # 系列上下文存储
│   ├── video_understanding/                 # 视频理解（api_adapters/core/models/story_builder）
│   └── __init__.py
│
├── pipeline/                                6,800 行 / 7 文件
│   ├── assembly_steps.py (585)              # 装配阶段
│   ├── understanding_steps.py (685)         # 理解阶段
│   ├── evaluation_steps.py                  # 评估阶段
│   ├── fp_workflow.py (124) ★               # 第一人称校验
│   ├── short_drama.py (520) ★               # 整季短剧
│   ├── narration/                           # 叙事子模块
│   │   ├── engine.py                        # 叙事引擎
│   │   ├── context.py                       # 上下文
│   │   ├── evaluator.py                     # 评估器
│   │   ├── state_machine.py                 # 状态机
│   │   └── steps.py                         # 步骤
│   └── __init__.py
│
├── ui/                                      ~18,000 行 / ~40 文件
│   ├── main/
│   │   ├── __init__.py                      # 入口
│   │   ├── main_window/                     # 主窗口 1,329 行 ★★★
│   │   │   ├── __init__.py                  # 巨型入口
│   │   │   ├── chrome.py                    # 顶部 chrome
│   │   │   ├── drop_zone.py                 # 拖拽
│   │   │   ├── production_runner.py         # 生产 runner
│   │   │   ├── content_area.py
│   │   │   ├── theme_controller.py
│   │   │   └── ...
│   │   ├── pages/                           # 4 个页面
│   │   │   ├── home_page.py (716)
│   │   │   ├── production_page.py (566)
│   │   │   ├── assets_page.py (504)
│   │   │   ├── settings_page.py (880)
│   │   │   └── update_page.py (958)
│   │   ├── dialogs/                         # 对话框
│   │   ├── widgets/                         # 主窗口专用 widgets
│   │   ├── system_tray.py                   # 系统托盘
│   │   ├── tray_manager.py
│   │   ├── page_router.py
│   │   ├── registry.py
│   │   └── controls.py
│   ├── viewmodels/                          # 4 个 ViewModel
│   │   ├── home_viewmodel.py
│   │   ├── production_viewmodel.py
│   │   ├── assets_viewmodel.py
│   │   └── dashboard_viewmodel.py
│   ├── widgets/                             # 通用组件
│   │   ├── glass_card.py
│   │   ├── command_palette.py
│   │   ├── help_panel.py
│   │   └── animated_chart.py
│   ├── theme/                               # 主题系统
│   │   ├── ds_tokens.py (728)               # 设计令牌 ★★
│   │   ├── animations.py (442)
│   │   ├── theme_manager.py (380)
│   │   └── runtime.py / font_loader.py
│   ├── commands/                            # 命令注册
│   ├── i18n/                                # 国际化
│   │   ├── messages_zh_CN.py
│   │   ├── messages_en_US.py
│   │   ├── message_keys.py
│   │   └── translator.py
│   └── ...
│
├── plugins/                                 1,500 行 / 6 文件
│   ├── registry.py (316)                    # 插件注册中心
│   ├── loader.py (416)                      # 加载器（目录+entry_points）
│   ├── interfaces/
│   │   ├── base.py                          # BasePlugin/PluginManifest/PluginType
│   │   ├── ai_generator.py                  # AI 生成器接口
│   │   └── export_plugin.py                 # 导出插件接口
│   └── examples/
│       ├── deepseek_ai_generator/           # DeepSeek 插件示例
│       └── cinematic_subtitle/              # 电影字幕插件示例
│
├── updater/                                 1,616 行 / 6 文件
│   ├── service.py (607)                     # 升级主控（5 阶段状态机）
│   ├── downloader.py (194)                  # 下载器（带进度回调）
│   ├── installer.py (372)                   # 安装器（备份+回滚）
│   ├── manifest.py (174)                    # Release 清单解析
│   └── verifier.py (74)                     # SHA-256 校验
│
├── update/                                  123 行 / 1 文件
│   └── checker.py                           # 旧版简易 check（v2.5 已 deprecate）
│
├── project/                                 900 行 / 4 文件
│   ├── manager.py (480)                     # 项目生命周期（create/open/save/close/delete）
│   ├── template_mgr.py                      # 模板管理
│   ├── template_models.py                   # 模板数据模型
│   └── __init__.py
│
├── help/                                    ~1,000 行
│   ├── registry.py                          # 帮助主题注册表
│   ├── markdown_parser.py                   # Markdown 解析
│   ├── models.py                            # HelpTopic 数据模型
│   ├── tooltip.py                           # 工具提示
│   └── content/                             # zh_CN / en_US 帮助文案
│
├── templates/                               内置模板
│   ├── video_tutorial/
│   └── ai_enhancement/
│
├── utils/                                   ~1,500 行
│   ├── project_io.py                        # 项目 IO（zip/导入导出）
│   ├── json_io.py                           # JSON 安全读写
│   ├── error_handler.py                     # 错误处理
│   ├── security.py                          # 路径白名单
│   ├── diagnostics.py                       # 诊断
│   ├── retry.py                             # 重试
│   ├── version.py                           # 版本号
│   └── ...
│
├── __init__.py · __main__.py
└── py.typed                                 # PEP 561 标记
```

## 2. 子系统审计（8 大系统）

### 2.1 `application.py` · DI 容器 + 状态机（359 行）

**职责**：

- 封装 PySide6 QObject（state_changed/error_occurred/progress_updated 信号）
- 管理 DIContainer（命名+类型服务）
- 7 阶段初始化序列：logger → config_manager → event_bus → error_handler → services
- start() / shutdown() 生命周期
- 暴露 get_service/get_service_by_name/register_service 三大接口

**关键不变量**：

- 服务名固定：`event_bus` / `config_manager` / `project_manager` / `template_manager` / `settings_manager` / `monologue_maker` / `logger` / `error_handler`
- 初始化顺序不可换（event_bus 早于 services，config_manager 早于 settings_manager）

**迁移到 Rust**：

- DI 容器 → `scenefab-core::di`（用 `shaku` 或自研轻量 DI）
- 状态机 → `scenefab-core::state`（`enum AppState` + `Arc<RwLock>`）
- 初始化 → `apps/desktop/src-tauri::bootstrap`（明确 `Result<(), Error>` 链路）
- 服务名 → `AppContext::get_service("name")` API 保持

**风险点**：

- DIContainer 的 `register()` 顺序与运行时查找必须保持一致
- 错误处理不能用 panic 替代 Error（必须 Result 链路）

### 2.2 `core/` · 基础设施（15 文件 · ~4,800 行）

#### 2.2.1 `di_container.py`（200 行）

- **3 种生命周期**：SINGLETON / TRANSIENT / FACTORY
- **双索引**：type → instance & name → instance
- **全局容器**：`get_app_container()` + `set_app_container()`
- **线程安全**：RLock
- **迁移**：`scenefab-core::di`（推荐 `shaku` crate 或自研 ~150 行）

#### 2.2.2 `unified_event_bus.py`（311 行）

- **特性**：同步/异步/通配订阅/线程池分发/统计
- **支持**：`subscribe` / `publish` / `publish_event(DomainEvent)` / `publish_many`
- **线程模型**：`ThreadPoolExecutor(max_workers=4)` + `asyncio.run_coroutine_threadsafe`
- **统计**：published_count / handler_invocations / handler_failures / avg_handler_time_ms
- **迁移**：`scenefab-core::event`（推荐 `tokio::sync::broadcast` + 自研 wrapper）

#### 2.2.3 `task_store.py`（407 行）

- **3 个后端**：`InMemoryTaskStore` / `SQLiteTaskStore` / `RedisTaskStore`
- **TTL 支持**：`set_ttl(seconds)` + `cleanup_expired()`
- **统一接口**：`save` / `get` / `exists` / `delete` / `list_ids` / `update`
- **迁移**：
  - 内存 → `scenefab-core::task::InMemoryStore`（用 `dashmap` + `Arc`）
  - SQLite → `scenefab-core::task::SqliteStore`（用 `sqlx` 0.8）
  - Redis → **删除**（v3.0 不再支持，桌面单用户无必要）
- **变更**：TTL 用 sled 自带的 expiry，schema 迁移走 sqlx-cli

#### 2.2.4 `audit.py`（428 行）

- 审计日志：who/when/what/where
- 写入路径：`~/.scenefab/audit/YYYY-MM-DD.log`
- 迁移：`scenefab-core::audit`（用 `tracing-subscriber` + `tracing-appender`）

#### 2.2.5 `security_keys.py`（414 行）

- 加密密钥管理：API Key、LLM Token 都通过它存取
- 后端：keyring（macOS Keychain / Windows Credential / Linux Secret Service）
- 迁移：`scenefab-core::security::Keyring`（用 `keyring` crate 3.x）

#### 2.2.6 `ffmpeg_safe.py`（702 行）

- FFmpeg 子进程安全包装
- 进度回调、错误转译、超时控制
- 迁移：`scenefab-ffmpeg::Ffmpeg`（用 `tokio::process::Command` + `indicatif` 进度条）

#### 2.2.7 其他核心

- `base_worker.py`：Worker 基类（迁移到 `scenefab-core::worker::BaseWorker` + async-trait）
- `stream_worker.py`：LLM 流式（迁移到 `scenefab-llm::StreamWorker`）
- `settings_store.py`：设置门面（迁移到 `scenefab-core::settings`）
- `signals.py`：Qt 信号助手（**废弃**，改 tokio broadcast）
- `metrics.py`：指标聚合（迁移到 `scenefab-core::metrics`，用 `prometheus` 协议可选）
- `exceptions.py`：领域异常（迁移到 `scenefab-core::error`，用 `thiserror`）
- `event_types.py`：事件枚举（迁移到 `scenefab-core::event::Event`）
- `task_model.py`：任务数据模型（迁移到 `scenefab-core::task::TaskRecord`）

### 2.3 `api/` · REST API（7 文件 · ~1,200 行）

#### 2.3.1 路由清单

| 路由前缀                       | 端点                              | 实现                  | 迁移到 Tauri Command        |
| ------------------------------ | --------------------------------- | --------------------- | --------------------------- |
| `/api/v1/health`               | GET                               | `routers/health.py`   | `command::health`           |
| `/api/v1/health/ready`         | GET                               | 同上                  | `command::health::ready`    |
| `/api/v1/health/live`          | GET                               | 同上                  | `command::health::live`     |
| `/api/v1/projects`             | POST / GET / GET{id} / DELETE     | `routers/projects.py` | `command::project::*`       |
| `/api/v1/pipeline/narrate`     | POST（异步任务，202）             | `routers/pipeline.py` | `command::pipeline::start`  |
| `/api/v1/pipeline/{id}/status` | GET                               | 同上                  | `command::pipeline::status` |
| `/api/v1/pipeline/{id}/cancel` | POST / GET（deprecated）          | 同上                  | `command::pipeline::cancel` |
| `/api/v1/export/*`             | POST / GET / 下载                 | `routers/export.py`   | `command::export::*`        |
| `/api/v1/plugins/*`            | list / enable / disable / install | `routers/plugins.py`  | `command::plugin::*`        |

#### 2.3.2 中间件

- `auth.py`（212 行）：API Key 鉴权（Bearer / X-API-Key / Query 3 种）
  - **迁移决策**：**完全废弃**。Tauri Command 不走 HTTP，前端位于同进程内，无 CORS/CSRF 风险
  - 但 **保留** Command 级别的 capability 鉴权（每个 Command 在 `capabilities/default.json` 显式声明）
- `rate_limit.py`：速率限制
  - **迁移决策**：**保留**逻辑到 `scenefab-core::ratelimit`（用 `governor` crate），但仅对 LLM/TTS 外部 API 调用生效（防止误用 token），不再做 HTTP 级别限流

#### 2.3.3 Pydantic 模式

- `schemas/models.py`（107 行）：9 个 Pydantic 模型（ProjectCreate/ProjectResponse/NarrationRequest/PipelineStatus/ExportRequest/ExportResponse/HealthResponse/InterleaveModeAPI）
- **迁移**：用 `specta::Type` + `serde` 重新定义（DTO 类型，1:1 映射到 TS）
- **关键不变量**：`PipelineStatus` 字段顺序必须保留（旧前端依赖字段位置）

#### 2.3.4 异常处理

- `SceneFabError` → 400 响应
- `HTTPException` → 对应 status_code
- `Exception` → 500（DEBUG 模式附 traceback）
- **迁移**：Tauri Command 用 `Result<T, SceneFabError>` 返回，前端 `try/catch`

### 2.4 `config/` · 配置管理（5 文件 · ~1,200 行）

#### 2.4.1 `config.py` · `ConfigManager` 强类型入口

- 读取 `config/app_config.yaml` + `config/llm.yaml` + 环境变量
- **迁移**：`scenefab-core::config::ConfigManager`（用 `figment` + `serde_yaml`）

#### 2.4.2 `manager.py`（581 行）· `ProjectSettingsManager`

- 5 个默认 profile：高性能 / 标准配置 / 节省资源 / 用户自定义 1 / 2
- 类别：性能 / 视频 / 音频 / 通用
- 验证器：分辨率格式、路径、颜色、自定义
- 持久化：`~/SceneFab/settings/{project_settings,profiles}.json`
- **迁移**：`scenefab-core::config::SettingsManager`（用 `arc-swap` 实现热加载 + `serde_json`）

#### 2.4.3 `definitions.py` · ConfigDefinition 表

- 200+ 项设置定义（key / type / default / min/max / options / validator / category）
- **迁移**：用 `inventory` 模式 + `#[setting]` 过程宏自动注册

#### 2.4.4 `types.py` · ConfigDefinition / SettingType / Profile

- **迁移**：`scenefab-domain::config` 纯数据类型

#### 2.4.5 `settings_data.py` · 默认值

- **迁移**：迁移到 `scenefab-domain::config::defaults`（编译期常量）

### 2.5 `models/` · 数据模型（9 文件 · 906 行）

#### 2.5.1 核心数据类

| Python 类型        | 行数 | 关键字段                                                                                                                     |
| ------------------ | ---- | ---------------------------------------------------------------------------------------------------------------------------- |
| `VideoProject`     | 325  | name / source_videos / segments / emotion_peaks / narration_blocks / subtitles / audio_track / output_path / style / emotion |
| `MultiVideoSource` | 325  | strategy / sources / context / narrator（v2.5 新增）                                                                         |
| `VideoSource`      | 325  | path / label / duration / size / thumbnail（v2.5 新增）                                                                      |
| `SeriesContext`    | 325  | series_name / season / characters / settings（v2.5 新增）                                                                    |
| `Project`          | 178  | id / path / metadata / settings / media_files / timeline                                                                     |
| `ProjectMetadata`  | 178  | name / description / project_type / author / version                                                                         |
| `ProjectSettings`  | 178  | video / audio / output 配置 + auto_save / backup                                                                             |
| `ProjectTimeline`  | 178  | tracks / clips / duration / fps / resolution                                                                                 |
| `ProjectMedia`     | 178  | id / type / path / metadata / imported_at                                                                                    |
| `NarrationBlock`   | 79   | text / voice_id / emotion / duration / start_time                                                                            |
| `EmotionType`      | 79   | NEUTRAL / HAPPY / SAD / HEALING / ROMANTIC / TENSE / ...                                                                     |
| `NarrationStyle`   | 79   | DOCUMENTARY / STORYTELLING / HUMOROUS / ...                                                                                  |
| `VideoSegment`     | 83   | start / end / scenes / visual_features                                                                                       |
| `EmotionPeak`      | 83   | time / intensity / type                                                                                                      |
| `AudioTrack`       | 52   | path / duration / voice_id / sample_rate / bitrate                                                                           |
| `SubtitleItem`     | 52   | text / start / end / style / position                                                                                        |
| `FileMetadata`     | 52   | path / size / mtime / hash / format                                                                                          |

#### 2.5.2 迁移方案

- **所有 dataclass** → Rust `struct` + `serde::{Serialize, Deserialize}` + `specta::Type`
- **`to_dict()` / `from_dict()`** → 改用 `serde_json::to_value/from_value`
- **枚举** → Rust `enum`（`#[serde(rename_all = "snake_case")]` 保持 JSON 字段名一致）
- **Optional 字段** → Rust `Option<T>`
- **关键不变量**：JSON 字段顺序与 v2.4.3 完全一致（向后兼容旧 `.scenefab` 文件）

#### 2.5.3 序列化约束

- `EmotionType.HEALING`（旧值 `"healing"`）必须保留
- `NarrationStyle.DOCUMENTARY`（旧值 `"documentary"`）必须保留
- 字段名 snake_case 不变

### 2.6 `services/` · 业务服务（60+ 文件 · ~23,000 行）

#### 2.6.1 `ai/` 子系统（22 文件 · ~8,500 行）

| 模块                   | 行数 | 职责                                    | Rust crate       |
| ---------------------- | ---- | --------------------------------------- | ---------------- |
| `base_llm_provider.py` | 535  | LLM Provider 抽象基类 + ProviderType    | `scenefab-llm`   |
| `llm_manager.py`       | -    | Provider 路由 + 失败切换 + 配置管理     | `scenefab-llm`   |
| `script_generator/`    | -    | 脚本生成（4 个子模块）                  | `scenefab-llm`   |
| `providers/`           | -    | 11 个 Provider 实现                     | `scenefab-llm`   |
| `tts_providers.py`     | 574  | TTS 抽象 + Edge-TTS + 备用 TTS          | `scenefab-tts`   |
| `voice_generator.py`   | -    | 配音合成主控                            | `scenefab-tts`   |
| `scene_analyzer.py`    | 515  | 视频场景分析（ffprobe + 视觉模型）      | `scenefab-video` |
| `vision_*.py`          | -    | 视觉分析 Provider                       | `scenefab-llm`   |
| `subtitle_*.py`        | -    | 5 个字幕模块（extract/merge/translate） | `scenefab-video` |
| `model_catalog.py`     | -    | 模型目录                                | `scenefab-llm`   |

**关键 LLM Provider（必须 1:1 迁移）**：

1. **Qwen** (qwen.py) ── 通义千问
2. **Kimi** (kimi.py) ── Moonshot
3. **GLM-5** (glm5.py) ── 智谱
4. **Claude** (claude.py) ── Anthropic
5. **Gemini** (gemini.py) ── Google
6. **DeepSeek** (deepseek.py) ── 深度求索
7. **Doubao** (doubao.py) ── 字节豆包
8. **Hunyuan** (hunyuan.py) ── 腾讯混元
9. **Local** (local.py) ── Ollama
10. **Qwen3.7** (qwen37.py) ── 通义 3.7
11. **OpenAI Compat** (openai_compat.py) ── 兼容层

**迁移决策**：

- 所有 Provider 改用 `async-trait` + `reqwest::Client`（异步 HTTPS）
- 用 `generic-LLM-provider` trait 抽象
- Token 限流用 `governor` crate
- 流式响应用 `tokio::sync::mpsc` 推送

**风险点**：

- ⚠️ 11 个 Provider 重写工作量大（建议 M2 阶段 4 周专门做）
- ⚠️ 某些 Provider 的特殊 header / 鉴权方式需逐一验证
- ⚠️ 流式响应（SSE / WebSocket）的不一致处理

#### 2.6.2 `video/` 子系统（18 文件 · ~11,000 行）

**核心模块**：

- `monologue_maker.py`（754 行）── ★ 第一人称独白制作器
  - 5 步：analyze_scenes → generate_script → generate_voice → generate_captions → export
  - 7 种第一人称风格：Melancholic / Reflective / Warm / Excited / Mysterious / Funny / Neutral
  - **迁移**：`scenefab-video::MonologueMaker`（**最复杂模块**，预计 2 周纯 Rust 工作）
- `pipeline_integrator.py`（503 行）── 整合 PerspectiveMapper + VideoInterleaver
  - **迁移**：`scenefab-video::PipelineIntegrator`
- `analyzer.py` / `scene_converter.py` ── 视频分析
- `caption_gen.py` ── 字幕生成
- `ffmpeg_tool.py` ── FFmpeg 命令封装
- `hardware.py` ── 硬件加速检测
- `perspective_mapper.py` ── 视角映射
- `video_interleaver.py` ── 视频穿插决策
- `track_builder.py` ── 轨道构建
- `extraction/first_person.py`（309 行）── 第一人称抽帧

**迁移决策**：

- 全部用 `tokio::task::spawn_blocking` 包装 CPU 密集操作（视频解码）
- 用 `rayon` 处理可并行的抽帧/分析任务
- FFmpeg 子进程改用 `tokio::process::Command`
- 进度推送走 `tokio::sync::broadcast`

#### 2.6.3 `export/` 子系统（8 文件 · ~3,000 行）

| 模块                   | 职责                        | 迁移              |
| ---------------------- | --------------------------- | ----------------- |
| `export_manager.py`    | 导出管理（统一接口）        | `scenefab-export` |
| `video_exporter.py`    | 视频导出（FFmpeg 调用）     | `scenefab-export` |
| `jianying_exporter.py` | 剪映草稿导出（JSON 格式）   | `scenefab-export` |
| `jianying_adapter.py`  | 剪映格式适配                | `scenefab-export` |
| `subtitle_exporter.py` | 字幕格式导出（SRT/ASS/VTT） | `scenefab-export` |
| `batch_export.py`      | 批量导出                    | `scenefab-export` |
| `presets.py`           | 预设（高质量/标准/省资源）  | `scenefab-domain` |
| `export_utils.py`      | 工具函数                    | `scenefab-export` |

**关键不变量**：

- 剪映草稿 JSON 格式不变（向后兼容）
- 字幕 SRT/ASS 格式不变
- 输出文件名规则保留

#### 2.6.4 其他服务

- `monitor/system_monitor.py` ── 1Hz 系统资源监控
  - 迁移：`scenefab-core::monitor::SystemMonitor`（用 `sysinfo` crate）
- `orchestration/` ── 编排（pipe_models.py / enums.py）
  - 迁移：`scenefab-video::orchestration`
- `series_context_store.py` ── 系列上下文
  - 迁移：`scenefab-domain::series::SeriesContextStore`（用 sled）
- `video_understanding/` ── 视频理解（4 文件）
  - 迁移：`scenefab-video::understanding`

### 2.7 `plugins/` · 插件系统（6 文件 · ~1,500 行）

#### 2.7.1 当前架构

```
┌─────────────────────────────────────────────┐
│ PluginRegistry                              │
│  ├─ _plugins: Dict[id, PluginEntry]         │
│  ├─ _hooks: Dict[event, List[callback]]     │
│  └─ 状态机：UNINSTALLED→INSTALLED→LOADED   │
│              →INITIALIZED→ENABLED→DISABLED  │
└─────────────────────────────────────────────┘
            │
            ▼
PluginLoader
  ├─ 目录扫描：./plugins/*/manifest.json
  ├─ entry_points：importlib.metadata
  ├─ 依赖校验：版本范围
  └─ 安全加载：_safe_load_entry_point (防止 sys.path 注入)
```

#### 2.7.2 关键类型

- `BasePlugin` ── 插件基类（initialize / enable / disable / destroy）
- `PluginManifest` ── 清单（id / name / version / author / dependencies / entry_point / permissions）
- `PluginType` ── 类型（AI_GENERATOR / SUBTITLE_STYLE / EXPORT / VOICE_CLONE / VIDEO_EFFECT / SCENE_DETECTOR）
- `AppContext` ── 上下文（注入到插件）
- `PluginState` ── 状态枚举（7 个）

#### 2.7.3 迁移到 Rust + WASM

- **`scenefab-plugin::Registry`** ── 改为 Rust trait
  - 内置插件：直接 `scenefab-plugin-builtin` crate
  - 第三方插件：`wasmtime` 沙箱
- **`scenefab-plugin::Manifest`** ── `manifest.json` schema 改为 TOML
- **`scenefab-plugin::Loader`** ── 目录扫描 + 数字签名验证
- **`#[scenefab_plugin]` 宏** ── 简化插件开发

#### 2.7.4 现有 2 个示例插件

- `deepseek_ai_generator` ── DeepSeek AI 生成器
- `cinematic_subtitle` ── 电影字幕样式

**迁移路径**：

- M3 阶段：先把这 2 个示例从 Python 重写为 Rust → 编译为 WASM
- 提供 `scenefab-plugin-sdk` 给第三方作者

#### 2.7.5 关键不变量

- 插件 id 全局唯一
- 状态机转换合法
- 依赖必须满足
- 数字签名验证（M3 阶段新增，v2.5 无）

### 2.8 `updater/` · 自动更新（6 文件 · ~1,616 行）

#### 2.8.1 当前架构

```
┌─────────────────────────────────────────────┐
│ UpdaterService                              │
│  ├─ 状态机：IDLE→CHECKING→AVAILABLE         │
│              →DOWNLOADING→VERIFYING          │
│              →INSTALLING→DONE / FAILED      │
│              →ROLLED_BACK                   │
│  ├─ Downloader (httpx 异步 + 进度回调)     │
│  ├─ Installer (原子化安装 + 备份 + 回滚)   │
│  ├─ Manifest (GitHub Releases 解析)        │
│  └─ Verifier (SHA-256 校验)                 │
└─────────────────────────────────────────────┘
```

#### 2.8.2 关键流程

1. **check** ── `GET https://api.github.com/repos/Agions/scene-fab/releases/latest`
2. **download** ── 流式下载到 `~/.cache/scenefab/updates/{asset_name}`
3. **verify** ── SHA-256 校验（增量包失败自动 fallback 完整包）
4. **backup** ── 备份当前 `app_dir` 到 `~/.cache/scenefab/updates/backups/`
5. **install** ── 原子化安装（解压覆盖 + 失败回滚）

#### 2.8.3 迁移到 Rust

- **`scenefab-update::UpdaterService`** ── `tauri-plugin-updater` 上层封装
- **优先用官方 `tauri-plugin-updater`**（Tauri 2 官方插件，已实现核心逻辑）
  - 仅在其上定制：增量包 fallback、5 阶段 UI 状态机、备份回滚

#### 2.8.4 关键不变量

- 5 阶段状态机顺序不变
- 增量包失败自动 fallback 完整包
- SHA-256 校验强制
- 备份策略：保留最近 5 份
- UI 通过 5 个信号（stage_changed/progress_changed/update_available/update_unavailable/install_complete/rolled_back/error_occurred）推送

### 2.9 `project/` · 项目管理（4 文件 · ~900 行）

#### 2.9.1 当前架构

```
Project
  ├─ id (UUID)
  ├─ path (本地目录)
  ├─ metadata (ProjectMetadata)
  ├─ settings (ProjectSettings)
  ├─ media_files: Dict[id, ProjectMedia]
  ├─ timeline (ProjectTimeline)
  ├─ is_modified / is_loaded
  └─ save() / load() / create_backup() / cleanup_old_backups()

ProjectManager (QObject)
  ├─ projects: Dict[id, Project]
  ├─ current_project
  ├─ projects_dir = ~/SceneFab/Projects
  ├─ templates_dir = ~/SceneFab/Templates
  ├─ temp_dir = ~/SceneFab/Temp
  ├─ recent_projects: List[str]
  └─ create/open/save/close/delete/export/import + 自动保存 (QTimer 60s)
```

#### 2.9.2 关键流程

1. **create_project** ── 创建目录 + metadata + 写 project.json
2. **open_project** ── 检查 .lock 文件（防多进程） + 读 project.json
3. **save_project** ── 写 project.json + .lock（PID）
4. **export_project** ── zip 打包
5. **import_project** ── zip 解包 + open

#### 2.9.3 迁移到 Rust

- **`scenefab-domain::project::Project`** ── 纯数据 + 序列化
- **`scenefab-domain::project::ProjectManager`** ── 业务逻辑
- **自动保存**：`tokio::time::interval` 替代 `QTimer`
- **进程锁**：`fs2` crate（`flock` 系统调用）

#### 2.9.4 关键不变量

- `.scenefab/project.json` 格式不变
- 备份策略：保留最近 10 份
- 最近项目列表保留最近 10 个

### 2.10 `ui/` · 用户界面（~18,000 行 · ~40 文件）

> ⚠️ **本子系统在 v3.0 中完全废弃**，需重写为 React + TS。

#### 2.10.1 主要页面（PySide6 → React 路由）

| Python 页面          | 行数 | 迁移到 React                   |
| -------------------- | ---- | ------------------------------ |
| `home_page.py`       | 716  | `/` (HomePage)                 |
| `production_page.py` | 566  | `/production` (ProductionPage) |
| `assets_page.py`     | 504  | `/assets` (AssetsPage)         |
| `settings_page.py`   | 880  | `/settings` (SettingsPage)     |
| `update_page.py`     | 958  | `/update` (UpdatePage)         |

#### 2.10.2 ViewModel → Zustand Store

| ViewModel                 | 迁移                                  |
| ------------------------- | ------------------------------------- |
| `home_viewmodel.py`       | `useHomeStore`                        |
| `production_viewmodel.py` | `useProductionStore` + TanStack Query |
| `assets_viewmodel.py`     | `useAssetsStore`                      |
| `dashboard_viewmodel.py`  | `useDashboardStore`                   |

#### 2.10.3 主题系统迁移

- `ds_tokens.py`（728 行）── 设计令牌
  - **迁移**：`apps/desktop/src/styles/tokens.css`（CSS Custom Properties）+ `tailwind.config.ts`
  - 暗/亮主题切换：`data-theme="dark|light"` 切换 + CSS 变量覆盖
- `theme_manager.py`（380 行）── 主题管理
  - **迁移**：`useThemeStore`（Zustand）+ `next-themes` 风格的 React hook
- `animations.py`（442 行）── 动画定义
  - **迁移**：Framer Motion 11
- `runtime.py` / `font_loader.py` ── 字体加载
  - **迁移**：`@fontsource` 预加载 + `font-display: swap`

#### 2.10.4 i18n 迁移

- `messages_zh_CN.py`（488 键）── 中文文案
- `messages_en_US.py`（474 键）── 英文文案
- `message_keys.py` ── 键定义
- `translator.py` ── 翻译器

**迁移路径**：

1. 写脚本 `bin/migrate_i18n.py` 把 .py 常量导出为 JSON
2. `apps/desktop/src/locales/{zh-CN,en-US}/common.json`
3. `react-i18next` 集成
4. 后端错误消息也走 i18n（`scenefab-i18n` crate）

## 3. 关键依赖关系图

```
        ┌────────────┐
        │ main.py    │
        └─────┬──────┘
              │
        ┌─────▼──────────────┐
        │ Application (DI)   │
        │ + DIContainer      │
        └─────┬──────────────┘
              │
    ┌─────────┼─────────┬──────────┬──────────┐
    │         │         │          │          │
    ▼         ▼         ▼          ▼          ▼
┌────────┐┌────────┐┌────────┐┌────────┐┌────────┐
│event_  ││config_ ││project_││template││mono-   │
│bus     ││manager ││manager ││_mgr   ││logue_  │
│        ││        ││        ││       ││maker   │
└────────┘└────────┘└────────┘└────────┘└────────┘
    │         │         │          │          │
    └─────────┴─────────┼──────────┴──────────┘
                        │
              ┌─────────┴─────────┐
              │                   │
              ▼                   ▼
        ┌────────────┐      ┌────────────┐
        │ core/      │      │ services/  │
        │  - task    │      │  - ai      │
        │  - audit   │◄────►│  - video   │
        │  - keys    │      │  - export  │
        │  - ffmpeg  │      │  - monitor │
        │  - event   │      │            │
        └────────────┘      └────────────┘
              │                   │
              └─────────┬─────────┘
                        │
                        ▼
              ┌────────────────┐
              │ pipeline/      │
              │  - narration   │
              │  - assembly    │
              │  - fp_workflow │
              │  - short_drama │
              └────────────────┘
                        │
                        ▼
              ┌────────────────┐
              │ plugins/       │
              │  - registry    │
              │  - loader      │
              │  - interfaces  │
              │  - examples    │
              └────────────────┘
                        │
                        ▼
              ┌────────────────┐
              │ updater/       │
              │  - service     │
              │  - downloader  │
              │  - installer   │
              └────────────────┘
                        │
                        ▼
              ┌────────────────┐
              │ api/           │
              │  - routers     │
              │  - middleware  │
              │  - schemas     │
              └────────────────┘
```

## 4. 缺陷清单（A/B/C 级）

### 4.1 A 级：必须修（影响功能或后续迁移）

| 编号 | 位置                                          | 缺陷                                  | 迁移到 Rust 时如何处理                   |
| ---- | --------------------------------------------- | ------------------------------------- | ---------------------------------------- |
| A-01 | `ui/main/main_window/__init__.py`（1,329 行） | 单一文件混合 4 个 Phase               | 完全重写，拆 6+ 组件                     |
| A-02 | `services/video/monologue_maker.py`（754 行） | 巨型模块，5 步流程 + 7 风格混在一起   | 拆 5 个子模块 + 7 风格枚举               |
| A-03 | `core/ffmpeg_safe.py`（702 行）               | FFmpeg 调用阻塞 UI 线程               | 改 `tokio::process::Command`             |
| A-04 | `core/unified_event_bus.py`（311 行）         | 同步/异步混用，async 事件处理不可靠   | 改 `tokio::sync::broadcast` 统一         |
| A-05 | `core/di_container.py`（200 行）              | 双索引（type + name）易不一致         | 改 `shaku` 或自研单索引                  |
| A-06 | `api/main.py`（202 行）                       | FastAPI + CORS + 限流 整套            | 完全废弃，改 Tauri Command               |
| A-07 | `plugins/loader.py`（416 行）                 | `sys.path` 注入风险，importlib 不可靠 | 改 wasmtime 沙箱                         |
| A-08 | `config/manager.py`（581 行）                 | 单例 + 全局可变状态，热重载困难       | 改 `arc-swap` 原子切换                   |
| A-09 | `updater/service.py`（607 行）                | 与 PySide6 强耦合（Signal）           | 改 `tauri-plugin-updater` + 自定义状态机 |

### 4.2 B 级：建议修

| 编号 | 位置                                     | 缺陷                                  | 迁移策略                         |
| ---- | ---------------------------------------- | ------------------------------------- | -------------------------------- |
| B-01 | `services/ai/providers/*.py`             | 11 个 Provider 大量重复样板           | 用 trait + macro 抽象            |
| B-02 | `models/project.py`（325 行）            | 单文件含 4 个数据类                   | 拆 4 个文件                      |
| B-03 | `pipeline/*.py`                          | 7 个文件，state_machine 与 steps 耦合 | 拆 state + handler 分离          |
| B-04 | `services/export/*.py`                   | 剪映格式硬编码                        | 抽 `JianyingDraft` builder       |
| B-05 | `services/ai/tts_providers.py`（574 行） | 3 个 TTS 实现耦合                     | 抽 `TtsProvider` trait           |
| B-06 | `ui/viewmodels/*`                        | 与 PySide6 Signal 强耦合              | 改 Zustand store                 |
| B-07 | `ui/theme/ds_tokens.py`（728 行）        | `_C` 全局变量无层级                   | 改 Tailwind tokens               |
| B-08 | `core/task_store.py`（407 行）           | 3 后端但 Redis 实际未启用             | 删 Redis，保留 2 后端            |
| B-09 | `core/audit.py`（428 行）                | 同步写文件可能阻塞                    | 改 `tokio::task::spawn`          |
| B-10 | `utils/project_io.py`                    | zip 导入导出阻塞                      | 改 `tokio::task::spawn_blocking` |

### 4.3 C 级：锦上添花

- C-01：i18n fallback 策略需在切换语言时不闪烁
- C-02：错误消息国际化
- C-03：监控指标导出 Prometheus 协议
- C-04：CLI 子命令补全（fish/zsh）
- C-05：插件热加载（开发模式）

## 5. 复杂度评估

| 子系统             | 迁移难度   | 预计工作量（人天） | 关键风险                                      |
| ------------------ | ---------- | ------------------ | --------------------------------------------- |
| `application.py`   | ⭐⭐       | 3                  | DI 容器实现                                   |
| `core/`            | ⭐⭐⭐     | 15                 | FFmpeg 包装、事件总线                         |
| `api/`             | ⭐         | 2                  | 完全废弃 HTTP 改 Command                      |
| `config/`          | ⭐⭐       | 5                  | 设置 schema 迁移                              |
| `models/`          | ⭐         | 3                  | 纯数据，机械迁移                              |
| `services/ai/`     | ⭐⭐⭐⭐   | 20                 | 11 个 Provider 重写 + LLM 流式                |
| `services/video/`  | ⭐⭐⭐⭐⭐ | 25                 | monologue_maker 是核心复杂模块                |
| `services/export/` | ⭐⭐⭐     | 8                  | 剪映格式兼容                                  |
| `plugins/`         | ⭐⭐⭐     | 10                 | wasmtime 沙箱 + 数字签名                      |
| `updater/`         | ⭐⭐       | 5                  | 状态机 + GitHub Releases 解析                 |
| `project/`         | ⭐⭐       | 5                  | 进程锁 + 备份策略                             |
| `ui/`              | ⭐⭐⭐⭐⭐ | 40                 | 5 页面 + 组件库 + 主题 + i18n                 |
| `pipeline/`        | ⭐⭐⭐     | 10                 | 状态机复杂                                    |
| 其他               | ⭐⭐       | 8                  | help / templates / utils / monitor            |
| **合计**           | —          | **159 人天**       | ≈ 32 周（单人）/ 16 周（双人）/ 11 周（4 人） |

## 6. 数据兼容性矩阵

| 数据类型            | v2.4.3 (Python) | v3.0 (Rust) 读取  | v3.0 写入 v2.x 兼容 | 备注               |
| ------------------- | --------------- | ----------------- | ------------------- | ------------------ |
| `.scenefab` 主项目  | ✅ 写入         | ✅ 读取           | ❌ 写入             | JSON 字段一致      |
| `.narrafilm` 旧项目 | ✅ 写入         | ✅ 读取（兼容层） | ❌                  | v3.1 后删除兼容    |
| `project.json`      | ✅ 写入         | ✅ 读取           | ❌                  | 字段一致           |
| 剪映草稿 JSON       | ✅              | ✅                | ✅                  | 外部格式，保留     |
| 字幕 SRT/ASS/VTT    | ✅              | ✅                | ✅                  | 外部格式，保留     |
| 配置文件 YAML       | ✅              | ✅                | ❌                  | ConfigManager 接管 |
| 密钥（keyring）     | ✅              | ✅                | ✅                  | keyring 跨进程     |
| 任务存储 SQLite     | ✅              | ✅ 迁移工具       | ❌                  | sqlx 接管          |
| 审计日志            | ✅              | ✅                | ❌                  | tracing 接管       |

## 7. 迁移期间的双栈并行策略

| 时段           | Python 主线             | Rust 分支                | 桥接层                          |
| -------------- | ----------------------- | ------------------------ | ------------------------------- |
| M0（2026-08）  | 正常迭代                | 脚手架                   | 无                              |
| M1 ~ M5        | 仅修 P0 Bug             | 全量开发（5 后端 crate） | 无                              |
| M6             | 仅修 P0 Bug             | Tauri Command 可调       | 兼容 adapter（可选）            |
| M7 ~ M9        | 仅修 P0 Bug             | 端到端测试 + 灰度        | 桥接期（v2.4 API → v3 Command） |
| M10（2027-05） | **删除**（commit 标记） | v3.0.0 GA                | 桥接层删除                      |

## 8. 总结：关键迁移决策

1. ✅ **彻底重写**（不渐进）
2. ✅ **HTTP 层完全废弃**（改 Tauri Command）
3. ✅ **FFmpeg 子进程化**（不用 ffmpeg-next，避免 GPL 风险）
4. ✅ **11 个 LLM Provider 1:1 重写**（协议不变）
5. ✅ **插件沙箱用 wasmtime**（不用 Python importlib）
6. ✅ **状态机统一用 tokio**（不用 Qt Signal）
7. ✅ **存储用 sqlx + sled**（不用 SQLAlchemy）
8. ✅ **i18n 用 i18next**（不用自研）
9. ✅ **测试用 cargo test + vitest + Playwright**（不用 pytest）
10. ✅ **打包用 Tauri Bundle**（不用 PyInstaller）

详细 Rust crate 清单见 [§03-rust-backend.md](./03-rust-backend.md)。
