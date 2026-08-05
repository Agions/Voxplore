# 02 · 目标 Tauri + Rust + React 架构

> 📌 本章详细描述 v3.0 目标架构：工作区结构、模块边界、依赖方向、运行时拓扑、部署形态。

## 1. 顶层工作区结构

### 1.1 目录布局（最终态）

```
scene-fab/                                       # Monorepo 根
├── .github/                                     # GitHub Actions CI/CD
│   ├── workflows/
│   │   ├── ci-rust.yml                          # Rust CI: test + clippy + fmt
│   │   ├── ci-web.yml                           # Web CI: vitest + playwright
│   │   ├── ci-integration.yml                   # 集成测试 (Python→Rust 行为对比)
│   │   ├── release.yml                          # 三平台打包 + 公证
│   │   └── docs.yml                             # VitePress 文档构建
│   ├── ISSUE_TEMPLATE/
│   └── pull_request_template.md
│
├── apps/                                        # pnpm workspace (前端)
│   ├── desktop/                                 # Tauri 桌面应用
│   │   ├── src/                                 # React 18 + TS 5 前端
│   │   │   ├── main.tsx                         # 入口
│   │   │   ├── App.tsx                          # 根组件
│   │   │   ├── routes/                          # TanStack Router 路由
│   │   │   │   ├── __root.tsx
│   │   │   │   ├── index.tsx                    # /  (HomePage)
│   │   │   │   ├── production.tsx               # /production
│   │   │   │   ├── assets.tsx                   # /assets
│   │   │   │   ├── settings.tsx                 # /settings
│   │   │   │   ├── update.tsx                   # /update
│   │   │   │   └── help.tsx                     # /help
│   │   │   ├── components/                      # 通用组件
│   │   │   │   ├── ui/                          # shadcn/ui 基础组件
│   │   │   │   │   ├── button.tsx
│   │   │   │   │   ├── input.tsx
│   │   │   │   │   ├── dialog.tsx
│   │   │   │   │   ├── dropdown-menu.tsx
│   │   │   │   │   ├── select.tsx
│   │   │   │   │   ├── slider.tsx
│   │   │   │   │   ├── switch.tsx
│   │   │   │   │   ├── tabs.tsx
│   │   │   │   │   ├── toast.tsx
│   │   │   │   │   └── ... (~30 组件)
│   │   │   │   ├── domain/                      # 业务组件
│   │   │   │   │   ├── MultiVideoDropzone.tsx
│   │   │   │   │   ├── PipelineStepper.tsx
│   │   │   │   │   ├── ScriptEditor.tsx
│   │   │   │   │   ├── VoiceSelector.tsx
│   │   │   │   │   ├── SubtitlePreview.tsx
│   │   │   │   │   ├── ExportQueue.tsx
│   │   │   │   │   ├── ProjectCard.tsx
│   │   │   │   │   ├── SystemMonitor.tsx
│   │   │   │   │   └── ...
│   │   │   │   └── layout/                      # 布局
│   │   │   │       ├── AppShell.tsx
│   │   │   │       ├── Sidebar.tsx
│   │   │   │       ├── TopBar.tsx
│   │   │   │       └── StatusBar.tsx
│   │   │   ├── stores/                          # Zustand 状态
│   │   │   │   ├── useThemeStore.ts
│   │   │   │   ├── usePipelineStore.ts
│   │   │   │   ├── useProjectStore.ts
│   │   │   │   └── useUpdateStore.ts
│   │   │   ├── hooks/                           # React Hooks
│   │   │   │   ├── useTauriCommand.ts          # 封装 invoke()
│   │   │   │   ├── useTauriEvent.ts            # 封装 listen()
│   │   │   │   ├── usePipelineTask.ts          # TanStack Query 包装
│   │   │   │   ├── useSystemMetrics.ts         # 订阅 system.metric 事件
│   │   │   │   └── ...
│   │   │   ├── ipc/                             # Tauri IPC 绑定
│   │   │   │   ├── bindings.ts                  # specta 自动生成的类型
│   │   │   │   ├── commands.ts                  # invoke 包装
│   │   │   │   └── events.ts                    # listen 包装
│   │   │   ├── lib/                             # 工具库
│   │   │   │   ├── api.ts                       # 唯一 IPC 入口
│   │   │   │   ├── format.ts
│   │   │   │   ├── validation.ts                # zod schemas
│   │   │   │   └── ...
│   │   │   ├── locales/                         # i18n 资源
│   │   │   │   ├── zh-CN/
│   │   │   │   │   ├── common.json
│   │   │   │   │   ├── home.json
│   │   │   │   │   ├── production.json
│   │   │   │   │   ├── settings.json
│   │   │   │   │   └── errors.json
│   │   │   │   └── en-US/
│   │   │   │       └── ... (同名)
│   │   │   ├── styles/                          # 样式
│   │   │   │   ├── tokens.css                   # CSS Variables (主题令牌)
│   │   │   │   ├── globals.css
│   │   │   │   └── animations.css
│   │   │   ├── types/                           # TS 类型
│   │   │   │   ├── domain.ts
│   │   │   │   ├── ipc.ts
│   │   │   │   └── ...
│   │   │   └── main.tsx
│   │   ├── public/                              # 静态资源
│   │   ├── index.html
│   │   ├── package.json
│   │   ├── tsconfig.json
│   │   ├── tsconfig.node.json
│   │   ├── vite.config.ts
│   │   ├── tailwind.config.ts
│   │   ├── postcss.config.js
│   │   ├── components.json                      # shadcn/ui 配置
│   │   └── .env.example
│   └── web/                                     # 文档站 (VitePress)
│       └── ... (保留 v2.5)
│
├── crates/                                      # Cargo workspace (后端)
│   ├── Cargo.toml                               # workspace root
│   ├── Cargo.lock
│   │
│   ├── scenefab-core/                           # 核心基础设施
│   │   ├── Cargo.toml
│   │   ├── src/
│   │   │   ├── lib.rs                           # 模块导出
│   │   │   ├── error.rs                         # SceneFabError (thiserror)
│   │   │   ├── result.rs                        # Result<T, SceneFabError>
│   │   │   ├── di.rs                            # DIContainer (命名服务)
│   │   │   ├── event.rs                         # EventBus (tokio broadcast)
│   │   │   ├── state.rs                         # AppState 状态机
│   │   │   ├── config.rs                        # ConfigManager (figment)
│   │   │   ├── settings.rs                      # SettingsManager (arc-swap)
│   │   │   ├── settings_data.rs                 # 内置默认设置
│   │   │   ├── i18n.rs                          # i18n 资源加载
│   │   │   ├── audit.rs                         # 审计日志 (tracing)
│   │   │   ├── security.rs                      # Keyring 包装
│   │   │   ├── ratelimit.rs                     # 限流 (governor)
│   │   │   ├── metrics.rs                       # 指标 (可选 prometheus)
│   │   │   ├── task/
│   │   │   │   ├── mod.rs
│   │   │   │   ├── store.rs                     # TaskStore trait
│   │   │   │   ├── memory.rs                    # InMemoryTaskStore
│   │   │   │   └── sqlite.rs                    # SqliteTaskStore (sqlx)
│   │   │   ├── worker.rs                        # BaseWorker (async-trait)
│   │   │   ├── monitor.rs                       # SystemMonitor (sysinfo)
│   │   │   ├── path.rs                          # 路径白名单校验
│   │   │   ├── version.rs                       # 版本号
│   │   │   ├── time.rs                          # 时间工具
│   │   │   ├── retry.rs                         # 重试策略
│   │   │   └── fs/
│   │   │       ├── mod.rs
│   │   │       ├── atomic_write.rs              # 原子化文件写入
│   │   │       └── zip.rs                       # zip 导入导出
│   │   └── tests/                               # 单元测试
│   │
│   ├── scenefab-domain/                         # 领域模型（纯数据 + 业务规则）
│   │   ├── Cargo.toml
│   │   ├── src/
│   │   │   ├── lib.rs
│   │   │   ├── project.rs                       # Project / ProjectMetadata / ProjectSettings
│   │   │   ├── project_repo.rs                  # ProjectRepository trait + SQLite impl
│   │   │   ├── template.rs                      # Template 模型 + 内置模板
│   │   │   ├── template_repo.rs
│   │   │   ├── video.rs                         # VideoProject / VideoSegment / EmotionPeak
│   │   │   ├── narration.rs                     # NarrationBlock / EmotionType / NarrationStyle
│   │   │   ├── media.rs                         # AudioTrack / SubtitleItem / FileMetadata
│   │   │   ├── series.rs                        # SeriesContext
│   │   │   ├── config.rs                        # ConfigDefinition / SettingType / Profile
│   │   │   ├── preset.rs                        # 视频/音频/导出预设
│   │   │   ├── serialization.rs                 # Serializable trait
│   │   │   └── validation.rs                    # 业务规则校验
│   │   └── tests/
│   │
│   ├── scenefab-ffmpeg/                         # FFmpeg 包装
│   │   ├── Cargo.toml
│   │   ├── src/
│   │   │   ├── lib.rs
│   │   │   ├── ffmpeg.rs                        # Ffmpeg 主类
│   │   │   ├── ffprobe.rs                       # Ffprobe 元数据
│   │   │   ├── command.rs                       # tokio::process 包装
│   │   │   ├── progress.rs                      # 进度解析
│   │   │   ├── error.rs                         # FFmpeg 错误转译
│   │   │   ├── hardware.rs                      # 硬件加速检测
│   │   │   └── filter.rs                        # filter 链构造
│   │   └── tests/
│   │
│   ├── scenefab-llm/                            # LLM 子系统
│   │   ├── Cargo.toml
│   │   ├── src/
│   │   │   ├── lib.rs
│   │   │   ├── provider.rs                      # LlmProvider trait
│   │   │   ├── request.rs                       # LlmRequest / Message
│   │   │   ├── response.rs                      # LlmResponse (含流式)
│   │   │   ├── manager.rs                       # LlmManager 路由
│   │   │   ├── stream.rs                        # SSE/WebSocket 流式
│   │   │   ├── error.rs
│   │   │   ├── retry.rs                         # 重试 + 失败切换
│   │   │   ├── rate_limit.rs                    # token 限流
│   │   │   ├── model_catalog.rs                 # 模型目录
│   │   │   ├── script_generator.rs              # 脚本生成器主类
│   │   │   ├── prompt_builder.rs
│   │   │   ├── response_parser.rs
│   │   │   ├── style_prompts.rs                 # 7 种风格
│   │   │   ├── providers/
│   │   │   │   ├── mod.rs
│   │   │   │   ├── openai_compat.rs             # OpenAI 兼容
│   │   │   │   ├── claude.rs
│   │   │   │   ├── deepseek.rs
│   │   │   │   ├── doubao.rs
│   │   │   │   ├── gemini.rs
│   │   │   │   ├── glm5.rs
│   │   │   │   ├── hunyuan.rs
│   │   │   │   ├── kimi.rs
│   │   │   │   ├── local.rs                     # Ollama
│   │   │   │   ├── qwen.rs
│   │   │   │   └── qwen37.rs
│   │   │   └── vision/
│   │   │       ├── mod.rs
│   │   │       ├── vision_provider.rs           # VisionProvider trait
│   │   │       └── ...
│   │   └── tests/
│   │
│   ├── scenefab-tts/                            # TTS 子系统
│   │   ├── Cargo.toml
│   │   ├── src/
│   │   │   ├── lib.rs
│   │   │   ├── provider.rs                      # TtsProvider trait
│   │   │   ├── edge.rs                          # Edge-TTS 实现
│   │   │   ├── voice_generator.rs
│   │   │   ├── voice_models.rs
│   │   │   ├── error.rs
│   │   │   └── audio/
│   │   │       ├── mod.rs
│   │   │       └── processor.rs                 # 音频后处理
│   │   └── tests/
│   │
│   ├── scenefab-video/                           # 视频处理
│   │   ├── Cargo.toml
│   │   ├── src/
│   │   │   ├── lib.rs
│   │   │   ├── monologue_maker.rs               # 核心：5 步制作器
│   │   │   ├── pipeline_integrator.rs           # 5 步流水线整合
│   │   │   ├── perspective_mapper.rs
│   │   │   ├── video_interleaver.rs
│   │   │   ├── scene_converter.rs
│   │   │   ├── scene_analyzer.rs
│   │   │   ├── track_builder.rs
│   │   │   ├── caption_gen.rs
│   │   │   ├── highlight_detector.rs
│   │   │   ├── analyzer.rs
│   │   │   ├── processor.rs
│   │   │   ├── session.rs
│   │   │   ├── extraction/
│   │   │   │   ├── mod.rs
│   │   │   │   └── first_person.rs
│   │   │   ├── cache/
│   │   │   │   ├── mod.rs
│   │   │   │   └── frame_cache.rs
│   │   │   ├── models/
│   │   │   │   ├── mod.rs
│   │   │   │   ├── monologue.rs
│   │   │   │   └── perspective.rs
│   │   │   ├── orchestration/
│   │   │   │   ├── mod.rs
│   │   │   │   ├── pipe_models.rs
│   │   │   │   └── enums.rs
│   │   │   ├── understanding/
│   │   │   │   ├── mod.rs
│   │   │   │   ├── core.rs
│   │   │   │   ├── story_builder.rs
│   │   │   │   └── api_adapters.rs
│   │   │   └── error.rs
│   │   └── tests/
│   │
│   ├── scenefab-export/                         # 导出子系统
│   │   ├── Cargo.toml
│   │   ├── src/
│   │   │   ├── lib.rs
│   │   │   ├── export_manager.rs
│   │   │   ├── video_exporter.rs
│   │   │   ├── jianying_exporter.rs
│   │   │   ├── jianying_adapter.rs
│   │   │   ├── subtitle_exporter.rs
│   │   │   ├── batch_export.rs
│   │   │   ├── presets.rs
│   │   │   └── export_utils.rs
│   │   └── tests/
│   │
│   ├── scenefab-pipeline/                       # 流水线（叙事）
│   │   ├── Cargo.toml
│   │   ├── src/
│   │   │   ├── lib.rs
│   │   │   ├── assembly_steps.rs
│   │   │   ├── understanding_steps.rs
│   │   │   ├── evaluation_steps.rs
│   │   │   ├── fp_workflow.rs                   # 第一人称校验
│   │   │   ├── short_drama.rs                   # 整季短剧
│   │   │   ├── narration/
│   │   │   │   ├── mod.rs
│   │   │   │   ├── engine.rs
│   │   │   │   ├── context.rs
│   │   │   │   ├── evaluator.rs
│   │   │   │   ├── state_machine.rs
│   │   │   │   └── steps.rs
│   │   │   └── error.rs
│   │   └── tests/
│   │
│   ├── scenefab-plugin/                         # 插件系统
│   │   ├── Cargo.toml
│   │   ├── src/
│   │   │   ├── lib.rs
│   │   │   ├── manifest.rs                      # 插件清单
│   │   │   ├── registry.rs                      # 插件注册表
│   │   │   ├── loader.rs                        # 加载器（沙箱）
│   │   │   ├── host.rs                          # 插件宿主 API
│   │   │   ├── signature.rs                     # 数字签名验证
│   │   │   ├── runtime.rs                       # wasmtime runtime
│   │   │   ├── sandbox.rs                       # 沙箱安全策略
│   │   │   ├── context.rs                       # AppContext trait
│   │   │   ├── permissions.rs                   # 权限模型
│   │   │   ├── error.rs
│   │   │   ├── examples/
│   │   │   │   ├── deepseek_voice/              # 第一个 WASM 插件示例
│   │   │   │   └── cinematic_subtitle/          # 第二个 WASM 插件示例
│   │   │   └── sdk/                             # 插件 SDK
│   │   │       ├── mod.rs
│   │   │       └── macros.rs                    # #[scenefab_plugin] 宏
│   │   └── tests/
│   │
│   ├── scenefab-update/                         # 自动更新
│   │   ├── Cargo.toml
│   │   ├── src/
│   │   │   ├── lib.rs
│   │   │   ├── service.rs                       # 5 阶段状态机
│   │   │   ├── downloader.rs                    # 流式下载
│   │   │   ├── installer.rs                     # 原子化安装
│   │   │   ├── manifest.rs                      # Release 清单
│   │   │   ├── verifier.rs                      # SHA-256
│   │   │   ├── backup.rs                        # 备份策略
│   │   │   ├── rollback.rs
│   │   │   └── error.rs
│   │   └── tests/
│   │
│   ├── scenefab-help/                           # 帮助系统
│   │   ├── Cargo.toml
│   │   ├── src/
│   │   │   ├── lib.rs
│   │   │   ├── registry.rs
│   │   │   ├── markdown_parser.rs
│   │   │   ├── models.rs
│   │   │   ├── tooltip.rs
│   │   │   └── content/
│   │   │       ├── mod.rs
│   │   │       ├── zh_CN.rs
│   │   │       └── en_US.rs
│   │   └── tests/
│   │
│   ├── scenefab-i18n/                           # 国际化（后端文案）
│   │   ├── Cargo.toml
│   │   ├── src/
│   │   │   ├── lib.rs
│   │   │   ├── catalog.rs
│   │   │   └── messages/
│   │   │       ├── mod.rs
│   │   │       ├── zh_CN.rs
│   │   │       └── en_US.rs
│   │   └── tests/
│   │
│   └── apps/desktop/src-tauri/                      # Tauri 应用入口
│       ├── Cargo.toml
│       ├── build.rs                             # tauri_build::build()
│       ├── tauri.conf.json
│       ├── capabilities/
│       │   ├── default.json                     # 默认权限
│       │   ├── production.json                  # 生产权限
│       │   └── plugins/                         # 各插件权限
│       │       ├── fs.json
│       │       ├── dialog.json
│       │       ├── shell.json
│       │       ├── updater.json
│       │       ├── store.json
│       │       ├── os.json
│       │       ├── notification.json
│       │       └── process.json
│       ├── icons/
│       ├── src/
│       │   ├── main.rs                          # 入口（调用 app_lib::run）
│       │   ├── lib.rs                           # run() + builder
│       │   ├── state.rs                         # AppState（共享）
│       │   ├── bootstrap.rs                     # 初始化序列
│       │   ├── error.rs                         # Tauri 错误转译
│       │   ├── commands/                        # 所有 Tauri Command
│       │   │   ├── mod.rs
│       │   │   ├── health.rs
│       │   │   ├── project.rs
│       │   │   ├── pipeline.rs
│       │   │   ├── export.rs
│       │   │   ├── config.rs
│       │   │   ├── plugin.rs
│       │   │   ├── update.rs
│       │   │   ├── system.rs
│       │   │   └── help.rs
│       │   ├── events/                          # 事件订阅/发布桥
│       │   │   ├── mod.rs
│       │   │   ├── pipeline.rs
│       │   │   ├── system.rs
│       │   │   └── update.rs
│       │   ├── ipc/                             # IPC 适配
│       │   │   ├── mod.rs
│       │   │   └── dto.rs                        # 前端 DTO 类型
│       │   └── migrations/                      # sqlx 迁移
│       │       ├── 20260804000001_init.sql
│       │       ├── 20260811000002_settings.sql
│       │       └── ...
│       └── tests/                               # 集成测试
│           ├── command_pipeline.rs
│           ├── command_project.rs
│           └── e2e_workflow.rs
│
├── docs/                                        # VitePress 文档
│   ├── .vitepress/
│   ├── guide/                                   # 用户指南
│   ├── refactor/                                # 重构方案
│   │   ├── 00-overview.md (v2.5)
│   │   ├── ...
│   │   └── v3-migration/                        # ★ v3.0 方案
│   │       ├── README.md
│   │       └── ...
│   └── ...
│
├── assets/                                      # 品牌资源
├── resources/                                   # 应用资源（图标等）
├── config/                                      # 配置（YAML/TOML）
│   ├── app_config.yaml                          # 应用配置
│   ├── llm.yaml                                 # LLM Provider 配置
│   └── logging.conf                             # 日志配置
│
├── tests/                                       # 跨模块集成测试
│   ├── python_baseline/                         # Python 实现作为行为黄金文件
│   │   ├── conftest.py
│   │   ├── fixtures/                            # 旧 .scenefab / 视频样本
│   │   └── test_*.py
│   ├── rust_integration/                        # Rust 端到端测试
│   │   └── ...
│   └── e2e/                                     # Playwright E2E
│       ├── home.spec.ts
│       ├── production.spec.ts
│       └── ...
│
├── scripts/                                     # 构建脚本
│   ├── build_linux.sh
│   ├── build_macos.sh
│   ├── build_windows.ps1
│   ├── bundle-docs.py
│   ├── migrate_i18n.py                          # 把 .py i18n 导出为 JSON
│   └── render-assets.py
│
├── bin/                                         # 工具脚本
│   ├── i18n_extract.py
│   └── validate_template_compliance.py
│
├── pnpm-workspace.yaml                          # pnpm workspace 定义
├── package.json                                 # 根 package.json
├── pyproject.toml                               # 仅保留：迁移期 Python 工具
├── Cargo.toml                                   # ★ Cargo workspace root
├── Cargo.lock
├── rust-toolchain.toml                          # Rust 1.85+ 锁定
├── .rustfmt.toml
├── .clippy.toml
├── Makefile                                     # 顶层命令
├── README.md
├── CHANGELOG.md
├── LICENSE
├── .gitignore
├── .editorconfig
├── .pre-commit-config.yaml
└── cspell.json
```

### 1.2 Cargo workspace 根（`Cargo.toml`）

```toml
[workspace]
resolver = "2"
members = [
    "crates/scenefab-core",
    "crates/scenefab-domain",
    "crates/scenefab-ffmpeg",
    "crates/scenefab-llm",
    "crates/scenefab-tts",
    "crates/scenefab-video",
    "crates/scenefab-export",
    "crates/scenefab-pipeline",
    "crates/scenefab-plugin",
    "crates/scenefab-update",
    "crates/scenefab-help",
    "crates/scenefab-i18n",
    "apps/desktop/src-tauri",
]

[workspace.package]
version = "3.0.0"
edition = "2021"
rust-version = "1.85"
license = "MIT"
authors = ["Agions <agions@qq.com>"]
repository = "https://github.com/Agions/scene-fab"

[workspace.dependencies]
# 异步运行时
tokio = { version = "1.42", features = ["full"] }
async-trait = "0.1"
futures = "0.3"
futures-util = "0.3"

# HTTP 客户端
reqwest = { version = "0.12", default-features = false, features = [
    "json", "stream", "rustls-tls", "gzip", "brotli"
] }

# 序列化
serde = { version = "1.0", features = ["derive"] }
serde_json = "1.0"
serde_yaml = "0.9"
toml = "0.8"
bincode = "1.3"

# 类型 + IPC
specta = { version = "2.0.0-rc.20", features = ["derive", "typescript"] }
specta-typescript = "0.0.9"
ts-rs = "10.0"

# 数据库
sqlx = { version = "0.8", features = [
    "runtime-tokio-rustls", "sqlite", "postgres", "macros", "chrono", "uuid"
] }
sled = "0.34"

# 错误
thiserror = "2.0"
anyhow = "1.0"

# 日志
tracing = "0.1"
tracing-subscriber = { version = "0.3", features = ["env-filter", "json"] }
tracing-appender = "0.2"

# 安全
keyring = { version = "3.6", features = ["apple-native", "windows-native", "sync-secret-service"] }
ring = "0.17"
rustls = "0.23"
constant_time_eq = "0.3"

# 系统
sysinfo = "0.32"
psutil = "0.2"  # 跨平台 psutil 兼容

# 并行
rayon = "1.10"
crossbeam-channel = "0.5"

# 文件
tokio-util = { version = "0.7", features = ["io"] }
zip = { version = "2.2", default-features = false, features = ["deflate"] }
tempfile = "3.13"
walkdir = "2.5"

# 时间
chrono = { version = "0.4", features = ["serde"] }

# 文本
regex = "1.11"
once_cell = "1.20"

# UUID
uuid = { version = "1.11", features = ["v4", "v7", "serde"] }

# 配置
figment = { version = "0.10", features = ["yaml", "env", "toml"] }
arc-swap = "1.7"

# 限流
governor = "0.7"

# 插件沙箱
wasmtime = "29.0"
wasmtime-wasi = "29.0"

# 国际化
rust-i18n = "3.1"
unic-langid = "0.9"

# 实用工具
url = "2.5"
mime = "0.3"
bytes = "1.8"
dotenvy = "0.15"
directories = "5.0"

# 加密 + 哈希
sha2 = "0.10"
sha1 = "0.10"
hmac = "0.12"
hex = "0.4"
base64 = "0.22"

# 锁
parking_lot = "0.12"
flock = "0.3"

# Tauri
tauri = { version = "2.1", features = ["macos-private-api", "tray-icon", "image-png"] }
tauri-plugin-fs = "2.0"
tauri-plugin-dialog = "2.0"
tauri-plugin-shell = "2.0"
tauri-plugin-updater = "2.0"
tauri-plugin-store = "2.0"
tauri-plugin-os = "2.0"
tauri-plugin-notification = "2.0"
tauri-plugin-process = "2.0"
tauri-plugin-window-state = "2.0"
tauri-plugin-deep-link = "2.0"
tauri-plugin-log = "2.0"
tauri-plugin-single-instance = "2.0"

# 序列化（DuckDB/Parquet 可选）
duckdb = { version = "1.1", optional = true }
parquet = { version = "53", optional = true }

# 测试
tokio-test = "0.4"
mockito = "1.5"
wiremock = "0.6"
criterion = { version = "0.5", features = ["html_reports"] }
proptest = "1.5"
tarpaulin = "0.31"  # 覆盖率

# 开发工具
cargo-watch = "1.0"
cargo-nextest = "0.9"
cargo-audit = "0.21"
sccache = "1.0"  # 编译缓存

[workspace.lints.rust]
unsafe_code = "deny"
unused_must_use = "deny"
missing_docs = "warn"

[profile.dev]
opt-level = 0
debug = 1
incremental = true

[profile.release]
opt-level = 3
lto = "thin"
codegen-units = 1
strip = "debuginfo"
panic = "abort"
```

### 1.3 pnpm workspace 根

`pnpm-workspace.yaml`：

```yaml
packages:
  - "apps/*"
```

## 2. 模块依赖关系图

### 2.1 Crate 依赖方向（严格分层）

```
┌─────────────────────────────────────────────────────┐
│  Layer 4: Application                               │
│  ┌──────────────────────────────────────────┐       │
│  │ apps/desktop/src-tauri                       │       │
│  └──────────────────────────────────────────┘       │
└──────────────────────┬──────────────────────────────┘
                       │
       ┌───────────────┼───────────────┐
       ▼               ▼               ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│  Layer 3:    │ │  Layer 3:    │ │  Layer 3:    │
│  Domain      │ │  Pipeline    │ │  Plugins     │
│  Services    │ │  (narration) │ │  (host)      │
│  (video/     │ │              │ │              │
│   export/    │ │              │ │              │
│   llm/       │ │              │ │              │
│   tts/       │ │              │ │              │
│   plugin/    │ │              │ │              │
│   update/    │ │              │ │              │
│   help/)     │ │              │ │              │
└──────┬───────┘ └──────┬───────┘ └──────┬───────┘
       │                │                │
       └────────────────┼────────────────┘
                        │
       ┌────────────────┼────────────────┐
       ▼                ▼                ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│  Layer 2:    │ │  Layer 2:    │ │  Layer 2:    │
│  Core        │ │  FFmpeg      │ │  Domain      │
│  (infra)     │ │  (wrapper)   │ │  (models)    │
└──────┬───────┘ └──────┬───────┘ └──────┬───────┘
       │                │                │
       └────────────────┼────────────────┘
                        │
                        ▼
                ┌──────────────┐
                │  Layer 1:    │
                │  3rd-party   │
                │  crates      │
                │  (tokio,     │
                │   serde,     │
                │   reqwest,   │
                │   wasmtime,  │
                │   tauri)     │
                └──────────────┘
```

### 2.2 Crate 间依赖（精确保留）

```toml
# scenefab-core
[dependencies]
tokio, serde, thiserror, tracing, figment, keyring, sqlx, sled, sysinfo, chrono, uuid, ...

# scenefab-domain
[dependencies]
scenefab-core (仅 error + result), serde, thiserror, specta

# scenefab-ffmpeg
[dependencies]
scenefab-core, tokio, serde, thiserror, tracing

# scenefab-llm
[dependencies]
scenefab-core, scenefab-domain, reqwest, tokio, async-trait, futures, governor, tracing, thiserror

# scenefab-tts
[dependencies]
scenefab-core, scenefab-domain, reqwest, tokio, async-trait, thiserror

# scenefab-video
[dependencies]
scenefab-core, scenefab-domain, scenefab-ffmpeg, scenefab-llm, scenefab-tts, tokio, rayon, async-trait, tracing

# scenefab-export
[dependencies]
scenefab-core, scenefab-domain, scenefab-ffmpeg, tokio, async-trait, thiserror

# scenefab-pipeline
[dependencies]
scenefab-core, scenefab-domain, scenefab-video, scenefab-llm, async-trait

# scenefab-plugin
[dependencies]
scenefab-core, scenefab-domain, wasmtime, async-trait, thiserror, tracing

# scenefab-update
[dependencies]
scenefab-core, scenefab-domain, reqwest, tokio, sha2, thiserror, tracing, async-trait

# scenefab-help
[dependencies]
scenefab-core, scenefab-domain, pulldown-cmark, serde, thiserror

# scenefab-i18n
[dependencies]
scenefab-core, rust-i18n, unic-langid, thiserror

# apps/desktop/src-tauri
[dependencies]
scenefab-core, scenefab-domain, scenefab-ffmpeg, scenefab-llm, scenefab-tts,
scenefab-video, scenefab-export, scenefab-pipeline, scenefab-plugin,
scenefab-update, scenefab-help, scenefab-i18n,
tauri, tauri-plugin-*, specta, tokio, async-trait
```

### 2.3 强制依赖规则（编译期保证）

通过 workspace lints + clippy.toml 强制：

```toml
# .clippy.toml
avoid-breaking-exported-api = false
disallowed-methods = [
    { path = "std::process::Command::new", reason = "Use tokio::process::Command instead" },
    { path = "std::fs::File::create", reason = "Use tokio::fs::File or async fs" },
]
disallowed-types = [
    { path = "tokio::sync::Mutex", reason = "Use parking_lot::Mutex for sync contexts" },
]
```

## 3. 运行时进程模型

### 3.1 Tauri 多进程架构

```
┌──────────────────────────────────────────────────────────┐
│  User launches scenefab                                  │
└────────────────────────┬─────────────────────────────────┘
                         ▼
┌──────────────────────────────────────────────────────────┐
│  Main Process (Rust)                                     │
│  ─────────────────                                       │
│  - tauri::Builder::default()                             │
│  - 初始化 AppContext (DI)                                │
│  - 初始化 EventBus                                       │
│  - 初始化所有子系统 (monologue_maker, llm_manager, ...) │
│  - 创建主窗口 (Main Window)                              │
│  - 监听退出信号                                           │
└────────────────────────┬─────────────────────────────────┘
                         │ spawns WebView
                         ▼
┌──────────────────────────────────────────────────────────┐
│  WebView Process (WebKit/Edge WebView2)                  │
│  ─────────────────────────────────────                   │
│  - 加载 apps/desktop/dist/index.html                      │
│  - React 18 应用运行                                      │
│  - invoke('command_name', args) → IPC → Main Process     │
│  - listen('event_name', handler) ← Event ← Main Process  │
│  - 完全沙箱（无 Node.js / 无 fetch 外网，仅经 Main 代理） │
└──────────────────────────────────────────────────────────┘

                         ▲
                         │ IPC Bridge (Tauri 2 JSON-RPC)
                         ▼
┌──────────────────────────────────────────────────────────┐
│  Plugin Processes (隔离子进程)                            │
│  ───────────────────────────                             │
│  - wasmtime 沙箱（每个插件 1 个实例）                     │
│  - 仅允许 manifest 中声明的权限                          │
│  - 网络访问经 Main Process 代理（白名单域名）              │
│  - 文件访问经 Main Process 代理（白名单目录）              │
└──────────────────────────────────────────────────────────┘

                         ▲
                         │ 临时子进程
                         ▼
┌──────────────────────────────────────────────────────────┐
│  External Subprocesses                                    │
│  ────────────────────                                    │
│  - ffmpeg (视频处理)                                     │
│  - ffprobe (元数据)                                      │
│  - edge-tts (TTS)                                        │
│  - 临时命令（如 git, curl）                               │
└──────────────────────────────────────────────────────────┘
```

### 3.2 tokio Runtime 配置

```rust
// apps/desktop/src-tauri/src/lib.rs

pub fn run() {
    let runtime = tokio::runtime::Builder::new_multi_thread()
        .enable_all()
        .worker_threads(num_cpus::get())
        .thread_name("scenefab-main")
        .build()
        .expect("Failed to create tokio runtime");

    runtime.block_on(async {
        tauri::async_runtime::set(tokio::runtime::Handle::current());

        tauri::Builder::default()
            .setup(|app| {
                // 1. 初始化 AppContext
                let ctx = AppContext::new(app.handle().clone()).await?;
                app.manage(ctx);

                // 2. 启动后台监控
                ctx.start_background_services().await?;

                Ok(())
            })
            .invoke_handler(tauri::generate_handler![
                // 所有 Command
                commands::health::get_health,
                commands::project::create_project,
                commands::project::list_projects,
                commands::pipeline::start_pipeline,
                commands::pipeline::get_status,
                // ... 30+ Commands
            ])
            .register_asynchronous_uri_scheme_protocol(...)
            .run(tauri::generate_context!())
            .expect("Error while running tauri application");
    });
}
```

## 4. 状态管理（AppContext）

### 4.1 AppContext 核心结构

```rust
// crates/scenefab-core/src/di.rs

pub struct AppContext {
    /// 内部服务注册表
    services: Arc<RwLock<HashMap<TypeId, Box<dyn Any + Send + Sync>>>>,
    named: Arc<RwLock<HashMap<String, Box<dyn Any + Send + Sync>>>>,

    /// Tauri AppHandle（用于 emit 事件）
    app_handle: tauri::AppHandle,

    /// 关闭信号
    shutdown_tx: broadcast::Sender<()>,

    /// 启动时间
    started_at: Instant,
}

impl AppContext {
    pub async fn new(app: tauri::AppHandle) -> Result<Self, SceneFabError> {
        let ctx = Self { /* ... */ };

        // 按顺序初始化服务
        ctx.init_logger().await?;
        ctx.init_config().await?;
        ctx.init_event_bus().await?;
        ctx.init_task_store().await?;
        ctx.init_audit().await?;
        ctx.init_security().await?;
        ctx.init_health_monitor().await?;
        ctx.init_llm_manager().await?;
        ctx.init_tts().await?;
        ctx.init_video().await?;
        ctx.init_export().await?;
        ctx.init_plugin_registry().await?;
        ctx.init_updater().await?;

        Ok(ctx)
    }

    /// 注册服务（单例）
    pub fn register<T: Send + Sync + 'static>(&self, service: Arc<T>) {
        let mut services = self.services.write().await;
        services.insert(TypeId::of::<T>(), Box::new(service));
    }

    /// 按名称注册
    pub fn register_named<T: Send + Sync + 'static>(&self, name: &str, service: Arc<T>) {
        let mut named = self.named.write().await;
        named.insert(name.to_string(), Box::new(service));
    }

    /// 获取服务
    pub fn get<T: Send + Sync + 'static>(&self) -> Option<Arc<T>> {
        let services = self.services.blocking_read();
        services.get(&TypeId::of::<T>())
            .and_then(|b| b.downcast_ref::<Arc<T>>())
            .cloned()
    }

    /// 按名称获取
    pub fn get_named<T: Send + Sync + 'static>(&self, name: &str) -> Option<Arc<T>> {
        let named = self.named.blocking_read();
        named.get(name)
            .and_then(|b| b.downcast_ref::<Arc<T>>())
            .cloned()
    }

    /// 关闭所有服务
    pub async fn shutdown(&self) {
        let _ = self.shutdown_tx.send(());
        // 顺序关闭：updater → plugin → export → video → tts → llm → monitor → task → audit → security
    }
}
```

### 4.2 核心服务清单

| 服务名（按名称）      | 类型                      | 生命周期  | 持久化 |
| --------------------- | ------------------------- | --------- | ------ |
| `logger`              | `Arc<Logger>`             | Singleton | 否     |
| `config_manager`      | `Arc<ConfigManager>`      | Singleton | ✅     |
| `settings_manager`    | `Arc<SettingsManager>`    | Singleton | ✅     |
| `event_bus`           | `Arc<EventBus>`           | Singleton | 否     |
| `task_store`          | `Arc<dyn TaskStore>`      | Singleton | ✅     |
| `audit`               | `Arc<AuditLogger>`        | Singleton | ✅     |
| `security`            | `Arc<Keyring>`            | Singleton | ✅     |
| `system_monitor`      | `Arc<SystemMonitor>`      | Singleton | 否     |
| `project_manager`     | `Arc<ProjectManager>`     | Singleton | ✅     |
| `template_manager`    | `Arc<TemplateManager>`    | Singleton | ✅     |
| `llm_manager`         | `Arc<LlmManager>`         | Singleton | 否     |
| `tts_manager`         | `Arc<TtsManager>`         | Singleton | 否     |
| `monologue_maker`     | `Arc<MonologueMaker>`     | Singleton | 否     |
| `pipeline_integrator` | `Arc<PipelineIntegrator>` | Singleton | 否     |
| `export_manager`      | `Arc<ExportManager>`      | Singleton | 否     |
| `plugin_registry`     | `Arc<PluginRegistry>`     | Singleton | ✅     |
| `updater_service`     | `Arc<UpdaterService>`     | Singleton | ✅     |
| `help_registry`       | `Arc<HelpRegistry>`       | Singleton | 否     |
| `i18n_catalog`        | `Arc<I18nCatalog>`        | Singleton | 否     |

## 5. IPC 命令清单（核心）

Tauri Command 命名采用 `领域_动作` 形式：

```rust
// apps/desktop/src-tauri/src/commands/mod.rs

#[tauri::command]
pub async fn health_get(app: tauri::AppHandle) -> Result<HealthDto, SceneFabError> { ... }

#[tauri::command]
pub async fn project_list(app: tauri::AppHandle) -> Result<Vec<ProjectDto>, SceneFabError> { ... }

#[tauri::command]
pub async fn project_create(
    app: tauri::AppHandle,
    request: ProjectCreateRequest,
) -> Result<ProjectDto, SceneFabError> { ... }

#[tauri::command]
pub async fn pipeline_start(
    app: tauri::AppHandle,
    request: PipelineStartRequest,
) -> Result<PipelineTaskDto, SceneFabError> { ... }

#[tauri::command]
pub async fn pipeline_get_status(
    app: tauri::AppHandle,
    task_id: TaskId,
) -> Result<PipelineStatusDto, SceneFabError> { ... }

#[tauri::command]
pub async fn pipeline_cancel(
    app: tauri::AppHandle,
    task_id: TaskId,
) -> Result<(), SceneFabError> { ... }

// ... 共 35 个 Commands
```

完整清单见 [§09-tauri-integration.md](./09-tauri-integration.md)。

## 6. 数据流示例（5 步流水线启动）

```
[React Frontend]                          [Rust Backend]                    [External]

User clicks "开始制作"

hooks/usePipelineTask.ts {
  startPipeline.mutate({
    sources: [video1.mp4, video2.mp4],
    strategy: 'batch',
    emotion: 'healing'
  })
}
        │
        │ invoke('pipeline_start', req)
        ▼
                                         commands/pipeline.rs::pipeline_start
                                         ├─ ctx.get_named::<ProjectManager>("project_manager")
                                         │    .create_project(...)
                                         ├─ ctx.get_named::<TaskStore>("task_store")
                                         │    .save(task_id, {status: 'pending', ...})
                                         ├─ ctx.get_named::<EventBus>("event_bus")
                                         │    .publish("task.created", task_id)
                                         ├─ tokio::spawn(async move {
                                         │      run_pipeline_task(...).await
                                         │  })
                                         │
                                         │  [PipelineIntegrator]
                                         │   ├─ 1. analyze_scenes() ───────────► ffmpeg subprocess
                                         │   │    [publish "task.progress" 15%]
                                         │   │    [emit to frontend]
                                         │   │
                                         │   ├─ 2. generate_script() ──────────► LLM (DeepSeek)
                                         │   │    [stream tokens via SSE]
                                         │   │    [emit "task.token" 实时推送]
                                         │   │    [publish "task.progress" 35%]
                                         │   │
                                         │   ├─ 3. generate_voice() ───────────► Edge-TTS subprocess
                                         │   │    [publish "task.progress" 60%]
                                         │   │
                                         │   ├─ 4. generate_captions() ────────► in-process
                                         │   │    [publish "task.progress" 75%]
                                         │   │
                                         │   ├─ 5. export_jianying() ──────────► in-process
                                         │   │    [publish "task.progress" 95%]
                                         │   │
                                         │   └─ 6. final ─────────────────────► task_store.update(status='completed')
                                         │        [emit "task.completed"]
                                         │  })
                                         │
        │
        ▼ listen('task.progress', ...)
hooks/usePipelineTask.ts {
  setState({ progress: 35, step: 'script' })
}
```

## 7. 部署形态对比

### 7.1 v2.4.3 (Python)

```
SceneFab-2.4.3.dmg (macOS)
├── SceneFab.app/         (PyInstaller 打包)
│   ├── Contents/
│   │   ├── MacOS/
│   │   │   ├── SceneFab               # 启动器
│   │   │   └── python311.dll + PySide6 + 200+ .so
│   │   ├── Resources/
│   │   │   ├── icon.icns
│   │   │   └── app/
│   │   │       ├── __init__.py
│   │   │       ├── core/
│   │   │       ├── services/
│   │   │       └── ...  (57,050 行)
│   │   └── Info.plist
└── 大小：~80 MB
启动：~1.5s
内存：~280 MB
```

### 7.2 v3.0.0 (Tauri + Rust)

```
SceneFab-3.0.0.dmg (macOS)
├── SceneFab.app/
│   ├── Contents/
│   │   ├── MacOS/
│   │   │   └── SceneFab              # 单个二进制（Rust）
│   │   ├── Resources/
│   │   │   ├── icon.icns
│   │   │   ├── app/
│   │   │   │   ├── dist/             # WebView 加载的静态资源
│   │   │   │   │   ├── index.html
│   │   │   │   │   ├── assets/
│   │   │   │   │   │   ├── index-abc123.js   # Vite 打包
│   │   │   │   │   │   ├── index-def456.css
│   │   │   │   │   │   └── ... (1-2 MB)
│   │   │   │   │   └── locales/      # i18n JSON
│   │   │   │   └── plugins/          # WASM 插件
│   │   │   │       ├── deepseek_voice.wasm
│   │   │   │       └── cinematic_subtitle.wasm
│   │   │   └── locales/              # 错误消息 i18n
│   │   └── Info.plist
└── 大小：<8 MB
启动：<500ms
内存：<90 MB
```

### 7.3 三平台打包目标

| 平台    | 打包格式                      | 大小目标 | 分发渠道                          |
| ------- | ----------------------------- | -------- | --------------------------------- |
| macOS   | `.dmg` (Universal)            | <10 MB   | GitHub Releases + Homebrew Cask   |
| Windows | `.msi` + `.exe`               | <8 MB    | GitHub Releases + Microsoft Store |
| Linux   | `.AppImage` + `.deb` + `.rpm` | <8 MB    | GitHub Releases + Flathub         |

## 8. CI/CD 矩阵

```yaml
# .github/workflows/ci-rust.yml
name: Rust CI
on: [push, pull_request]
jobs:
  test:
    strategy:
      matrix:
        os: [ubuntu-latest, macos-latest, windows-latest]
        rust: [stable, 1.85]
    runs-on: ${{ matrix.os }}
    steps:
      - uses: actions/checkout@v4
      - uses: dtolnay/rust-toolchain@${{ matrix.rust }}
      - uses: Swatinem/rust-cache@v2
      - run: cargo nextest run --all-features
      - run: cargo clippy --all-targets --all-features -- -D warnings
      - run: cargo fmt --all -- --check
      - run: cargo audit

# .github/workflows/ci-web.yml
name: Web CI
on: [push, pull_request]
jobs:
  test:
    strategy:
      matrix:
        os: [ubuntu-latest, macos-latest, windows-latest]
    runs-on: ${{ matrix.os }}
    steps:
      - uses: actions/checkout@v4
      - uses: pnpm/action-setup@v4
        with:
          version: 9
      - uses: actions/setup-node@v4
        with:
          node-version: 22
      - run: pnpm install --frozen-lockfile
      - run: pnpm --filter desktop test
      - run: pnpm --filter desktop typecheck
      - run: pnpm --filter desktop lint
      - run: pnpm --filter desktop build
```

## 9. 总结：架构关键变化

| 维度         | v2.4.3 (Python)         | v3.0 (Tauri + Rust)                    |
| ------------ | ----------------------- | -------------------------------------- |
| **进程数**   | 1（单进程多线程）       | 4（Main + WebView + 多个 Plugin WASM） |
| **语言**     | Python 3.10             | Rust 1.85 + TypeScript 5               |
| **UI 框架**  | PySide6 (Qt Widgets)    | React 18 + shadcn/ui + Tailwind v4     |
| **IPC**      | Qt Signal + QTimer      | Tauri Command + Event + tokio          |
| **状态机**   | enum + QObject State    | enum + Arc<RwLock<AppState>>           |
| **事件总线** | Python dict + threading | tokio broadcast channel                |
| **HTTP 层**  | FastAPI + Uvicorn       | 完全废弃                               |
| **DI 容器**  | 自研 dict-based         | 自研 TypeId-based (类型安全)           |
| **存储**     | SQLite + Redis          | sqlx (SQLite/Postgres) + sled          |
| **插件**     | importlib + 路径校验    | wasmtime + 数字签名                    |
| **安全**     | cryptography + keyring  | ring + keyring-rs + rustls             |
| **测试**     | pytest + pytest-qt      | cargo test + vitest + Playwright       |
| **打包**     | PyInstaller (~80MB)     | Tauri Bundle (<8MB)                    |
| **启动**     | 1.5s                    | <500ms                                 |
| **内存**     | 280MB                   | <90MB                                  |

详细 Rust crate 与映射见 [§03-rust-backend.md](./03-rust-backend.md) 与 [§04-module-mapping.md](./04-module-mapping.md)。
