//! vynaro-subtitle — Step 5 · 字幕合成
//!
//! 职责：
//! - VAD（语音端点检测）驱动字幕时间轴自动对齐
//! - 格式输出：SRT / VTT / ASS
//! - 动态字幕：逐字高亮 + 情绪关键词变色
//! - 双语字幕：中英双语同轨生成

pub mod formats;
pub mod vad;
pub mod dynamic;

use serde::{Deserialize, Serialize};
use thiserror::Error;

#[derive(Debug, Error)]
pub enum SubtitleError {
    #[error("VAD 端点检测失败: {0}")]
    VadError(String),
    #[error("字幕格式化失败: {0}")]
    FormatError(String),
    #[error("时间轴对齐失败: {0}")]
    AlignError(String),
}

/// 字幕条目
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SubtitleEntry {
    pub index: u32,
    pub start_ms: u64,
    pub end_ms: u64,
    pub text: String,
    pub emotion_tag: Option<String>,
}

/// 字幕轨道
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SubtitleTrack {
    pub entries: Vec<SubtitleEntry>,
    pub format: SubtitleFormat,
    pub language: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum SubtitleFormat {
    Srt,
    Vtt,
    Ass,
}

/// 字幕生成器 trait
#[async_trait::async_trait]
pub trait SubtitleGenerator: Send + Sync {
    /// 从音频 + 脚本文本生成字幕轨道
    async fn generate(
        &self,
        audio_path: &std::path::Path,
        script: &str,
        format: SubtitleFormat,
    ) -> Result<SubtitleTrack, SubtitleError>;

    /// 将字幕轨道序列化为目标格式字符串
    fn serialize(&self, track: &SubtitleTrack) -> Result<String, SubtitleError>;
}
