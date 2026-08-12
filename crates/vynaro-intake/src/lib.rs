//! vynaro-video v1.0.0  · 视频编排核心 (M4.3 实装)
//!
//! ## 责任范围
//! 4 种多视频策略的"编排计划"生成 (与 v2.4
//! `app/services/video/four_strategy.py` 1:1 对应):
//!
//! | 策略   | 输入            | 输出                |
//! | ------ | --------------- | ------------------- |
//! | single | 1 条素材        | 1 条成片            |
//! | concat | N 条素材 (N≥2)  | 1 条拼接成片        |
//! | batch  | N 条素材同模板  | N 条独立成片        |
//! | series | N 集素材+剧集上下文 | N 集成套成片 (带集号) |
//!
//! ## 设计
//! - 本 crate 只做**纯编排计划** (素材 → 输出计划的映射),不碰 IO;
//!   真正的 ffmpeg 拼接 / 转码由 [`vynaro-ffmpeg`] 在执行层完成
//! - 复用 [`vynaro_domain::ExportStrategy`] 枚举,避免类型重复
//! - 校验失败返回 [`VideoPlanError`],由上层转 `VynaroError::Pipeline`
//!
//! ## 用法
//! ```
//! use vynaro_domain::ExportStrategy;
//! use vynaro_intake::{build_plans, PlanOptions};
//! use std::path::PathBuf;
//!
//! let sources = vec![PathBuf::from("a.mp4"), PathBuf::from("b.mp4")];
//! let plans = build_plans(&sources, ExportStrategy::Concat, &PlanOptions::default()).unwrap();
//! assert_eq!(plans.len(), 1);
//! assert_eq!(plans[0].ordered_sources.len(), 2);
//! ```

use std::path::{Path, PathBuf};

use serde::{Deserialize, Serialize};
use thiserror::Error;
use vynaro_domain::ExportStrategy;

// ════════════════════════════════════════════════════════════════════════
// 错误类型
// ════════════════════════════════════════════════════════════════════════

#[derive(Debug, Error, PartialEq)]
pub enum VideoPlanError {
    /// 素材数量与策略不匹配 (如 concat 只有 1 条)
    #[error("素材数量不匹配策略 {strategy:?}: 需要 {expected},实际 {actual}")]
    SourceCountMismatch {
        strategy: ExportStrategy,
        expected: String,
        actual: usize,
    },
    /// series 策略缺剧集上下文
    #[error("series 策略必须提供 series_context (剧集主题描述)")]
    MissingSeriesContext,
    /// 集号模板不含 {n} 占位符
    #[error("episode_template 必须包含 {{n}} 占位符: {0}")]
    BadEpisodeTemplate(String),
    /// 素材路径无效 (空 / 无文件名)
    #[error("素材路径无效: {0}")]
    BadSourcePath(String),
}

// ════════════════════════════════════════════════════════════════════════
// 编排计划模型
// ════════════════════════════════════════════════════════════════════════

/// 编排选项
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PlanOptions {
    /// 输出文件基础名 (不含扩展名),缺省 "output"
    pub base_name: String,
    /// series 策略的剧集上下文 (主题 / 人物 / 剧情线描述)
    pub series_context: Option<String>,
    /// 集号命名模板,`{n}` 为 2 位补零集号,缺省 "第{n}集"
    pub episode_template: String,
}

impl Default for PlanOptions {
    fn default() -> Self {
        Self {
            base_name: "output".into(),
            series_context: None,
            episode_template: "第{n}集".into(),
        }
    }
}

/// 一个输出成片的编排计划 (执行层按此调 ffmpeg)
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct OutputPlan {
    /// 输出名 (不含扩展名)
    pub name: String,
    /// 按时间线顺序排列的素材路径 (single/batch 为 1 条,concat/series 为 N 条)
    pub ordered_sources: Vec<PathBuf>,
    /// 集号 (仅 series 有值,1-based)
    pub episode_number: Option<u32>,
    /// 集标签 (仅 series,如 "第01集")
    pub episode_label: Option<String>,
    /// series 上下文透传 (跨集复用,与 v2.4 SeriesContext 对应)
    pub series_context: Option<String>,
}

impl OutputPlan {
    /// 建议输出文件名 (container 扩展名由执行层决定)
    pub fn suggested_file_name(&self, container: &str) -> String {
        format!("{}.{}", self.name, container.trim_start_matches('.'))
    }

    /// 素材数
    pub fn source_count(&self) -> usize {
        self.ordered_sources.len()
    }
}

// ════════════════════════════════════════════════════════════════════════
// 计划生成
// ════════════════════════════════════════════════════════════════════════

/// 按策略生成编排计划 (纯函数,不读文件系统)
pub fn build_plans(
    sources: &[PathBuf],
    strategy: ExportStrategy,
    opts: &PlanOptions,
) -> Result<Vec<OutputPlan>, VideoPlanError> {
    validate_sources(sources)?;
    let base = sanitize_base_name(&opts.base_name);
    match strategy {
        ExportStrategy::Single => {
            if sources.len() != 1 {
                return Err(VideoPlanError::SourceCountMismatch {
                    strategy,
                    expected: "恰好 1 条".into(),
                    actual: sources.len(),
                });
            }
            Ok(vec![OutputPlan {
                name: base,
                ordered_sources: sources.to_vec(),
                episode_number: None,
                episode_label: None,
                series_context: None,
            }])
        }
        ExportStrategy::Concat => {
            if sources.len() < 2 {
                return Err(VideoPlanError::SourceCountMismatch {
                    strategy,
                    expected: "至少 2 条".into(),
                    actual: sources.len(),
                });
            }
            Ok(vec![OutputPlan {
                name: format!("{base}-concat"),
                ordered_sources: sources.to_vec(),
                episode_number: None,
                episode_label: None,
                series_context: None,
            }])
        }
        ExportStrategy::Batch => {
            if sources.is_empty() {
                return Err(VideoPlanError::SourceCountMismatch {
                    strategy,
                    expected: "至少 1 条".into(),
                    actual: 0,
                });
            }
            let pad = sources.len().to_string().len();
            Ok(sources
                .iter()
                .enumerate()
                .map(|(i, src)| OutputPlan {
                    name: format!("{base}-{:0width$}", i + 1, width = pad),
                    ordered_sources: vec![src.clone()],
                    episode_number: None,
                    episode_label: None,
                    series_context: None,
                })
                .collect())
        }
        ExportStrategy::Series => {
            if sources.is_empty() {
                return Err(VideoPlanError::SourceCountMismatch {
                    strategy,
                    expected: "至少 1 条".into(),
                    actual: 0,
                });
            }
            let context = opts
                .series_context
                .clone()
                .filter(|c| !c.trim().is_empty())
                .ok_or(VideoPlanError::MissingSeriesContext)?;
            if !opts.episode_template.contains("{n}") {
                return Err(VideoPlanError::BadEpisodeTemplate(
                    opts.episode_template.clone(),
                ));
            }
            let pad = sources.len().to_string().len();
            Ok(sources
                .iter()
                .enumerate()
                .map(|(i, src)| {
                    let n = i + 1;
                    let label = episode_label(&opts.episode_template, n as u32, pad);
                    OutputPlan {
                        name: format!("{base}-ep{n:0pad$}"),
                        ordered_sources: vec![src.clone()],
                        episode_number: Some(n as u32),
                        episode_label: Some(label),
                        series_context: Some(context.clone()),
                    }
                })
                .collect())
        }
    }
}

/// 按模板渲染集标签:`episode_label("第{n}集", 1, 2)` → "第01集"
pub fn episode_label(template: &str, n: u32, pad_width: usize) -> String {
    template.replace("{n}", &format!("{n:0width$}", width = pad_width))
}

/// 预估输出总条数 (UI 展示用,不落盘)
pub fn expected_output_count(source_count: usize, strategy: ExportStrategy) -> usize {
    match strategy {
        ExportStrategy::Single | ExportStrategy::Concat => {
            if source_count == 0 {
                0
            } else {
                1
            }
        }
        ExportStrategy::Batch | ExportStrategy::Series => source_count,
    }
}

// ── 内部校验 ────────────────────────────────────────────────────────────

fn validate_sources(sources: &[PathBuf]) -> Result<(), VideoPlanError> {
    for src in sources {
        if src.as_os_str().is_empty()
            || src
                .file_name()
                .is_none_or(|f| f.to_string_lossy().trim().is_empty())
        {
            return Err(VideoPlanError::BadSourcePath(src.display().to_string()));
        }
    }
    Ok(())
}

fn sanitize_base_name(raw: &str) -> String {
    let trimmed = raw.trim();
    if trimmed.is_empty() {
        return "output".to_owned();
    }
    // 去掉路径分隔符与非法字符,保持文件系统友好
    let cleaned: String = trimmed
        .chars()
        .map(|c| match c {
            '/' | '\\' | ':' | '*' | '?' | '"' | '<' | '>' | '|' => '_',
            c => c,
        })
        .collect();
    cleaned
}

/// 便捷入口:从素材文件名派生 base_name
pub fn base_name_from(source: &Path) -> String {
    source
        .file_stem()
        .map(|s| sanitize_base_name(&s.to_string_lossy()))
        .unwrap_or_else(|| "output".into())
}

#[cfg(test)]
mod tests {
    use super::*;

    fn paths(names: &[&str]) -> Vec<PathBuf> {
        names.iter().map(PathBuf::from).collect()
    }

    // ── single ──────────────────────────────────────────────────────
    #[test]
    fn single_one_source_one_plan() {
        let plans = build_plans(
            &paths(&["a.mp4"]),
            ExportStrategy::Single,
            &PlanOptions::default(),
        )
        .unwrap();
        assert_eq!(plans.len(), 1);
        assert_eq!(plans[0].name, "output");
        assert_eq!(plans[0].ordered_sources, paths(&["a.mp4"]));
        assert!(plans[0].episode_number.is_none());
    }

    #[test]
    fn single_rejects_two_sources() {
        let err = build_plans(
            &paths(&["a.mp4", "b.mp4"]),
            ExportStrategy::Single,
            &PlanOptions::default(),
        )
        .unwrap_err();
        assert!(matches!(err, VideoPlanError::SourceCountMismatch { .. }));
    }

    // ── concat ──────────────────────────────────────────────────────
    #[test]
    fn concat_merges_in_order() {
        let plans = build_plans(
            &paths(&["a.mp4", "b.mp4", "c.mp4"]),
            ExportStrategy::Concat,
            &PlanOptions {
                base_name: "vlog".into(),
                ..Default::default()
            },
        )
        .unwrap();
        assert_eq!(plans.len(), 1);
        assert_eq!(plans[0].name, "vlog-concat");
        assert_eq!(plans[0].source_count(), 3);
        assert_eq!(plans[0].ordered_sources[0], PathBuf::from("a.mp4"));
        assert_eq!(plans[0].ordered_sources[2], PathBuf::from("c.mp4"));
    }

    #[test]
    fn concat_requires_at_least_two() {
        let err = build_plans(
            &paths(&["a.mp4"]),
            ExportStrategy::Concat,
            &PlanOptions::default(),
        )
        .unwrap_err();
        assert!(matches!(err, VideoPlanError::SourceCountMismatch { .. }));
    }

    // ── batch ───────────────────────────────────────────────────────
    #[test]
    fn batch_one_plan_per_source_padded() {
        let sources: Vec<PathBuf> = (1..=12)
            .map(|i| PathBuf::from(format!("s{i:02}.mp4")))
            .collect();
        let plans = build_plans(&sources, ExportStrategy::Batch, &PlanOptions::default()).unwrap();
        assert_eq!(plans.len(), 12);
        // 12 条 → 2 位补零
        assert_eq!(plans[0].name, "output-01");
        assert_eq!(plans[11].name, "output-12");
        // 每个 plan 只含自己的素材
        assert_eq!(plans[3].ordered_sources, vec![PathBuf::from("s04.mp4")]);
    }

    #[test]
    fn batch_requires_nonempty() {
        let err = build_plans(&[], ExportStrategy::Batch, &PlanOptions::default()).unwrap_err();
        assert!(matches!(err, VideoPlanError::SourceCountMismatch { .. }));
    }

    // ── series ──────────────────────────────────────────────────────
    #[test]
    fn series_carries_episode_number_and_context() {
        let opts = PlanOptions {
            base_name: "我的故事".into(),
            series_context: Some("都市悬疑,主角林晓".into()),
            episode_template: "第{n}集".into(),
        };
        let plans = build_plans(
            &paths(&["ep1.mp4", "ep2.mp4", "ep3.mp4"]),
            ExportStrategy::Series,
            &opts,
        )
        .unwrap();
        assert_eq!(plans.len(), 3);
        assert_eq!(plans[0].name, "我的故事-ep1");
        assert_eq!(plans[0].episode_number, Some(1));
        assert_eq!(plans[0].episode_label.as_deref(), Some("第1集"));
        assert_eq!(plans[2].episode_number, Some(3));
        for p in &plans {
            assert_eq!(p.series_context.as_deref(), Some("都市悬疑,主角林晓"));
        }
    }

    #[test]
    fn series_requires_context() {
        let err = build_plans(
            &paths(&["ep1.mp4"]),
            ExportStrategy::Series,
            &PlanOptions::default(),
        )
        .unwrap_err();
        assert_eq!(err, VideoPlanError::MissingSeriesContext);
    }

    #[test]
    fn series_rejects_blank_context_and_bad_template() {
        let blank = PlanOptions {
            series_context: Some("   ".into()),
            ..Default::default()
        };
        assert_eq!(
            build_plans(&paths(&["e.mp4"]), ExportStrategy::Series, &blank).unwrap_err(),
            VideoPlanError::MissingSeriesContext
        );
        let bad_tpl = PlanOptions {
            series_context: Some("ctx".into()),
            episode_template: "EP".into(), // 缺 {n}
            ..Default::default()
        };
        assert!(matches!(
            build_plans(&paths(&["e.mp4"]), ExportStrategy::Series, &bad_tpl),
            Err(VideoPlanError::BadEpisodeTemplate(_))
        ));
    }

    // ── 通用校验 / 工具 ─────────────────────────────────────────────
    #[test]
    fn rejects_empty_or_bad_source_paths() {
        let err = build_plans(
            &paths(&[""]),
            ExportStrategy::Batch,
            &PlanOptions::default(),
        )
        .unwrap_err();
        assert!(matches!(err, VideoPlanError::BadSourcePath(_)));
    }

    #[test]
    fn base_name_sanitizes_illegal_chars() {
        let opts = PlanOptions {
            base_name: "a/b:c?d".into(),
            ..Default::default()
        };
        let plans = build_plans(&paths(&["a.mp4"]), ExportStrategy::Single, &opts).unwrap();
        assert_eq!(plans[0].name, "a_b_c_d");
        // 空白 base_name 回落 output
        let plans = build_plans(
            &paths(&["a.mp4"]),
            ExportStrategy::Single,
            &PlanOptions {
                base_name: "  ".into(),
                ..Default::default()
            },
        )
        .unwrap();
        assert_eq!(plans[0].name, "output");
    }

    #[test]
    fn episode_label_pads_to_width() {
        assert_eq!(episode_label("第{n}集", 1, 2), "第01集");
        assert_eq!(episode_label("第{n}集", 12, 2), "第12集");
        assert_eq!(episode_label("EP {n}", 3, 3), "EP 003");
    }

    #[test]
    fn expected_output_count_table() {
        assert_eq!(expected_output_count(1, ExportStrategy::Single), 1);
        assert_eq!(expected_output_count(5, ExportStrategy::Concat), 1);
        assert_eq!(expected_output_count(5, ExportStrategy::Batch), 5);
        assert_eq!(expected_output_count(5, ExportStrategy::Series), 5);
        assert_eq!(expected_output_count(0, ExportStrategy::Single), 0);
    }

    #[test]
    fn suggested_file_name_uses_container() {
        let plan = OutputPlan {
            name: "demo".into(),
            ordered_sources: vec![],
            episode_number: None,
            episode_label: None,
            series_context: None,
        };
        assert_eq!(plan.suggested_file_name("mp4"), "demo.mp4");
        assert_eq!(plan.suggested_file_name(".mov"), "demo.mov");
    }

    #[test]
    fn base_name_from_file_stem() {
        assert_eq!(base_name_from(Path::new("/x/y/vlog 01.mp4")), "vlog 01");
        assert_eq!(base_name_from(Path::new("")), "output");
    }

    #[test]
    fn plan_serde_roundtrip() {
        let plans = build_plans(
            &paths(&["a.mp4", "b.mp4"]),
            ExportStrategy::Concat,
            &PlanOptions::default(),
        )
        .unwrap();
        let json = serde_json::to_string(&plans).unwrap();
        let back: Vec<OutputPlan> = serde_json::from_str(&json).unwrap();
        assert_eq!(plans, back);
    }
}
