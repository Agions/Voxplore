//! Vynaro v1.0.0 · AI 脚本生成 Tauri 命令

use vynaro_script::{factory, LlmProviderKind, LlmRequest};

#[allow(dead_code)]
#[derive(serde::Deserialize)]
pub struct ScriptGenerateParams {
    pub provider: String,
    pub api_key: Option<String>,
    pub base_url: Option<String>,
    pub model: Option<String>,
    pub prompt: String,
    pub style: Option<String>, // "immersive" | "critic" | "story" | "roast"
    pub emotion_density: Option<f32>,
    pub word_count_target: Option<u32>,
    /// 可选多模态关键帧图片 Base64 数组
    pub images_base64: Option<Vec<String>>,
}

#[derive(serde::Serialize)]
pub struct ScriptGenerateResult {
    pub text: String,
    pub word_count: usize,
    pub estimated_duration_sec: u32,
}

fn parse_provider(kind: &str) -> LlmProviderKind {
    match kind.to_lowercase().as_str() {
        "qwen" => LlmProviderKind::Qwen,
        "kimi" => LlmProviderKind::Kimi,
        "glm5" => LlmProviderKind::Glm5,
        "claude" => LlmProviderKind::Claude,
        "gemini" => LlmProviderKind::Gemini,
        "deepseek" => LlmProviderKind::DeepSeek,
        "doubao" => LlmProviderKind::Doubao,
        "hunyuan" => LlmProviderKind::Hunyuan,
        "local" => LlmProviderKind::Local,
        "qwen37" => LlmProviderKind::Qwen37,
        _ => LlmProviderKind::OpenAi,
    }
}

#[tauri::command]
pub async fn script_generate(params: ScriptGenerateParams) -> Result<ScriptGenerateResult, String> {
    if params.prompt.trim().is_empty() {
        return Err("提示词不能为空".into());
    }

    let kind = parse_provider(&params.provider);
    let api_key = params.api_key.unwrap_or_default();
    let generator = factory(kind, api_key);

    let style_str = params.style.as_deref().unwrap_or("immersive");
    let target_words = params.word_count_target.unwrap_or(800);

    let system_prompt = format!(
        "你是一位顶尖短剧/影视的第一人称解说剧本创作大师。请以【第一人称沉浸式视角】（我/我们）为核心，\
         风格定调为【{style_str}】，目标字数约 {target_words} 字。在关键高潮句前加上情绪标注，如 [情绪高潮] 或 [激烈冲突]。"
    );

    let req = LlmRequest {
        system: system_prompt,
        user: params.prompt,
        model: params.model,
        max_tokens: Some(2048),
        temperature: Some(0.7),
        stream: false,
        images_base64: params.images_base64.unwrap_or_default(),
    };

    let resp = generator
        .chat(&req)
        .await
        .map_err(|e| format!("生成 AI 独白脚本失败: {e}"))?;

    let text = resp.content;
    let word_count = text.chars().count();
    let estimated_duration_sec = (word_count as u32 / 4).max(10); // 约4字/秒

    Ok(ScriptGenerateResult {
        text,
        word_count,
        estimated_duration_sec,
    })
}
