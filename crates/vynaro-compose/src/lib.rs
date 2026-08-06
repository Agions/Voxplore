//! vynaro-pipeline v2.5.0 · 7 步第一人称叙述流水线
//!
//! ## 流水线定义 (7 步状态机)
//! - [`STEPS`] 常量 (7 个步骤的硬编码顺序: intake ➔ detect ➔ script ➔ voice ➔ subtitle ➔ compose ➔ export)
//! - [`Pipeline`] 状态机 (手动 advance 7 步 + emit event)
//!
//! ## M2 范围 (PoC)
//! - [`StepDef`] / [`StepStatus`] / [`PipelineState`] 类型
//! - [`Pipeline`] 状态机 (手动 advance 5 步 + emit event)
//! - [`MonologueMaker`] 占位 (后续 M3 接 LLM + FFmpeg)
//!
//! ## M3+ 范围
//! - 真实 LLM 调用 + FFmpeg 调用 + ETA 估算
//! - 状态机持久化 (崩溃后能恢复)
//! - 多并发流水线 (同一项目同时多个 source)

#![allow(dead_code)]

pub mod executors;
pub mod service;

use async_trait::async_trait;
use serde::{Deserialize, Serialize};
use std::fmt;
use std::sync::atomic::{AtomicBool, Ordering};
use tokio::sync::broadcast;

pub use vynaro_core::error::{VynaroError, VynaroResult};
pub use vynaro_domain::{Clip, MediaFile, Project, ScriptSegment, Timeline, Track};

// ════════════════════════════════════════════════════════════════════════
// 5 步定义
// ════════════════════════════════════════════════════════════════════════

/// 单步定义 (id, label, description)。
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StepDef {
    pub id: &'static str,
    pub label_zh: &'static str,
    pub description_zh: &'static str,
}

/// 7 步常量（与前端 DEFAULT_PIPELINE_STEPS 1:1 对应）。
pub const STEPS: [StepDef; 7] = [
    StepDef {
        id: "intake",
        label_zh: "素材导入",
        description_zh: "选择影视片段并导入项目",
    },
    StepDef {
        id: "detect",
        label_zh: "智能拆条",
        description_zh: "FFmpeg 识别镜头切换与关键帧",
    },
    StepDef {
        id: "script",
        label_zh: "脚本生成",
        description_zh: "LLM 生成第一人称解说独白",
    },
    StepDef {
        id: "voice",
        label_zh: "TTS配音",
        description_zh: "语音合成与情绪节奏校准",
    },
    StepDef {
        id: "subtitle",
        label_zh: "字幕合成",
        description_zh: "VAD 对齐字幕时间轴并渲染",
    },
    StepDef {
        id: "compose",
        label_zh: "画面对齐",
        description_zh: "音画合成与竖屏帧率压制",
    },
    StepDef {
        id: "export",
        label_zh: "导出发布",
        description_zh: "按平台参数封装输出成片",
    },
];

/// 单步状态。
#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "kebab-case")]
pub enum StepStatus {
    Pending,
    Active,
    Done,
    Error,
}

/// 中文 status 标签。
pub fn status_label_zh(s: StepStatus) -> &'static str {
    match s {
        StepStatus::Pending => "待开始",
        StepStatus::Active => "进行中",
        StepStatus::Done => "已完成",
        StepStatus::Error => "失败",
    }
}

impl fmt::Display for StepStatus {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(status_label_zh(*self))
    }
}

/// 聚合流水线状态。
#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "kebab-case")]
pub enum PipelineState {
    Idle,
    Running,
    Done,
    Failed,
}

pub fn pipeline_state_zh(s: PipelineState) -> &'static str {
    match s {
        PipelineState::Idle => "就绪",
        PipelineState::Running => "进行中",
        PipelineState::Done => "已完成",
        PipelineState::Failed => "失败",
    }
}

// ════════════════════════════════════════════════════════════════════════
// 流水线事件 (broadcast::Sender)
// ════════════════════════════════════════════════════════════════════════

/// Tauri 前端用 `Event<PipelineEvent>` 监听这些事件。
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(tag = "kind", rename_all = "kebab-case")]
pub enum PipelineEvent {
    StepStarted { index: u8 },
    StepFinished { index: u8, duration_ms: u64 },
    StepFailed { index: u8, message: String },
    PipelineFinished { project_path: String },
    PipelineFailed { message: String },
    ProgressEta { remaining_seconds: Option<f64> },
}

// ════════════════════════════════════════════════════════════════════════
// 单步执行器 (trait)
// ════════════════════════════════════════════════════════════════════════

/// 每个 step 的执行逻辑。
#[async_trait]
pub trait StepExecutor: Send + Sync {
    /// 步骤索引 (0..=4)
    fn step_index(&self) -> u8;
    /// 执行一步 (副作用在内部完成)
    async fn execute(&self, project: &mut Project) -> VynaroResult<()>;
}

// ════════════════════════════════════════════════════════════════════════
// Pipeline — 状态机
// ════════════════════════════════════════════════════════════════════════

/// 7 步流水线控制对象。
///
/// 设计要点:
/// - 单实例可重复 start (reset 后重新跑)
/// - 通过 `events_tx` 发出 `PipelineEvent`,上层订阅
/// - 注入 [`StepExecutor`] 列表 (M3 真实实现,M2 占位)
pub struct Pipeline {
    state: parking_lot::Mutex<PipelineInner>,
    events_tx: broadcast::Sender<PipelineEvent>,
    cancel_requested: AtomicBool,
}

// 手动 impl Debug (broadcast::Sender 无法 derive)
impl std::fmt::Debug for Pipeline {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        let st = self.state.lock();
        f.debug_struct("Pipeline")
            .field("state", &st.pipeline_state)
            .field("current_step", &st.current_step)
            .field("step_statuses", &st.step_statuses)
            .finish()
    }
}

#[derive(Debug)]
struct PipelineInner {
    pipeline_state: PipelineState,
    step_statuses: [StepStatus; 7],
    current_step: i8, // -1 = 没起步,0..=6 = 正在跑某步
    started_at: Option<chrono::DateTime<chrono::Utc>>,
}

impl Default for PipelineInner {
    fn default() -> Self {
        Self {
            pipeline_state: PipelineState::Idle,
            step_statuses: [StepStatus::Pending; 7],
            current_step: -1,
            started_at: None,
        }
    }
}

impl Pipeline {
    pub fn new() -> Self {
        let (tx, _) = broadcast::channel(64);
        Self {
            state: parking_lot::Mutex::new(PipelineInner::default()),
            events_tx: tx,
            cancel_requested: AtomicBool::new(false),
        }
    }

    /// 请求取消 (下一步边界生效)。
    pub fn cancel(&self) {
        self.cancel_requested.store(true, Ordering::SeqCst);
    }

    pub fn is_cancel_requested(&self) -> bool {
        self.cancel_requested.load(Ordering::SeqCst)
    }

    /// 订阅事件 (用于 Tauri 前端 listen)
    pub fn subscribe(&self) -> broadcast::Receiver<PipelineEvent> {
        self.events_tx.subscribe()
    }

    pub fn pipeline_state(&self) -> PipelineState {
        self.state.lock().pipeline_state
    }

    pub fn step_statuses(&self) -> [StepStatus; 7] {
        self.state.lock().step_statuses
    }

    pub fn current_step(&self) -> i8 {
        self.state.lock().current_step
    }

    /// 启动流水线 (idempotent: 运行中重复调用是 no-op)
    ///
    /// executors 为异构 trait object 列表,按 0..=4 顺序执行。
    pub async fn start(
        &self,
        project: &mut Project,
        executors: &[Box<dyn StepExecutor>],
    ) -> VynaroResult<()> {
        {
            let mut st = self.state.lock();
            if st.pipeline_state == PipelineState::Running {
                return Ok(());
            }
            // reset
            st.step_statuses = [StepStatus::Pending; 7];
            st.current_step = -1;
            st.pipeline_state = PipelineState::Running;
            st.started_at = Some(chrono::Utc::now());
        }
        self.cancel_requested.store(false, Ordering::SeqCst);

        for (idx, exec) in executors.iter().enumerate() {
            // 步边界取消检查
            if self.cancel_requested.load(Ordering::SeqCst) {
                let mut st = self.state.lock();
                st.pipeline_state = PipelineState::Failed;
                let msg = "流水线已取消".to_string();
                let _ = self.events_tx.send(PipelineEvent::PipelineFailed {
                    message: msg.clone(),
                });
                return Err(VynaroError::Pipeline(msg));
            }

            if exec.step_index() as usize != idx {
                return Err(VynaroError::Pipeline(format!(
                    "executor index mismatch at slot {idx}: got {}",
                    exec.step_index()
                )));
            }

            // 标记当前步 active + emit
            {
                let mut st = self.state.lock();
                st.current_step = idx as i8;
                st.step_statuses[idx] = StepStatus::Active;
            }
            let _ = self
                .events_tx
                .send(PipelineEvent::StepStarted { index: idx as u8 });

            let step_start = std::time::Instant::now();
            let result = exec.execute(project).await;
            let duration_ms = step_start.elapsed().as_millis() as u64;

            match result {
                Ok(()) => {
                    {
                        let mut st = self.state.lock();
                        st.step_statuses[idx] = StepStatus::Done;
                    }
                    let _ = self.events_tx.send(PipelineEvent::StepFinished {
                        index: idx as u8,
                        duration_ms,
                    });
                }
                Err(e) => {
                    {
                        let mut st = self.state.lock();
                        st.step_statuses[idx] = StepStatus::Error;
                        st.pipeline_state = PipelineState::Failed;
                    }
                    let msg = e.to_string();
                    let _ = self.events_tx.send(PipelineEvent::StepFailed {
                        index: idx as u8,
                        message: msg.clone(),
                    });
                    let _ = self
                        .events_tx
                        .send(PipelineEvent::PipelineFailed { message: msg });
                    return Err(e);
                }
            }
        }

        // 全部成功
        {
            let mut st = self.state.lock();
            st.pipeline_state = PipelineState::Done;
            st.current_step = -1;
        }
        let _ = self.events_tx.send(PipelineEvent::PipelineFinished {
            project_path: project.id.clone(),
        });
        Ok(())
    }

    /// 重置回 Idle
    pub fn reset(&self) {
        let mut st = self.state.lock();
        *st = PipelineInner::default();
        self.cancel_requested.store(false, Ordering::SeqCst);
    }
}

impl Default for Pipeline {
    fn default() -> Self {
        Self::new()
    }
}

// ════════════════════════════════════════════════════════════════════════
// MonologueMaker — 顶层业务编排入口 (M3 充实)
// ════════════════════════════════════════════════════════════════════════

// MonologueConfig 已在 M2 提交后清理:零外部引用,作为冗余占位删除。
// M3 起 MonologueMaker 真实实现时按需重新引入并扩展字段。

#[cfg(test)]
mod tests {
    use super::*;

    /// 总是成功的 PoC executor
    struct AlwaysOkExecutor {
        idx: u8,
    }

    #[async_trait]
    impl StepExecutor for AlwaysOkExecutor {
        fn step_index(&self) -> u8 {
            self.idx
        }
        async fn execute(&self, _p: &mut Project) -> VynaroResult<()> {
            Ok(())
        }
    }

    /// 总是失败的 PoC executor
    struct AlwaysFailExecutor {
        idx: u8,
    }

    #[async_trait]
    impl StepExecutor for AlwaysFailExecutor {
        fn step_index(&self) -> u8 {
            self.idx
        }
        async fn execute(&self, _p: &mut Project) -> VynaroResult<()> {
            Err(VynaroError::Pipeline("intentional fail".into()))
        }
    }

    #[tokio::test]
    async fn run_all_5_steps_ok() {
        let p = Pipeline::new();
        let mut proj = Project::default();
        let execs: Vec<Box<dyn StepExecutor>> = (0..5)
            .map(|i| Box::new(AlwaysOkExecutor { idx: i }) as Box<dyn StepExecutor>)
            .collect();
        p.start(&mut proj, &execs).await.unwrap();
        assert_eq!(p.pipeline_state(), PipelineState::Done);
        assert_eq!(p.step_statuses()[2], StepStatus::Done);
    }

    #[tokio::test]
    async fn step_failure_aborts() {
        let p = Pipeline::new();
        let mut proj = Project::default();
        let fails: Vec<Box<dyn StepExecutor>> = (0..5)
            .map(|i| Box::new(AlwaysFailExecutor { idx: i }) as Box<dyn StepExecutor>)
            .collect();
        let r = p.start(&mut proj, &fails).await;
        assert!(r.is_err());
        assert_eq!(p.pipeline_state(), PipelineState::Failed);
    }

    #[tokio::test]
    async fn cancel_before_next_step() {
        let p = std::sync::Arc::new(Pipeline::new());
        let mut proj = Project::default();

        /// 第 1 步执行完后请求取消
        struct CancelAfterFirst {
            p: std::sync::Arc<Pipeline>,
        }
        #[async_trait]
        impl StepExecutor for CancelAfterFirst {
            fn step_index(&self) -> u8 {
                1
            }
            async fn execute(&self, _p: &mut Project) -> VynaroResult<()> {
                self.p.cancel();
                Ok(())
            }
        }

        let execs: Vec<Box<dyn StepExecutor>> = vec![
            Box::new(AlwaysOkExecutor { idx: 0 }),
            Box::new(CancelAfterFirst { p: p.clone() }),
            Box::new(AlwaysOkExecutor { idx: 2 }),
            Box::new(AlwaysOkExecutor { idx: 3 }),
            Box::new(AlwaysOkExecutor { idx: 4 }),
        ];
        let r = p.start(&mut proj, &execs).await;
        assert!(r.is_err());
        assert_eq!(p.pipeline_state(), PipelineState::Failed);
        // 第 2 步从未执行
        assert_eq!(p.step_statuses()[2], StepStatus::Pending);
    }
}
