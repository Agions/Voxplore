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
    /// 黄金前3秒爆款钩子策略 ("conflict" | "paradox" | "survival" | "emotion")
    pub hook_style: Option<String>,
    pub include_hook: Option<bool>,
    /// 可选多模态关键帧图片 Base64 数组
    pub images_base64: Option<Vec<String>>,
}

#[derive(serde::Serialize)]
pub struct ScriptGenerateResult {
    pub text: String,
    pub hook_text: Option<String>,
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
    let hook_strategy = params.hook_style.as_deref().unwrap_or("conflict");
    let include_hook = params.include_hook.unwrap_or(true);

    let hook_guidance = if include_hook {
        match hook_strategy {
            "paradox" => "【黄金前3秒钩子：悬念悖论型】开头第1句必须抛出极具反常识的违和行为或设问（如“这个女人不仅当场释放了杀害丈夫的凶手，还宣布要嫁给他…”），用 [HOOK 0~3s] 标记。",
            "survival" => "【黄金前3秒钩子：生死极限型】开头第1句必须制造生死倒计时与极度紧迫感（如“注意看！这个男人只剩下最后30秒生命，而唯一的解药…”），用 [HOOK 0~3s] 标记。",
            "emotion" => "【黄金前3秒钩子：情感撕裂型】开头第1句必须直击人性痛点与撕心裂肺的抉择（如“结婚五年，妻子为了初恋的一通电话，竟然将亲生女儿抛弃在风雪中…”），用 [HOOK 0~3s] 标记。",
            _ => "【黄金前3秒钩子：战神冲突反转型】开头第1句必须是惊天反差与身份揭秘（如“如果不是亲眼所见，谁敢相信眼前这个被当众羞辱的穷小子，真实身份竟然是统领全球的修罗殿主…”），用 [HOOK 0~3s] 标记。",
        }
    } else {
        ""
    };

    let system_prompt = format!(
        "你是一位顶尖短剧/影视的第一人称解说剧本创作大师。请以【第一人称沉浸式视角】（我/我们）为核心，\
         风格定调为【{style_str}】，目标字数约 {target_words} 字。\n\
         {hook_guidance}\n\
         在关键高潮句前加上情绪标注，如 [情绪高潮] 或 [激烈冲突]。"
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

    // 提取 Hook 文本（优先匹配 [HOOK ...] 标记，若无则提取开头第 1 句高光设问）
    let hook_text = if let Some(pos) = text.find("[HOOK") {
        let after = &text[pos..];
        let end_pos = after.find('\n').unwrap_or(after.len());
        Some(after[..end_pos].trim().to_string())
    } else if include_hook {
        // 智能提取首句作为黄金前3秒文案
        let first_sentence = text
            .split(&['。', '！', '？', '\n'][..])
            .next()
            .unwrap_or("")
            .trim();
        if !first_sentence.is_empty() {
            Some(format!("[HOOK 0~3s] {first_sentence}"))
        } else {
            None
        }
    } else {
        None
    };

    Ok(ScriptGenerateResult {
        text,
        hook_text,
        word_count,
        estimated_duration_sec,
    })
}
