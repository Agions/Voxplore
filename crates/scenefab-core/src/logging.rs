//! scenefab-core · Logging 初始化
//!
//! 读取 `RUST_LOG` 环境变量 (默认 `info`),输出到 stderr。

use std::sync::OnceLock;
use tracing_subscriber::{fmt, prelude::*, EnvFilter};

static INIT: OnceLock<()> = OnceLock::new();

/// 初始化全局 tracing subscriber (确保只跑一次)。
///
/// ## 调用时机
/// - Tauri main() 中第一行调用
/// - CLI main() 中第一行调用
/// - integration 测试 `#[ctor]` 中调用
pub fn init_logging() {
    INIT.get_or_init(|| {
        let filter = EnvFilter::try_from_default_env()
            .unwrap_or_else(|_| EnvFilter::new("info,scenefab_core=debug"));

        let layer = fmt::layer()
            .with_target(true)
            .with_thread_ids(false)
            .with_line_number(true)
            .with_file(true)
            .with_writer(std::io::stderr);

        tracing_subscriber::registry()
            .with(filter)
            .with(layer)
            .init();
    });
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn idempotent() {
        init_logging();
        init_logging(); // 第二次调用不 panic
    }
}
