# 04 · Python → Rust 1:1 模块映射表

> 📌 本章是 v3.0 迁移的**核心交付物**，列出 249 个 Python 文件到 13 个 Rust crate 的精确映射。

## 1. 映射总览

| Python 模块                                          | 行数       | 目标 Rust 模块                                                                                                           | crate            | 迁移难度   |
| ---------------------------------------------------- | ---------- | ------------------------------------------------------------------------------------------------------------------------ | ---------------- | ---------- |
| **`src/app/application.py`**                         | 359        | `src/bootstrap.rs` + `src/lib.rs` + `scenefab-core::di`                                                                  | core + tauri-app | ⭐⭐       |
| **`src/app/core/`** (15 文件)                        | 4800       | `scenefab-core/src/{error,di,event,config,settings,audit,security,ratelimit,metrics,monitor,retry,version,time,fs/}/`    | core             | ⭐⭐⭐     |
| **`src/app/api/`** (7 文件)                          | 1200       | `apps/desktop/src-tauri/src/commands/` (HTTP 完全废弃)                                                                       | tauri-app        | ⭐         |
| **`src/app/config/`** (5 文件)                       | 1200       | `scenefab-core/src/config/` + `scenefab-domain/src/config.rs`                                                            | core + domain    | ⭐⭐       |
| **`src/app/models/`** (9 文件)                       | 906        | `scenefab-domain/src/{project,project_models,narration,video,media,file_metadata,constants,serialization,validation}.rs` | domain           | ⭐         |
| **`src/app/services/ai/`** (22 文件)                 | 8500       | `scenefab-llm/src/` + `scenefab-llm/src/providers/*.rs`                                                                  | llm              | ⭐⭐⭐⭐   |
| **`src/app/services/video/`** (18 文件)              | 11000      | `scenefab-video/src/` + `scenefab-video/src/{extraction,cache,models,orchestration,understanding}/`                      | video            | ⭐⭐⭐⭐⭐ |
| **`src/app/services/export/`** (8 文件)              | 3000       | `scenefab-export/src/`                                                                                                   | export           | ⭐⭐⭐     |
| **`src/app/services/monitor/`** (1 文件)             | 350        | `scenefab-core/src/monitor.rs`                                                                                           | core             | ⭐         |
| **`src/app/services/orchestration/`** (2 文件)       | 200        | `scenefab-video/src/orchestration/`                                                                                      | video            | ⭐⭐       |
| **`src/app/services/series_context_store.py`**       | 200        | `scenefab-domain/src/series.rs` + `scenefab-core/src/task/sqlite.rs`                                                     | domain + core    | ⭐⭐       |
| **`src/app/services/video_understanding/`** (4 文件) | 800        | `scenefab-video/src/understanding/`                                                                                      | video            | ⭐⭐⭐     |
| **`src/app/pipeline/`** (7 文件)                     | 6800       | `scenefab-pipeline/src/` + `scenefab-pipeline/src/narration/`                                                            | pipeline         | ⭐⭐⭐     |
| **`src/app/plugins/`** (6 文件)                      | 1500       | `scenefab-plugin/src/` + `scenefab-plugin/src/{examples,sdk}/`                                                           | plugin           | ⭐⭐⭐     |
| **`src/app/updater/`** (6 文件)                      | 1616       | `scenefab-update/src/`                                                                                                   | update           | ⭐⭐       |
| **`src/app/update/`** (1 文件)                       | 123        | **删除**（v2.5 已 deprecate，v3.0 完全删除）                                                                             | -                | -          |
| **`src/app/project/`** (4 文件)                      | 900        | `scenefab-domain/src/project_repo.rs` + `scenefab-domain/src/template.rs`                                                | domain           | ⭐⭐       |
| **`src/app/help/`** (5 文件)                         | 1000       | `scenefab-help/src/`                                                                                                     | help             | ⭐         |
| **`src/app/templates/`** (3 文件)                    | 300        | `scenefab-domain/src/template.rs` (编译期常量)                                                                           | domain           | ⭐         |
| **`src/app/utils/`** (12 文件)                       | 1500       | 分散到 `scenefab-core/src/{retry,version,time,fs,path,security}/`                                                        | core             | ⭐         |
| **`src/app/ui/`** (~40 文件)                         | 18000      | **完全废弃**，重写为 React + TS                                                                                          | apps/desktop     | ⭐⭐⭐⭐⭐ |
| **总迁移量**                                         | **57,050** | **~25,000 行 Rust + ~15,000 行 TS/TSX**                                                                                  | -                | -          |

## 2. 核心模块详细映射

### 2.1 `application.py` (359 行)

| Python 类/方法                  | 映射到 Rust                                                                   |
| ------------------------------- | ----------------------------------------------------------------------------- |
| `ApplicationState` 枚举         | `scenefab-core::state::AppState`                                              |
| `Application.__init__`          | `apps/desktop/src-tauri::bootstrap::Bootstrap::new`                               |
| `initialize()`                  | `Bootstrap::initialize()` + `AppContext::new()`                               |
| `start()`                       | `Bootstrap::start()`（启动所有服务）                                          |
| `shutdown()`                    | `AppContext::shutdown()`（优雅关闭）                                          |
| `state_changed` Signal          | `tokio::sync::watch::Sender<AppState>`                                        |
| `error_occurred` Signal         | `EventBus::publish("app.error", ...)`                                         |
| `progress_updated` Signal       | `EventBus::publish("app.progress", ...)`                                      |
| `get_service(T)`                | `AppContext::get::<T>()`                                                      |
| `get_service_by_name(name)`     | `AppContext::get_named::<T>(name)`                                            |
| `register_service(name, s)`     | `AppContext::register_named(name, s)`                                         |
| `subscribe/unsubscribe/publish` | `AppContext::event_bus().subscribe/unsubscribe/publish`                       |
| `add_timer(name, interval, cb)` | `tokio::spawn(async move { tokio::time::interval(...).tick().await; cb(); })` |
| `_init_sequence`                | `bootstrap::init_sequence()`（明确顺序）                                      |

### 2.2 `core/di_container.py` (200 行)

| Python 类/方法                     | 映射到 Rust                                       |
| ---------------------------------- | ------------------------------------------------- |
| `DIContainer`                      | `scenefab-core::di::AppContext`（按 TypeId 索引） |
| `ServiceLifetime` 枚举             | `scenefab-core::di::ServiceLifetime`              |
| `register(T, instance)`            | `AppContext::register::<T>(instance)`             |
| `register_by_name(name, instance)` | `AppContext::register_named::<T>(name, instance)` |
| `register_transient`               | `AppContext::register_factory::<T>(factory)`      |
| `get(T)`                           | `AppContext::get::<T>()`                          |
| `get_by_name(name)`                | `AppContext::get_named::<T>(name)`                |
| `get_required(T)`                  | `AppContext::get_required::<T>()`（找不到抛错）   |
| `get_or_create(T, factory)`        | `AppContext::get_or_create::<T>(factory)`         |
| `remove/remove_by_name`            | `AppContext::unregister/unregister_named`         |
| `clear/all_names/all_types`        | `AppContext::clear/all_named/all_types`           |
| `get_app_container()`              | `AppContext::global()`                            |

**关键差异**：

- Python 走 `dict[type, Entry]`，Rust 走 `HashMap<TypeId, Box<dyn Any>>`（编译期类型安全）
- Python 线程安全用 `RLock`，Rust 用 `RwLock`（async）
- Python 工厂模式用 `callable`，Rust 用 `Fn() -> Arc<T>`

### 2.3 `core/unified_event_bus.py` (311 行)

| Python 方法                     | 映射到 Rust                                         |
| ------------------------------- | --------------------------------------------------- |
| `UnifiedEventBus`               | `scenefab-core::event::EventBus`                    |
| `subscribe(event, handler)`     | `EventBus::subscribe::<E>(handler) -> Unsubscriber` |
| `unsubscribe(event, handler)`   | `EventBus::unsubscribe`                             |
| `publish(event, data)`          | `EventBus::publish("event.name", data)`             |
| `publish_event(DomainEvent)`    | `EventBus::publish_event(event)`                    |
| `publish_many([(event, data)])` | `EventBus::publish_many(events)`                    |
| `on/off` 别名                   | 同 subscribe/unsubscribe                            |
| `stats()`                       | `EventBus::stats() -> EventStats`                   |
| `handler_count(event)`          | `EventBus::handler_count(event)`                    |
| `registered_events()`           | `EventBus::registered_events()`                     |
| `clear_handlers(event?)`        | `EventBus::clear_handlers(event?)`                  |
| `close()`                       | `EventBus::close()`（关闭内部 broadcast channel）   |
| `get_default/set_default`       | `EventBus::global()/set_global(bus)`                |

**关键差异**：

- Python 同步/异步混用（`ThreadPoolExecutor`），Rust 统一用 `tokio::sync::broadcast`
- Python 弱类型（`data: Any`），Rust 强类型（`Event` trait + 泛型）
- Python 通配符 `*`，Rust 用独立方法 `subscribe_all`

### 2.4 `core/task_store.py` (407 行)

| Python 类                    | 映射到 Rust                                           |
| ---------------------------- | ----------------------------------------------------- |
| `TaskStore` 抽象             | `scenefab-core::task::TaskStore` (trait)              |
| `InMemoryTaskStore`          | `scenefab-core::task::InMemoryTaskStore`              |
| `SQLiteTaskStore`            | `scenefab-core::task::SqliteTaskStore`（用 sqlx）     |
| `RedisTaskStore`             | **删除**（v3.0 不再支持 Redis）                       |
| `save(task_id, task)`        | `store.save(&task_id, &task).await?`                  |
| `get(task_id)`               | `store.get(&task_id).await?`                          |
| `update(task_id, **fields)`  | `store.update(&task_id, fields).await?`               |
| `delete(task_id)`            | `store.delete(&task_id).await?`                       |
| `list_ids()`                 | `store.list_ids().await?`                             |
| `list_all()`                 | `store.list_all().await?`                             |
| `set_ttl(task_id, seconds)`  | `store.set_ttl(&task_id, Duration::seconds(seconds))` |
| `cleanup_expired()`          | `store.cleanup_expired().await?`                      |
| `create_task_store(backend)` | `TaskStoreFactory::create(backend, config)`           |
| `get_task_store()`           | `TaskStore::global()`                                 |
| `set_task_store(store)`      | `TaskStore::set_global(store)`                        |

**关键差异**：

- Python 用 `dict` + `RLock`，Rust 用 `Arc<DashMap>` 或 `sqlx::SqlitePool`
- Python TTL 用 timestamp + 懒清理，Rust 用 sled 自带 expiry 或 sqlx 的 `WHERE expires_at > ?`
- Python `set_ttl` 是单独的 RPC，Rust 可以 set_ttl 时即时生效

### 2.5 `core/audit.py` (428 行)

| Python 类/方法             | 映射到 Rust                                              |
| -------------------------- | -------------------------------------------------------- |
| `AuditLogger`              | `scenefab-core::audit::AuditLogger`                      |
| `log_event(action, ...)`   | `audit.log(AuditEvent { action, ... })`                  |
| `log(level, message, ...)` | `tracing::info!/warn!/error!`（结构化日志）              |
| 持久化（文件）             | `tracing-appender` 写 `~/.scenefab/audit/YYYY-MM-DD.log` |
| 异步写                     | `tokio::task::spawn_blocking`                            |
| 搜索/过滤                  | `tracing-subscriber::EnvFilter` + 自定义 layer           |

### 2.6 `core/security_keys.py` (414 行)

| Python 类                   | 映射到 Rust                                              |
| --------------------------- | -------------------------------------------------------- |
| `SecureKeyManager`          | `scenefab-core::security::Keyring`（用 `keyring` crate） |
| `get_api_key(service)`      | `keyring.get_password(service, "api_key")?`              |
| `set_api_key(service, key)` | `keyring.set_password(service, "api_key", &key)?`        |
| `delete_api_key(service)`   | `keyring.delete_password(service, "api_key")?`           |
| 加密/解密                   | `scenefab-core::security::encrypt/decrypt`（用 `ring`）  |
| 主密码派生                  | `scenefab-core::security::derive_key`（用 `argon2`）     |

**新增**：

- `Keyring::rotate_master_password()`（v2.5 缺失）
- `Keyring::export_for_backup()`（v2.5 缺失）

### 2.7 `core/ffmpeg_safe.py` (702 行)

| Python 函数             | 映射到 Rust                                           |
| ----------------------- | ----------------------------------------------------- |
| `run_ffmpeg(args, ...)` | `scenefab-ffmpeg::Ffmpeg::execute(args, on_progress)` |
| `probe_video(path)`     | `scenefab-ffmpeg::Ffprobe::probe(path)`               |
| `get_duration(path)`    | `scenefab-ffmpeg::Ffprobe::duration(path)`            |
| `get_resolution(path)`  | `scenefab-ffmpeg::Ffprobe::resolution(path)`          |
| `extract_audio(...)`    | `scenefab-ffmpeg::Ffmpeg::extract_audio(...)`         |
| `concat_videos(...)`    | `scenefab-ffmpeg::Ffmpeg::concat(...)`                |
| `get_hardware_accel()`  | `scenefab-ffmpeg::hardware::detect()`                 |
| 进度解析（stderr 解析） | `scenefab-ffmpeg::progress::Parser`                   |
| 错误转译                | `scenefab-ffmpeg::error::translate_exit_code`         |
| 超时控制                | `tokio::time::timeout(duration, fut)`                 |

**关键差异**：

- Python `subprocess.run`，Rust `tokio::process::Command`（async）
- Python 同步阻塞 UI，Rust 走 tokio（不阻塞）
- 进度解析用 `BufReader::lines()` 流式处理

### 2.8 `api/routers/pipeline.py` (262 行)

| Python 端点                  | 映射到 Tauri Command                                   |
| ---------------------------- | ------------------------------------------------------ |
| `POST /pipeline/narrate`     | `pipeline_start(request: PipelineStartRequest)`        |
| `GET /pipeline/{id}/status`  | `pipeline_get_status(task_id: TaskId)`                 |
| `POST /pipeline/{id}/cancel` | `pipeline_cancel(task_id: TaskId)`                     |
| `_process_narration()`       | `MonologueMaker::run_full_pipeline()`（tokio::spawn）  |
| `_update()`                  | `EventBus::publish("task.progress", ...)`              |
| `task_store`                 | `AppContext::get_named::<dyn TaskStore>("task_store")` |

**完整 Tauri Command 清单**（替代全部 5 个 router）：

| 原 HTTP 端点                        | 新 Tauri Command          | 入参                        | 出参                     |
| ----------------------------------- | ------------------------- | --------------------------- | ------------------------ |
| `GET /api/v1/health`                | `health_get`              | -                           | `HealthDto`              |
| `GET /api/v1/health/ready`          | `health_ready`            | -                           | `HealthDto`              |
| `GET /api/v1/health/live`           | `health_live`             | -                           | `HealthDto`              |
| `POST /api/v1/projects`             | `project_create`          | `ProjectCreateRequest`      | `ProjectDto`             |
| `GET /api/v1/projects`              | `project_list`            | -                           | `Vec<ProjectDto>`        |
| `GET /api/v1/projects/{id}`         | `project_get`             | `project_id: Uuid`          | `ProjectDto`             |
| `DELETE /api/v1/projects/{id}`      | `project_delete`          | `project_id: Uuid`          | `()`                     |
| `POST /api/v1/pipeline/narrate`     | `pipeline_start`          | `PipelineStartRequest`      | `PipelineTaskDto`        |
| `GET /api/v1/pipeline/{id}/status`  | `pipeline_get_status`     | `task_id: Uuid`             | `PipelineStatusDto`      |
| `POST /api/v1/pipeline/{id}/cancel` | `pipeline_cancel`         | `task_id: Uuid`             | `()`                     |
| `POST /api/v1/export`               | `export_start`            | `ExportRequest`             | `ExportTaskDto`          |
| `GET /api/v1/export/{id}`           | `export_get_status`       | `task_id: Uuid`             | `ExportStatusDto`        |
| `GET /api/v1/export/{id}/download`  | `export_download_file`    | `task_id: Uuid`             | `PathBuf` (file path)    |
| `GET /api/v1/plugins`               | `plugin_list`             | -                           | `Vec<PluginDto>`         |
| `POST /api/v1/plugins/{id}/enable`  | `plugin_enable`           | `plugin_id: String`         | `()`                     |
| `POST /api/v1/plugins/{id}/disable` | `plugin_disable`          | `plugin_id: String`         | `()`                     |
| `POST /api/v1/plugins/install`      | `plugin_install`          | `PluginInstallRequest`      | `PluginDto`              |
| `GET /api/v1/config`                | `config_get_all`          | -                           | `HashMap<String, Value>` |
| `GET /api/v1/config/{key}`          | `config_get`              | `key: String`               | `Value`                  |
| `PUT /api/v1/config/{key}`          | `config_set`              | `key: String, value: Value` | `()`                     |
| `POST /api/v1/config/reset`         | `config_reset`            | -                           | `()`                     |
| `POST /api/v1/update/check`         | `update_check`            | -                           | `UpdateManifestDto`      |
| `POST /api/v1/update/download`      | `update_download_install` | -                           | `()`                     |
| `POST /api/v1/update/rollback`      | `update_rollback`         | `version: String`           | `()`                     |
| `GET /api/v1/system/metrics`        | `system_get_metrics`      | -                           | `SystemMetricsDto`       |

**关键不变量**：

- 字段名完全一致（如 `PipelineStatus` 的 `task_id` / `status` / `progress` / `current_step` / `estimated_remaining` / `result_url` / `error`）
- 状态字符串不变（`pending` / `processing` / `completed` / `failed` / `cancelled`）

### 2.9 `services/ai/llm_manager.py` + `services/ai/providers/`

| Python 模块                  | 映射到 Rust                                       |
| ---------------------------- | ------------------------------------------------- |
| `LLMManager`                 | `scenefab-llm::LlmManager`                        |
| `BaseLLMProvider`            | `scenefab-llm::provider::LlmProvider` (trait)     |
| `ProviderType` 枚举          | `scenefab-llm::ProviderType`                      |
| `LLMRequest/Response`        | `scenefab-llm::LlmRequest/LlmResponse`            |
| `providers/openai_compat.py` | `scenefab-llm::providers::OpenAiCompatProvider`   |
| `providers/claude.py`        | `scenefab-llm::providers::ClaudeProvider`         |
| `providers/deepseek.py`      | `scenefab-llm::providers::DeepSeekProvider`       |
| `providers/doubao.py`        | `scenefab-llm::providers::DoubaoProvider`         |
| `providers/gemini.py`        | `scenefab-llm::providers::GeminiProvider`         |
| `providers/glm5.py`          | `scenefab-llm::providers::Glm5Provider`           |
| `providers/hunyuan.py`       | `scenefab-llm::providers::HunyuanProvider`        |
| `providers/kimi.py`          | `scenefab-llm::providers::KimiProvider`           |
| `providers/local.py`         | `scenefab-llm::providers::LocalProvider` (Ollama) |
| `providers/qwen.py`          | `scenefab-llm::providers::QwenProvider`           |
| `providers/qwen37.py`        | `scenefab-llm::providers::Qwen37Provider`         |
| `script_generator/`          | `scenefab-llm::script_generator::*`               |
| `scene_analyzer.py`          | `scenefab-video::scene_analyzer`                  |
| `tts_providers.py`           | `scenefab-tts::providers::*`                      |
| `vision_*.py`                | `scenefab-llm::vision::*`                         |
| `subtitle_*.py`              | `scenefab-video::subtitle::*`                     |
| `model_catalog.py`           | `scenefab-llm::model_catalog`                     |
| `retry.py`                   | `scenefab-llm::retry`                             |

**关键约束**：

- 11 个 Provider 全部 1:1 迁移，**调用协议不变**（HTTP 头、参数、响应解析）
- 流式响应统一用 `tokio_stream::wrappers::ReceiverStream` 包装 `mpsc::Receiver<LlmChunk>`
- 失败切换逻辑保留（`LlmManager` 内置）
- token 限流用 `governor::RateLimiter`

### 2.10 `services/video/monologue_maker.py` (754 行)

| Python 类/方法                      | 映射到 Rust                                              |
| ----------------------------------- | -------------------------------------------------------- |
| `MonologueMaker`                    | `scenefab-video::MonologueMaker`                         |
| `MonologueProject`                  | `scenefab-domain::project::MonologueProject`（数据）     |
| `create_project(...)`               | `MonologueMaker::create_project(...)`                    |
| `analyze_scenes(project)`           | `MonologueMaker::analyze_scenes(project)`                |
| `generate_script(project)`          | `MonologueMaker::generate_script(project)`               |
| `generate_voice(project)`           | `MonologueMaker::generate_voice(project)`                |
| `generate_captions(project, style)` | `MonologueMaker::generate_captions(project, style)`      |
| `export_to_jianying(project, dir)`  | `MonologueMaker::export_to_jianying(project, dir)`       |
| `EmotionType` 枚举                  | `scenefab-domain::narration::EmotionType`                |
| `MonologueStyle` 枚举               | `scenefab-domain::narration::MonologueStyle`             |
| 7 种风格 prompt                     | `scenefab-llm::style_prompts::STYLE_PROMPTS`（常量数组） |
| 多视频策略（4 种）                  | `scenefab-domain::project::MultiVideoStrategy` 枚举      |
| `MultiVideoSource`                  | `scenefab-domain::project::MultiVideoSource`             |
| `VideoSource`                       | `scenefab-domain::project::VideoSource`                  |
| `SeriesContext`                     | `scenefab-domain::series::SeriesContext`                 |

### 2.11 `services/video/pipeline_integrator.py` (503 行)

| Python 类/方法                     | 映射到 Rust                                                        |
| ---------------------------------- | ------------------------------------------------------------------ |
| `PipelineIntegrator`               | `scenefab-video::PipelineIntegrator`                               |
| `run_full_pipeline(...)`           | `PipelineIntegrator::run_full_pipeline(...)`                       |
| `run_perspective_mapping(...)`     | `PipelineIntegrator::run_perspective_mapping(...)`                 |
| `run_video_interleave(...)`        | `PipelineIntegrator::run_video_interleave(...)`                    |
| `apply_interleave_to_project(...)` | `PipelineIntegrator::apply_interleave_to_project(...)`             |
| `PerspectiveShot`                  | `scenefab-video::models::perspective::PerspectiveShot`             |
| `InterleaveTimeline`               | `scenefab-video::models::perspective::InterleaveTimeline`          |
| `SceneSegment/ClipSegment`         | `scenefab-video::models::perspective::{SceneSegment, ClipSegment}` |
| `EmotionCurveGenerator`            | `scenefab-video::scene_converter::EmotionCurveGenerator`           |

### 2.12 `services/export/` (8 文件)

| Python 模块            | 映射到 Rust                             |
| ---------------------- | --------------------------------------- |
| `export_manager.py`    | `scenefab-export::ExportManager`        |
| `video_exporter.py`    | `scenefab-export::VideoExporter`        |
| `jianying_exporter.py` | `scenefab-export::JianyingExporter`     |
| `jianying_adapter.py`  | `scenefab-export::JianyingAdapter`      |
| `subtitle_exporter.py` | `scenefab-export::SubtitleExporter`     |
| `batch_export.py`      | `scenefab-export::BatchExporter`        |
| `presets.py`           | `scenefab-domain::preset::ExportPreset` |
| `export_utils.py`      | `scenefab-export::utils`                |

### 2.13 `plugins/` (6 文件)

| Python 模块                       | 映射到 Rust                                                     |
| --------------------------------- | --------------------------------------------------------------- |
| `registry.py` (316 行)            | `scenefab-plugin::registry::PluginRegistry`                     |
| `loader.py` (416 行)              | `scenefab-plugin::loader::PluginLoader`                         |
| `interfaces/base.py`              | `scenefab-plugin::manifest::PluginManifest`                     |
| `interfaces/ai_generator.py`      | `scenefab-plugin::traits::AiGenerator`                          |
| `interfaces/export_plugin.py`     | `scenefab-plugin::traits::ExportPlugin`                         |
| `examples/deepseek_ai_generator/` | `scenefab-plugin/examples/deepseek_ai_generator/` (Rust → WASM) |
| `examples/cinematic_subtitle/`    | `scenefab-plugin/examples/cinematic_subtitle/` (Rust → WASM)    |

**关键变化**：

- 旧 importlib 动态加载 → **wasmtime 沙箱**
- 旧 .py 文件 → **WASM 字节码 + manifest.toml**
- 旧 entry_points 自动发现 → **目录扫描 + 数字签名验证**
- 新增 `#[scenefab_plugin]` 宏简化开发

### 2.14 `updater/service.py` (607 行)

| Python 类/方法                          | 映射到 Rust                                                    |
| --------------------------------------- | -------------------------------------------------------------- |
| `UpdaterService`                        | `scenefab-update::UpdaterService`（基于 tauri-plugin-updater） |
| `UpdaterState`                          | `scenefab-update::UpdaterState`                                |
| `UpdateStage` 枚举                      | `scenefab-update::UpdateStage`                                 |
| `check()`                               | `UpdaterService::check()`                                      |
| `download_and_install()`                | `UpdaterService::download_and_install()`                       |
| `rollback_to(version)`                  | `UpdaterService::rollback(version)`                            |
| `cleanup_downloads()`                   | `UpdaterService::cleanup_downloads()`                          |
| `from_settings()`                       | `UpdaterService::from_settings()`                              |
| 5 阶段状态机                            | `enum UpdateStage` + `match` 模式                              |
| 6 个 Qt Signal                          | `tokio::sync::broadcast::Sender<UpdaterEvent>`                 |
| `_fetch_release_payload`                | `reqwest::Client::get(...).json()`                             |
| `_stage_download/verify/backup/install` | 对应同名方法                                                   |
| `downloader.py`                         | `scenefab-update::downloader::Downloader`                      |
| `installer.py`                          | `scenefab-update::installer::Installer`                        |
| `manifest.py`                           | `scenefab-update::manifest::UpdateManifest`                    |
| `verifier.py`                           | `scenefab-update::verifier::verify_sha256`                     |

### 2.15 `project/manager.py` (480 行)

| Python 类/方法             | 映射到 Rust                                              |
| -------------------------- | -------------------------------------------------------- |
| `Project`                  | `scenefab-domain::project::Project`                      |
| `ProjectManager`           | `scenefab-domain::project_repo::ProjectManager`          |
| `create_project(...)`      | `ProjectManager::create_project(...)`                    |
| `open_project(path)`       | `ProjectManager::open_project(path)`                     |
| `save_project(id)`         | `ProjectManager::save_project(id)`                       |
| `close_project(id)`        | `ProjectManager::close_project(id)`                      |
| `delete_project(id)`       | `ProjectManager::delete_project(id)`                     |
| `export_project(id, path)` | `ProjectManager::export_project(id, path)`               |
| `import_project(path)`     | `ProjectManager::import_project(path)`                   |
| `get_recent_projects()`    | `ProjectManager::recent_projects()`                      |
| `scan_projects()`          | `ProjectManager::scan_all()`                             |
| 自动保存（QTimer 60s）     | `tokio::time::interval(Duration::from_secs(60))`         |
| `.lock` 文件（PID 锁）     | `flock` crate（系统级文件锁）                            |
| `ProjectMetadata`          | `scenefab-domain::project::ProjectMetadata`              |
| `ProjectSettings`          | `scenefab-domain::project::ProjectSettings`              |
| `ProjectTimeline`          | `scenefab-domain::project::ProjectTimeline`              |
| `ProjectMedia`             | `scenefab-domain::project::ProjectMedia`                 |
| `ProjectStatus/Type`       | `scenefab-domain::project::{ProjectStatus, ProjectType}` |
| `template_mgr.py`          | `scenefab-domain::template::*`                           |

### 2.16 `ui/` 完全重写（~40 文件 · ~18,000 行）

| Python UI 模块                             | 映射到 React 组件                                                                           |
| ------------------------------------------ | ------------------------------------------------------------------------------------------- |
| `ui/main/__init__.py`                      | `apps/desktop/src/main.tsx`（入口）                                                         |
| `ui/main/main_window/__init__.py`          | `apps/desktop/src/components/layout/AppShell.tsx`                                           |
| `ui/main/main_window/chrome.py`            | `apps/desktop/src/components/layout/TopBar.tsx`                                             |
| `ui/main/main_window/drop_zone.py`         | `apps/desktop/src/components/domain/MultiVideoDropzone.tsx`                                 |
| `ui/main/main_window/production_runner.py` | `apps/desktop/src/stores/usePipelineStore.ts`                                               |
| `ui/main/main_window/content_area.py`      | `apps/desktop/src/components/layout/ContentArea.tsx`                                        |
| `ui/main/main_window/theme_controller.py`  | `apps/desktop/src/stores/useThemeStore.ts`                                                  |
| `ui/main/pages/home_page.py` (716)         | `apps/desktop/src/routes/index.tsx` (HomePage)                                              |
| `ui/main/pages/production_page.py` (566)   | `apps/desktop/src/routes/production.tsx` (ProductionPage)                                   |
| `ui/main/pages/assets_page.py` (504)       | `apps/desktop/src/routes/assets.tsx` (AssetsPage)                                           |
| `ui/main/pages/settings_page.py` (880)     | `apps/desktop/src/routes/settings.tsx` (SettingsPage)                                       |
| `ui/main/pages/update_page.py` (958)       | `apps/desktop/src/routes/update.tsx` (UpdatePage)                                           |
| `ui/main/dialogs/`                         | `apps/desktop/src/components/ui/dialog.tsx` (shadcn/ui)                                     |
| `ui/main/widgets/`                         | 分散到 `apps/desktop/src/components/{ui,domain,layout}/`                                    |
| `ui/viewmodels/home_viewmodel.py`          | `apps/desktop/src/stores/useHomeStore.ts`                                                   |
| `ui/viewmodels/production_viewmodel.py`    | `apps/desktop/src/stores/usePipelineStore.ts` + `hooks/usePipelineTask.ts` (TanStack Query) |
| `ui/viewmodels/assets_viewmodel.py`        | `apps/desktop/src/stores/useAssetsStore.ts`                                                 |
| `ui/viewmodels/dashboard_viewmodel.py`     | `apps/desktop/src/stores/useDashboardStore.ts`                                              |
| `ui/widgets/glass_card.py`                 | `apps/desktop/src/components/ui/card.tsx`                                                   |
| `ui/widgets/command_palette.py`            | `apps/desktop/src/components/domain/CommandPalette.tsx`                                     |
| `ui/widgets/help_panel.py`                 | `apps/desktop/src/components/domain/HelpPanel.tsx`                                          |
| `ui/widgets/animated_chart.py`             | `apps/desktop/src/components/domain/AnimatedChart.tsx` (用 Recharts)                        |
| `ui/theme/ds_tokens.py` (728)              | `apps/desktop/src/styles/tokens.css` + `tailwind.config.ts`                                 |
| `ui/theme/animations.py` (442)             | `apps/desktop/src/styles/animations.css` + Framer Motion                                    |
| `ui/theme/theme_manager.py` (380)          | `apps/desktop/src/stores/useThemeStore.ts`                                                  |
| `ui/theme/runtime.py`                      | `apps/desktop/src/hooks/useTheme.ts`                                                        |
| `ui/theme/font_loader.py`                  | `apps/desktop/src/main.tsx`（@fontsource 预加载）                                           |
| `ui/commands/registry.py`                  | `apps/desktop/src/lib/commands.ts`（前端命令注册）                                          |
| `ui/i18n/messages_zh_CN.py`                | `apps/desktop/src/locales/zh-CN/{common,home,...}.json`                                     |
| `ui/i18n/messages_en_US.py`                | `apps/desktop/src/locales/en-US/{common,home,...}.json`                                     |
| `ui/i18n/translator.py`                    | `apps/desktop/src/lib/i18n.ts`（i18next 配置）                                              |

## 3. 关键映射注意事项

### 3.1 不可破坏的不变量

1. **JSON 字段顺序**：所有 Pydantic 模型 → Rust struct，字段顺序完全一致
2. **枚举值**：所有 Python `Enum` 字符串值与 Rust enum 的 `#[serde(rename_all = "snake_case")]` 一致
3. **服务名**：`event_bus` / `config_manager` / `project_manager` 等字符串在 `AppContext::register_named` 中保持
4. **5 步流水线**：`analyze → script → voice → caption → export` 顺序不变
5. **4 种多视频策略**：`single` / `concat` / `batch` / `series` 字符串不变
6. **7 种叙事风格**：`melancholic` / `reflective` / `warm` / `excited` / `mysterious` / `funny` / `neutral` 不变
7. **i18n 命名空间**：`home.*` / `production.*` / `nav.*` / `step.*` / `settings.*` 不变
8. **配置键**：`performance.enable_gpu` / `video.resolution` / `update.channel` 等保持

### 3.2 完全废弃

- ❌ **FastAPI**：全部路由废弃，改 Tauri Command
- ❌ **CORS 中间件**：同进程无需
- ❌ **HTTP API Key 鉴权**：改 Capability ACL
- ❌ **PySide6**：完全替换
- ❌ **pytest + pytest-qt**：改 cargo test + vitest + Playwright
- ❌ **asyncio + ThreadPool**：改 tokio
- ❌ **QSettings**：改 sled（keyring 不变）
- ❌ **Pydantic v2**：改 serde + specta
- ❌ **importlib 插件加载**：改 wasmtime
- ❌ **RedisTaskStore**：删除

### 3.3 保留但增强

- ✅ **5 步流水线状态机**：保留 + 增强（事件订阅）
- ✅ **EventBus**：保留 + 改 tokio broadcast
- ✅ **DI 容器**：保留 + 改 TypeId 索引
- ✅ **配置 5 档 profile**：保留
- ✅ **.scenefab JSON 格式**：保留
- ✅ **剪映草稿 JSON 格式**：保留
- ✅ **11 个 LLM Provider**：保留
- ✅ **Edge-TTS**：保留
- ✅ **5 阶段更新状态机**：保留
- ✅ **自动备份 + 回滚**：保留
- ✅ **路径白名单**：保留 + 增强

## 4. 迁移工作量估算

| 模块                             | 估计工作量（人天） | 关键风险                                     |
| -------------------------------- | ------------------ | -------------------------------------------- |
| `application.py`                 | 2                  | DI 容器实现                                  |
| `core/` (15 文件)                | 10                 | FFmpeg 包装、事件总线、TaskStore             |
| `api/` (7 文件)                  | 2                  | HTTP 改 Tauri Command（机械）                |
| `config/` (5 文件)               | 4                  | 200+ 设置定义迁移                            |
| `models/` (9 文件)               | 3                  | 纯数据，机械迁移                             |
| `services/ai/` (22)              | 18                 | 11 个 Provider 重写                          |
| `services/video/` (18)           | 22                 | monologue_maker 核心复杂                     |
| `services/export/` (8)           | 6                  | 剪映格式兼容                                 |
| `plugins/` (6 文件)              | 10                 | wasmtime 沙箱                                |
| `updater/` (6 文件)              | 4                  | 状态机迁移                                   |
| `project/` (4 文件)              | 4                  | 进程锁                                       |
| `pipeline/` (7 文件)             | 8                  | 状态机                                       |
| `help/` (5 文件)                 | 2                  | Markdown 解析                                |
| `ui/` (~40 文件)                 | 35                 | 5 页面 + 组件库 + 主题 + i18n                |
| 其他（utils/templates/services） | 5                  | 简单                                         |
| **合计**                         | **135 人天**       | ≈ 27 周（单人）/ 14 周（双人）/ 7 周（4 人） |

## 5. 总结

本映射表是 v3.0 迁移的**精确施工蓝图**，每个 Python 文件都明确指定了目标 Rust 模块。关键不变量（JSON 格式、服务名、状态机、5 步流水线、4 种多视频策略）全部保留，确保 v3.0 是**完全等价的功能迁移**，而非重新设计。

下一步：

- [§05-api-routers.md](./05-api-routers.md) ── 详细描述 Tauri Command 重写
- [§06-services-layer.md](./06-services-layer.md) ── 业务服务重写细节
- [§07-config-plugin-updater.md](./07-config-plugin-updater.md) ── 配置/插件/更新器迁移
- [§08-frontend-react.md](./08-frontend-react.md) ── React 前端架构
- [§09-tauri-integration.md](./09-tauri-integration.md) ── Tauri 集成
