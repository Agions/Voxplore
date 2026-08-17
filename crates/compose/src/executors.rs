//! vynaro-compose · 流水线执行器矩阵
//!
//! ## 依赖注入
//! [`PipelineDeps`] 集中持有 LLM / TTS / FFmpeg / workdir,
//! 由 Tauri command 层按 ConfigService 快照构造。
//!
//! ## 降级策略
//! - ffmpeg 缺失: 探针/场景检测/导出降级为明确错误 (前端提示安装)
//! - llm/tts 未配置密钥: 返回 Config 错误 (前端引导到设置页)

use std::path::PathBuf;
use std::sync::Arc;

use async_trait::async_trait;
use vynaro_detect::Ffmpeg;
use vynaro_domain::{ExportRecord, Project, ScriptSegment};
use vynaro_script::{LlmProvider, LlmRequest};
use vynaro_voice::{TtsEngine, TtsRequest};

use crate::{StepExecutor, VynaroError, VynaroResult};

// ════════════════════════════════════════════════════════════════════════
// 依赖注入
// ════════════════════════════════════════════════════════════════════════

/// 流水线运行时依赖 (由 Tauri command 层构造)。
pub struct PipelineDeps {
    /// LLM provider (None = 未配置,脚本生成步报 Config 错误)
    pub llm: Option<Box<dyn LlmProvider>>,
    /// TTS 引擎 (None = 未配置,配音步报 Config 错误)
    pub tts: Option<Box<dyn TtsEngine>>,
    /// FFmpeg 包装 (None = 未安装,探针/导出步报 Ffmpeg 错误)
    pub ffmpeg: Option<Arc<Ffmpeg>>,
    /// 项目工作目录 (audio/captions/export 子目录)
    pub workdir: PathBuf,
}

impl std::fmt::Debug for PipelineDeps {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("PipelineDeps")
            .field("llm", &self.llm.as_ref().map(|l| l.kind()))
            .field("tts", &self.tts.as_ref().map(|t| t.kind()))
            .field("ffmpeg", &self.ffmpeg.is_some())
            .field("workdir", &self.workdir)
            .finish()
    }
}

/// 构造标准 7 步执行器列表 (与 STEPS 常量 1:1)。
pub fn default_executors(deps: Arc<PipelineDeps>) -> Vec<Box<dyn StepExecutor>> {
    vec![
        Box::new(IngestStep { deps: deps.clone() }), // 0: intake
        Box::new(SceneSplitStep { deps: deps.clone() }), // 1: detect
        Box::new(ScriptGenStep { deps: deps.clone() }), // 2: script
        Box::new(VoiceCaptionsStep { deps: deps.clone() }), // 3: voice
        Box::new(SubtitleStep { deps: deps.clone() }), // 4: subtitle
        Box::new(ComposeStep { deps: deps.clone() }), // 5: compose
        Box::new(ExportStep { deps }),               // 6: export
    ]
}

// ════════════════════════════════════════════════════════════════════════
// Step 0 · 素材导入
// ════════════════════════════════════════════════════════════════════════

#[derive(Debug)]
pub struct IngestStep {
    pub deps: Arc<PipelineDeps>,
}

#[async_trait]
impl StepExecutor for IngestStep {
    fn step_index(&self) -> u8 {
        0
    }

    async fn execute(&self, project: &mut Project) -> VynaroResult<()> {
        if project.media_files.is_empty() {
            return Err(VynaroError::Project(
                "请先在素材页导入至少一个视频文件".into(),
            ));
        }

        // 工作目录
        for sub in ["audio", "captions", "export"] {
            tokio::fs::create_dir_all(self.deps.workdir.join(sub)).await?;
        }

        // 逐个校验 + 探针补全元数据
        for mf in project.media_files.iter_mut() {
            if !mf.path.exists() {
                return Err(VynaroError::Project(format!(
                    "素材文件不存在: {}",
                    mf.path.display()
                )));
            }
            mf.file_size_bytes = tokio::fs::metadata(&mf.path).await?.len();
            if let Some(ff) = &self.deps.ffmpeg {
                if let Ok(probe) = ff.probe(&mf.path).await {
                    mf.duration_seconds = probe.duration_seconds;
                    mf.resolution = Some(format!("{}x{}", probe.width, probe.height));
                    mf.codec = probe.video_codec;
                }
            }
        }
        Ok(())
    }
}

// ════════════════════════════════════════════════════════════════════════
// Step 1 · 场景拆分
// ════════════════════════════════════════════════════════════════════════

#[derive(Debug)]
pub struct SceneSplitStep {
    pub deps: Arc<PipelineDeps>,
}

#[async_trait]
impl StepExecutor for SceneSplitStep {
    fn step_index(&self) -> u8 {
        1
    }

    async fn execute(&self, project: &mut Project) -> VynaroResult<()> {
        let media = &project.media_files[0];
        let duration = if media.duration_seconds > 0.0 {
            media.duration_seconds
        } else {
            60.0
        };

        // 场景切点 (ffmpeg 可用时;最多 12 个切点防止碎片化)
        let mut boundaries: Vec<f64> = vec![0.0];
        if let Some(ff) = &self.deps.ffmpeg {
            if let Ok(cuts) = ff.detect_scenes(&media.path, 0.35).await {
                for c in cuts.into_iter().take(12) {
                    if c > 0.5 && c < duration - 0.5 {
                        boundaries.push(c);
                    }
                }
            }
        }
        boundaries.push(duration);
        boundaries.sort_by(|a, b| a.partial_cmp(b).unwrap_or(std::cmp::Ordering::Equal));
        boundaries.dedup();

        // 生成场景占位脚本 (Step 2 会替换 text)
        project.scripts = boundaries
            .windows(2)
            .enumerate()
            .map(|(i, w)| ScriptSegment {
                id: format!("scene-{:02}", i),
                step_index: 1,
                text: format!("场景 {}", i + 1),
                emotion: None,
                start_seconds: Some(w[0]),
                end_seconds: Some(w[1]),
                is_hook: None,
                hook_style: None,
            })
            .collect();
        Ok(())
    }
}

// ════════════════════════════════════════════════════════════════════════
// Step 2 · 脚本生成 (LLM 第一人称叙述)
// ════════════════════════════════════════════════════════════════════════

#[derive(Debug)]
pub struct ScriptGenStep {
    pub deps: Arc<PipelineDeps>,
}

impl ScriptGenStep {
    /// 从 LLM 输出解析脚本段。支持 JSON 数组 / markdown fence 包裹。
    fn parse_segments(content: &str) -> Option<Vec<(String, Option<String>)>> {
        let cleaned = content
            .trim()
            .trim_start_matches("```json")
            .trim_start_matches("```")
            .trim_end_matches("```")
            .trim();
        let v: serde_json::Value = serde_json::from_str(cleaned).ok()?;
        let arr = v.as_array()?;
        let mut out = Vec::new();
        for item in arr {
            let text = item["text"].as_str()?.to_string();
            if text.trim().is_empty() {
                continue;
            }
            let emotion = item["emotion"].as_str().map(String::from);
            out.push((text, emotion));
        }
        if out.is_empty() {
            None
        } else {
            Some(out)
        }
    }
}

#[async_trait]
impl StepExecutor for ScriptGenStep {
    fn step_index(&self) -> u8 {
        2
    }

    async fn execute(&self, project: &mut Project) -> VynaroResult<()> {
        let llm = self.deps.llm.as_ref().ok_or_else(|| {
            VynaroError::Config("未配置 LLM 提供商或 API 密钥,请先到设置页填写".into())
        })?;

        // 场景摘要 → prompt
        let scenes_desc = project
            .scripts
            .iter()
            .map(|s| {
                format!(
                    "- 场景 ({}s ~ {}s)",
                    s.start_seconds.unwrap_or(0.0),
                    s.end_seconds.unwrap_or(0.0)
                )
            })
            .collect::<Vec<_>>()
            .join("\n");

        let req = LlmRequest {
            system: "你是一位短视频第一人称叙述编剧。输出严格 JSON 数组,\
                     每项 {\"text\": 中文叙述, \"emotion\": 情绪标签}。\
                     不要输出任何 JSON 之外的文字。"
                .into(),
            user: format!(
                "项目「{}」共有 {} 个场景:\n{}\n\
                 请为每个场景写一段第一人称中文旁白 (每段 30-60 字),带情绪标签。",
                project.name,
                project.scripts.len(),
                scenes_desc
            ),
            model: None,
            max_tokens: Some(2048),
            temperature: Some(0.7),
            stream: false,
            images_base64: vec![],
        };

        let resp = llm.chat(&req).await?;
        let parsed = Self::parse_segments(&resp.content);

        match parsed {
            Some(segs) => {
                for (i, seg) in project.scripts.iter_mut().enumerate() {
                    if let Some((text, emotion)) = segs.get(i) {
                        seg.text = text.clone();
                        seg.emotion = emotion.clone();
                    }
                    seg.step_index = 2;
                }
            }
            None => {
                // 降级: 整段文本作为单脚本
                tracing::warn!("LLM 输出无法解析为 JSON,降级为单段脚本");
                let timing = project.scripts.first().map(|s| {
                    (
                        s.start_seconds.unwrap_or(0.0),
                        s.end_seconds.unwrap_or(60.0),
                    )
                });
                project.scripts = vec![ScriptSegment {
                    id: "script-full".into(),
                    step_index: 2,
                    text: resp.content.trim().to_string(),
                    emotion: None,
                    start_seconds: Some(timing.map(|t| t.0).unwrap_or(0.0)),
                    end_seconds: Some(timing.map(|t| t.1).unwrap_or(60.0)),
                    is_hook: None,
                    hook_style: None,
                }];
            }
        }
        Ok(())
    }
}

// ════════════════════════════════════════════════════════════════════════
// Step 3 · 配音 + 字幕
// ════════════════════════════════════════════════════════════════════════

#[derive(Debug)]
pub struct VoiceCaptionsStep {
    pub deps: Arc<PipelineDeps>,
}

#[async_trait]
impl StepExecutor for VoiceCaptionsStep {
    fn step_index(&self) -> u8 {
        3
    }

    async fn execute(&self, project: &mut Project) -> VynaroResult<()> {
        let tts = self.deps.tts.as_ref().ok_or_else(|| {
            VynaroError::Config("未配置 TTS 引擎,请先到设置页选择配音引擎".into())
        })?;

        let total = project
            .media_files
            .first()
            .map(|m| {
                if m.duration_seconds > 0.0 {
                    m.duration_seconds
                } else {
                    60.0
                }
            })
            .unwrap_or(60.0);

        // 按文本长度分配时间 (若脚本没带时间)
        let total_chars: usize = project.scripts.iter().map(|s| s.text.chars().count()).sum();
        let script_count = project.scripts.len().max(1);
        let mut cursor = 0.0_f64;

        let mut srt_entries: Vec<(f64, f64, String)> = Vec::new();
        for (i, seg) in project.scripts.iter_mut().enumerate() {
            let (start, end) = match (seg.start_seconds, seg.end_seconds) {
                (Some(s), Some(e)) if e > s => (s, e),
                _ => {
                    let share = if total_chars > 0 {
                        total * (seg.text.chars().count() as f64 / total_chars as f64)
                    } else {
                        total / script_count as f64
                    };
                    let s = cursor;
                    cursor += share;
                    (s, cursor)
                }
            };
            seg.start_seconds = Some(start);
            seg.end_seconds = Some(end);
            seg.step_index = 3;

            let out = self.deps.workdir.join(format!("audio/seg_{i:02}.mp3"));
            tts.synthesize(&TtsRequest {
                text: seg.text.clone(),
                voice: None,
                rate_percent: 0,
                output_path: out,
            })
            .await?;

            srt_entries.push((start, end, seg.text.clone()));
        }

        // SRT 字幕落盘
        let srt = vynaro_detect::build_srt(&srt_entries);
        let srt_path = self.deps.workdir.join("captions/captions.srt");
        tokio::fs::create_dir_all(self.deps.workdir.join("captions")).await?;
        tokio::fs::write(&srt_path, srt).await?;
        Ok(())
    }
}

// ════════════════════════════════════════════════════════════════════════
// Step 4 · 导出发布
// ════════════════════════════════════════════════════════════════════════
// Step 4 · 字幕合成 (VAD 对齐字幕时间轴)
// ════════════════════════════════════════════════════════════════════════

/// 字幕合成步骤——字幕生成通过前端 subtitleIpc 触发，
/// 流水线这里仅做状态推进。
#[derive(Debug)]
pub struct SubtitleStep {
    pub deps: Arc<PipelineDeps>,
}

#[async_trait]
impl StepExecutor for SubtitleStep {
    fn step_index(&self) -> u8 {
        4
    }

    async fn execute(&self, _project: &mut Project) -> VynaroResult<()> {
        // 字幕生成通过前端 subtitleIpc.generate 独立完成，
        // 此处仅负责流水线状态标记为 Done。
        tracing::info!("[subtitle] 字幕合成步骤标记为完成");
        Ok(())
    }
}

// ════════════════════════════════════════════════════════════════════════
// Step 5 · 画面对齐 (Compose & Sync)
// ════════════════════════════════════════════════════════════════════════

/// 画面对齐步骤——音画开工通过前端 Step6ComposePanel 触发，
/// 流水线这里仅做状态标记。
#[derive(Debug)]
pub struct ComposeStep {
    pub deps: Arc<PipelineDeps>,
}

#[async_trait]
impl StepExecutor for ComposeStep {
    fn step_index(&self) -> u8 {
        5
    }

    async fn execute(&self, project: &mut Project) -> VynaroResult<()> {
        tracing::info!(
            "[compose] 正在为项目「{}」执行画面与音频智能对齐...",
            project.name
        );

        let compose_dir = self.deps.workdir.join("compose");
        tokio::fs::create_dir_all(&compose_dir).await?;

        if let Some(ff) = &self.deps.ffmpeg {
            if let Some(media) = project.media_files.first() {
                let narration = self.deps.workdir.join("audio/seg_00.mp3");
                let aligned = compose_dir.join("aligned.mp4");
                if narration.exists() {
                    if let Err(e) = ff.mix_narration(&media.path, &narration, &aligned).await {
                        tracing::warn!("[compose] 混流失败（将进行回退）: {e}");
                    } else {
                        tracing::info!("[compose] 画面与音频轨道对齐完成: {}", aligned.display());
                    }
                }
            }
        }

        tracing::info!("[compose] 画面对齐步骤标记为完成");
        Ok(())
    }
}

// ════════════════════════════════════════════════════════════════════════
// Step 6 · 导出发布

#[derive(Debug)]
pub struct ExportStep {
    pub deps: Arc<PipelineDeps>,
}

impl ExportStep {
    /// 解析 "1080x1920" → (1080, 1920)
    fn parse_resolution(s: &str) -> (u32, u32) {
        let mut parts = s.split('x');
        let w = parts.next().and_then(|x| x.parse().ok()).unwrap_or(1080);
        let h = parts.next().and_then(|x| x.parse().ok()).unwrap_or(1920);
        (w, h)
    }
}

#[async_trait]
impl StepExecutor for ExportStep {
    fn step_index(&self) -> u8 {
        6
    }

    async fn execute(&self, project: &mut Project) -> VynaroResult<()> {
        let ff = self.deps.ffmpeg.as_ref().ok_or_else(|| {
            VynaroError::Ffmpeg("ffmpeg 未安装或不在 PATH 中,无法导出成片".into())
        })?;

        let media = project
            .media_files
            .first()
            .ok_or_else(|| VynaroError::Project("没有可导出的素材".into()))?;

        let export_dir = self.deps.workdir.join("export");
        tokio::fs::create_dir_all(&export_dir).await?;
        let started_at = chrono::Utc::now();

        // ① 竖屏画布
        let vertical = export_dir.join("vertical.mp4");
        let (w, h) = Self::parse_resolution(&project.settings.resolution);
        ff.scale_pad_vertical(
            &media.path,
            &vertical,
            w,
            h,
            project.settings.fps,
            &project.settings.bitrate,
        )
        .await?;

        // ② 字幕烧录 (若存在)
        let srt = self.deps.workdir.join("captions/captions.srt");
        let captioned = export_dir.join("captioned.mp4");
        let base = if srt.exists() {
            ff.burn_captions(&vertical, &srt, &captioned).await?;
            captioned
        } else {
            vertical
        };

        // ③ 旁白混流 (若存在第一段配音)
        let narration = self.deps.workdir.join("audio/seg_00.mp3");
        let final_path = export_dir.join(format!("{}.mp4", project.name));
        if narration.exists() {
            ff.mix_narration(&base, &narration, &final_path).await?;
        } else {
            tokio::fs::rename(&base, &final_path).await?;
        }

        // ④ 导出记录
        project.exports.push(ExportRecord {
            id: format!("export-{}", chrono::Utc::now().timestamp()),
            strategy: project.settings.four_strategy,
            output_path: final_path,
            started_at,
            finished_at: Some(chrono::Utc::now()),
            success: true,
        });
        Ok(())
    }
}

// ════════════════════════════════════════════════════════════════════════
// 测试 (全部离线,不依赖 ffmpeg/网络)
// ════════════════════════════════════════════════════════════════════════

#[cfg(test)]
mod tests {
    use super::*;
    use vynaro_domain::MediaFile;

    fn deps(tmp: &str) -> Arc<PipelineDeps> {
        Arc::new(PipelineDeps {
            llm: None,
            tts: None,
            ffmpeg: None,
            workdir: PathBuf::from(tmp),
        })
    }

    fn project_with_media() -> Project {
        let mut p = Project::default();
        p.media_files.push(MediaFile {
            path: PathBuf::from("/tmp/vynaro-test-dummy.mp4"),
            duration_seconds: 30.0,
            resolution: None,
            codec: None,
            file_size_bytes: 0,
            import_time: chrono::Utc::now(),
        });
        p
    }

    #[tokio::test]
    async fn ingest_rejects_empty_media() {
        let step = IngestStep {
            deps: deps("/tmp/sf-ingest-test"),
        };
        let mut p = Project::default();
        let r = step.execute(&mut p).await;
        assert!(matches!(r, Err(VynaroError::Project(_))));
    }

    #[tokio::test]
    async fn ingest_rejects_missing_file() {
        let step = IngestStep {
            deps: deps("/tmp/sf-ingest-test2"),
        };
        let mut p = project_with_media();
        let r = step.execute(&mut p).await;
        assert!(matches!(r, Err(VynaroError::Project(_))));
    }

    #[tokio::test]
    async fn scene_split_fallback_without_ffmpeg() {
        // 无 ffmpeg → 单场景覆盖全长
        let step = SceneSplitStep {
            deps: deps("/tmp/sf-scene-test"),
        };
        let mut p = project_with_media();
        step.execute(&mut p).await.unwrap();
        assert_eq!(p.scripts.len(), 1);
        assert_eq!(p.scripts[0].start_seconds, Some(0.0));
        assert_eq!(p.scripts[0].end_seconds, Some(30.0));
    }

    #[tokio::test]
    async fn script_gen_requires_llm() {
        let step = ScriptGenStep {
            deps: deps("/tmp/sf-script-test"),
        };
        let mut p = project_with_media();
        let r = step.execute(&mut p).await;
        assert!(matches!(r, Err(VynaroError::Config(_))));
    }

    #[test]
    fn parse_segments_json_and_fence() {
        let raw =
            r#"[{"text": "第一段旁白", "emotion": "平静"}, {"text": "第二段", "emotion": "激动"}]"#;
        let segs = ScriptGenStep::parse_segments(raw).unwrap();
        assert_eq!(segs.len(), 2);

        let fenced = format!("```json\n{raw}\n```");
        assert_eq!(ScriptGenStep::parse_segments(&fenced).unwrap().len(), 2);

        assert!(ScriptGenStep::parse_segments("不是 JSON").is_none());
    }

    #[tokio::test]
    async fn voice_requires_tts() {
        let step = VoiceCaptionsStep {
            deps: deps("/tmp/sf-voice-test"),
        };
        let mut p = project_with_media();
        let r = step.execute(&mut p).await;
        assert!(matches!(r, Err(VynaroError::Config(_))));
    }

    #[tokio::test]
    async fn export_requires_ffmpeg() {
        let step = ExportStep {
            deps: deps("/tmp/sf-export-test"),
        };
        let mut p = project_with_media();
        let r = step.execute(&mut p).await;
        assert!(matches!(r, Err(VynaroError::Ffmpeg(_))));
    }

    #[test]
    fn parse_resolution_ok() {
        assert_eq!(ExportStep::parse_resolution("1080x1920"), (1080, 1920));
        assert_eq!(ExportStep::parse_resolution("bad"), (1080, 1920));
    }

    #[test]
    fn default_executors_order() {
        let execs = default_executors(deps("/tmp/sf-order-test"));
        assert_eq!(execs.len(), 7);
        for (i, e) in execs.iter().enumerate() {
            assert_eq!(e.step_index(), i as u8);
        }
    }
}
