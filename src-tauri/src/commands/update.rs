//! src-tauri 命令 · update
//!
//! - update_get_state: 查询当前状态(给前端轮询 fallback 用)
//! - update_check: 探测 GitHub Releases latest
//! - update_download: 下载到本地(带进度推送)
//! - update_install: M4 阶段触发 UI 提示用户手动重启(M5 接入 tauri-plugin-updater)
//! - update_reset: 重置状态(用户取消)
//!
//! 所有命令通过 `AppContext.services` 解析 `UpdateService` 单例。

use tauri::{AppHandle, Emitter, State};
use tauri_plugin_opener::OpenerExt;
use vynaro_core::AppContext;
use vynaro_update::{UpdateInfo, UpdateState};

/// 查询当前更新状态快照
#[tauri::command]
pub async fn update_get_state(state: State<'_, AppContext>) -> Result<UpdateState, String> {
    let svc = state
        .service::<vynaro_update::UpdateService>()
        .await
        .map_err(|e| e.to_string())?;
    Ok(svc.snapshot().await)
}

/// 探测 GitHub Releases latest。返回 UpdateInfo(同时写状态)
#[tauri::command]
pub async fn update_check(state: State<'_, AppContext>) -> Result<UpdateInfo, String> {
    let svc = state
        .service::<vynaro_update::UpdateService>()
        .await
        .map_err(|e| e.to_string())?;
    svc.check().await.map_err(|e| e.to_string())
}

/// 下载 latest binary 到本地。返回文件路径。
/// 进度通过 `updater:event` 事件实时推送。
#[tauri::command]
pub async fn update_download(
    app: AppHandle,
    state: State<'_, AppContext>,
) -> Result<String, String> {
    let svc = state
        .service::<vynaro_update::UpdateService>()
        .await
        .map_err(|e| e.to_string())?;
    let path = svc.download(None).await.map_err(|e| e.to_string())?;

    // 额外 emit 一个 phase=ready 事件(给 listen 兜底)
    let _ = app.emit("updater:event", "ready");

    Ok(path.to_string_lossy().into_owned())
}

/// M4 阶段:打开下载目录让用户手动替换 / 重启。
///
/// M5 接入 tauri-plugin-updater 后,这里改为自动调用 `tauri::updater`
/// 的 install_and_restart。当前阶段仅返回已下载路径与 toast 提示。
#[tauri::command]
pub async fn update_install(
    app: AppHandle,
    state: State<'_, AppContext>,
) -> Result<UpdateInstallResult, String> {
    let svc = state
        .service::<vynaro_update::UpdateService>()
        .await
        .map_err(|e| e.to_string())?;
    let snap = svc.snapshot().await;
    let path = snap
        .downloaded_path
        .ok_or_else(|| "尚未下载更新,请先调用 update_download".to_string())?;

    // 尝试用 opener 插件打开下载目录
    if let Some(dir) = std::path::Path::new(&path).parent() {
        let dir_str = dir.to_string_lossy().into_owned();
        let url = format!("file://{dir_str}");
        let _ = app.opener().open_url(url, None::<&str>);
    }

    Ok(UpdateInstallResult {
        downloaded_path: path,
        note:
            "M4 阶段:已打开下载目录,请手动替换应用并重启。M5 将接入 tauri-plugin-updater 自动安装。"
                .into(),
    })
}

#[derive(Debug, serde::Serialize)]
#[serde(rename_all = "camelCase")]
pub struct UpdateInstallResult {
    pub downloaded_path: String,
    pub note: String,
}

/// 重置状态(用户取消 / 完成后清场)
#[tauri::command]
pub async fn update_reset(state: State<'_, AppContext>) -> Result<(), String> {
    let svc = state
        .service::<vynaro_update::UpdateService>()
        .await
        .map_err(|e| e.to_string())?;
    svc.reset().await;
    Ok(())
}
