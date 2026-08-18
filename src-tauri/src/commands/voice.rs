//! splicr v1.0.0 · TTS 试听与合成 Tauri 命令

use splicr_voice::{
    engine, EdgeTtsOptions, GptSovitsOptions, MimoTtsOptions, OpenAiTtsOptions, TtsEngineConfig,
    TtsRequest,
};
use std::path::PathBuf;
use tauri::Manager;

#[derive(serde::Deserialize)]
pub struct VoicePreviewParams {
    pub text: String,
    pub provider: String, // "edge" | "open-ai" | "mimo" | "gpt-sovits"
    pub voice: Option<String>,
    pub rate_percent: i32,
    pub api_key: Option<String>,
    pub base_url: Option<String>,
    pub model: Option<String>,
    pub ref_audio_path: Option<String>,
    pub prompt_text: Option<String>,
}

#[derive(serde::Serialize)]
pub struct VoicePreviewResult {
    pub file_path: String,
    pub format: String,
    pub bytes_written: u64,
}

/// 快捷试听生成: 将试听文本生成音频并存入 App 临时缓存目录 `~/.splicr/cache/tts/`
#[tauri::command]
pub async fn voice_preview(
    app_handle: tauri::AppHandle,
    params: VoicePreviewParams,
) -> Result<VoicePreviewResult, String> {
    if params.text.trim().is_empty() {
        return Err("试听文本不能为空".into());
    }

    // 默认缓存目录
    let cache_dir = app_handle
        .path()
        .app_cache_dir()
        .unwrap_or_else(|_| PathBuf::from("/tmp/splicr/cache"));
    let tts_cache_dir = cache_dir.join("tts");
    tokio::fs::create_dir_all(&tts_cache_dir)
        .await
        .map_err(|e| format!("创建 TTS 缓存目录失败: {e}"))?;

    let file_id = chrono::Utc::now().timestamp_millis();
    let ext = if params.provider == "gpt-sovits" {
        "wav"
    } else {
        "mp3"
    };
    let output_path = tts_cache_dir.join(format!("preview_{file_id}.{ext}"));

    let config = match params.provider.as_str() {
        "open-ai" => TtsEngineConfig::OpenAi(OpenAiTtsOptions {
            api_key: params.api_key.unwrap_or_default(),
            base_url: params
                .base_url
                .unwrap_or_else(|| "https://api.openai.com".into()),
            model: params.model.unwrap_or_else(|| "tts-1".into()),
            voice: params.voice.clone().unwrap_or_else(|| "alloy".into()),
        }),
        "mimo" => TtsEngineConfig::Mimo(MimoTtsOptions {
            api_key: params.api_key.unwrap_or_default(),
            base_url: params
                .base_url
                .unwrap_or_else(|| "https://api.xiaomimimo.com/v1".into()),
            model: params.model.unwrap_or_else(|| "mimo-v2.5-tts".into()),
            voice: params.voice.clone().unwrap_or_else(|| "default".into()),
        }),
        "gpt-sovits" => TtsEngineConfig::GptSovits(GptSovitsOptions {
            base_url: params
                .base_url
                .unwrap_or_else(|| "http://127.0.0.1:9880".into()),
            ref_audio_path: params.ref_audio_path.unwrap_or_default(),
            prompt_text: params.prompt_text.unwrap_or_default(),
            prompt_lang: "zh".into(),
        }),
        _ => TtsEngineConfig::Edge(EdgeTtsOptions {
            voice: params
                .voice
                .clone()
                .unwrap_or_else(|| "zh-CN-XiaoxiaoNeural".into()),
        }),
    };

    let tts_engine = engine(config);
    let outcome = tts_engine
        .synthesize(&TtsRequest {
            text: params.text,
            voice: params.voice,
            rate_percent: params.rate_percent,
            output_path: output_path.clone(),
        })
        .await
        .map_err(|e| format!("TTS 试听合成失败: {e}"))?;

    Ok(VoicePreviewResult {
        file_path: output_path.to_string_lossy().to_string(),
        format: outcome.format.to_string(),
        bytes_written: outcome.bytes_written,
    })
}

/// 完整配音合成导出: 将文本合成至指定目标文件路径
#[tauri::command]
pub async fn voice_synthesize(
    params: VoicePreviewParams,
    output_path: String,
) -> Result<VoicePreviewResult, String> {
    if params.text.trim().is_empty() {
        return Err("合成文本不能为空".into());
    }

    let out_path = PathBuf::from(&output_path);

    let config = match params.provider.as_str() {
        "open-ai" => TtsEngineConfig::OpenAi(OpenAiTtsOptions {
            api_key: params.api_key.unwrap_or_default(),
            base_url: params
                .base_url
                .unwrap_or_else(|| "https://api.openai.com".into()),
            model: params.model.unwrap_or_else(|| "tts-1".into()),
            voice: params.voice.clone().unwrap_or_else(|| "alloy".into()),
        }),
        "mimo" => TtsEngineConfig::Mimo(MimoTtsOptions {
            api_key: params.api_key.unwrap_or_default(),
            base_url: params
                .base_url
                .unwrap_or_else(|| "https://api.minimax.chat".into()),
            model: params.model.unwrap_or_else(|| "speech-01-hd".into()),
            voice: params
                .voice
                .clone()
                .unwrap_or_else(|| "male-qn-qingse".into()),
        }),
        "gpt-sovits" => TtsEngineConfig::GptSovits(GptSovitsOptions {
            base_url: params
                .base_url
                .unwrap_or_else(|| "http://127.0.0.1:9880".into()),
            ref_audio_path: params.ref_audio_path.unwrap_or_default(),
            prompt_text: params.prompt_text.unwrap_or_default(),
            prompt_lang: "zh".into(),
        }),
        _ => TtsEngineConfig::Edge(EdgeTtsOptions {
            voice: params
                .voice
                .clone()
                .unwrap_or_else(|| "zh-CN-XiaoxiaoNeural".into()),
        }),
    };

    let tts_engine = engine(config);
    let outcome = tts_engine
        .synthesize(&TtsRequest {
            text: params.text,
            voice: params.voice,
            rate_percent: params.rate_percent,
            output_path: out_path.clone(),
        })
        .await
        .map_err(|e| format!("TTS 完整合成失败: {e}"))?;

    Ok(VoicePreviewResult {
        file_path: out_path.to_string_lossy().to_string(),
        format: outcome.format.to_string(),
        bytes_written: outcome.bytes_written,
    })
}
