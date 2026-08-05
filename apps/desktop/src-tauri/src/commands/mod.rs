//! scenefab src-tauri · Tauri 命令分组 (M4.5 · 35 个命令)
//!
//! 业务域分 module:
//! - [`app`]      : 应用元信息 + 系统探测 (3 个)
//! - [`project`]  : 项目 CRUD (6 个)
//! - [`pipeline`] : 5 步运行时 (5 个)
//! - [`settings`] : 配置持久化 (2 个)
//! - [`update`]   : 应用更新器 (5 个, M4 完整实装)
//! - [`assets`]   : 素材资产管理 (4 个, M3 后续完整实装)
//! - [`export`]   : 导出参数规划 + 字幕渲染 + 多视频编排 (4 个, M4.5 接 scenefab-export/video)
//! - [`help`]     : 内置帮助主题 + 加权搜索 (3 个, M5.7 接 scenefab-help)
//! - [`theme`]    : 后端文案 / Locale 切换 (3 个, M5.6 接 scenefab-i18n)

pub mod app;
pub mod assets;
pub mod export;
pub mod help;
pub mod pipeline;
pub mod project;
pub mod settings;
pub mod theme;
pub mod update;
