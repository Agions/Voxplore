//! src-tauri 命令 · 视频导出与剪映草稿交付
//!
//! - export_plan: 按 quick/custom/silent 模式生成导出计划 (ffmpeg 参数)
//! - export_validate_params: 校验自定义编码参数 (分辨率/fps/码率/codec×container)
//! - export_render_subtitles: 渲染 SRT/ASS/VTT 字幕文本
//! - video_build_plans: 按 single/concat/batch/series 策略生成多视频编排计划
//!
//! 本组命令全部委托纯函数 crate,不做 IO;执行层 (ffmpeg 进程) 由 pipeline 侧负责。

use std::path::PathBuf;

use splicr_domain::{ExportStrategy, ProjectSettings};
use splicr_export::{
    render_subtitles, validate_params, ExportMode, ExportParams, ExportPlan, ExportPlanner,
    SubtitleFormat, SubtitleItem,
};
use splicr_intake::{build_plans, OutputPlan, PlanOptions};

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

#[derive(serde::Serialize)]
pub struct CapcutDraftResult {
    pub draft_folder: String,
    pub draft_id: String,
    pub created_at: String,
}

/// 导出剪映工程草稿 (.draft 文件夹结构)
#[tauri::command]
pub async fn export_capcut_draft(
    app_handle: tauri::AppHandle,
    project_name: String,
    target_dir: Option<String>,
) -> Result<CapcutDraftResult, String> {
    use tauri::Manager;
    let base_dir = if let Some(d) = target_dir {
        PathBuf::from(d)
    } else {
        app_handle
            .path()
            .download_dir()
            .unwrap_or_else(|_| PathBuf::from("/tmp"))
    };

    let draft_id = format!("splicr_draft_{}", chrono::Utc::now().timestamp_millis());
    let draft_folder = base_dir.join(&draft_id);

    tokio::fs::create_dir_all(&draft_folder)
        .await
        .map_err(|e| format!("创建剪映工程草稿目录失败: {e}"))?;

    let info_content = serde_json::json!({
        "draft_id": draft_id,
        "draft_name": project_name,
        "draft_type": "jianyying",
        "version": "2.5.0",
        "fps": 30,
        "canvas_config": {
            "width": 1080,
            "height": 1920,
            "ratio": "9:16"
        }
    });

    let info_str = serde_json::to_string_pretty(&info_content)
        .map_err(|e| format!("序列化 draft_info.json 失败: {e}"))?;

    tokio::fs::write(draft_folder.join("draft_info.json"), info_str)
        .await
        .map_err(|e| format!("写入 draft_info.json 失败: {e}"))?;

    // 生成剪映原生多轨工程 content 描述 (draft_content.json)
    let content_data = serde_json::json!({
        "id": draft_id,
        "version": 250000,
        "duration": 60000000, // 60s in microseconds
        "fps": 30.0,
        "materials": {
            "videos": [],
            "audios": [],
            "texts": [],
            "effects": [
                {
                    "type": "sweep_light",
                    "name": "动态微扫光去重滤镜",
                    "intensity": 0.35
                }
            ]
        },
        "tracks": [
            {
                "id": "track_video_main",
                "type": "video",
                "attribute": 0,
                "segments": []
            },
            {
                "id": "track_voice_narration",
                "type": "audio",
                "attribute": 0,
                "segments": []
            },
            {
                "id": "track_subtitles",
                "type": "text",
                "attribute": 0,
                "segments": []
            },
            {
                "id": "track_bgm_ducking",
                "type": "audio",
                "attribute": 1, // 背景音乐 / 动态闪避
                "segments": []
            }
        ],
        "config": {
            "anti_deduplication": {
                "smart_crop": true,
                "ambient_blur": true,
                "sweep_light": true,
                "subtle_zoom": 1.02
            }
        }
    });

    let content_str = serde_json::to_string_pretty(&content_data)
        .map_err(|e| format!("序列化 draft_content.json 失败: {e}"))?;

    tokio::fs::write(draft_folder.join("draft_content.json"), content_str)
        .await
        .map_err(|e| format!("写入 draft_content.json 失败: {e}"))?;

    Ok(CapcutDraftResult {
        draft_folder: draft_folder.to_string_lossy().to_string(),
        draft_id,
        created_at: chrono::Utc::now().to_rfc3339(),
    })
}
