//! src-tauri 命令 · settings 持久化 (M3.2)
//!
//! ConfigSnapshot 落盘到 `app_data_dir/config.json`。
//! 第一次启动若无文件 → 返回默认 snapshot。

use std::path::PathBuf;

use tauri::{Manager, State};
use vynaro_core::services::{ConfigService, ConfigSnapshot};
use vynaro_core::AppContext;

const CONFIG_FILE: &str = "config.json";

/// 读取配置 (优先磁盘,缺则返回默认)
#[tauri::command]
pub async fn settings_get(
    app: tauri::AppHandle,
    state: State<'_, AppContext>,
) -> Result<ConfigSnapshot, String> {
    let path = config_path(&app).map_err(|e| e.to_string())?;
    if let Ok(bytes) = tokio::fs::read(&path).await {
        if let Ok(snap) = serde_json::from_slice::<ConfigSnapshot>(&bytes) {
            // 同步到内存 service
            let svc = state
                .service::<ConfigService>()
                .await
                .map_err(|e| e.to_string())?;
            svc.set_snapshot(snap.clone()).await;
            return Ok(snap);
        }
    }
    // fallback: 默认 snapshot
    Ok(ConfigSnapshot::default())
}

/// 保存配置 (同时落盘 + 更新内存)
#[tauri::command]
pub async fn settings_set(
    app: tauri::AppHandle,
    state: State<'_, AppContext>,
    snapshot: ConfigSnapshot,
) -> Result<(), String> {
    let path = config_path(&app).map_err(|e| e.to_string())?;
    if let Some(parent) = path.parent() {
        tokio::fs::create_dir_all(parent)
            .await
            .map_err(|e| e.to_string())?;
    }
    let bytes = serde_json::to_vec_pretty(&snapshot).map_err(|e| e.to_string())?;
    tokio::fs::write(&path, bytes)
        .await
        .map_err(|e| e.to_string())?;

    let svc = state
        .service::<ConfigService>()
        .await
        .map_err(|e| e.to_string())?;
    svc.set_snapshot(snapshot).await;
    Ok(())
}

// ── helpers ───────────────────────────────────────────────────────────

fn config_path(app: &tauri::AppHandle) -> Result<PathBuf, tauri::Error> {
    let dir = app
        .path()
        .app_data_dir()
        .map_err(|e| tauri::Error::Anyhow(anyhow::anyhow!("无法获取 app data 目录: {e}")))?;
    Ok(dir.join(CONFIG_FILE))
}
