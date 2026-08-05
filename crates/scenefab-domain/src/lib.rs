//! scenefab-domain v3.0 · 领域模型
//!
//! ## 责任范围
//! 整个应用的"业务对象" — 不依赖任何基础设施 (无 IO / 无 HTTP / 无 IO error 类型)
//!
//! ## M2 范围
//! - [`Project`]   : 顶层项目 (1 个 .scenefab 文件对应 1 个 Project)
//! - [`MediaFile`] : 媒体文件 (mp4 / mov / wav / mp3)
//! - [`Timeline`]  : 时间线 (含 tracks + clips)
//! - [`Track`]     : 时间线轨道
//! - [`Clip`]      : 时间线片段 (引用 MediaFile 的一部分)
//! - [`ScriptSegment`] : 脚本一段 (第一人称叙述段)
//! - [`ExportRecord`]  : 一次导出记录
//! - [`ExportStrategy`]: 4 策略枚举 (single/concat/batch/series)
//!
//! ## 序列化
//! 所有结构体 `#[derive(Serialize, Deserialize)]`,
//! 既能直接 `serde_json` 落盘、又能 Tauri IPC 直接收发。

#![allow(dead_code)]

use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use std::path::PathBuf;

/// 顶层项目。一个 .scenefab 文件对应 1 个 Project。
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct Project {
    pub id: String,
    pub name: String,
    pub created_at: DateTime<Utc>,
    pub updated_at: DateTime<Utc>,
    pub version: semver::Version,
    pub settings: ProjectSettings,
    pub media_files: Vec<MediaFile>,
    pub timeline: Timeline,
    pub scripts: Vec<ScriptSegment>,
    pub exports: Vec<ExportRecord>,
}

impl Default for Project {
    fn default() -> Self {
        Self {
            id: uuid_v4_like(),
            name: "未命名项目".into(),
            created_at: Utc::now(),
            updated_at: Utc::now(),
            version: semver::Version::parse("1.0.0").unwrap(),
            settings: ProjectSettings::default(),
            media_files: vec![],
            timeline: Timeline::default(),
            scripts: vec![],
            exports: vec![],
        }
    }
}

/// 项目的运行时设置 (与全局 ConfigService 不同)。
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct ProjectSettings {
    pub resolution: String, // "1080x1920" 等
    pub fps: u32,           // 30 / 60
    pub bitrate: String,    // "8000k"
    pub container: String,  // "mp4"
    pub codec: String,      // "h264"
    pub four_strategy: ExportStrategy,
}

impl Default for ProjectSettings {
    fn default() -> Self {
        Self {
            resolution: "1080x1920".into(), // 竖屏默认
            fps: 30,
            bitrate: "8000k".into(),
            container: "mp4".into(),
            codec: "h264".into(),
            four_strategy: ExportStrategy::Single,
        }
    }
}

/// 媒体文件 (mp4 / mov / wav / mp3)。
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct MediaFile {
    pub path: PathBuf,
    pub duration_seconds: f64,
    pub resolution: Option<String>, // 仅视频有意义
    pub codec: Option<String>,
    pub file_size_bytes: u64,
    pub import_time: DateTime<Utc>,
}

/// 时间线。
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Default)]
pub struct Timeline {
    pub tracks: Vec<Track>,
}

/// 时间线轨道 (单视频轨 / 多音频轨 / 字幕轨)。
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct Track {
    pub id: String,
    pub kind: TrackKind,
    pub clips: Vec<Clip>,
}

/// 轨道类型。
#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq)]
#[serde(rename_all = "kebab-case")]
pub enum TrackKind {
    Video,
    Audio,
    Subtitle,
}

/// 时间线片段。
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct Clip {
    pub id: String,
    pub media_ref: PathBuf,     // 引用的 MediaFile.path
    pub start_seconds: f64,      // 在时间线上的起点
    pub in_seconds: f64,         // 在 MediaFile 中的入点
    pub out_seconds: f64,        // 在 MediaFile 中的出点
    pub volume: Option<f32>,     // 仅 audio 有意义
}

/// 第一人称叙述脚本的一段。
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct ScriptSegment {
    pub id: String,
    pub step_index: u8, // 0..=4 (对应 5 步流水线)
    pub text: String,   // 中文人称
    pub emotion: Option<String>,
    pub start_seconds: Option<f64>,
    pub end_seconds: Option<f64>,
}

/// 一次导出记录。
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct ExportRecord {
    pub id: String,
    pub strategy: ExportStrategy,
    pub output_path: PathBuf,
    pub started_at: DateTime<Utc>,
    pub finished_at: Option<DateTime<Utc>>,
    pub success: bool,
}

/// 4 种导出策略 (与 v2.4 Python `app/services/export/four_strategy.py` 1:1)。
#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq)]
#[serde(rename_all = "kebab-case")]
pub enum ExportStrategy {
    /// 单条影视做第一人称叙述 (常规)
    Single,
    /// 多素材拼接 (视频拼贴 / 蒙太奇)
    Concat,
    /// 批量并行 (同模板多个 source)
    Batch,
    /// 整季系列 (多集 / 多人物 / 跨多期)
    Series,
}

/// 4 策略的人类可读标签 (zh-CN)
pub fn strategy_label(s: ExportStrategy) -> &'static str {
    match s {
        ExportStrategy::Single => "单条",
        ExportStrategy::Concat => "拼接",
        ExportStrategy::Batch => "批量",
        ExportStrategy::Series => "整季系列",
    }
}

/// 仅用作示例,后续 M3 替换为 `uuid` crate 依赖。
fn uuid_v4_like() -> String {
    use std::time::{SystemTime, UNIX_EPOCH};
    let nanos = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_nanos())
        .unwrap_or(0);
    format!("proj-{:x}", nanos)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn project_default_is_serde_compatible() {
        let p = Project::default();
        let json = serde_json::to_string(&p).unwrap();
        let back: Project = serde_json::from_str(&json).unwrap();
        assert_eq!(p, back);
    }

    #[test]
    fn four_strategy_serde_roundtrip() {
        for s in [
            ExportStrategy::Single,
            ExportStrategy::Concat,
            ExportStrategy::Batch,
            ExportStrategy::Series,
        ] {
            let j = serde_json::to_string(&s).unwrap();
            let back: ExportStrategy = serde_json::from_str(&j).unwrap();
            assert_eq!(s, back);
        }
    }

    #[test]
    fn strategy_label_covers_all() {
        for s in [
            ExportStrategy::Single,
            ExportStrategy::Concat,
            ExportStrategy::Batch,
            ExportStrategy::Series,
        ] {
            // 永远是有标签的 (不 panic)
            let _ = strategy_label(s);
        }
    }
}
