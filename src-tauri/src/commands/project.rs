//! src-tauri 命令 · project 完整 CRUD (M3.2)
//!
//! Tauri command 层:将 [`ProjectService`] 暴露为前端可调用的 IPC 指令。

use std::path::{Path, PathBuf};

use tauri::{Manager, State};
use vynaro_core::domain::Project;
use vynaro_core::services::ProjectService;
use vynaro_core::AppContext;
use vynaro_domain::MediaFile;

/// 列举最近项目 (M3.2 真实从 ProjectService 取)
#[tauri::command]
pub async fn project_list_recent(state: State<'_, AppContext>) -> Result<Vec<String>, String> {
    let svc = state
        .service::<ProjectService>()
        .await
        .map_err(|e| e.to_string())?;
    let paths = svc.recent_projects().await;
    Ok(paths
        .into_iter()
        .map(|p| p.to_string_lossy().into_owned())
        .collect())
}

/// 创建空白 Project 并保存到默认 projects 目录。
/// 返回 (path, project) 元组:前端用 path 记住文件位置。
#[tauri::command]
pub async fn project_create_blank(
    app: tauri::AppHandle,
    state: State<'_, AppContext>,
) -> Result<ProjectRecord, String> {
    let proj = Project::default();
    let dir = project_dir(&app).map_err(|e| e.to_string())?;
    tokio::fs::create_dir_all(&dir)
        .await
        .map_err(|e| e.to_string())?;
    let path = dir.join(format!("{}.vynaro.json", proj.id));
    write_project(&path, &proj)
        .await
        .map_err(|e| e.to_string())?;

    let svc = state
        .service::<ProjectService>()
        .await
        .map_err(|e| e.to_string())?;
    svc.push_recent(path.clone()).await;

    Ok(ProjectRecord {
        path: path.to_string_lossy().into_owned(),
        project: proj,
    })
}

/// 从指定路径加载 Project (.vynaro.json)
#[tauri::command]
pub async fn project_load(
    path: String,
    state: State<'_, AppContext>,
) -> Result<ProjectRecord, String> {
    let p = PathBuf::from(&path);
    let bytes = tokio::fs::read(&p).await.map_err(|e| e.to_string())?;
    let proj: Project = serde_json::from_slice(&bytes).map_err(|e| format!("解析失败: {e}"))?;

    let svc = state
        .service::<ProjectService>()
        .await
        .map_err(|e| e.to_string())?;
    svc.push_recent(p.clone()).await;

    Ok(ProjectRecord {
        path,
        project: proj,
    })
}

/// 把 Project 落盘到指定路径
#[tauri::command]
pub async fn project_save(path: String, project: Project) -> Result<(), String> {
    let p = PathBuf::from(&path);
    write_project(&p, &project).await.map_err(|e| e.to_string())
}

/// 删除指定路径的 Project 文件，并同步从最近工程列表中注销
#[tauri::command]
pub async fn project_delete(
    state: State<'_, AppContext>,
    path: String,
) -> Result<(), String> {
    let p = PathBuf::from(&path);
    if p.exists() {
        let _ = tokio::fs::remove_file(&p).await;
    }
    if let Ok(svc) = state.service::<ProjectService>().await {
        svc.remove_recent(&p).await;
    }
    Ok(())
}

/// 给现有 Project 追加一个素材 (前端素材页拖拽后调用)
#[tauri::command]
pub async fn project_add_media(
    path: String,
    project: Project,
    media: MediaFile,
) -> Result<Project, String> {
    let p = PathBuf::from(&path);
    let mut proj = project;
    proj.media_files.push(media);
    proj.updated_at = chrono::Utc::now();
    write_project(&p, &proj).await.map_err(|e| e.to_string())?;
    Ok(proj)
}

// ── IPC 类型 ──────────────────────────────────────────────────────────

#[derive(Debug, serde::Serialize)]
#[serde(rename_all = "camelCase")]
pub struct ProjectRecord {
    pub path: String,
    pub project: Project,
}

// ── helpers ───────────────────────────────────────────────────────────

pub fn project_dir(app: &tauri::AppHandle) -> Result<PathBuf, tauri::Error> {
    let dir = app
        .path()
        .app_data_dir()
        .map_err(|e| tauri::Error::Anyhow(anyhow::anyhow!("无法获取 app data 目录: {e}")))?;
    Ok(dir.join("projects"))
}

async fn write_project(path: &Path, proj: &Project) -> Result<(), std::io::Error> {
    if let Some(parent) = path.parent() {
        tokio::fs::create_dir_all(parent).await?;
    }
    let bytes = serde_json::to_vec_pretty(proj)
        .map_err(|e| std::io::Error::new(std::io::ErrorKind::InvalidData, e))?;
    tokio::fs::write(path, bytes).await
}
