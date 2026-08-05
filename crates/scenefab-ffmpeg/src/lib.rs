//! scenefab-ffmpeg v2.5.0 · FFmpeg 包装层 (M3.2 完整实现)
//!
//! ## 责任范围
//! - 二进制发现 (`ffmpeg` / `ffprobe` PATH 探测)
//! - 探针 (时长 / 分辨率 / 编码)
//! - 场景检测 (select+showinfo 滤镜,解析 pts_time)
//! - 音轨抽取 / 竖屏 scale+pad / 字幕烧录 / 配音混流 / 多段拼接
//! - 进度解析 (stderr `time=HH:MM:SS.xx` → 百分比回调)
//!
//! ## 与 v2.4 Python 对应
//! - `app/services/video/ffmpeg_runner.py` (白名单命令 + stderr 捕获)
//!
//! ## 安全设计
//! - 所有命令为"固定参数构造",不经过 shell,不接受任意用户字符串拼接
//! - 失败统一 `SceneFabError::Ffmpeg(stderr tail)`

#![allow(dead_code)]

use std::path::{Path, PathBuf};
use std::process::Stdio;

use scenefab_core::error::{SceneFabError, SceneFabResult};
use serde::{Deserialize, Serialize};

// ════════════════════════════════════════════════════════════════════════
// 数据结构
// ════════════════════════════════════════════════════════════════════════

/// ffprobe 探针结果。
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(rename_all = "camelCase")]
pub struct FfmpegProbe {
    pub duration_seconds: f64,
    pub width: u32,
    pub height: u32,
    pub video_codec: Option<String>,
    pub audio_codec: Option<String>,
    pub size_bytes: u64,
}

/// 场景切点 (秒)。
pub type SceneCut = f64;

/// FFmpeg 进度回调: (已处理秒数, 百分比 0-100 if known)
pub type ProgressFn = dyn Fn(f64, Option<u8>) + Send + Sync;

// ════════════════════════════════════════════════════════════════════════
// Ffmpeg 主结构
// ════════════════════════════════════════════════════════════════════════

#[derive(Debug, Clone)]
pub struct Ffmpeg {
    pub ffmpeg_bin: PathBuf,
    pub ffprobe_bin: PathBuf,
}

impl Ffmpeg {
    /// 从 PATH 发现 ffmpeg + ffprobe。缺失返回 `Ffmpeg` 错误。
    pub fn discover() -> SceneFabResult<Self> {
        let ffmpeg = which("ffmpeg").ok_or_else(|| {
            SceneFabError::Ffmpeg("ffmpeg 不在 PATH 中 (请先安装 ffmpeg)".into())
        })?;
        let ffprobe = which("ffprobe").ok_or_else(|| {
            SceneFabError::Ffmpeg("ffprobe 不在 PATH 中 (请先安装 ffmpeg)".into())
        })?;
        Ok(Self {
            ffmpeg_bin: ffmpeg,
            ffprobe_bin: ffprobe,
        })
    }

    /// 是否可用 (不抛错版本)
    pub fn is_available() -> bool {
        which("ffmpeg").is_some() && which("ffprobe").is_some()
    }

    /// 自定义路径构造 (测试 / sidecar 场景)
    pub fn with_bins(ffmpeg: PathBuf, ffprobe: PathBuf) -> Self {
        Self {
            ffmpeg_bin: ffmpeg,
            ffprobe_bin: ffprobe,
        }
    }

    // ── 探针 ────────────────────────────────────────────────────────────

    pub async fn probe(&self, path: &Path) -> SceneFabResult<FfmpegProbe> {
        if !path.exists() {
            return Err(SceneFabError::Ffmpeg(format!(
                "文件不存在: {}",
                path.display()
            )));
        }
        let out = self
            .run_raw(
                &self.ffprobe_bin,
                &[
                    "-v",
                    "quiet",
                    "-print_format",
                    "json",
                    "-show_format",
                    "-show_streams",
                    &path.to_string_lossy(),
                ],
                None,
                None,
            )
            .await?;
        parse_probe_json(&out)
    }

    // ── 场景检测 ────────────────────────────────────────────────────────

    /// select+showinfo 场景检测。返回切点时间列表 (秒)。
    pub async fn detect_scenes(
        &self,
        input: &Path,
        threshold: f64,
    ) -> SceneFabResult<Vec<SceneCut>> {
        let filter = format!("select='gt(scene,{threshold})',showinfo");
        let stderr = self
            .run_stderr(
                &[
                    "-i",
                    &input.to_string_lossy(),
                    "-vf",
                    &filter,
                    "-an",
                    "-f",
                    "null",
                    "-",
                ],
                None,
            )
            .await?;
        Ok(parse_scene_lines(&stderr))
    }

    // ── 转码操作 (白名单参数) ───────────────────────────────────────────

    /// 抽取音轨 → wav (16k 单声道,TTS 参考音频标准格式)
    pub async fn extract_audio(&self, input: &Path, output: &Path) -> SceneFabResult<()> {
        self.run_encode(
            &[
                "-i",
                &input.to_string_lossy(),
                "-vn",
                "-acodec",
                "pcm_s16le",
                "-ar",
                "16000",
                "-ac",
                "1",
                &output.to_string_lossy(),
            ],
            None,
        )
        .await
    }

    /// 竖屏画布: scale 适配 + pad 居中 (默认 1080x1920)
    pub async fn scale_pad_vertical(
        &self,
        input: &Path,
        output: &Path,
        width: u32,
        height: u32,
        fps: u32,
        bitrate: &str,
    ) -> SceneFabResult<()> {
        let filter = format!(
            "scale={width}:{height}:force_original_aspect_ratio=decrease,\
             pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=black,setsar=1"
        );
        self.run_encode(
            &[
                "-i",
                &input.to_string_lossy(),
                "-vf",
                &filter,
                "-r",
                &fps.to_string(),
                "-c:v",
                "libx264",
                "-b:v",
                bitrate,
                "-preset",
                "veryfast",
                "-c:a",
                "aac",
                &output.to_string_lossy(),
            ],
            None,
        )
        .await
    }

    /// SRT 字幕烧录
    pub async fn burn_captions(
        &self,
        input: &Path,
        srt: &Path,
        output: &Path,
    ) -> SceneFabResult<()> {
        // subtitles 滤镜需要转义路径中的特殊字符
        let srt_escaped = srt.to_string_lossy().replace(':', "\\:").replace('\'', "\\'");
        let filter = format!("subtitles='{srt_escaped}'");
        self.run_encode(
            &[
                "-i",
                &input.to_string_lossy(),
                "-vf",
                &filter,
                "-c:v",
                "libx264",
                "-preset",
                "veryfast",
                "-c:a",
                "copy",
                &output.to_string_lossy(),
            ],
            None,
        )
        .await
    }

    /// 配音混流: 视频 + 旁白音频 (旁白为主混,原声降低到 15%)
    pub async fn mix_narration(
        &self,
        video: &Path,
        narration: &Path,
        output: &Path,
    ) -> SceneFabResult<()> {
        self.run_encode(
            &[
                "-i",
                &video.to_string_lossy(),
                "-i",
                &narration.to_string_lossy(),
                "-filter_complex",
                "[0:a]volume=0.15[a0];[1:a]volume=1.0[a1];[a0][a1]amix=inputs=2:duration=first[aout]",
                "-map",
                "0:v",
                "-map",
                "[aout]",
                "-c:v",
                "copy",
                "-c:a",
                "aac",
                "-shortest",
                &output.to_string_lossy(),
            ],
            None,
        )
        .await
    }

    /// 多段拼接 (concat demuxer,先写 list 文件)
    pub async fn concat(
        &self,
        inputs: &[PathBuf],
        output: &Path,
    ) -> SceneFabResult<()> {
        if inputs.is_empty() {
            return Err(SceneFabError::Ffmpeg("concat: 输入列表为空".into()));
        }
        let list_path = output.with_extension("concat.txt");
        let list_content = inputs
            .iter()
            .map(|p| format!("file '{}'", p.to_string_lossy().replace('\'', "'\\''")))
            .collect::<Vec<_>>()
            .join("\n");
        tokio::fs::write(&list_path, list_content).await?;

        let result = self
            .run_encode(
                &[
                    "-f",
                    "concat",
                    "-safe",
                    "0",
                    "-i",
                    &list_path.to_string_lossy(),
                    "-c",
                    "copy",
                    &output.to_string_lossy(),
                ],
                None,
            )
            .await;
        let _ = tokio::fs::remove_file(&list_path).await;
        result
    }

    // ── 内部执行 ────────────────────────────────────────────────────────

    /// 执行编码类命令: 成功要求 exit 0,失败带 stderr tail。
    async fn run_encode(
        &self,
        args: &[&str],
        on_progress: Option<&ProgressFn>,
    ) -> SceneFabResult<()> {
        let _ = self.run_stderr(args, on_progress).await?;
        Ok(())
    }

    /// 执行 ffmpeg 并返回 stderr (进度解析内嵌)。
    async fn run_stderr(
        &self,
        args: &[&str],
        on_progress: Option<&ProgressFn>,
    ) -> Result<String, SceneFabError> {
        // -nostats 去掉 time= 行;需要进度回调时保留 stats
        let mut full: Vec<&str> = vec!["-hide_banner"];
        if on_progress.is_none() {
            full.push("-nostats");
        }
        full.extend_from_slice(args);
        Ok(self.run_raw(&self.ffmpeg_bin, &full, on_progress, None).await?)
    }

    /// 底层执行: 捕获 stdout/stderr,解析 time= 进度。exit != 0 → Err(stderr tail)。
    async fn run_raw(
        &self,
        bin: &Path,
        args: &[&str],
        on_progress: Option<&ProgressFn>,
        _total_seconds: Option<f64>,
    ) -> Result<String, RawExecError> {
        use tokio::io::AsyncReadExt;

        let mut cmd = tokio::process::Command::new(bin);
        cmd.args(args)
            .stdin(Stdio::null())
            .stdout(Stdio::piped())
            .stderr(Stdio::piped());

        let mut child = cmd.spawn().map_err(|e| RawExecError {
            stderr_tail: format!("spawn failed: {e}"),
        })?;

        // stdout / stderr 并发读取,避免管道写满死锁
        let stdout_take = child.stdout.take();
        let stderr_take = child.stderr.take();
        let on_progress_ptr: Option<&ProgressFn> = on_progress;

        let stderr_task = async move {
            let mut buf = String::new();
            if let Some(mut err) = stderr_take {
                let mut chunk = [0u8; 4096];
                loop {
                    let n = err
                        .read(&mut chunk)
                        .await
                        .map_err(|e| RawExecError {
                            stderr_tail: format!("read stderr: {e}"),
                        })?;
                    if n == 0 {
                        break;
                    }
                    let text = String::from_utf8_lossy(&chunk[..n]);
                    buf.push_str(&text);
                    if let Some(cb) = on_progress_ptr {
                        for line in text.split('\r') {
                            if let Some(sec) = extract_time_line(line) {
                                cb(sec, None);
                            }
                        }
                    }
                    // 只保留 tail 4KB
                    if buf.len() > 8192 {
                        let start = buf.len() - 4096;
                        buf = buf.split_off(start);
                    }
                }
            }
            Ok::<String, RawExecError>(buf)
        };

        let stdout_task = async move {
            let mut buf = Vec::new();
            if let Some(mut out) = stdout_take {
                out.read_to_end(&mut buf).await.map_err(|e| RawExecError {
                    stderr_tail: format!("read stdout: {e}"),
                })?;
            }
            Ok::<Vec<u8>, RawExecError>(buf)
        };

        let (stderr_res, stdout_res) = tokio::join!(stderr_task, stdout_task);
        let stderr_buf = stderr_res?;
        let stdout_buf = stdout_res?;

        let status = child.wait().await.map_err(|e| RawExecError {
            stderr_tail: format!("wait: {e}"),
        })?;

        if !status.success() {
            return Err(RawExecError {
                stderr_tail: tail_lines(&stderr_buf, 8),
            });
        }
        Ok(String::from_utf8_lossy(&stdout_buf).into_owned())
    }
}

#[derive(Debug)]
struct RawExecError {
    stderr_tail: String,
}

impl From<RawExecError> for SceneFabError {
    fn from(e: RawExecError) -> Self {
        SceneFabError::Ffmpeg(e.stderr_tail)
    }
}

// ════════════════════════════════════════════════════════════════════════
// 解析 helpers (可单测,不依赖 ffmpeg 二进制)
// ════════════════════════════════════════════════════════════════════════

/// 解析 ffprobe -print_format json 输出
pub fn parse_probe_json(json: &str) -> SceneFabResult<FfmpegProbe> {
    let v: serde_json::Value = serde_json::from_str(json)
        .map_err(|e| SceneFabError::Ffmpeg(format!("ffprobe JSON 解析失败: {e}")))?;

    let duration = v["format"]["duration"]
        .as_str()
        .and_then(|s| s.parse::<f64>().ok())
        .unwrap_or(0.0);
    let size = v["format"]["size"].as_str().and_then(|s| s.parse().ok()).unwrap_or(0);

    let mut width = 0u32;
    let mut height = 0u32;
    let mut video_codec = None;
    let mut audio_codec = None;
    if let Some(streams) = v["streams"].as_array() {
        for s in streams {
            match s["codec_type"].as_str() {
                Some("video") if video_codec.is_none() => {
                    width = s["width"].as_u64().unwrap_or(0) as u32;
                    height = s["height"].as_u64().unwrap_or(0) as u32;
                    video_codec = s["codec_name"].as_str().map(String::from);
                }
                Some("audio") if audio_codec.is_none() => {
                    audio_codec = s["codec_name"].as_str().map(String::from);
                }
                _ => {}
            }
        }
    }

    Ok(FfmpegProbe {
        duration_seconds: duration,
        width,
        height,
        video_codec,
        audio_codec,
        size_bytes: size,
    })
}

/// 解析 showinfo 输出中的 pts_time (场景切点)
pub fn parse_scene_lines(stderr: &str) -> Vec<SceneCut> {
    let mut cuts = Vec::new();
    for line in stderr.lines() {
        if !line.contains("Parsed_showinfo") {
            continue;
        }
        if let Some(idx) = line.find("pts_time:") {
            let rest = &line[idx + "pts_time:".len()..];
            let num: String = rest
                .chars()
                .take_while(|c| c.is_ascii_digit() || *c == '.')
                .collect();
            if let Ok(t) = num.parse::<f64>() {
                cuts.push(t);
            }
        }
    }
    cuts.sort_by(|a, b| a.partial_cmp(b).unwrap_or(std::cmp::Ordering::Equal));
    cuts
}

/// 从 ffmpeg 进度行提取 `time=00:00:12.34` → 秒
pub fn extract_time_line(line: &str) -> Option<f64> {
    let idx = line.find("time=")?;
    let rest = &line[idx + 5..];
    let stamp: String = rest.chars().take_while(|c| *c != ' ').collect();
    parse_timestamp(&stamp)
}

/// `HH:MM:SS.xx` → 秒
pub fn parse_timestamp(ts: &str) -> Option<f64> {
    let parts: Vec<&str> = ts.split(':').collect();
    if parts.len() != 3 {
        return None;
    }
    let h: f64 = parts[0].parse().ok()?;
    let m: f64 = parts[1].parse().ok()?;
    let s: f64 = parts[2].parse().ok()?;
    Some(h * 3600.0 + m * 60.0 + s)
}

fn tail_lines(s: &str, n: usize) -> String {
    let lines: Vec<&str> = s.lines().filter(|l| !l.trim().is_empty()).collect();
    let start = lines.len().saturating_sub(n);
    lines[start..].join("\n")
}

/// 极简 which: PATH 探测
fn which(bin: &str) -> Option<PathBuf> {
    let path_var = std::env::var_os("PATH")?;
    for dir in std::env::split_paths(&path_var) {
        let candidate = dir.join(bin);
        if candidate.is_file() {
            return Some(candidate);
        }
    }
    None
}

/// SRT 字幕生成 helper (由 pipeline 层调用): (start, end, text) → SRT 文本
pub fn build_srt(entries: &[(f64, f64, String)]) -> String {
    let mut out = String::new();
    for (i, (start, end, text)) in entries.iter().enumerate() {
        out.push_str(&format!(
            "{}\n{} --> {}\n{}\n\n",
            i + 1,
            format_srt_time(*start),
            format_srt_time(*end),
            text
        ));
    }
    out
}

fn format_srt_time(sec: f64) -> String {
    let ms = (sec * 1000.0) as u64;
    let (h, rem) = (ms / 3_600_000, ms % 3_600_000);
    let (m, rem) = (rem / 60_000, rem % 60_000);
    let (s, ms) = (rem / 1000, rem % 1000);
    format!("{h:02}:{m:02}:{s:02},{ms:03}")
}

// ════════════════════════════════════════════════════════════════════════
// 测试 (不依赖 ffmpeg 二进制)
// ════════════════════════════════════════════════════════════════════════

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn parse_probe_json_full() {
        let json = r#"{
            "streams": [
                {"codec_type": "video", "codec_name": "h264", "width": 1920, "height": 1080},
                {"codec_type": "audio", "codec_name": "aac"}
            ],
            "format": {"duration": "123.456", "size": "9999"}
        }"#;
        let p = parse_probe_json(json).unwrap();
        assert_eq!(p.duration_seconds, 123.456);
        assert_eq!(p.width, 1920);
        assert_eq!(p.height, 1080);
        assert_eq!(p.video_codec.as_deref(), Some("h264"));
        assert_eq!(p.audio_codec.as_deref(), Some("aac"));
        assert_eq!(p.size_bytes, 9999);
    }

    #[test]
    fn parse_scene_lines_extracts_sorted() {
        let stderr = "[Parsed_showinfo_1 @ 0x1] n:0 pts:100 pts_time:12.5 \n\
                      [Parsed_showinfo_1 @ 0x1] n:1 pts:50 pts_time:3.2 \n\
                      unrelated line";
        let cuts = parse_scene_lines(stderr);
        assert_eq!(cuts, vec![3.2, 12.5]);
    }

    #[test]
    fn parse_timestamp_and_time_line() {
        assert_eq!(parse_timestamp("00:01:30.50"), Some(90.5));
        assert_eq!(extract_time_line("frame=10 fps=5 time=00:00:12.34 bitrate=1x"), Some(12.34));
        assert_eq!(extract_time_line("no progress here"), None);
    }

    #[test]
    fn build_srt_format() {
        let srt = build_srt(&[(0.0, 2.5, "你好".into()), (2.5, 5.0, "世界".into())]);
        assert!(srt.contains("1\n00:00:00,000 --> 00:00:02,500\n你好"));
        assert!(srt.contains("2\n00:00:02,500 --> 00:00:05,000\n世界"));
    }

    #[tokio::test]
    async fn probe_missing_file_errors() {
        if let Ok(f) = Ffmpeg::discover() {
            let r = f.probe(Path::new("/nonexistent/video.mp4")).await;
            assert!(r.is_err());
        }
        // ffmpeg 不存在时 discover 本身就是 Err
    }
}
