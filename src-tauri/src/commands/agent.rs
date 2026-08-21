//! Tauri 命令分组 · splicr-agent 多智能体协同服务

use splicr_agent::{AgentContext, AgentEventPayload, AgentOrchestrator, BreakpointRequest};
use splicr_core::services::{ConfigService, ConfigSnapshot};
use splicr_core::AppContext;
use splicr_domain::Project;
use std::sync::Arc;
use tauri::{Emitter, State};
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
    app_handle: tauri::AppHandle,
    project: Project,
    auto_mode: bool,
    app_ctx: State<'_, AppContext>,
    state: State<'_, AgentServiceState>,
) -> Result<AgentContext, String> {
    let mut ctx = AgentContext::new(project, auto_mode);

    // 自动装配当前设置中的 LLM 与 TTS 凭证至 Agent 上下文内存
    if let Ok(cfg_svc) = app_ctx.service::<ConfigService>().await {
        let snap: ConfigSnapshot = cfg_svc.snapshot().await;
        if let Some(key) = snap.llm_api_key {
            ctx.memory.insert("llm_api_key".to_string(), key);
        }
        if let Some(model) = snap.llm_model {
            ctx.memory.insert("llm_model".to_string(), model);
        }
        if let Some(base_url) = snap.llm_base_url {
            ctx.memory.insert("llm_base_url".to_string(), base_url);
        }
        ctx.memory
            .insert("llm_provider".to_string(), snap.llm_provider.to_string());
    }

    let handle_clone = app_handle.clone();
    let emitter = Arc::new(move |payload: AgentEventPayload| {
        let _ = handle_clone.emit("agent://event", payload);
    });

    let orch = AgentOrchestrator::new(ctx.clone()).with_emitter(emitter);
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
        orch.run_step(step_idx).await.map_err(|e| e.to_string())
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
        let ctx_lock = orch.context().await;
        let ctx = ctx_lock.read().await;
        Ok(Some(ctx.clone()))
    } else {
        Ok(None)
    }
}
