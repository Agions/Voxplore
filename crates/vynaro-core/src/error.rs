//! vynaro-core · 统一错误类型
//!
//! 实现了 `serde::Serialize` 让 Tauri IPC 能直接传回前端 (前端拿到的是结构化 JSON)。

use serde::{Deserialize, Serialize};
use thiserror::Error;

/// 全应用统一 Result 别名。
pub type VynaroResult<T> = Result<T, VynaroError>;

/// 全应用统一错误。9 类变体覆盖所有业务失败路径。
///
/// ## 使用指南 (M3+ 起严格执行)
/// - `Io` / `Config` 由基础设施层返回
/// - `Project` / `Pipeline` / `Ffmpeg` 由业务编排层返回
/// - `Llm` / `Tts` 由外部服务层返回 (含 HTTP 状态码 + 重试标记)
/// - `Plugin` 由插件宿主返回 (WASM trap / capability 拒)
/// - `Updater` 由自动更新返回 (下载 / 校验)
/// - `Other` 仅作为兜底,新增业务错误前优先复用现有变体
#[derive(Debug, Error)]
pub enum VynaroError {
    /// IO 错误 (文件 / 网络 / 临时目录创建失败)
    #[error("IO error: {0}")]
    Io(#[from] std::io::Error),

    /// 配置 / 解析 / 校验失败
    #[error("config error: {0}")]
    Config(String),

    /// LLM 调用失败 (HTTP 非 2xx / JSON 解析 / Token 超限)
    #[error("llm error ({provider:?}): {message}")]
    Llm {
        provider: LlmProviderKind,
        message: String,
    },

    /// TTS 调用失败
    #[error("tts error ({provider:?}): {message}")]
    Tts {
        provider: TtsProviderKind,
        message: String,
    },

    /// FFmpeg 调用失败 (含 stderr tail)
    #[error("ffmpeg error: {0}")]
    Ffmpeg(String),

    /// 项目 / 媒体 / 脚本操作失败
    #[error("project error: {0}")]
    Project(String),

    /// 流水线编排失败 (7 步 / MonologueMaker)
    #[error("pipeline error: {0}")]
    Pipeline(String),

    /// 插件加载 / 执行失败 (WASM trap / capability)
    #[error("plugin error: {0}")]
    Plugin(String),

    /// 自动更新失败
    #[error("updater error: {0}")]
    Updater(String),

    /// 兜底 (新错误应优先复用现有变体)
    #[error("{0}")]
    Other(String),
}

/// LLM 提供商标识 (与 `vynaro-llm::LlmManager` 中定义的 11 个 provider 一一对应)。
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "kebab-case")]
pub enum LlmProviderKind {
    Qwen,
    Kimi,
    Glm5,
    Claude,
    Gemini,
    DeepSeek,
    Doubao,
    Hunyuan,
    Local,
    OpenAi,
    Qwen37,
}

/// TTS 引擎标识
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "kebab-case")]
pub enum TtsProviderKind {
    Edge,
    OpenAi,
    GptSovits,
}

// 把 VynaroError 序列化为 JSON 对象给 Tauri 前端
impl Serialize for VynaroError {
    fn serialize<S: serde::Serializer>(&self, s: S) -> Result<S::Ok, S::Error> {
        use serde::ser::SerializeStruct;
        let kind = match self {
            Self::Io(_) => "io",
            Self::Config(_) => "config",
            Self::Llm { .. } => "llm",
            Self::Tts { .. } => "tts",
            Self::Ffmpeg(_) => "ffmpeg",
            Self::Project(_) => "project",
            Self::Pipeline(_) => "pipeline",
            Self::Plugin(_) => "plugin",
            Self::Updater(_) => "updater",
            Self::Other(_) => "other",
        };
        let mut st = s.serialize_struct("VynaroError", 2)?;
        st.serialize_field("kind", kind)?;
        st.serialize_field("message", &self.to_string())?;
        st.end()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn serialization_shape() {
        let err = VynaroError::Config("missing api_key".into());
        let json = serde_json::to_value(&err).unwrap();
        assert_eq!(json["kind"], "config");
        assert!(json["message"]
            .as_str()
            .unwrap()
            .contains("missing api_key"));
    }

    #[test]
    fn llm_error_carries_provider() {
        let err = VynaroError::Llm {
            provider: LlmProviderKind::OpenAi,
            message: "401".into(),
        };
        let s = err.to_string();
        assert!(s.contains("OpenAi"));
        assert!(s.contains("401"));
    }
}
