//! splicr-voice v1.0.0  · TTS 配音与语音克隆引擎
//!
//! ## 责任范围
//! 3 个 TTS 引擎的统一抽象与实现:
//! - [`OpenAiTtsEngine`]  : OpenAI 兼容 `/v1/audio/speech` (OpenAI / Azure 兼容端点 / 本地代理)
//! - [`EdgeTtsEngine`]    : Microsoft Edge TTS (WebSocket 协议,免费无需密钥)
//! - [`GptSovitsTtsEngine`]: GPT-SoVITS 本地推理 API (默认 127.0.0.1:9880)
//!
//! ## 设计
//! - [`TtsEngine`] trait 是唯一出口,业务层只依赖 trait
//! - 所有失败统一为 `SplicrError::Tts { provider, message }`
//! - 合成产物直接落盘 (`output_path`),返回写入字节数

#![allow(dead_code)]

use std::path::{Path, PathBuf};

use async_trait::async_trait;
use futures::{SinkExt, StreamExt};
use tokio_tungstenite::tungstenite::Message;
use splicr_core::error::{SplicrError, SplicrResult};

// 同时保留两个常用名称,方便业务侧 import 习惯
pub use splicr_core::error::TtsProviderKind;
pub use splicr_core::error::TtsProviderKind as ProviderKind;

// ════════════════════════════════════════════════════════════════════════
// 请求 / 结果 / trait
// ════════════════════════════════════════════════════════════════════════

/// 一次合成请求。
#[derive(Debug, Clone)]
pub struct TtsRequest {
    /// 待合成文本 (中文叙述段)
    pub text: String,
    /// 音色覆盖 (None = 引擎默认)
    pub voice: Option<String>,
    /// 语速百分比偏移 (-50..=+50,0 = 常速)
    pub rate_percent: i32,
    /// 音频产物落盘路径 (mp3 / wav 由引擎决定)
    pub output_path: PathBuf,
}

/// 合成结果。
#[derive(Debug, Clone)]
pub struct TtsOutcome {
    pub bytes_written: u64,
    pub format: &'static str, // "mp3" / "wav"
}

/// TTS 引擎统一抽象。
#[async_trait]
pub trait TtsEngine: Send + Sync {
    fn kind(&self) -> TtsProviderKind;

    /// 合成并落盘。失败返回 `SplicrError::Tts`。
    async fn synthesize(&self, req: &TtsRequest) -> SplicrResult<TtsOutcome>;
}

fn tts_err(provider: TtsProviderKind, message: impl Into<String>) -> SplicrError {
    SplicrError::Tts {
        provider,
        message: message.into(),
    }
}

/// 落盘 helper: 自动建父目录。
async fn write_output(path: &Path, bytes: &[u8]) -> SplicrResult<u64> {
    if let Some(parent) = path.parent() {
        tokio::fs::create_dir_all(parent).await?;
    }
    tokio::fs::write(path, bytes).await?;
    Ok(bytes.len() as u64)
}

// ════════════════════════════════════════════════════════════════════════
// 引擎 1 · OpenAI 兼容 /v1/audio/speech
// ════════════════════════════════════════════════════════════════════════

#[derive(Debug, Clone)]
pub struct OpenAiTtsOptions {
    pub api_key: String,
    pub base_url: String, // 默认 https://api.openai.com
    pub model: String,    // 默认 tts-1
    pub voice: String,    // 默认 alloy
}

impl Default for OpenAiTtsOptions {
    fn default() -> Self {
        Self {
            api_key: String::new(),
            base_url: "https://api.openai.com".into(),
            model: "tts-1".into(),
            voice: "alloy".into(),
        }
    }
}

#[derive(Debug)]
pub struct OpenAiTtsEngine {
    opts: OpenAiTtsOptions,
    client: reqwest::Client,
}

impl OpenAiTtsEngine {
    pub fn new(opts: OpenAiTtsOptions) -> Self {
        Self {
            opts,
            client: reqwest::Client::new(),
        }
    }
}

#[async_trait]
impl TtsEngine for OpenAiTtsEngine {
    fn kind(&self) -> TtsProviderKind {
        TtsProviderKind::OpenAi
    }

    async fn synthesize(&self, req: &TtsRequest) -> SplicrResult<TtsOutcome> {
        let url = format!(
            "{}/v1/audio/speech",
            self.opts.base_url.trim_end_matches('/')
        );
        let speed = (100 + req.rate_percent).clamp(50, 150) as f64 / 100.0;
        let body = serde_json::json!({
            "model": self.opts.model,
            "input": req.text,
            "voice": req.voice.clone().unwrap_or_else(|| self.opts.voice.clone()),
            "response_format": "mp3",
            "speed": speed,
        });
        let resp = self
            .client
            .post(&url)
            .bearer_auth(&self.opts.api_key)
            .json(&body)
            .send()
            .await
            .map_err(|e| tts_err(TtsProviderKind::OpenAi, format!("request failed: {e}")))?;

        if !resp.status().is_success() {
            let status = resp.status();
            let text = resp.text().await.unwrap_or_default();
            return Err(tts_err(
                TtsProviderKind::OpenAi,
                format!("HTTP {status}: {}", truncate(&text, 300)),
            ));
        }
        let bytes = resp
            .bytes()
            .await
            .map_err(|e| tts_err(TtsProviderKind::OpenAi, format!("read body: {e}")))?;
        let n = write_output(&req.output_path, &bytes).await?;
        Ok(TtsOutcome {
            bytes_written: n,
            format: "mp3",
        })
    }
}

// ════════════════════════════════════════════════════════════════════════
// 引擎 2 · Microsoft Edge TTS (WebSocket,免费)
// ════════════════════════════════════════════════════════════════════════

/// Edge TTS 公开客户端令牌 (与 edge-tts Python 包同源,微软公开协议)。
const EDGE_TOKEN: &str = "6A5AA1D4EAFF4E9FB37E23D68491D6F4";
const EDGE_URL: &str =
    "wss://speech.platform.bing.com/consumer/speech/synthesize/readaloud/edge/v1";

#[derive(Debug, Clone)]
pub struct EdgeTtsOptions {
    /// 默认中文女声
    pub voice: String,
}

impl Default for EdgeTtsOptions {
    fn default() -> Self {
        Self {
            voice: "zh-CN-XiaoxiaoNeural".into(),
        }
    }
}

#[derive(Debug)]
pub struct EdgeTtsEngine {
    opts: EdgeTtsOptions,
}

impl EdgeTtsEngine {
    pub fn new(opts: EdgeTtsOptions) -> Self {
        Self { opts }
    }

    /// 构造 SSML (XML 转义 + 语速)
    fn build_ssml(&self, req: &TtsRequest) -> String {
        let voice = req.voice.clone().unwrap_or_else(|| self.opts.voice.clone());
        let rp = req.rate_percent.clamp(-50, 50);
        let rate = format!("{}{}%", if rp >= 0 { "+" } else { "" }, rp);
        format!(
            "<speak version='1.0' xmlns='http://www.w3.org/2001/10/synthesis' xml:lang='zh-CN'>\
             <voice name='{voice}'>\
             <prosody pitch='+0Hz' rate='{rate}' volume='+0%'>{text}</prosody>\
             </voice></speak>",
            text = escape_xml(&req.text),
        )
    }
}

/// XML 属性/文本转义
pub fn escape_xml(s: &str) -> String {
    s.replace('&', "&amp;")
        .replace('<', "&lt;")
        .replace('>', "&gt;")
        .replace('\'', "&apos;")
        .replace('"', "&quot;")
}

fn now_http_date() -> String {
    chrono::Utc::now()
        .format("%a, %d %b %Y %H:%M:%S GMT")
        .to_string()
}

fn random_connection_id() -> String {
    use std::time::{SystemTime, UNIX_EPOCH};
    let n = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_nanos())
        .unwrap_or(0);
    format!("{:032x}", n)
}

#[async_trait]
impl TtsEngine for EdgeTtsEngine {
    fn kind(&self) -> TtsProviderKind {
        TtsProviderKind::Edge
    }

    async fn synthesize(&self, req: &TtsRequest) -> SplicrResult<TtsOutcome> {
        let conn_id = random_connection_id();
        let url = format!("{EDGE_URL}?TrustedClientToken={EDGE_TOKEN}&ConnectionId={conn_id}");

        let (ws, _resp) = tokio_tungstenite::connect_async(&url)
            .await
            .map_err(|e| tts_err(TtsProviderKind::Edge, format!("websocket connect: {e}")))?;
        let (mut tx, mut rx) = ws.split();

        // ① speech.config 消息
        let config_msg = format!(
            "X-Timestamp:{ts}\r\nContent-Type:application/json; charset=utf-8\r\nPath:speech.config\r\n\r\n\
             {{\"context\":{{\"synthesis\":{{\"audio\":{{\"metadataoptions\":\
             {{\"sentenceBoundaryEnabled\":\"false\",\"wordBoundaryEnabled\":\"true\"}},\
             \"outputFormat\":\"audio-24khz-48kbitrate-mono-mp3\"}}}}}}}}\r\n",
            ts = now_http_date(),
        );
        tx.send(Message::Text(config_msg))
            .await
            .map_err(|e| tts_err(TtsProviderKind::Edge, format!("send config: {e}")))?;

        // ② SSML 消息
        let ssml_msg = format!(
            "X-RequestId:{conn_id}\r\nContent-Type:application/ssml+xml\r\nX-Timestamp:{ts}\r\nPath:ssml\r\n\r\n{ssml}",
            ts = now_http_date(),
            ssml = self.build_ssml(req),
        );
        tx.send(Message::Text(ssml_msg))
            .await
            .map_err(|e| tts_err(TtsProviderKind::Edge, format!("send ssml: {e}")))?;

        // ③ 收音频块直到 turn.end
        let mut audio: Vec<u8> = Vec::new();
        loop {
            let msg = rx
                .next()
                .await
                .ok_or_else(|| tts_err(TtsProviderKind::Edge, "stream closed before turn.end"))?
                .map_err(|e| tts_err(TtsProviderKind::Edge, format!("websocket: {e}")))?;

            match msg {
                Message::Text(t) if t.contains("Path:turn.end") => break,
                Message::Binary(b) => {
                    // 二进制帧 = 2 字节 header 长度 (BE) + JSON header + 音频数据
                    if b.len() < 2 {
                        continue;
                    }
                    let header_len = u16::from_be_bytes([b[0], b[1]]) as usize;
                    let audio_start = 2 + header_len;
                    if audio_start < b.len() {
                        audio.extend_from_slice(&b[audio_start..]);
                    }
                }
                Message::Close(_) => {
                    return Err(tts_err(
                        TtsProviderKind::Edge,
                        "server closed before synthesis finished",
                    ))
                }
                _ => {}
            }
        }

        if audio.is_empty() {
            return Err(tts_err(TtsProviderKind::Edge, "empty audio payload"));
        }
        let n = write_output(&req.output_path, &audio).await?;
        Ok(TtsOutcome {
            bytes_written: n,
            format: "mp3",
        })
    }
}

// ════════════════════════════════════════════════════════════════════════
// 引擎 3 · GPT-SoVITS 本地推理 API
// ════════════════════════════════════════════════════════════════════════

#[derive(Debug, Clone)]
pub struct GptSovitsOptions {
    pub base_url: String,       // 默认 http://127.0.0.1:9880
    pub ref_audio_path: String, // 参考音频路径 (克隆音色)
    pub prompt_text: String,    // 参考音频对应文本
    pub prompt_lang: String,    // 默认 zh
}

impl Default for GptSovitsOptions {
    fn default() -> Self {
        Self {
            base_url: "http://127.0.0.1:9880".into(),
            ref_audio_path: String::new(),
            prompt_text: String::new(),
            prompt_lang: "zh".into(),
        }
    }
}

#[derive(Debug)]
pub struct GptSovitsTtsEngine {
    opts: GptSovitsOptions,
    client: reqwest::Client,
}

impl GptSovitsTtsEngine {
    pub fn new(opts: GptSovitsOptions) -> Self {
        Self {
            opts,
            client: reqwest::Client::new(),
        }
    }
}

#[async_trait]
impl TtsEngine for GptSovitsTtsEngine {
    fn kind(&self) -> TtsProviderKind {
        TtsProviderKind::GptSovits
    }

    async fn synthesize(&self, req: &TtsRequest) -> SplicrResult<TtsOutcome> {
        if self.opts.ref_audio_path.is_empty() {
            return Err(tts_err(
                TtsProviderKind::GptSovits,
                "ref_audio_path 未配置 (GPT-SoVITS 需要参考音频克隆音色)",
            ));
        }
        let url = format!("{}/tts", self.opts.base_url.trim_end_matches('/'));
        let body = serde_json::json!({
            "text": req.text,
            "text_lang": "zh",
            "ref_audio_path": self.opts.ref_audio_path,
            "prompt_text": self.opts.prompt_text,
            "prompt_lang": self.opts.prompt_lang,
            "speed_factor": (100 + req.rate_percent).clamp(50, 150) as f64 / 100.0,
        });
        let resp = self
            .client
            .post(&url)
            .json(&body)
            .send()
            .await
            .map_err(|e| {
                tts_err(
                    TtsProviderKind::GptSovits,
                    format!("无法连接 GPT-SoVITS API ({}): {e}", self.opts.base_url),
                )
            })?;

        if !resp.status().is_success() {
            let status = resp.status();
            let text = resp.text().await.unwrap_or_default();
            return Err(tts_err(
                TtsProviderKind::GptSovits,
                format!("HTTP {status}: {}", truncate(&text, 300)),
            ));
        }
        let bytes = resp
            .bytes()
            .await
            .map_err(|e| tts_err(TtsProviderKind::GptSovits, format!("read body: {e}")))?;
        let n = write_output(&req.output_path, &bytes).await?;
        Ok(TtsOutcome {
            bytes_written: n,
            format: "wav",
        })
    }
}

// ════════════════════════════════════════════════════════════════════════
// 引擎 4 · MiniMax / MiMo TTS 引擎
// ════════════════════════════════════════════════════════════════════════

fn decode_hex(s: &str) -> Option<Vec<u8>> {
    if s.len() % 2 != 0 {
        return None;
    }
    (0..s.len())
        .step_by(2)
        .map(|i| u8::from_str_radix(&s[i..i + 2], 16).ok())
        .collect()
}

#[derive(Debug, Clone)]
pub struct MimoTtsOptions {
    pub api_key: String,
    pub base_url: String, // 默认 https://api.xiaomimimo.com/v1
    pub model: String,    // 默认 mimo-v2.5-tts
    pub voice: String,    // 默认 default
}

impl Default for MimoTtsOptions {
    fn default() -> Self {
        Self {
            api_key: String::new(),
            base_url: "https://api.xiaomimimo.com/v1".into(),
            model: "mimo-v2.5-tts".into(),
            voice: "default".into(),
        }
    }
}

#[derive(Debug)]
pub struct MimoTtsEngine {
    opts: MimoTtsOptions,
    client: reqwest::Client,
}

impl MimoTtsEngine {
    pub fn new(opts: MimoTtsOptions) -> Self {
        Self {
            opts,
            client: reqwest::Client::new(),
        }
    }
}

#[async_trait]
impl TtsEngine for MimoTtsEngine {
    fn kind(&self) -> TtsProviderKind {
        TtsProviderKind::Mimo
    }

    async fn synthesize(&self, req: &TtsRequest) -> SplicrResult<TtsOutcome> {
        let base_url = self.opts.base_url.trim_end_matches('/');
        let url = if base_url.contains("/audio/speech") || base_url.contains("/t2a") {
            base_url.to_string()
        } else {
            format!("{}/audio/speech", base_url)
        };
        let speed = (100 + req.rate_percent).clamp(50, 150) as f64 / 100.0;
        let voice = req.voice.clone().unwrap_or_else(|| self.opts.voice.clone());

        let body = serde_json::json!({
            "model": self.opts.model,
            "input": req.text,
            "voice": voice,
            "response_format": "mp3",
            "speed": speed,
        });

        let mut req_builder = self.client.post(&url);
        if !self.opts.api_key.is_empty() {
            req_builder = req_builder.bearer_auth(&self.opts.api_key);
        }

        let resp = req_builder
            .json(&body)
            .send()
            .await
            .map_err(|e| tts_err(TtsProviderKind::Mimo, format!("request failed: {e}")))?;

        if !resp.status().is_success() {
            let status = resp.status();
            let text = resp.text().await.unwrap_or_default();
            return Err(tts_err(
                TtsProviderKind::Mimo,
                format!("HTTP {status}: {}", truncate(&text, 300)),
            ));
        }

        let bytes = resp
            .bytes()
            .await
            .map_err(|e| tts_err(TtsProviderKind::Mimo, format!("read body: {e}")))?;

        if let Ok(val) = serde_json::from_slice::<serde_json::Value>(&bytes) {
            if let Some(audio_hex) = val.get("audio_file").and_then(|v| v.as_str()) {
                if let Some(raw_audio) = decode_hex(audio_hex) {
                    let n = write_output(&req.output_path, &raw_audio).await?;
                    return Ok(TtsOutcome {
                        bytes_written: n,
                        format: "mp3",
                    });
                }
            }
            if let Some(data) = val
                .get("data")
                .and_then(|v| v.get("audio"))
                .and_then(|v| v.as_str())
            {
                if let Some(raw_audio) = decode_hex(data) {
                    let n = write_output(&req.output_path, &raw_audio).await?;
                    return Ok(TtsOutcome {
                        bytes_written: n,
                        format: "mp3",
                    });
                }
            }
        }

        let n = write_output(&req.output_path, &bytes).await?;
        Ok(TtsOutcome {
            bytes_written: n,
            format: "mp3",
        })
    }
}

// ════════════════════════════════════════════════════════════════════════
// 工厂
// ════════════════════════════════════════════════════════════════════════

/// 按引擎类型构造 (与 ConfigService 的 tts_provider 字段对接)。
#[derive(Debug)]
pub enum TtsEngineConfig {
    Edge(EdgeTtsOptions),
    OpenAi(OpenAiTtsOptions),
    GptSovits(GptSovitsOptions),
    Mimo(MimoTtsOptions),
}

pub fn engine(config: TtsEngineConfig) -> Box<dyn TtsEngine> {
    match config {
        TtsEngineConfig::Edge(o) => Box::new(EdgeTtsEngine::new(o)),
        TtsEngineConfig::OpenAi(o) => Box::new(OpenAiTtsEngine::new(o)),
        TtsEngineConfig::GptSovits(o) => Box::new(GptSovitsTtsEngine::new(o)),
        TtsEngineConfig::Mimo(o) => Box::new(MimoTtsEngine::new(o)),
    }
}

/// 便捷构造: 免费 Edge 引擎 (无密钥场景默认)
pub fn edge_engine() -> Box<dyn TtsEngine> {
    engine(TtsEngineConfig::Edge(EdgeTtsOptions::default()))
}

fn truncate(s: &str, n: usize) -> String {
    if s.chars().count() <= n {
        s.to_string()
    } else {
        s.chars().take(n).collect::<String>() + "…"
    }
}

// ════════════════════════════════════════════════════════════════════════
// 测试
// ════════════════════════════════════════════════════════════════════════

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn factory_kinds_correct() {
        let e = engine(TtsEngineConfig::Edge(EdgeTtsOptions::default()));
        assert_eq!(e.kind(), TtsProviderKind::Edge);
        let o = engine(TtsEngineConfig::OpenAi(OpenAiTtsOptions::default()));
        assert_eq!(o.kind(), TtsProviderKind::OpenAi);
        let g = engine(TtsEngineConfig::GptSovits(GptSovitsOptions::default()));
        assert_eq!(g.kind(), TtsProviderKind::GptSovits);
    }

    #[test]
    fn ssml_escapes_xml() {
        let e = EdgeTtsEngine::new(EdgeTtsOptions::default());
        let ssml = e.build_ssml(&TtsRequest {
            text: "我说：<你好> & '世界'".into(),
            voice: None,
            rate_percent: 10,
            output_path: PathBuf::from("/tmp/x.mp3"),
        });
        assert!(ssml.contains("&lt;你好&gt;"));
        assert!(ssml.contains("&amp;"));
        assert!(ssml.contains("rate='+10%'"));
        assert!(ssml.contains("zh-CN-XiaoxiaoNeural"));
    }

    #[test]
    fn gpt_sovits_requires_ref_audio() {
        let rt = tokio::runtime::Runtime::new().unwrap();
        let e = GptSovitsTtsEngine::new(GptSovitsOptions::default());
        let r = rt.block_on(e.synthesize(&TtsRequest {
            text: "测试".into(),
            voice: None,
            rate_percent: 0,
            output_path: PathBuf::from("/tmp/x.wav"),
        }));
        let err = r.unwrap_err();
        assert!(matches!(
            err,
            SplicrError::Tts {
                provider: TtsProviderKind::GptSovits,
                ..
            }
        ));
    }

    #[tokio::test]
    async fn write_output_creates_parent_dirs() {
        let dir = std::env::temp_dir().join(format!("sf-tts-test-{}", std::process::id()));
        let path = dir.join("nested/out.mp3");
        let n = write_output(&path, b"hello").await.unwrap();
        assert_eq!(n, 5);
        assert!(path.exists());
        let _ = tokio::fs::remove_dir_all(&dir).await;
    }
}
