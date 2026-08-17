//! splicr-subtitle · formats — 字幕格式序列化

use crate::{SubtitleError, SubtitleFormat, SubtitleTrack};

/// 将字幕轨道序列化为 SRT 格式
pub fn to_srt(track: &SubtitleTrack) -> Result<String, SubtitleError> {
    let mut out = String::new();
    for entry in &track.entries {
        let start = ms_to_srt_time(entry.start_ms);
        let end = ms_to_srt_time(entry.end_ms);
        out.push_str(&format!(
            "{}\n{} --> {}\n{}\n\n",
            entry.index, start, end, entry.text
        ));
    }
    Ok(out)
}

/// 将字幕轨道序列化为 WebVTT 格式
pub fn to_vtt(track: &SubtitleTrack) -> Result<String, SubtitleError> {
    let mut out = String::from("WEBVTT\n\n");
    for entry in &track.entries {
        let start = ms_to_vtt_time(entry.start_ms);
        let end = ms_to_vtt_time(entry.end_ms);
        out.push_str(&format!("{} --> {}\n{}\n\n", start, end, entry.text));
    }
    Ok(out)
}

fn ms_to_srt_time(ms: u64) -> String {
    let h = ms / 3_600_000;
    let m = (ms % 3_600_000) / 60_000;
    let s = (ms % 60_000) / 1_000;
    let ms = ms % 1_000;
    format!("{:02}:{:02}:{:02},{:03}", h, m, s, ms)
}

fn ms_to_vtt_time(ms: u64) -> String {
    let h = ms / 3_600_000;
    let m = (ms % 3_600_000) / 60_000;
    let s = (ms % 60_000) / 1_000;
    let ms = ms % 1_000;
    format!("{:02}:{:02}:{:02}.{:03}", h, m, s, ms)
}

pub fn serialize(track: &SubtitleTrack) -> Result<String, SubtitleError> {
    match track.format {
        SubtitleFormat::Srt => to_srt(track),
        SubtitleFormat::Vtt => to_vtt(track),
        SubtitleFormat::Ass => Err(SubtitleError::FormatError("ASS 格式暂未实现".into())),
    }
}
