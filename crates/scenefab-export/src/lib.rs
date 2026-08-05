//! scenefab-export v3.0 · 导出器 (M4.5 实装)
//!
//! ## 责任范围
//! 3 种导出模式的参数规划 + 字幕渲染 (与 v2.4
//! `app/services/export/` 对应):
//!
//! | 模式   | 语义                              |
//! | ------ | --------------------------------- |
//! | quick  | 快速导出:1080x1920 / 30fps / 4M 码率预设 |
//! | custom | 自定义:完全取自 ProjectSettings   |
//! | silent | 静默导出:同 quick 但剥离音轨       |
//!
//! ## 设计
//! - 本 crate 只做**纯参数规划**:校验 + 生成 ffmpeg 参数列表,不执行进程
//! - [`ExportPlanner::plan`] 产出 [`ExportPlan`],执行层 (src-tauri command)
//!   将其交给 scenefab-ffmpeg
//! - [`render_subtitles`] 纯函数渲染 SRT / ASS / VTT 三种字幕文本
//! - codec/container 兼容性表在 [`validate_params`] 中集中维护
//!
//! ## 用法
//! ```
//! use scenefab_export::{ExportMode, ExportPlanner};
//!
//! let plan = ExportPlanner::new()
//!     .plan(ExportMode::Quick, None)
//!     .unwrap();
//! assert!(plan.params.include_audio);
//! assert!(plan.ffmpeg_args.contains(&"libx264".to_string()));
//! ```

use scenefab_domain::ProjectSettings;
use serde::{Deserialize, Serialize};
use thiserror::Error;

// ════════════════════════════════════════════════════════════════════════
// 错误类型
// ════════════════════════════════════════════════════════════════════════

#[derive(Debug, Error, PartialEq, Eq)]
pub enum ExportError {
    /// custom 模式必须提供 ProjectSettings
    #[error("custom 模式必须提供 ProjectSettings")]
    MissingCustomSettings,
    /// 分辨率格式错误 (应为 "WxH")
    #[error("分辨率格式错误: {0} (应为 宽x高,如 1080x1920)")]
    BadResolution(String),
    /// fps 超出范围
    #[error("fps 超出范围 (1..=240): {0}")]
    BadFps(u32),
    /// 码率格式错误 (应为 "8000k" / "8M")
    #[error("码率格式错误: {0} (应为 数字+k 或 数字+M)")]
    BadBitrate(String),
    /// codec 与 container 组合不受支持
    #[error("codec {codec} 与容器 {container} 组合不受支持")]
    UnsupportedCombination { codec: String, container: String },
    /// 字幕条目非法 (时间区间倒挂)
    #[error("字幕条目 {index} 时间区间非法: start={start}s >= end={end}s")]
    BadSubtitleRange { index: usize, start: u64, end: u64 },
}

// ════════════════════════════════════════════════════════════════════════
// 导出模式与参数
// ════════════════════════════════════════════════════════════════════════

/// 3 种导出模式
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "kebab-case")]
pub enum ExportMode {
    Quick,
    Custom,
    Silent,
}

/// 一次导出的完整编码参数
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ExportParams {
    /// "1080x1920" (宽x高)
    pub resolution: String,
    pub fps: u32,
    /// "4000k" / "8M"
    pub bitrate: String,
    /// "mp4" / "mov" / "webm"
    pub container: String,
    /// "h264" / "h265" / "vp9"
    pub codec: String,
    /// silent 模式为 false
    pub include_audio: bool,
}

/// 规划产物:校验后的参数 + ffmpeg 参数列表
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ExportPlan {
    pub mode: ExportMode,
    pub params: ExportParams,
    /// ffmpeg 编码参数 (不含输入/输出文件,执行层拼接)
    pub ffmpeg_args: Vec<String>,
}

/// quick / silent 预设 (竖屏默认)
const QUICK_RESOLUTION: &str = "1080x1920";
const QUICK_FPS: u32 = 30;
const QUICK_BITRATE: &str = "4000k";
const QUICK_CONTAINER: &str = "mp4";
const QUICK_CODEC: &str = "h264";

// ════════════════════════════════════════════════════════════════════════
// ExportPlanner
// ════════════════════════════════════════════════════════════════════════

/// 导出参数规划器 (纯函数,无状态)
#[derive(Debug, Clone, Copy, Default)]
pub struct ExportPlanner;

impl ExportPlanner {
    pub fn new() -> Self {
        Self
    }

    /// 按模式生成导出计划。
    /// - `Quick` / `Silent`:使用内置预设,忽略 settings
    /// - `Custom`:settings 必填,完全采用项目设置
    pub fn plan(
        &self,
        mode: ExportMode,
        settings: Option<&ProjectSettings>,
    ) -> Result<ExportPlan, ExportError> {
        let params = match mode {
            ExportMode::Quick | ExportMode::Silent => ExportParams {
                resolution: QUICK_RESOLUTION.into(),
                fps: QUICK_FPS,
                bitrate: QUICK_BITRATE.into(),
                container: QUICK_CONTAINER.into(),
                codec: QUICK_CODEC.into(),
                include_audio: mode == ExportMode::Quick,
            },
            ExportMode::Custom => {
                let s = settings.ok_or(ExportError::MissingCustomSettings)?;
                ExportParams {
                    resolution: s.resolution.clone(),
                    fps: s.fps,
                    bitrate: s.bitrate.clone(),
                    container: s.container.clone(),
                    codec: s.codec.clone(),
                    include_audio: true,
                }
            }
        };
        validate_params(&params)?;
        Ok(ExportPlan {
            mode,
            ffmpeg_args: build_ffmpeg_args(&params),
            params,
        })
    }
}

/// 参数校验:分辨率 / fps / 码率 / codec×container 兼容性
pub fn validate_params(p: &ExportParams) -> Result<(), ExportError> {
    // 分辨率 "WxH"
    let (w, h) = p
        .resolution
        .split_once('x')
        .ok_or_else(|| ExportError::BadResolution(p.resolution.clone()))?;
    let (w, h): (u32, u32) = match (w.parse(), h.parse()) {
        (Ok(w), Ok(h)) if w > 0 && h > 0 => (w, h),
        _ => return Err(ExportError::BadResolution(p.resolution.clone())),
    };
    let _ = (w, h);

    if !(1..=240).contains(&p.fps) {
        return Err(ExportError::BadFps(p.fps));
    }

    // 码率:数字 + k/M 后缀
    let br = p.bitrate.trim();
    let ok = br.len() > 1
        && matches!(br.as_bytes()[br.len() - 1], b'k' | b'K' | b'm' | b'M')
        && br[..br.len() - 1].chars().all(|c| c.is_ascii_digit())
        && br[..br.len() - 1].parse::<u64>().is_ok_and(|v| v > 0);
    if !ok {
        return Err(ExportError::BadBitrate(p.bitrate.clone()));
    }

    // codec × container 兼容表
    let codec = p.codec.to_ascii_lowercase();
    let container = p.container.to_ascii_lowercase();
    let compatible = match codec.as_str() {
        "h264" | "h265" | "hevc" | "av1" => matches!(container.as_str(), "mp4" | "mov"),
        "vp9" => container == "webm",
        _ => false,
    };
    if !compatible {
        return Err(ExportError::UnsupportedCombination {
            codec: p.codec.clone(),
            container: p.container.clone(),
        });
    }
    Ok(())
}

/// codec 名 → ffmpeg 编码器名
pub fn ffmpeg_encoder(codec: &str) -> &'static str {
    match codec.to_ascii_lowercase().as_str() {
        "h264" => "libx264",
        "h265" | "hevc" => "libx265",
        "vp9" => "libvpx-vp9",
        "av1" => "libaom-av1",
        _ => "libx264", // 兜底:已通过 validate_params 的不会走到这里
    }
}

fn build_ffmpeg_args(p: &ExportParams) -> Vec<String> {
    let mut args: Vec<String> = vec![
        "-r".into(),
        p.fps.to_string(),
        "-s".into(),
        p.resolution.clone(),
        "-c:v".into(),
        ffmpeg_encoder(&p.codec).into(),
        "-b:v".into(),
        p.bitrate.clone(),
        "-y".into(),
    ];
    if p.include_audio {
        args.extend(["-c:a".into(), "aac".into(), "-b:a".into(), "192k".into()]);
    } else {
        args.extend(["-an".into()]);
    }
    args
}

// ════════════════════════════════════════════════════════════════════════
// 字幕渲染 (SRT / ASS / VTT)
// ════════════════════════════════════════════════════════════════════════

/// 字幕输出格式
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "kebab-case")]
pub enum SubtitleFormat {
    Srt,
    Ass,
    Vtt,
}

impl SubtitleFormat {
    /// 文件扩展名 (不含点)
    pub fn extension(self) -> &'static str {
        match self {
            Self::Srt => "srt",
            Self::Ass => "ass",
            Self::Vtt => "vtt",
        }
    }
}

/// 一条字幕
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct SubtitleItem {
    pub start_seconds: f64,
    pub end_seconds: f64,
    pub text: String,
}

/// 渲染字幕文本 (纯函数)。条目按入参顺序编号 (1-based),
/// 时间区间倒挂返回错误。
pub fn render_subtitles(
    items: &[SubtitleItem],
    format: SubtitleFormat,
) -> Result<String, ExportError> {
    for (i, item) in items.iter().enumerate() {
        if item.start_seconds >= item.end_seconds {
            return Err(ExportError::BadSubtitleRange {
                index: i + 1,
                start: item.start_seconds as u64,
                end: item.end_seconds as u64,
            });
        }
    }
    Ok(match format {
        SubtitleFormat::Srt => render_srt(items),
        SubtitleFormat::Vtt => render_vtt(items),
        SubtitleFormat::Ass => render_ass(items),
    })
}

fn ts_srt(seconds: f64) -> String {
    let ms = (seconds.max(0.0) * 1000.0).round() as u64;
    let (h, rem) = (ms / 3_600_000, ms % 3_600_000);
    let (m, rem) = (rem / 60_000, rem % 60_000);
    let (s, ms) = (rem / 1000, rem % 1000);
    format!("{h:02}:{m:02}:{s:02},{ms:03}")
}

fn ts_vtt(seconds: f64) -> String {
    ts_srt(seconds).replace(',', ".")
}

fn ts_ass(seconds: f64) -> String {
    let cs = (seconds.max(0.0) * 100.0).round() as u64;
    let (h, rem) = (cs / 360_000, cs % 360_000);
    let (m, rem) = (rem / 6_000, rem % 6_000);
    let (s, cs) = (rem / 100, rem % 100);
    format!("{h}:{m:02}:{s:02}.{cs:02}")
}

fn render_srt(items: &[SubtitleItem]) -> String {
    let mut out = String::new();
    for (i, item) in items.iter().enumerate() {
        out.push_str(&format!(
            "{}\n{} --> {}\n{}\n\n",
            i + 1,
            ts_srt(item.start_seconds),
            ts_srt(item.end_seconds),
            item.text
        ));
    }
    out
}

fn render_vtt(items: &[SubtitleItem]) -> String {
    let mut out = String::from("WEBVTT\n\n");
    for (i, item) in items.iter().enumerate() {
        out.push_str(&format!(
            "{}\n{} --> {}\n{}\n\n",
            i + 1,
            ts_vtt(item.start_seconds),
            ts_vtt(item.end_seconds),
            item.text
        ));
    }
    out
}

const ASS_HEADER: &str = "[Script Info]\n\
ScriptType: v4.00+\n\
PlayResX: 1080\n\
PlayResY: 1920\n\
\n\
[V4+ Styles]\n\
Format: Name, Fontname, Fontsize, PrimaryColour, Alignment, MarginV\n\
Style: Default,Noto Sans CJK SC,58,&H00FFFFFF,2,120\n\
\n\
[Events]\n\
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n";

fn render_ass(items: &[SubtitleItem]) -> String {
    let mut out = String::from(ASS_HEADER);
    for item in items {
        out.push_str(&format!(
            "Dialogue: 0,{},{},Default,,0,0,0,,{}\n",
            ts_ass(item.start_seconds),
            ts_ass(item.end_seconds),
            item.text
        ));
    }
    out
}

#[cfg(test)]
mod tests {
    use super::*;

    fn sample_items() -> Vec<SubtitleItem> {
        vec![
            SubtitleItem {
                start_seconds: 0.0,
                end_seconds: 2.5,
                text: "第一句".into(),
            },
            SubtitleItem {
                start_seconds: 2.5,
                end_seconds: 61.234,
                text: "第二句".into(),
            },
        ]
    }

    // ── 模式规划 ────────────────────────────────────────────────────
    #[test]
    fn quick_mode_uses_preset_with_audio() {
        let plan = ExportPlanner::new().plan(ExportMode::Quick, None).unwrap();
        assert_eq!(plan.params.resolution, "1080x1920");
        assert_eq!(plan.params.fps, 30);
        assert!(plan.params.include_audio);
        assert!(plan.ffmpeg_args.contains(&"-c:a".to_string()));
    }

    #[test]
    fn silent_mode_strips_audio() {
        let plan = ExportPlanner::new().plan(ExportMode::Silent, None).unwrap();
        assert!(!plan.params.include_audio);
        assert!(plan.ffmpeg_args.contains(&"-an".to_string()));
        assert!(!plan.ffmpeg_args.contains(&"-c:a".to_string()));
    }

    #[test]
    fn custom_mode_takes_project_settings() {
        let s = ProjectSettings {
            resolution: "1920x1080".into(),
            fps: 60,
            bitrate: "12M".into(),
            ..Default::default()
        };
        let plan = ExportPlanner::new()
            .plan(ExportMode::Custom, Some(&s))
            .unwrap();
        assert_eq!(plan.params.resolution, "1920x1080");
        assert_eq!(plan.params.fps, 60);
        assert_eq!(plan.params.bitrate, "12M");
    }

    #[test]
    fn custom_mode_requires_settings() {
        let err = ExportPlanner::new()
            .plan(ExportMode::Custom, None)
            .unwrap_err();
        assert_eq!(err, ExportError::MissingCustomSettings);
    }

    // ── 参数校验 ────────────────────────────────────────────────────
    #[test]
    fn validate_rejects_bad_resolution() {
        let mut p = ExportPlanner::new()
            .plan(ExportMode::Quick, None)
            .unwrap()
            .params;
        p.resolution = "1080".into();
        assert!(matches!(
            validate_params(&p),
            Err(ExportError::BadResolution(_))
        ));
        p.resolution = "0x1920".into();
        assert!(matches!(
            validate_params(&p),
            Err(ExportError::BadResolution(_))
        ));
    }

    #[test]
    fn validate_rejects_bad_fps_and_bitrate() {
        let mut p = ExportPlanner::new()
            .plan(ExportMode::Quick, None)
            .unwrap()
            .params;
        p.fps = 0;
        assert!(matches!(validate_params(&p), Err(ExportError::BadFps(0))));
        p.fps = 30;
        p.bitrate = "fast".into();
        assert!(matches!(
            validate_params(&p),
            Err(ExportError::BadBitrate(_))
        ));
        p.bitrate = "0k".into();
        assert!(matches!(
            validate_params(&p),
            Err(ExportError::BadBitrate(_))
        ));
    }

    #[test]
    fn validate_codec_container_matrix() {
        let base = ExportPlanner::new()
            .plan(ExportMode::Quick, None)
            .unwrap()
            .params;
        let try_combo = |codec: &str, container: &str| {
            let p = ExportParams {
                codec: codec.into(),
                container: container.into(),
                ..base.clone()
            };
            validate_params(&p).is_ok()
        };
        assert!(try_combo("h264", "mp4"));
        assert!(try_combo("h265", "mov"));
        assert!(try_combo("vp9", "webm"));
        assert!(!try_combo("vp9", "mp4"));
        assert!(!try_combo("h264", "webm"));
        assert!(!try_combo("prores", "mov")); // 未知 codec
    }

    #[test]
    fn ffmpeg_encoder_mapping() {
        assert_eq!(ffmpeg_encoder("h264"), "libx264");
        assert_eq!(ffmpeg_encoder("H265"), "libx265");
        assert_eq!(ffmpeg_encoder("hevc"), "libx265");
        assert_eq!(ffmpeg_encoder("vp9"), "libvpx-vp9");
        assert_eq!(ffmpeg_encoder("av1"), "libaom-av1");
    }

    // ── 字幕渲染 ────────────────────────────────────────────────────
    #[test]
    fn srt_format() {
        let out = render_subtitles(&sample_items(), SubtitleFormat::Srt).unwrap();
        assert!(out.starts_with("1\n00:00:00,000 --> 00:00:02,500\n第一句\n"));
        assert!(out.contains("2\n00:00:02,500 --> 00:01:01,234\n第二句\n"));
    }

    #[test]
    fn vtt_format_has_header_and_dot_separator() {
        let out = render_subtitles(&sample_items(), SubtitleFormat::Vtt).unwrap();
        assert!(out.starts_with("WEBVTT\n\n"));
        assert!(out.contains("00:00:00.000 --> 00:00:02.500"));
        assert!(!out.contains(',')); // VTT 毫秒分隔符是点
    }

    #[test]
    fn ass_format_has_sections_and_dialogue() {
        let out = render_subtitles(&sample_items(), SubtitleFormat::Ass).unwrap();
        assert!(out.contains("[Script Info]"));
        assert!(out.contains("[V4+ Styles]"));
        assert!(out.contains("[Events]"));
        assert!(out.contains("Dialogue: 0,0:00:00.00,0:00:02.50,Default,,0,0,0,,第一句"));
        assert!(out.contains("0:01:01.23"));
    }

    #[test]
    fn subtitles_reject_inverted_range() {
        let bad = vec![SubtitleItem {
            start_seconds: 5.0,
            end_seconds: 3.0,
            text: "x".into(),
        }];
        assert!(matches!(
            render_subtitles(&bad, SubtitleFormat::Srt),
            Err(ExportError::BadSubtitleRange { index: 1, .. })
        ));
    }

    #[test]
    fn subtitles_empty_list_renders_empty_or_header() {
        assert_eq!(render_subtitles(&[], SubtitleFormat::Srt).unwrap(), "");
        assert!(render_subtitles(&[], SubtitleFormat::Vtt)
            .unwrap()
            .starts_with("WEBVTT"));
        assert!(render_subtitles(&[], SubtitleFormat::Ass)
            .unwrap()
            .contains("[Events]"));
    }

    #[test]
    fn subtitle_format_extension() {
        assert_eq!(SubtitleFormat::Srt.extension(), "srt");
        assert_eq!(SubtitleFormat::Ass.extension(), "ass");
        assert_eq!(SubtitleFormat::Vtt.extension(), "vtt");
    }

    // ── serde ───────────────────────────────────────────────────────
    #[test]
    fn mode_and_params_serde_roundtrip() {
        let plan = ExportPlanner::new().plan(ExportMode::Silent, None).unwrap();
        let json = serde_json::to_string(&plan).unwrap();
        let back: ExportPlan = serde_json::from_str(&json).unwrap();
        assert_eq!(plan, back);
        assert_eq!(
            serde_json::to_string(&ExportMode::Quick).unwrap(),
            "\"quick\""
        );
    }
}
