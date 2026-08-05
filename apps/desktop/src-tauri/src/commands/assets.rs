//! src-tauri 命令 · assets (M3 后续完整实装)
//!
//! - assets_scan       : 扫描目录,返回可导入素材列表
//! - assets_metadata   : ffprobe 抽取单个素材元数据
//! - assets_thumbnail  : ffmpeg 生成首帧缩略图
//! - assets_search     : 在已有 media_files 中按 substring 过滤
//!
//! 所有命令通过 `AppContext.services` 解析 `AssetService` 单例。

use vynaro_storage::{AssetService, ScanResult, ThumbnailResult};
use vynaro_core::AppContext;
use vynaro_detect::FfmpegProbe;
use tauri::State;

/// 扫描目录,返回可导入素材条目列表
#[tauri::command]
pub async fn assets_scan(
    state: State<'_, AppContext>,
    dir: String,
    recursive: Option<bool>,
) -> Result<ScanResult, String> {
    let svc = state
        .service::<AssetService>()
        .await
        .map_err(|e| e.to_string())?;
    svc.scan(&dir, recursive.unwrap_or(false))
        .map_err(|e| e.to_string())
}

/// 提取单个素材的元数据 (duration / resolution / codec / size)
#[tauri::command]
pub async fn assets_metadata(
    state: State<'_, AppContext>,
    path: String,
) -> Result<FfmpegProbe, String> {
    let svc = state
        .service::<AssetService>()
        .await
        .map_err(|e| e.to_string())?;
    svc.metadata(&path).await.map_err(|e| e.to_string())
}

/// 生成首帧缩略图,返回本地路径
#[tauri::command]
pub async fn assets_thumbnail(
    state: State<'_, AppContext>,
    path: String,
    width: Option<u32>,
) -> Result<ThumbnailResult, String> {
    let svc = state
        .service::<AssetService>()
        .await
        .map_err(|e| e.to_string())?;
    svc.thumbnail(&path, width.unwrap_or(320))
        .await
        .map_err(|e| e.to_string())
}

/// 在已有 media_files 中按 substring 过滤
#[tauri::command]
pub async fn assets_search(
    state: State<'_, AppContext>,
    media_paths: Vec<String>,
    pattern: String,
) -> Result<Vec<String>, String> {
    let svc = state
        .service::<AssetService>()
        .await
        .map_err(|e| e.to_string())?;
    Ok(svc.search(&media_paths, &pattern))
}
