//! src-tauri 命令 · app 元信息 + 系统探测

use chrono::{DateTime, Utc};
use scenefab_core::AppContext;
use scenefab_ffmpeg::Ffmpeg;
use serde::Serialize;
use tauri::State;

/// 返回 AppContext 中的 semver 版本 (字符串格式)
#[tauri::command]
pub fn app_version(state: State<'_, AppContext>) -> String {
    state.version.to_string()
}

/// 返回 AppContext 中记录的进程启动时间 (ISO 8601)
#[tauri::command]
pub fn app_started_at(state: State<'_, AppContext>) -> Result<DateTime<Utc>, String> {
    Ok(state.started_at)
}

/// 系统探测 (ffmpeg 可用性 + 版本)
#[tauri::command]
pub async fn app_system_info() -> SystemInfo {
    let ffmpeg_available = Ffmpeg::is_available();
    let ffmpeg_version = if ffmpeg_available {
        probe_ffmpeg_version().await
    } else {
        None
    };
    SystemInfo {
        ffmpeg_available,
        ffmpeg_version,
    }
}

#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct SystemInfo {
    pub ffmpeg_available: bool,
    pub ffmpeg_version: Option<String>,
}

/// 调用 ffmpeg -version 并提取第一行 (用于 UI 显示)
async fn probe_ffmpeg_version() -> Option<String> {
    use tokio::process::Command;
    let out = Command::new("ffmpeg").arg("-version").output().await.ok()?;
    if !out.status.success() {
        return None;
    }
    let s = String::from_utf8_lossy(&out.stdout);
    s.lines().next().map(|l| l.to_string())
}
