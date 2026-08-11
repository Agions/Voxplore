//! vynaro-llm v1.0.0  · LlmProvider trait + 11 provider 真实实现 + LlmManager 故障切换
//!
//! ## 11 个 Provider
//! - Qwen (Qwen3-Max / Qwen-Plus / Qwen-Turbo)        — OpenAI 兼容
//! - Kimi (Moonshot)                                   — OpenAI 兼容
//! - GLM5 (智谱)                                       — OpenAI 兼容
//! - Claude (Anthropic)                                — Anthropic 原生
//! - Gemini (Google)                                   — Google Gen AI 原生
//! - DeepSeek                                          — OpenAI 兼容
//! - Doubao (字节豆包)                                  — OpenAI 兼容
//! - Hunyuan (腾讯混元)                                 — OpenAI 兼容
//! - Local (Ollama 等本地)                              — OpenAI 兼容
//! - OpenAI (GPT-4o / GPT-4-Turbo)                     — OpenAI
//! - Qwen3.7 (实验版)                                  — OpenAI 兼容
//!
//! ## M3 范围
//! - 9 个 OpenAI 兼容 provider 共享 `OpenAiCompatible` 底座
//! - Claude 与 Gemini 各自实现原生协议
//! - 11 个 provider 全部可实际调用
//! - `LlmProviderFactory` 按 `LlmProviderKind` 工厂创建
//!
//! ## 历史
//! - M2: OpenAI 作为 PoC,其余 10 个 stub
//! - M3: 全部 11 个真实实现

use async_trait::async_trait;
use serde::{Deserialize, Serialize};

pub use vynaro_core::error::{LlmProviderKind, VynaroError, VynaroResult};

// ════════════════════════════════════════════════════════════════════════
// 输入 / 输出契约
// ════════════════════════════════════════════════════════════════════════

/// 单次 LLM 调用的输入。
#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct LlmRequest {
    pub system: String,
    pub user: String,
    pub model: Option<String>,    // 默认使用 provider 的 default model
    pub max_tokens: Option<u32>,  // 默认 4096
    pub temperature: Option<f32>, // 默认 0.7
    pub stream: bool,             // 是否流式
    /// 多模态视觉关键帧 (Base64 字符串列表, 供 GPT-5.6 / Gemini / Qwen3.8 等视觉模型分析)
    #[serde(default)]
    pub images_base64: Vec<String>,
}

/// LLM 响应 (一次性)。
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LlmResponse {
    pub content: String,
    pub model: String,
    pub tokens_used: u32,
    pub duration_ms: u64,
}

/// LlmProvider trait — 每个 11 个 provider 实现它。
#[async_trait]
pub trait LlmProvider: Send + Sync {
    fn kind(&self) -> LlmProviderKind;
    fn default_model(&self) -> &'static str;
    async fn chat(&self, req: &LlmRequest) -> VynaroResult<LlmResponse>;
}

// ════════════════════════════════════════════════════════════════════════
// 公共 builder: 9 个 OpenAI 兼容 provider 共享
// ════════════════════════════════════════════════════════════════════════

/// OpenAI 兼容协议 (8 个厂商 + OpenAI 自己也用)
#[derive(Debug, Clone)]
pub struct OpenAiCompatible {
    pub kind: LlmProviderKind,
    pub api_key: String,
    pub base_url: String,
    pub default_model: &'static str,
    pub client: reqwest::Client,
}

impl OpenAiCompatible {
    pub fn new(
        kind: LlmProviderKind,
        api_key: impl Into<String>,
        base_url: impl Into<String>,
        default_model: &'static str,
    ) -> Self {
        Self {
            kind,
            api_key: api_key.into(),
            base_url: base_url.into(),
            default_model,
            client: reqwest::Client::builder()
                .timeout(std::time::Duration::from_secs(60))
                .build()
                .expect("reqwest client build"),
        }
    }
}

#[async_trait]
impl LlmProvider for OpenAiCompatible {
    fn kind(&self) -> LlmProviderKind {
        self.kind
    }

    fn default_model(&self) -> &'static str {
        self.default_model
    }

    async fn chat(&self, req: &LlmRequest) -> VynaroResult<LlmResponse> {
        let start = std::time::Instant::now();

        let user_content = if req.images_base64.is_empty() {
            serde_json::json!(req.user)
        } else {
            let mut parts = vec![serde_json::json!({
                "type": "text",
                "text": req.user
            })];
            for b64 in &req.images_base64 {
                parts.push(serde_json::json!({
                    "type": "image_url",
                    "image_url": {
                        "url": format!("data:image/jpeg;base64,{}", b64)
                    }
                }));
            }
            serde_json::json!(parts)
        };

        let body = serde_json::json!({
            "model": req.model.clone().unwrap_or_else(|| self.default_model.to_string()),
            "messages": [
                { "role": "system", "content": req.system },
                { "role": "user",   "content": user_content },
            ],
            "max_tokens": req.max_tokens.unwrap_or(4096),
            "temperature": req.temperature.unwrap_or(0.7),
            "stream": false,
        });

        let resp = self
            .client
            .post(&self.base_url)
            .bearer_auth(&self.api_key)
            .json(&body)
            .send()
            .await
            .map_err(|e| VynaroError::Llm {
                provider: self.kind,
                message: format!("request send failed: {e}"),
            })?;

        let status = resp.status();
        if !status.is_success() {
            let body = resp.text().await.unwrap_or_default();
            return Err(VynaroError::Llm {
                provider: self.kind,
                message: format!("HTTP {status}: {body}"),
            });
        }

        #[derive(Deserialize)]
        struct Choice {
            message: ChoiceMessage,
        }
        #[derive(Deserialize)]
        struct ChoiceMessage {
            content: String,
        }
        #[derive(Deserialize)]
        struct Usage {
            total_tokens: u32,
        }
        #[derive(Deserialize)]
        struct ApiResp {
            model: String,
            choices: Vec<Choice>,
            usage: Usage,
        }

        let api: ApiResp = resp.json().await.map_err(|e| VynaroError::Llm {
            provider: self.kind,
            message: format!("response json parse failed: {e}"),
        })?;

        let content = api
            .choices
            .into_iter()
            .next()
            .map(|c| c.message.content)
            .unwrap_or_default();

        Ok(LlmResponse {
            content,
            model: api.model,
            tokens_used: api.usage.total_tokens,
            duration_ms: start.elapsed().as_millis() as u64,
        })
    }
}

// ════════════════════════════════════════════════════════════════════════
// Claude (Anthropic 原生协议)
// ════════════════════════════════════════════════════════════════════════

const CLAUDE_MESSAGES_URL: &str = "https://api.anthropic.com/v1/messages";

#[derive(Debug, Clone)]
pub struct ClaudeProvider {
    api_key: String,
    client: reqwest::Client,
}

impl ClaudeProvider {
    pub fn new(api_key: impl Into<String>) -> Self {
        Self {
            api_key: api_key.into(),
            client: reqwest::Client::builder()
                .timeout(std::time::Duration::from_secs(60))
                .build()
                .expect("reqwest client build"),
        }
    }
}

#[async_trait]
impl LlmProvider for ClaudeProvider {
    fn kind(&self) -> LlmProviderKind {
        LlmProviderKind::Claude
    }

    fn default_model(&self) -> &'static str {
        "claude-sonnet-5"
    }

    async fn chat(&self, req: &LlmRequest) -> VynaroResult<LlmResponse> {
        let start = std::time::Instant::now();

        let body = serde_json::json!({
            "model": req.model.clone().unwrap_or_else(|| self.default_model().to_string()),
            "system": req.system,
            "messages": [
                { "role": "user", "content": req.user },
            ],
            "max_tokens": req.max_tokens.unwrap_or(4096),
            "temperature": req.temperature.unwrap_or(0.7),
        });

        let resp = self
            .client
            .post(CLAUDE_MESSAGES_URL)
            .header("x-api-key", &self.api_key)
            .header("anthropic-version", "2023-06-01")
            .json(&body)
            .send()
            .await
            .map_err(|e| VynaroError::Llm {
                provider: LlmProviderKind::Claude,
                message: format!("request send failed: {e}"),
            })?;

        let status = resp.status();
        if !status.is_success() {
            let body = resp.text().await.unwrap_or_default();
            return Err(VynaroError::Llm {
                provider: LlmProviderKind::Claude,
                message: format!("HTTP {status}: {body}"),
            });
        }

        #[derive(Deserialize)]
        struct Content {
            #[serde(rename = "type")]
            kind: String,
            text: Option<String>,
        }
        #[derive(Deserialize)]
        struct ApiResp {
            model: String,
            content: Vec<Content>,
            usage: ClaudeUsage,
        }
        #[derive(Deserialize)]
        struct ClaudeUsage {
            input_tokens: u32,
            output_tokens: u32,
        }

        let api: ApiResp = resp.json().await.map_err(|e| VynaroError::Llm {
            provider: LlmProviderKind::Claude,
            message: format!("response json parse failed: {e}"),
        })?;

        let content = api
            .content
            .into_iter()
            .filter(|c| c.kind == "text")
            .filter_map(|c| c.text)
            .collect::<Vec<_>>()
            .join("");

        Ok(LlmResponse {
            content,
            model: api.model,
            tokens_used: api.usage.input_tokens + api.usage.output_tokens,
            duration_ms: start.elapsed().as_millis() as u64,
        })
    }
}

// ════════════════════════════════════════════════════════════════════════
// Gemini (Google Gen AI 原生协议)
// ════════════════════════════════════════════════════════════════════════

#[derive(Debug, Clone)]
pub struct GeminiProvider {
    api_key: String,
    client: reqwest::Client,
}

impl GeminiProvider {
    pub fn new(api_key: impl Into<String>) -> Self {
        Self {
            api_key: api_key.into(),
            client: reqwest::Client::builder()
                .timeout(std::time::Duration::from_secs(60))
                .build()
                .expect("reqwest client build"),
        }
    }
}

#[async_trait]
impl LlmProvider for GeminiProvider {
    fn kind(&self) -> LlmProviderKind {
        LlmProviderKind::Gemini
    }

    fn default_model(&self) -> &'static str {
        "gemini-3.6-flash"
    }

    async fn chat(&self, req: &LlmRequest) -> VynaroResult<LlmResponse> {
        let start = std::time::Instant::now();

        let model = req
            .model
            .clone()
            .unwrap_or_else(|| self.default_model().to_string());
        // 使用 streamGenerateContent=false 切到非流式
        let url = format!(
            "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}",
            model = model,
            key = self.api_key,
        );

        let body = serde_json::json!({
            "systemInstruction": {
                "parts": [{ "text": req.system }],
            },
            "contents": [
                {
                    "role": "user",
                    "parts": [{ "text": req.user }],
                },
            ],
            "generationConfig": {
                "maxOutputTokens": req.max_tokens.unwrap_or(4096),
                "temperature": req.temperature.unwrap_or(0.7),
            },
        });

        let resp = self
            .client
            .post(&url)
            .json(&body)
            .send()
            .await
            .map_err(|e| VynaroError::Llm {
                provider: LlmProviderKind::Gemini,
                message: format!("request send failed: {e}"),
            })?;

        let status = resp.status();
        if !status.is_success() {
            let body = resp.text().await.unwrap_or_default();
            return Err(VynaroError::Llm {
                provider: LlmProviderKind::Gemini,
                message: format!("HTTP {status}: {body}"),
            });
        }

        #[derive(Deserialize)]
        struct Part {
            text: Option<String>,
        }
        #[derive(Deserialize)]
        struct Content {
            parts: Vec<Part>,
        }
        #[derive(Deserialize)]
        struct Candidate {
            content: Content,
        }
        #[derive(Deserialize)]
        struct UsageMetadata {
            total_token_count: u32,
        }
        #[derive(Deserialize)]
        struct ApiResp {
            candidates: Vec<Candidate>,
            #[serde(rename = "modelVersion")]
            model_version: String,
            #[serde(rename = "usageMetadata")]
            usage_metadata: UsageMetadata,
        }

        let api: ApiResp = resp.json().await.map_err(|e| VynaroError::Llm {
            provider: LlmProviderKind::Gemini,
            message: format!("response json parse failed: {e}"),
        })?;

        let content = api
            .candidates
            .into_iter()
            .next()
            .map(|c| {
                c.content
                    .parts
                    .into_iter()
                    .filter_map(|p| p.text)
                    .collect::<Vec<_>>()
                    .join("")
            })
            .unwrap_or_default();

        Ok(LlmResponse {
            content,
            model: api.model_version,
            tokens_used: api.usage_metadata.total_token_count,
            duration_ms: start.elapsed().as_millis() as u64,
        })
    }
}

// ════════════════════════════════════════════════════════════════════════
// Provider 别名 (11 个工厂 constructor)
// ════════════════════════════════════════════════════════════════════════

/// OpenAI 公开别名 (M2 兼容)
pub type OpenAiProvider = OpenAiCompatible;

pub fn openai(api_key: impl Into<String>) -> OpenAiProvider {
    OpenAiCompatible::new(
        LlmProviderKind::OpenAi,
        api_key,
        "https://api.openai.com/v1/chat/completions",
        "gpt-5.6-sol",
    )
}

pub fn qwen(api_key: impl Into<String>) -> OpenAiCompatible {
    OpenAiCompatible::new(
        LlmProviderKind::Qwen,
        api_key,
        "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
        "qwen3.8-max",
    )
}

pub fn kimi(api_key: impl Into<String>) -> OpenAiCompatible {
    OpenAiCompatible::new(
        LlmProviderKind::Kimi,
        api_key,
        "https://api.moonshot.cn/v1/chat/completions",
        "kimi-k3",
    )
}

pub fn glm5(api_key: impl Into<String>) -> OpenAiCompatible {
    OpenAiCompatible::new(
        LlmProviderKind::Glm5,
        api_key,
        "https://open.bigmodel.cn/api/paas/v4/chat/completions",
        "glm-5.2",
    )
}

pub fn deepseek(api_key: impl Into<String>) -> OpenAiCompatible {
    OpenAiCompatible::new(
        LlmProviderKind::DeepSeek,
        api_key,
        "https://api.deepseek.com/v1/chat/completions",
        "deepseek-v4-pro",
    )
}

pub fn doubao(api_key: impl Into<String>) -> OpenAiCompatible {
    OpenAiCompatible::new(
        LlmProviderKind::Doubao,
        api_key,
        "https://ark.cn-beijing.volces.com/api/v3/chat/completions",
        "doubao-seed-2-1-pro-260628",
    )
}

pub fn hunyuan(api_key: impl Into<String>) -> OpenAiCompatible {
    OpenAiCompatible::new(
        LlmProviderKind::Hunyuan,
        api_key,
        "https://api.hunyuan.tencent.com/v1/chat/completions",
        "hunyuan-pro",
    )
}

// Hunyuan 与 Qwen3.7 端点为开发中默认值,M3.1 任务说明:
// - Hunyuan: 视腾讯侧正式 GA 端点调整
// - Qwen3.7: 实验版,默认端点为标准 DashScope
pub fn local(base_url: Option<String>) -> OpenAiCompatible {
    OpenAiCompatible::new(
        LlmProviderKind::Local,
        "no-key-required",
        base_url.unwrap_or_else(|| "http://localhost:11434/v1/chat/completions".into()),
        "llama3.2",
    )
}

pub fn qwen37(api_key: impl Into<String>) -> OpenAiCompatible {
    OpenAiCompatible::new(
        LlmProviderKind::Qwen37,
        api_key,
        "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
        "qwen3.7-max",
    )
}

pub fn claude(api_key: impl Into<String>) -> ClaudeProvider {
    ClaudeProvider::new(api_key)
}

pub fn gemini(api_key: impl Into<String>) -> GeminiProvider {
    GeminiProvider::new(api_key)
}

/// 工厂: 按 `LlmProviderKind` 构造(API key 必传)
pub fn factory(kind: LlmProviderKind, api_key: impl Into<String>) -> Box<dyn LlmProvider> {
    let key: String = api_key.into();
    match kind {
        LlmProviderKind::OpenAi => Box::new(openai(key)),
        LlmProviderKind::Qwen => Box::new(qwen(key)),
        LlmProviderKind::Kimi => Box::new(kimi(key)),
        LlmProviderKind::Glm5 => Box::new(glm5(key)),
        LlmProviderKind::DeepSeek => Box::new(deepseek(key)),
        LlmProviderKind::Doubao => Box::new(doubao(key)),
        LlmProviderKind::Hunyuan => Box::new(hunyuan(key)),
        LlmProviderKind::Local => Box::new(local(None)),
        LlmProviderKind::Qwen37 => Box::new(qwen37(key)),
        LlmProviderKind::Claude => Box::new(claude(key)),
        LlmProviderKind::Gemini => Box::new(gemini(key)),
    }
}

// ════════════════════════════════════════════════════════════════════════
// LlmManager — 故障切换链
// ════════════════════════════════════════════════════════════════════════

/// 多个 provider 链式调用,失败 fallback 至下一个。
///
/// 设计: 顺序尝试 `chain` 中的 provider,第一个成功的返回;全部失败返回最后一次错误。
pub struct LlmManager {
    chain: Vec<Box<dyn LlmProvider>>,
}

impl std::fmt::Debug for LlmManager {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        let names: Vec<_> = self.chain.iter().map(|p| p.kind()).collect();
        f.debug_struct("LlmManager").field("chain", &names).finish()
    }
}

impl LlmManager {
    pub fn new(chain: Vec<Box<dyn LlmProvider>>) -> Self {
        Self { chain }
    }

    /// 顺序尝试所有 provider,直到有成功响应。
    pub async fn chat(&self, req: &LlmRequest) -> VynaroResult<LlmResponse> {
        if self.chain.is_empty() {
            return Err(VynaroError::Llm {
                provider: LlmProviderKind::OpenAi, // 占位
                message: "no LLM provider configured".into(),
            });
        }

        let mut last_err: Option<VynaroError> = None;
        for provider in &self.chain {
            match provider.chat(req).await {
                Ok(resp) => {
                    tracing::info!(
                        provider = ?provider.kind(),
                        tokens = resp.tokens_used,
                        duration_ms = resp.duration_ms,
                        "llm request succeeded"
                    );
                    return Ok(resp);
                }
                Err(e) => {
                    tracing::warn!(
                        provider = ?provider.kind(),
                        error = %e,
                        "llm request failed, fallback to next provider"
                    );
                    last_err = Some(e);
                }
            }
        }

        Err(last_err.unwrap_or_else(|| {
            VynaroError::Other("LlmManager: chain empty after iteration".into())
        }))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn manager_chain_empty_returns_err() {
        let m = LlmManager::new(vec![]);
        let r = m
            .chat(&LlmRequest {
                system: "test".into(),
                user: "hi".into(),
                model: None,
                max_tokens: None,
                temperature: None,
                stream: false,
                images_base64: vec![],
            })
            .await;
        assert!(r.is_err());
    }

    #[test]
    fn all_eleven_providers_kind_correct() {
        let all: Vec<(&str, LlmProviderKind)> = vec![
            ("openai", LlmProviderKind::OpenAi),
            ("qwen", LlmProviderKind::Qwen),
            ("kimi", LlmProviderKind::Kimi),
            ("glm5", LlmProviderKind::Glm5),
            ("deepseek", LlmProviderKind::DeepSeek),
            ("doubao", LlmProviderKind::Doubao),
            ("hunyuan", LlmProviderKind::Hunyuan),
            ("local", LlmProviderKind::Local),
            ("qwen37", LlmProviderKind::Qwen37),
            ("claude", LlmProviderKind::Claude),
            ("gemini", LlmProviderKind::Gemini),
        ];

        for (name, kind) in all {
            let p = factory(kind, "test-key");
            assert_eq!(p.kind(), kind, "factory[{name}] kind mismatch");
        }
    }

    #[test]
    fn default_models_distinct() {
        let m = [
            (LlmProviderKind::OpenAi, openai("k").default_model()),
            (LlmProviderKind::Qwen, qwen("k").default_model()),
            (LlmProviderKind::Kimi, kimi("k").default_model()),
            (LlmProviderKind::Glm5, glm5("k").default_model()),
            (LlmProviderKind::DeepSeek, deepseek("k").default_model()),
            (LlmProviderKind::Doubao, doubao("k").default_model()),
            (LlmProviderKind::Hunyuan, hunyuan("k").default_model()),
            (LlmProviderKind::Local, local(None).default_model()),
            (LlmProviderKind::Qwen37, qwen37("k").default_model()),
            (LlmProviderKind::Claude, claude("k").default_model()),
            (LlmProviderKind::Gemini, gemini("k").default_model()),
        ];
        for (kind, model) in m {
            assert!(!model.is_empty(), "{kind:?} default model empty");
        }
    }

    #[tokio::test]
    async fn manager_chain_propagates_last_error() {
        // 1 个无法联通的 provider (无 URL) 应该得到 Err
        let bad = OpenAiCompatible::new(
            LlmProviderKind::OpenAi,
            "k",
            "http://127.0.0.1:1/v1/chat/completions", // 1 端口不可达
            "gpt-4o-mini",
        );
        let mgr = LlmManager::new(vec![Box::new(bad)]);
        let r = mgr
            .chat(&LlmRequest {
                system: "test".into(),
                user: "hi".into(),
                model: None,
                max_tokens: None,
                temperature: None,
                stream: false,
                images_base64: vec![],
            })
            .await;
        assert!(r.is_err());
    }
}
