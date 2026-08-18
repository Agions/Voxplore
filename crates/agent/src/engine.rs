use crate::agents::*;
use crate::context::AgentContext;
use crate::types::{AgentRole, AgentStatus, BreakpointRequest};
use splicr_core::SplicrResult;
use std::sync::Arc;
use tokio::sync::RwLock;

// 调度引擎（内部结构，字段不为 pub 以免被抽取为前端 TS interface）
pub struct AgentOrchestrator {
    pub(crate) context: Arc<RwLock<AgentContext>>,
    agents: Vec<Box<dyn Agent>>,
}

impl AgentOrchestrator {
    pub fn new(context: AgentContext) -> Self {
        Self {
            context: Arc::new(RwLock::new(context)),
            agents: vec![
                Box::new(DirectorAgent),
                Box::new(VisualCriticAgent),
                Box::new(ScreenwriterAgent),
                Box::new(VoiceArtistAgent),
                Box::new(SoundEngineerAgent),
                Box::new(QualityReviewerAgent),
            ],
        }
    }

    pub async fn context(&self) -> Arc<RwLock<AgentContext>> {
        self.context.clone()
    }

    pub async fn run_step(&self, step_idx: usize) -> SplicrResult<Option<BreakpointRequest>> {
        if step_idx >= self.agents.len() {
            let mut ctx = self.context.write().await;
            ctx.status = AgentStatus::Completed;
            return Ok(None);
        }

        let agent = &self.agents[step_idx];
        let mut ctx = self.context.write().await;
        ctx.current_role = agent.role();
        ctx.status = AgentStatus::Thinking;

        let result = agent.execute(&mut ctx).await?;

        // 若非纯全自动模式且在编剧/配音节点，触发断点请求
        if !ctx.auto_mode
            && (agent.role() == AgentRole::Screenwriter || agent.role() == AgentRole::VoiceArtist)
        {
            ctx.status = AgentStatus::AwaitingApproval;
            return Ok(Some(BreakpointRequest {
                agent: agent.role(),
                step_title: agent.name().to_string(),
                content: result.unwrap_or_default(),
                options: vec!["批准继续".to_string(), "重新生成".to_string()],
            }));
        }

        Ok(None)
    }

    pub async fn run_all(&self) -> SplicrResult<()> {
        for i in 0..self.agents.len() {
            let _ = self.run_step(i).await?;
        }
        Ok(())
    }
}
