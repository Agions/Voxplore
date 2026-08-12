//! vynaro-update v1.0.0  · 应用更新器 (M4 完整实装)
//!
//! ## 责任范围
//! - GitHub Releases 探测最新版本
//! - sha256 校验下载包
//! - 5 阶段状态机:Idle → Checking → Available → Downloading → Ready
//! - 进度通过 `tokio::sync::broadcast` 推送
//!
//! ## 设计
//! - 与 `tauri-plugin-updater` 解耦:本 crate 自己用 reqwest 探测 + 下载
//! - tauri-plugin-updater 主要用于 capability 与正式发布签名(在 src-tauri 注册)
//! - 简化 M4 范围:不实装二进制替换(macOS/Windows 需重启应用)
//!   M4.1 可用 tauri-plugin-updater::Updater::check/check_update 实装自动替换
//!
//! ## 状态机
//!
//! ```text
//! Idle ──check()──► Checking ──成功──► Available ──download()──► Downloading ──完成──► Ready
//!                       │                                                       │
//!                       └──失败──► Idle (error)                                   └──失败──► Available (error)
//! ```
//!
use std::path::PathBuf;
use std::time::Duration;

use serde::{Deserialize, Serialize};
use thiserror::Error;
use tokio::sync::broadcast;

// ════════════════════════════════════════════════════════════════════════
// 错误类型
// ════════════════════════════════════════════════════════════════════════

#[derive(Debug, Error)]
pub enum UpdateError {
    #[error("GitHub API HTTP {0}")]
    Http(u16),
    #[error("GitHub API: {0}")]
    Api(String),
    #[error("下载失败: {0}")]
    Download(String),
    #[error("SHA-256 校验失败: expected={expected}, actual={actual}")]
    ChecksumMismatch { expected: String, actual: String },
    #[error("版本比较失败: {0}")]
    Version(String),
    #[error("IO: {0}")]
    Io(#[from] std::io::Error),
    #[error("JSON: {0}")]
    Json(#[from] serde_json::Error),
}

impl From<reqwest::Error> for UpdateError {
    fn from(e: reqwest::Error) -> Self {
        UpdateError::Api(format!("reqwest: {e}"))
    }
}

// ════════════════════════════════════════════════════════════════════════
// 公开类型
// ════════════════════════════════════════════════════════════════════════

/// 5 阶段更新状态机
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum UpdatePhase {
    Idle,
    Checking,
    Available,
    Downloading,
    Ready,
}

/// 探测结果(一次"check"动作的产物)
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct UpdateInfo {
    pub version: String,
    pub release_date: Option<String>,
    pub notes: Option<String>,
    pub download_url: Option<String>,
    pub sha256: Option<String>,
    pub file_size_bytes: Option<u64>,
}

/// 下载进度
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct UpdateProgress {
    pub downloaded_bytes: u64,
    pub total_bytes: u64,
    /// 0-100
    pub percent: u8,
}

/// 完整状态快照(给前端 GET)
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct UpdateState {
    pub phase: UpdatePhase,
    pub current_version: String,
    pub available: Option<UpdateInfo>,
    pub progress: Option<UpdateProgress>,
    pub error: Option<String>,
    pub downloaded_path: Option<String>,
}

/// 实时事件(payload 推送给前端 listen)
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(tag = "kind", rename_all = "snake_case")]
pub enum UpdateEvent {
    /// 状态阶段切换
    PhaseChanged { phase: UpdatePhase },
    /// 探测到新版本
    Available { info: UpdateInfo },
    /// 进度更新(高频)
    Progress { progress: UpdateProgress },
    /// 下载完成
    Downloaded { path: String, sha256: String },
    /// 发生错误(状态保留在错误前的 phase)
    Error { message: String },
}

// ════════════════════════════════════════════════════════════════════════
// UpdateService · 运行时
// ════════════════════════════════════════════════════════════════════════

/// 应用更新器服务
///
/// - 当前版本从构造参数传入(由 src-tauri/Cargo.toml 的 package.version 决定)
/// - 仓库 / tag 模板可配置(默认 `qingshanyanyu/Vynaro`)
/// - 进度通过 `broadcast::Sender<UpdateEvent>` 推送,前端 listen `updater:*`
pub struct UpdateService {
    current_version: String,
    repo: String,
    client: reqwest::Client,
    state: tokio::sync::Mutex<UpdateState>,
    event_tx: broadcast::Sender<UpdateEvent>,
}

impl std::fmt::Debug for UpdateService {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("UpdateService")
            .field("current_version", &self.current_version)
            .field("repo", &self.repo)
            .finish()
    }
}

impl UpdateService {
    /// 构造服务
    pub fn new(current_version: impl Into<String>, repo: impl Into<String>) -> Self {
        let (event_tx, _) = broadcast::channel(64);
        Self {
            current_version: current_version.into(),
            repo: repo.into(),
            client: reqwest::Client::builder()
                .timeout(Duration::from_secs(30))
                .user_agent("vynaro-updater/3.0")
                .build()
                .expect("reqwest client build"),
            state: tokio::sync::Mutex::new(UpdateState {
                phase: UpdatePhase::Idle,
                current_version: String::new(),
                available: None,
                progress: None,
                error: None,
                downloaded_path: None,
            }),
            event_tx,
        }
    }

    /// 暴露事件订阅端(给前端 listen 用)
    pub fn subscribe(&self) -> broadcast::Receiver<UpdateEvent> {
        self.event_tx.subscribe()
    }

    /// 读取当前状态快照(给 Tauri command `update_get_state` 用)
    pub async fn snapshot(&self) -> UpdateState {
        let mut s = self.state.lock().await.clone();
        // current_version 由构造期固定,状态切换时也确保一致
        if s.current_version.is_empty() {
            s.current_version = self.current_version.clone();
        }
        s
    }

    fn emit_phase(&self, phase: UpdatePhase) {
        let _ = self.event_tx.send(UpdateEvent::PhaseChanged { phase });
    }

    fn emit_error(&self, msg: String) {
        let _ = self.event_tx.send(UpdateEvent::Error { message: msg });
    }

    fn emit_available(&self, info: UpdateInfo) {
        let _ = self.event_tx.send(UpdateEvent::Available { info });
    }

    fn emit_progress(&self, progress: UpdateProgress) {
        let _ = self.event_tx.send(UpdateEvent::Progress { progress });
    }

    fn emit_downloaded(&self, path: String, sha256: String) {
        let _ = self.event_tx.send(UpdateEvent::Downloaded { path, sha256 });
    }

    /// 探测最新版本 (GitHub Releases latest)
    pub async fn check(&self) -> Result<UpdateInfo, UpdateError> {
        {
            let mut s = self.state.lock().await;
            s.phase = UpdatePhase::Checking;
            s.error = None;
        }
        self.emit_phase(UpdatePhase::Checking);

        let url = format!("https://api.github.com/repos/{}/releases/latest", self.repo);

        let resp = match self
            .client
            .get(&url)
            .header("Accept", "application/vnd.github+json")
            .send()
            .await
        {
            Ok(r) => r,
            Err(e) => {
                let msg = format!("reqwest: {e}");
                self.set_error(msg.clone()).await;
                self.emit_error(msg);
                return Err(UpdateError::Api(e.to_string()));
            }
        };

        let status = resp.status();
        if !status.is_success() {
            let msg = format!("HTTP {status}");
            self.set_error(msg.clone()).await;
            self.emit_error(msg.clone());
            return Err(UpdateError::Http(status.as_u16()));
        }

        #[derive(Deserialize)]
        struct Release {
            tag_name: String,
            published_at: Option<String>,
            body: Option<String>,
            assets: Vec<Asset>,
        }
        #[derive(Deserialize)]
        struct Asset {
            #[allow(dead_code)]
            name: String,
            browser_download_url: String,
            size: u64,
            digest: Option<String>,
        }

        let rel: Release = match resp.json().await {
            Ok(r) => r,
            Err(e) => {
                let msg = format!("json: {e}");
                self.set_error(msg.clone()).await;
                self.emit_error(msg);
                return Err(UpdateError::Api(e.to_string()));
            }
        };
        let version = rel.tag_name.trim_start_matches('v').to_string();
        let release_date = rel.published_at;
        let notes = rel.body;

        // 优先找带 sha256 digest 的二进制(.sig 配套留待 M4.1)
        let binary = rel.assets.iter().find(|a| {
            a.digest
                .as_deref()
                .map(|d| d.starts_with("sha256:"))
                .unwrap_or(false)
        });
        let download_url = binary.map(|a| a.browser_download_url.clone());
        let sha256 = binary
            .and_then(|a| a.digest.as_deref())
            .map(|d| d.trim_start_matches("sha256:").to_string());
        let file_size_bytes = binary.map(|a| a.size);

        let info = UpdateInfo {
            version: version.clone(),
            release_date,
            notes,
            download_url,
            sha256,
            file_size_bytes,
        };

        // 版本对比:远端 > 当前 → Available;否则仍记 Available(给前端展示)
        let cmp = compare_semver(&version, &self.current_version);
        if cmp <= 0 {
            // 已是最新(或本地更高),仍记为 Available 让前端 toast "已是最新"
            tracing::info!(
                current = %self.current_version,
                remote = %version,
                cmp,
                "no newer version available"
            );
        } else {
            tracing::info!(
                current = %self.current_version,
                remote = %version,
                "newer version detected"
            );
        }

        {
            let mut s = self.state.lock().await;
            s.phase = UpdatePhase::Available;
            s.available = Some(info.clone());
            s.error = None;
        }
        self.emit_available(info.clone());
        self.emit_phase(UpdatePhase::Available);

        Ok(info)
    }

    /// 下载 latest 到 `dest`(可显式传;否则落到 std::env::temp_dir()/vynaro-update-<version>)
    pub async fn download(&self, dest: Option<PathBuf>) -> Result<PathBuf, UpdateError> {
        let info = {
            let s = self.state.lock().await;
            s.available.clone()
        };
        let info = info.ok_or_else(|| UpdateError::Api("尚未探测,无 download_url".into()))?;
        let url = info
            .download_url
            .clone()
            .ok_or_else(|| UpdateError::Api("release 无 binary asset".into()))?;

        let dest = dest.unwrap_or_else(|| {
            std::env::temp_dir().join(format!("vynaro-update-{}.bin", info.version))
        });

        {
            let mut s = self.state.lock().await;
            s.phase = UpdatePhase::Downloading;
            s.progress = Some(UpdateProgress {
                downloaded_bytes: 0,
                total_bytes: info.file_size_bytes.unwrap_or(0),
                percent: 0,
            });
            s.error = None;
        }
        self.emit_phase(UpdatePhase::Downloading);

        let resp = self.client.get(&url).send().await?;
        let status = resp.status();
        if !status.is_success() {
            let msg = format!("HTTP {status}");
            self.set_error(msg.clone()).await;
            self.emit_error(msg);
            return Err(UpdateError::Http(status.as_u16()));
        }

        let total = resp
            .content_length()
            .unwrap_or(info.file_size_bytes.unwrap_or(0));

        // 流式写入 + 进度推送
        let mut stream = resp.bytes_stream();
        let mut file = tokio::fs::File::create(&dest).await?;
        let mut downloaded: u64 = 0;
        use futures::StreamExt;
        while let Some(chunk) = stream.next().await {
            let chunk = chunk.map_err(|e| UpdateError::Download(e.to_string()))?;
            tokio::io::AsyncWriteExt::write_all(&mut file, &chunk).await?;
            downloaded += chunk.len() as u64;
            let percent = if total > 0 {
                ((downloaded as f64 / total as f64) * 100.0).min(100.0) as u8
            } else {
                0
            };
            let progress = UpdateProgress {
                downloaded_bytes: downloaded,
                total_bytes: total,
                percent,
            };
            {
                let mut s = self.state.lock().await;
                s.progress = Some(progress.clone());
            }
            self.emit_progress(progress);
        }
        tokio::io::AsyncWriteExt::shutdown(&mut file).await.ok();

        // 校验 sha256(若 release 提供了)
        if let Some(expected) = info.sha256.as_deref() {
            let actual = sha256_file(&dest).await?;
            if !actual.eq_ignore_ascii_case(expected) {
                // 校验失败 → 删除文件 + 状态回退
                let _ = tokio::fs::remove_file(&dest).await;
                let msg = format!("SHA-256 mismatch: expected={expected}, actual={actual}");
                self.set_error(msg.clone()).await;
                self.emit_error(msg.clone());
                return Err(UpdateError::ChecksumMismatch {
                    expected: expected.to_string(),
                    actual,
                });
            }
            let dest_str = dest.to_string_lossy().into_owned();
            self.emit_downloaded(dest_str.clone(), actual.clone());
            {
                let mut s = self.state.lock().await;
                s.phase = UpdatePhase::Ready;
                s.progress = None;
                s.downloaded_path = Some(dest_str.clone());
            }
            self.emit_phase(UpdatePhase::Ready);
        } else {
            // 无 digest → 不校验,直接 Ready
            let dest_str = dest.to_string_lossy().into_owned();
            self.emit_downloaded(dest_str.clone(), String::new());
            {
                let mut s = self.state.lock().await;
                s.phase = UpdatePhase::Ready;
                s.progress = None;
                s.downloaded_path = Some(dest_str.clone());
            }
            self.emit_phase(UpdatePhase::Ready);
        }

        Ok(dest)
    }

    /// 重置状态(用户取消)
    pub async fn reset(&self) {
        let mut s = self.state.lock().await;
        s.phase = UpdatePhase::Idle;
        s.error = None;
        s.progress = None;
        s.downloaded_path = None;
        s.available = None;
        self.emit_phase(UpdatePhase::Idle);
    }

    async fn set_error(&self, msg: String) {
        let mut s = self.state.lock().await;
        s.error = Some(msg);
    }
}

// ════════════════════════════════════════════════════════════════════════
// helpers
// ════════════════════════════════════════════════════════════════════════

/// 简易 semver 比较
/// - 返回 1 (a > b),-1 (a < b),0 (a == b)
pub fn compare_semver(a: &str, b: &str) -> i32 {
    let pa: Vec<u32> = a
        .split('.')
        .map(|n| n.parse::<u32>().unwrap_or(0))
        .collect();
    let pb: Vec<u32> = b
        .split('.')
        .map(|n| n.parse::<u32>().unwrap_or(0))
        .collect();
    for i in 0..std::cmp::max(pa.len(), pb.len()) {
        let da = pa.get(i).copied().unwrap_or(0);
        let db = pb.get(i).copied().unwrap_or(0);
        if da > db {
            return 1;
        }
        if da < db {
            return -1;
        }
    }
    0
}

async fn sha256_file(path: &PathBuf) -> Result<String, UpdateError> {
    use sha2::{Digest, Sha256};
    use tokio::io::AsyncReadExt;
    let mut file = tokio::fs::File::open(path).await?;
    let mut hasher = Sha256::new();
    let mut buf = vec![0u8; 64 * 1024];
    loop {
        let n = file.read(&mut buf).await?;
        if n == 0 {
            break;
        }
        hasher.update(&buf[..n]);
    }
    Ok(hex::encode(hasher.finalize()))
}

// ════════════════════════════════════════════════════════════════════════
// tests
// ════════════════════════════════════════════════════════════════════════

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn semver_compare_basic() {
        assert_eq!(compare_semver("3.0.0", "3.0.0"), 0);
        assert_eq!(compare_semver("3.0.1", "3.0.0"), 1);
        assert_eq!(compare_semver("3.0.0", "3.0.1"), -1);
        assert_eq!(compare_semver("3.0.0", "3.0.0.0"), 0);
        assert_eq!(compare_semver("3.1.0", "3.0.9"), 1);
        assert_eq!(compare_semver("2.9.9", "3.0.0"), -1);
    }

    #[test]
    fn phase_state_default_is_idle() {
        let svc = UpdateService::new("1.0.0", "Agions/vynaro");
        let rt = tokio::runtime::Runtime::new().unwrap();
        let s = rt.block_on(svc.snapshot());
        assert_eq!(s.phase, UpdatePhase::Idle);
        assert!(s.available.is_none());
        assert!(s.error.is_none());
    }

    #[test]
    fn subscribe_returns_receiver() {
        let svc = UpdateService::new("1.0.0", "Agions/vynaro");
        let _rx = svc.subscribe();
        // 至少能拿到一个 sender,且不会因为 receiver drop 而 panic
    }

    #[test]
    fn reset_returns_to_idle() {
        let svc = UpdateService::new("1.0.0", "Agions/vynaro");
        let rt = tokio::runtime::Runtime::new().unwrap();
        rt.block_on(svc.reset());
        let s = rt.block_on(svc.snapshot());
        assert_eq!(s.phase, UpdatePhase::Idle);
        assert!(s.error.is_none());
    }

    #[tokio::test]
    async fn check_handles_http_error_gracefully() {
        // 用一个不存在的 repo 触发 HTTP 404
        let svc = UpdateService::new("1.0.0", "Agions/this-repo-does-not-exist-zzz");
        let res = svc.check().await;
        assert!(res.is_err());
        let s = svc.snapshot().await;
        // 错误后 phase 保持 Available(因为 check 内部已经把 phase 切过去再返回 err)
        // 但 error 字段应被设置
        assert!(s.error.is_some());
    }
}
