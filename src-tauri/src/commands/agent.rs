//! Tauri 命令分组 · splicr-agent 多智能体协同服务

use splicr_agent::{AgentContext, AgentOrchestrator, BreakpointRequest};
use splicr_domain::Project;
use std::sync::Arc;
use tauri::State;
use tokio::sync::RwLock;

// 内部状态管理器（非 pub struct，避免 gen-ipc 抽取为前端 TS interface）
pub struct AgentServiceState(pub Arc<RwLock<Option<AgentOrchestrator>>>);

impl AgentServiceState {
    pub fn new() -> Self {
        Self(Arc::new(RwLock::new(None)))
    }
}

/// 启动多智能体团队协同
#[tauri::command]
pub async fn agent_start(
    project: Project,
    auto_mode: bool,
    state: State<'_, AgentServiceState>,
) -> Result<AgentContext, String> {
    let ctx = AgentContext::new(project, auto_mode);
    let orch = AgentOrchestrator::new(ctx.clone());
    let mut lock = state.0.write().await;
    *lock = Some(orch);
    Ok(ctx)
}

/// 执行单步智能体调度 (支持 Breakpoint 响应)
#[tauri::command]
pub async fn agent_step(
    step_idx: usize,
    state: State<'_, AgentServiceState>,
) -> Result<Option<BreakpointRequest>, String> {
    let lock = state.0.read().await;
    if let Some(orch) = lock.as_ref() {
        orch.run_step(step_idx)
            .await
            .map_err(|e| e.to_string())
    } else {
        Err("智能体调度器尚未初始化".to_string())
    }
}

/// 获取当前多智能体上下文日志与思考流
#[tauri::command]
pub async fn agent_get_context(
    state: State<'_, AgentServiceState>,
) -> Result<Option<AgentContext>, String> {
    let lock = state.0.read().await;
    if let Some(orch) = lock.as_ref() {
        let ctx = orch.context.read().await;
        Ok(Some(ctx.clone()))
    } else {
        Ok(None)
    }
}
