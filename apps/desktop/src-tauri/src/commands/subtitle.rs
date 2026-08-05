//! Vynaro v2.5.0 · 智能字幕与 ASS/SRT/VTT 渲染 Tauri 命令

use vynaro_export::{SubtitleFormat, SubtitleItem};

#[derive(serde::Deserialize)]
pub struct SubtitleGenerateParams {
    pub script_text: String,
    pub format: String, // "srt" | "vtt" | "ass"
}

#[derive(serde::Serialize)]
pub struct SubtitleGenerateResult {
    pub content: String,
    pub format: String,
    pub item_count: usize,
    pub items: Vec<SubtitleItem>,
}

#[tauri::command]
pub async fn subtitle_generate(
    params: SubtitleGenerateParams,
) -> Result<SubtitleGenerateResult, String> {
    if params.script_text.trim().is_empty() {
        return Err("字幕生成文本不能为空".into());
    }

    let lines: Vec<&str> = params
        .script_text
        .lines()
        .map(|l| l.trim())
        .filter(|l| !l.is_empty())
        .collect();

    let mut items = Vec::new();
    let mut curr_sec = 0.0f64;

    for (idx, line) in lines.iter().enumerate() {
        let clean = line
            .replace("[激烈冲突]", "")
            .replace("[情绪高潮]", "")
            .replace("[悬疑收尾]", "")
            .trim()
            .to_string();
        if clean.is_empty() {
            continue;
        }

        let dur = (clean.chars().count() as f64 * 0.28).max(1.8);
        let start = curr_sec;
        let end = curr_sec + dur;
        curr_sec = end + 0.2;

        items.push(SubtitleItem {
            start_seconds: start,
            end_seconds: end,
            text: clean,
        });
    }

    let sub_fmt = match params.format.to_lowercase().as_str() {
        "vtt" => SubtitleFormat::Vtt,
        "ass" => SubtitleFormat::Ass,
        _ => SubtitleFormat::Srt,
    };

    let content = vynaro_export::render_subtitles(&items, sub_fmt)
        .map_err(|e| format!("渲染字幕失败: {e}"))?;

    let count = items.len();

    Ok(SubtitleGenerateResult {
        content,
        format: params.format,
        item_count: count,
        items,
    })
}
