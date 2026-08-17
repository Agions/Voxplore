//! splicr-storage v1.0.0  · 素材资产管理服务
//!
//! ## 责任范围
//! - `assets_scan`        : 扫描目录,按 MIME 白名单返回可导入素材
//! - `assets_metadata`    : ffprobe 抽 metadata (duration / resolution / codec / size)
//! - `assets_thumbnail`   : ffmpeg 抽首帧 JPEG,落盘到 `~/.cache/splicr/thumb/`
//! - `assets_search`      : 在项目已有 media_files 中按 name/path substring 过滤
//!
//! ## 安全
//! - 所有 IO 失败统一 `SplicrError::Io`
//! - 缩略图路径用 `<cache_dir>/thumb/<sha256(path)>.jpg` 防目录穿越
//! - 扫描递归深度上限 8,文件大小上限 2 GB

use std::path::{Path, PathBuf};

use serde::{Deserialize, Serialize};
use thiserror::Error;
use walkdir::WalkDir;

use splicr_detect::{parse_probe_json, Ffmpeg, FfmpegProbe};

// ════════════════════════════════════════════════════════════════════════
// 错误
// ════════════════════════════════════════════════════════════════════════

#[derive(Debug, Error)]
pub enum AssetError {
    #[error("路径不存在: {0}")]
    NotFound(String),
    #[error("非媒体文件: {0}")]
    NotMedia(String),
    #[error("ffmpeg 不可用")]
    FfmpegUnavailable,
    #[error("ffprobe JSON 解析失败: {0}")]
    ProbeParse(String),
    #[error("缩略图生成失败: {0}")]
    Thumbnail(String),
    #[error("IO: {0}")]
    Io(#[from] std::io::Error),
    #[error("splicr 错误: {0}")]
    Core(#[from] splicr_core::error::SplicrError),
}

pub type AssetResult<T> = Result<T, AssetError>;

// ════════════════════════════════════════════════════════════════════════
// 公开类型
// ════════════════════════════════════════════════════════════════════════

/// 扫描结果中的单个素材条目
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct AssetEntry {
    pub path: String,
    pub size_bytes: u64,
    pub mime: String,
    pub kind: AssetKind,
}

#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "snake_case")]
pub enum AssetKind {
    Video,
    Audio,
    Image,
    Subtitle,
    Other,
}

impl AssetKind {
    /// 从 MIME 推断类别
    pub fn from_mime(mime: &str) -> Self {
        if mime.starts_with("video/") {
            Self::Video
        } else if mime.starts_with("audio/") {
            Self::Audio
        } else if mime.starts_with("image/") {
            Self::Image
        } else if mime.starts_with("text/") || mime.contains("subtitle") {
            Self::Subtitle
        } else {
            Self::Other
        }
    }
}

/// 扫描结果汇总
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct ScanResult {
    pub dir: String,
    pub total: usize,
    pub entries: Vec<AssetEntry>,
    pub skipped: usize,
}

/// 缩略图生成结果
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct ThumbnailResult {
    pub source: String,
    pub thumbnail_path: String,
    pub width: u32,
    pub height: u32,
}

// ════════════════════════════════════════════════════════════════════════
// 工具
// ════════════════════════════════════════════════════════════════════════

/// MIME 白名单 (M3 后续:视频/音频/图片)
fn is_media_extension(ext: &str) -> bool {
    matches!(
        ext.to_lowercase().as_str(),
        "mp4"
            | "mov"
            | "mkv"
            | "avi"
            | "webm"
            | "flv"
            | "m4v"
            | "mp3"
            | "wav"
            | "flac"
            | "aac"
            | "ogg"
            | "m4a"
            | "jpg"
            | "jpeg"
            | "png"
            | "webp"
            | "gif"
            | "bmp"
            | "srt"
            | "vtt"
            | "ass"
            | "ssa"
    )
}

fn detect_mime(path: &Path) -> String {
    mime_guess::from_path(path)
        .first_or_octet_stream()
        .to_string()
}

fn sha256_hex(s: &str) -> String {
    use sha2::{Digest, Sha256};
    let mut h = Sha256::new();
    h.update(s.as_bytes());
    format!("{:x}", h.finalize())
}

/// 获取缩略图缓存根目录
fn thumb_cache_dir() -> AssetResult<PathBuf> {
    let base = dirs::cache_dir()
        .or_else(dirs::data_local_dir)
        .ok_or_else(|| AssetError::Io(std::io::Error::other("无法获取 cache dir")))?;
    let dir = base.join("splicr").join("thumb");
    std::fs::create_dir_all(&dir)?;
    Ok(dir)
}

// ════════════════════════════════════════════════════════════════════════
// AssetService · 业务方法
// ════════════════════════════════════════════════════════════════════════

/// 素材服务
///
/// 设计:
/// - 纯函数式服务,无内部状态(查询时 IO,完成即返回)
/// - 由 Tauri command 包装调用
/// - 不持有 ProjectService,扫描/缩略图/元数据都不依赖具体项目
#[derive(Debug, Default, Clone)]
pub struct AssetService;

impl AssetService {
    pub fn new() -> Self {
        Self
    }

    /// 扫描目录,返回所有可作为素材的文件
    ///
    /// - `recursive` = true 时递归 8 层深度
    /// - 按扩展名白名单过滤 (视频/音频/图片/字幕)
    /// - 单文件 > 2 GB 跳过 (避免占内存)
    pub fn scan(&self, dir: &str, recursive: bool) -> AssetResult<ScanResult> {
        let p = Path::new(dir);
        if !p.exists() {
            return Err(AssetError::NotFound(dir.into()));
        }

        let walker = if recursive {
            WalkDir::new(p).max_depth(8)
        } else {
            WalkDir::new(p).max_depth(1)
        };

        let mut entries = Vec::new();
        let mut skipped = 0;
        for ent in walker.into_iter().filter_map(Result::ok) {
            let path = ent.path();
            if !path.is_file() {
                continue;
            }
            let ext = path
                .extension()
                .and_then(|e| e.to_str())
                .unwrap_or("")
                .to_string();
            if !is_media_extension(&ext) {
                continue;
            }
            let meta = match std::fs::metadata(path) {
                Ok(m) => m,
                Err(_) => {
                    skipped += 1;
                    continue;
                }
            };
            let size = meta.len();
            if size > 2 * 1024 * 1024 * 1024 {
                skipped += 1;
                continue;
            }
            let mime = detect_mime(path);
            let kind = AssetKind::from_mime(&mime);
            entries.push(AssetEntry {
                path: path.to_string_lossy().into_owned(),
                size_bytes: size,
                mime,
                kind,
            });
        }

        let total = entries.len();
        Ok(ScanResult {
            dir: dir.to_string(),
            total,
            entries,
            skipped,
        })
    }

    /// 提取媒体元数据
    pub async fn metadata(&self, path: &str) -> AssetResult<FfmpegProbe> {
        let p = Path::new(path);
        if !p.exists() {
            return Err(AssetError::NotFound(path.into()));
        }

        let ff = Ffmpeg::discover().map_err(|_| AssetError::FfmpegUnavailable)?;

        // 跑 `ffprobe -v error -print_format json -show_format -show_streams <path>`
        let output = tokio::process::Command::new(&ff.ffprobe_bin)
            .arg("-v")
            .arg("error")
            .arg("-print_format")
            .arg("json")
            .arg("-show_format")
            .arg("-show_streams")
            .arg(p)
            .output()
            .await?;

        if !output.status.success() {
            let stderr = String::from_utf8_lossy(&output.stderr);
            return Err(AssetError::ProbeParse(stderr.into_owned()));
        }

        let json = String::from_utf8_lossy(&output.stdout);
        let probe = parse_probe_json(&json).map_err(|e| AssetError::ProbeParse(e.to_string()))?;
        Ok(probe)
    }

    /// 生成缩略图 (首帧 JPEG)
    ///
    /// - 输出到 `<cache_dir>/thumb/<sha256(path)>.jpg`
    /// - 用 ffmpeg 抽 `-ss 00:00:01` (1 秒处),避免黑屏
    /// - 失败时返回 `AssetError::Thumbnail`
    pub async fn thumbnail(&self, path: &str, width: u32) -> AssetResult<ThumbnailResult> {
        let p = Path::new(path);
        if !p.exists() {
            return Err(AssetError::NotFound(path.into()));
        }

        let ff = Ffmpeg::discover().map_err(|_| AssetError::FfmpegUnavailable)?;
        let dir = thumb_cache_dir()?;
        let out = dir.join(format!("{}.jpg", sha256_hex(path)));

        // ffmpeg -ss 1 -i <path> -vframes 1 -vf scale=<w>:-1 -y <out>
        let w_str = width.to_string();
        let status = tokio::process::Command::new(&ff.ffmpeg_bin)
            .arg("-ss")
            .arg("1")
            .arg("-i")
            .arg(p)
            .arg("-vframes")
            .arg("1")
            .arg("-vf")
            .arg(format!("scale={w_str}:-1"))
            .arg("-y")
            .arg(&out)
            .output()
            .await?;

        if !status.status.success() {
            let stderr = String::from_utf8_lossy(&status.stderr);
            return Err(AssetError::Thumbnail(stderr.into_owned()));
        }

        // 读取生成图尺寸 (用 std::fs::metadata 不够,这里简化返回 width)
        let _ = std::fs::metadata(&out)?;
        Ok(ThumbnailResult {
            source: path.into(),
            thumbnail_path: out.to_string_lossy().into_owned(),
            width,
            height: 0,
        })
    }

    /// 在已有 media 列表中按 substring 过滤
    pub fn search(&self, media_paths: &[String], pattern: &str) -> Vec<String> {
        if pattern.is_empty() {
            return media_paths.to_vec();
        }
        let pat = pattern.to_lowercase();
        media_paths
            .iter()
            .filter(|p| p.to_lowercase().contains(&pat))
            .cloned()
            .collect()
    }
}

// ════════════════════════════════════════════════════════════════════════
// 单元测试
// ════════════════════════════════════════════════════════════════════════

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn asset_kind_from_mime_classifies() {
        assert_eq!(AssetKind::from_mime("video/mp4"), AssetKind::Video);
        assert_eq!(AssetKind::from_mime("audio/mpeg"), AssetKind::Audio);
        assert_eq!(AssetKind::from_mime("image/png"), AssetKind::Image);
        assert_eq!(AssetKind::from_mime("text/plain"), AssetKind::Subtitle);
        assert_eq!(
            AssetKind::from_mime("application/octet-stream"),
            AssetKind::Other
        );
    }

    #[test]
    fn media_extension_whitelist() {
        assert!(is_media_extension("mp4"));
        assert!(is_media_extension("MP4"));
        assert!(!is_media_extension("exe"));
        assert!(!is_media_extension(""));
    }

    #[test]
    fn sha256_is_deterministic() {
        let a = sha256_hex("/tmp/foo.mp4");
        let b = sha256_hex("/tmp/foo.mp4");
        let c = sha256_hex("/tmp/bar.mp4");
        assert_eq!(a, b);
        assert_ne!(a, c);
        assert_eq!(a.len(), 64); // 32 bytes hex
    }

    #[test]
    fn search_empty_pattern_returns_all() {
        let svc = AssetService::new();
        let media = vec!["/a.mp4".into(), "/b.mp4".into()];
        assert_eq!(svc.search(&media, ""), media);
    }

    #[test]
    fn search_substring_case_insensitive() {
        let svc = AssetService::new();
        let media = vec![
            "/Users/Me/Video.mp4".into(),
            "/tmp/AUDIO.mp3".into(),
            "/Users/Me/image.png".into(),
        ];
        let r = svc.search(&media, "VIDEO");
        assert_eq!(r, vec!["/Users/Me/Video.mp4".to_string()]);
    }

    #[test]
    fn scan_nonexistent_dir_returns_error() {
        let svc = AssetService::new();
        let r = svc.scan("/this/does/not/exist/zzz", false);
        assert!(matches!(r, Err(AssetError::NotFound(_))));
    }

    #[test]
    fn scan_current_dir_filters_non_media() {
        let svc = AssetService::new();
        let r = svc.scan(".", false).unwrap();
        // src/ 下没有 mp4 / png 等,主要是 .rs;total 应该为 0
        assert_eq!(r.total, 0);
    }
}
