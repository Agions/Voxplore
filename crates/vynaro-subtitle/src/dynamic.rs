//! vynaro-subtitle · dynamic — 动态字幕：逐字高亮 + 情绪关键词变色

use crate::{SubtitleEntry, SubtitleError};

/// 情绪关键词定义
const EMOTION_KEYWORDS: &[&str] = &[
    "没想到",
    "震惊",
    "愤怒",
    "爱上",
    "痛苦",
    "复仇",
    "真相",
    "秘密",
    "背叛",
    "死亡",
    "绝望",
    "希望",
    "奇迹",
    "突然",
];

/// 为字幕条目添加情绪标签（基于关键词匹配）
pub fn tag_emotion(entry: &mut SubtitleEntry) {
    for keyword in EMOTION_KEYWORDS {
        if entry.text.contains(keyword) {
            entry.emotion_tag = Some(keyword.to_string());
            return;
        }
    }
}

/// 将文本分词为逐字高亮 ASS 样式标记
/// 每个字符加上 {\an8\1c&HFFD242&} 金色高亮
pub fn to_karaoke_ass(entry: &SubtitleEntry) -> Result<String, SubtitleError> {
    let chars: Vec<char> = entry.text.chars().collect();
    let duration_per_char = if chars.is_empty() {
        100u64
    } else {
        (entry.end_ms - entry.start_ms) / chars.len() as u64
    };

    let mut result = String::new();
    for (i, ch) in chars.iter().enumerate() {
        let t = (i as u64 * duration_per_char) / 10; // ASS 时间单位是 10ms
        result.push_str(&format!("{{\\k{}}}{}", t, ch));
    }
    Ok(result)
}

/// 批量处理字幕条目：标注情绪 + 可选逐字高亮
pub fn process_entries(
    entries: &mut [SubtitleEntry],
    enable_emotion: bool,
) -> Result<(), SubtitleError> {
    for entry in entries.iter_mut() {
        if enable_emotion {
            tag_emotion(entry);
        }
    }
    Ok(())
}
