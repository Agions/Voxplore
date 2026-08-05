//! vynaro-core · 默认 19 个核心服务的注册与实现
//!
//! ## M2 已落地 (3 个)
//! - [`ProjectService`] : 项目管理 (open / save / list / delete)
//! - [`ConfigService`]  : 配置管理 (load / save / get / set)
//! - [`LoggingService`] : 日志门面 (info / warn / error + tracing 桥接)
//!
//! ## M3+ 待落地 (16 个)
//! LlmService / TtsService / FfmpegService / VideoService /
//! ExportService / PipelineService / PluginService /
//! UpdaterService / HelpService / I18nService /
//! ThemeService / DiagnosticsService / MetricsService /
//! NotificationService / TrayService / WindowStateService
//!
//! 详见 docs/refactor/v3-migration/03-rust-backend.md § Services

use std::path::PathBuf;
use std::sync::Arc;
use tokio::sync::Mutex;

use super::container::ServiceContainer;

#[derive(Debug, Default)]
pub struct ProjectService {
    recent: Mutex<Vec<PathBuf>>,
}

impl ProjectService {
    pub fn new() -> Self {
        Self::default()
    }

    /// 返回最近项目列表 (M2 占位,后续 M3 会从 ConfigService 读取 + 自动刷新)
    pub async fn recent_projects(&self) -> Vec<PathBuf> {
        self.recent.lock().await.clone()
    }

    pub async fn push_recent(&self, path: PathBuf) {
        let mut list = self.recent.lock().await;
        list.retain(|p| p != &path);
        list.insert(0, path);
        list.truncate(20); // 最多保存 20 条
    }
}

#[derive(Debug)]
pub struct ConfigService {
    inner: Mutex<Option<ConfigSnapshot>>,
}

impl Default for ConfigService {
    fn default() -> Self {
        Self {
            inner: Mutex::new(None),
        }
    }
}

impl ConfigService {
    pub fn new() -> Self {
        Self::default()
    }

    /// 当前配置快照 (M2 占位返回默认)
    pub async fn snapshot(&self) -> ConfigSnapshot {
        self.inner
            .lock()
            .await
            .clone()
            .unwrap_or_else(ConfigSnapshot::default)
    }

    pub async fn set_snapshot(&self, snapshot: ConfigSnapshot) {
        *self.inner.lock().await = Some(snapshot);
    }
}

#[derive(Debug, Default, Clone, serde::Serialize, serde::Deserialize)]
#[serde(default)]
pub struct ConfigSnapshot {
    pub theme: String,
    pub language: String,
    pub llm_provider: String,
    pub auto_update: bool,
    pub first_run: bool,
    // ── M3+ 扩展 (前端 Settings 页面需要) ──
    pub llm_api_key: Option<String>,
    pub llm_base_url: Option<String>,
    pub llm_model: Option<String>,
    pub tts_provider: Option<String>,
    pub tts_voice: Option<String>,
    /// GPT-SoVITS 本地参考音频路径
    pub tts_ref_audio_path: Option<String>,
    /// GPT-SoVITS 参考音频对应文本
    pub tts_prompt_text: Option<String>,
}

#[derive(Debug, Default)]
pub struct LoggingService;

impl LoggingService {
    pub fn new() -> Self {
        Self
    }

    pub fn info(&self, msg: &str) {
        tracing::info!("{}", msg);
    }

    pub fn warn(&self, msg: &str) {
        tracing::warn!("{}", msg);
    }

    pub fn error(&self, msg: &str) {
        tracing::error!("{}", msg);
    }
}

/// 默认注册函数:M2 注册 3 个 service,M3+ 逐个添加直至 19 个。
pub async fn register_default_services(container: &ServiceContainer) {
    container
        .register::<ProjectService>(Arc::new(ProjectService::new()))
        .await;
    container
        .register::<ConfigService>(Arc::new(ConfigService::new()))
        .await;
    container
        .register::<LoggingService>(Arc::new(LoggingService::new()))
        .await;

    tracing::info!(
        "vynaro-core: 3/{total} default services registered (M2 milestone)",
        total = 19
    );
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn project_service_recent_works() {
        let s = ProjectService::new();
        s.push_recent(PathBuf::from("/tmp/a.vynaro")).await;
        s.push_recent(PathBuf::from("/tmp/b.vynaro")).await;
        s.push_recent(PathBuf::from("/tmp/a.vynaro")).await; // 重复会移到首位
        let r = s.recent_projects().await;
        assert_eq!(r.len(), 2);
        assert_eq!(r[0], PathBuf::from("/tmp/a.vynaro"));
    }

    #[tokio::test]
    async fn config_service_snapshot_roundtrip() {
        let s = ConfigService::new();
        let snap = ConfigSnapshot {
            theme: "dark".into(),
            language: "zh-CN".into(),
            llm_provider: "openai".into(),
            auto_update: true,
            first_run: false,
            ..Default::default()
        };
        s.set_snapshot(snap.clone()).await;
        let read = s.snapshot().await;
        assert_eq!(read.theme, snap.theme);
    }
}
