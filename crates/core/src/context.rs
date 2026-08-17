//! splicr-core · AppContext
//!
//! 全应用单一状态对象,通过 `app.manage(AppContext::new())` 注入 Tauri State,
//! 每个 Tauri Command 用 `state: State<'_, AppContext>` 即可拿到。

use chrono::{DateTime, Utc};
use std::sync::Arc;

use super::container::ServiceContainer;

/// 全局应用上下文。包含服务容器 + 启动时间 + 版本号。
#[derive(Debug, Clone)]
pub struct AppContext {
    pub services: Arc<ServiceContainer>,
    pub started_at: DateTime<Utc>,
    pub version: semver::Version,
    pub debug: bool,
}

impl AppContext {
    /// 构造生产环境 AppContext。会自动初始化 tracing。
    pub async fn new() -> Self {
        super::init_logging();
        Self::builder().build().await
    }

    pub fn builder() -> AppContextBuilder {
        AppContextBuilder::default()
    }

    /// 获取已注册的 service。语法糖,减少 boilerplate。
    pub async fn service<T: std::any::Any + Send + Sync>(
        &self,
    ) -> Result<Arc<T>, super::SplicrError> {
        self.services.resolve::<T>().await
    }
}

/// Builder 模式注入环境特定配置 (test / debug / 自定义 version)
#[derive(Debug, Default)]
pub struct AppContextBuilder {
    version: Option<semver::Version>,
    debug: Option<bool>,
    skip_default_services: bool,
}

impl AppContextBuilder {
    pub fn version(mut self, v: semver::Version) -> Self {
        self.version = Some(v);
        self
    }

    pub fn debug(mut self, d: bool) -> Self {
        self.debug = Some(d);
        self
    }

    pub fn skip_default_services(mut self) -> Self {
        self.skip_default_services = true;
        self
    }

    /// 构造并注册默认 19 个 service。返回的 AppContext 已经包含所有 service。
    pub async fn build(self) -> AppContext {
        let version = self
            .version
            .unwrap_or_else(|| semver::Version::parse(env!("CARGO_PKG_VERSION")).unwrap());

        let ctx = AppContext {
            services: Arc::new(ServiceContainer::new()),
            started_at: Utc::now(),
            version,
            debug: self.debug.unwrap_or(cfg!(debug_assertions)),
        };

        if !self.skip_default_services {
            super::services::register_default_services(&ctx.services).await;
        }

        ctx
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::services::{ConfigService, LoggingService, ProjectService};

    #[tokio::test]
    async fn builder_registers_default_services() {
        let ctx = AppContext::builder().build().await;
        assert!(!ctx.services.is_empty().await);
        // 验证 3 个核心 service 在 default 注册
        assert!(ctx.service::<ProjectService>().await.is_ok());
        assert!(ctx.service::<ConfigService>().await.is_ok());
        assert!(ctx.service::<LoggingService>().await.is_ok());
    }

    #[tokio::test]
    async fn skip_default_services_works() {
        let ctx = AppContext::builder().skip_default_services().build().await;
        assert!(ctx.services.is_empty().await);
    }
}
