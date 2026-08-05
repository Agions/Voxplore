//! src-tauri 命令 · export (M4.5 · 接 scenefab-export / scenefab-video)
//!
//! - export_plan: 按 quick/custom/silent 模式生成导出计划 (ffmpeg 参数)
//! - export_validate_params: 校验自定义编码参数 (分辨率/fps/码率/codec×container)
//! - export_render_subtitles: 渲染 SRT/ASS/VTT 字幕文本
//! - video_build_plans: 按 single/concat/batch/series 策略生成多视频编排计划
//!
//! 本组命令全部委托纯函数 crate,不做 IO;执行层 (ffmpeg 进程) 由 pipeline 侧负责。

use std::path::PathBuf;

use scenefab_domain::{ExportStrategy, ProjectSettings};
use scenefab_export::{
    render_subtitles, validate_params, ExportMode, ExportParams, ExportPlan, ExportPlanner,
    SubtitleFormat, SubtitleItem,
};
use scenefab_video::{build_plans, OutputPlan, PlanOptions};

/// 按模式生成导出计划。custom 模式必须携带 settings。
#[tauri::command]
pub async fn export_plan(
    mode: ExportMode,
    settings: Option<ProjectSettings>,
) -> Result<ExportPlan, String> {
    ExportPlanner::new()
        .plan(mode, settings.as_ref())
        .map_err(|e| e.to_string())
}

/// 校验自定义编码参数 (前端"高级导出"表单即时校验用)
#[tauri::command]
pub async fn export_validate_params(params: ExportParams) -> Result<(), String> {
    validate_params(&params).map_err(|e| e.to_string())
}

/// 渲染字幕文本 (SRT / ASS / VTT),条目时间区间倒挂返回错误
#[tauri::command]
pub async fn export_render_subtitles(
    items: Vec<SubtitleItem>,
    format: SubtitleFormat,
) -> Result<String, String> {
    render_subtitles(&items, format).map_err(|e| e.to_string())
}

/// 按 4 策略生成多视频编排计划。options 缺省用 PlanOptions::default()。
#[tauri::command]
pub async fn video_build_plans(
    sources: Vec<PathBuf>,
    strategy: ExportStrategy,
    options: Option<PlanOptions>,
) -> Result<Vec<OutputPlan>, String> {
    let opts = options.unwrap_or_default();
    build_plans(&sources, strategy, &opts).map_err(|e| e.to_string())
}
