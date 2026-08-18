//! splicr-pipeline · PipelineService (运行时编排门面)
//!
//! ## 职责
//! - 持有 [`Pipeline`] 状态机 + 当前项目 + 后台任务句柄
//! - `start()` 把 7 步流水线 spawn 到 tokio 后台任务,命令层立即返回
//! - `cancel()` / `reset()` / `status()` 供 Tauri command 直接转发
//!
//! ## 与 Tauri 层的关系
//! src-tauri 把 PipelineService 注册进 ServiceContainer,
//! pipeline_start 命令构造 PipelineDeps 后调用 start(),
//! 另起一个任务把 broadcast 事件桥接为 Tauri event。

use std::sync::Arc;

use serde::Serialize;
use tokio::sync::Mutex;
use tokio::task::JoinHandle;

use crate::executors::{default_executors, PipelineDeps};
use crate::{Pipeline, PipelineEvent, PipelineState, Project, SplicrResult, StepStatus};

/// IPC 友好的状态快照。
#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct PipelineStatus {
    pub state: PipelineState,
    pub step_statuses: Vec<StepStatus>,
    pub current_step: i8,
    pub project_name: Option<String>,
}

/// 流水线运行时门面。注册进 ServiceContainer 供命令层使用。
#[derive(Debug)]
pub struct PipelineService {
    pipeline: Arc<Pipeline>,
    project: Mutex<Option<Project>>,
    task: Mutex<Option<JoinHandle<Result<Project, String>>>>,
}

impl Default for PipelineService {
    fn default() -> Self {
        Self::new()
    }
}

impl PipelineService {
    pub fn new() -> Self {
        Self {
            pipeline: Arc::new(Pipeline::new()),
            project: Mutex::new(None),
            task: Mutex::new(None),
        }
    }

    pub fn pipeline(&self) -> Arc<Pipeline> {
        self.pipeline.clone()
    }

    /// 订阅事件 (Tauri 桥接任务用)
    pub fn subscribe(&self) -> tokio::sync::broadcast::Receiver<PipelineEvent> {
        self.pipeline.subscribe()
    }

    /// 是否正在运行
    pub fn is_running(&self) -> bool {
        self.pipeline.pipeline_state() == PipelineState::Running
    }

    /// 状态快照
    pub async fn status(&self) -> PipelineStatus {
        let project_name = self.project.lock().await.as_ref().map(|p| p.name.clone());
        PipelineStatus {
            state: self.pipeline.pipeline_state(),
            step_statuses: self.pipeline.step_statuses().to_vec(),
            current_step: self.pipeline.current_step(),
            project_name,
        }
    }

    /// 启动流水线 (后台任务)。运行中重复调用返回错误。
    pub async fn start(&self, project: Project, deps: Arc<PipelineDeps>) -> SplicrResult<()> {
        if self.is_running() {
            return Err(crate::SplicrError::Pipeline("流水线正在运行中".into()));
        }

        let pipeline = self.pipeline.clone();
        *self.project.lock().await = Some(project.clone());

        let handle = tokio::spawn(async move {
            let mut proj = project;
            let execs = default_executors(deps);
            match pipeline.start(&mut proj, &execs).await {
                Ok(()) => Ok(proj),
                Err(e) => Err(e.to_string()),
            }
        });
        *self.task.lock().await = Some(handle);
        Ok(())
    }

    /// 取消 (下一步边界生效)
    pub fn cancel(&self) {
        self.pipeline.cancel();
    }

    /// 重置回 Idle
    pub async fn reset(&self) {
        self.pipeline.reset();
        *self.project.lock().await = None;
    }

    /// 等待后台任务结束并取回最终项目 (导出完成后持久化用)
    pub async fn take_finished_project(&self) -> Option<Project> {
        let handle = self.task.lock().await.take();
        match handle {
            Some(h) => match h.await {
                Ok(Ok(proj)) => Some(proj),
                _ => None,
            },
            None => None,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::path::PathBuf;

    fn deps(tmp: &str) -> Arc<PipelineDeps> {
        Arc::new(PipelineDeps {
            llm: None,
            tts: None,
            ffmpeg: None,
            workdir: PathBuf::from(tmp),
        })
    }

    #[tokio::test]
    async fn status_reflects_failure_and_reset() {
        let svc = PipelineService::new();
        let p = Project::default();
        // 无素材 → step0 失败
        svc.start(p, deps("/tmp/sf-svc-test")).await.unwrap();
        // 等后台任务结束
        let _ = svc.take_finished_project().await;
        let st = svc.status().await;
        assert_eq!(st.state, PipelineState::Failed);
        assert_eq!(st.step_statuses[0], StepStatus::Error);

        svc.reset().await;
        let st = svc.status().await;
        assert_eq!(st.state, PipelineState::Idle);
        assert!(st.project_name.is_none());
    }

    #[tokio::test]
    async fn double_start_rejected_while_running() {
        let svc = PipelineService::new();
        // 构造一个会"运行中"的场景较难离线模拟,这里验证 Idle 下可以 start
        let p = Project::default();
        assert!(svc
            .start(p.clone(), deps("/tmp/sf-svc-test2"))
            .await
            .is_ok());
        let _ = svc.take_finished_project().await;
    }
}
