//! monoloop-core v1.0.0  · 服务容器 + 错误 + Tracing 全应用基础设施
//!
//! ## 责任范围
//! 提供整个应用共享的基础设施层:
//! - [`context`]   : `AppContext` — 全局状态容器 (Tauri `State` 注入对象)
//! - [`container`] : `ServiceContainer` — 19 个核心服务的注册与解析
//! - [`error`]     : `MonoloopError` + `MonoloopResult` — 统一错误类型 (Tauri Command 返回)
//! - [`logging`]   : `init_logging` — `tracing_subscriber` 初始化
//! - [`domain`]    : re-export 跨模块领域原语 (delegate 给 monoloop-domain)
//! - [`services`]  : 19 个 service 注册入口
//!
//! ## M2 范围
//! - `AppContext` 含 `ServiceContainer` + `Version` + `started_at`
//! - `ServiceContainer` 暴露 `Arc<Mutex<HashMap<TypeId, Box<dyn Any>>>>`
//! - `MonoloopError` 共 9 类 (`Config`/`Llm`/`Tts`/`Ffmpeg`/`Io`/`Project`/`Pipeline`/`Plugin`/`Updater`)
//! - `init_logging` 读取 `RUST_LOG` 环境变量,默认 `info`
//!
//! ## 后续模块规划 (M3+)
//! - 详见 docs/refactor/v3-migration/03-rust-backend.md § Core Layer

#![allow(dead_code, unused_imports)]

pub mod container;
pub mod context;
pub mod domain;
pub mod error;
pub mod help;
pub mod i18n;
pub mod logging;
pub mod services;

pub use container::ServiceContainer;
pub use context::{AppContext, AppContextBuilder};
pub use error::{MonoloopError, MonoloopResult};
pub use help::{HelpCategory, HelpRegistry, HelpTopic, SearchHit};
pub use i18n::{Locale, Translator};
pub use logging::init_logging;
pub use services::{ConfigService, LoggingService, ProjectService};
