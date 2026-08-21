use crate::agents::*;
use crate::context::AgentContext;
use crate::types::{AgentEventPayload, AgentRole, AgentStatus, BreakpointRequest};
use splicr_core::SplicrResult;
use std::sync::Arc;
use tokio::sync::RwLock;

pub type EventEmitter = Arc<dyn Fn(AgentEventPayload) + Send + Sync>;

// 调度引擎
pub struct AgentOrchestrator {
    pub(crate) context: Arc<RwLock<AgentContext>>,
    agents: Vec<Box<dyn Agent>>,
    event_emitter: Option<EventEmitter>,
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
            event_emitter: None,
        }
    }

    pub fn with_emitter(mut self, emitter: EventEmitter) -> Self {
        self.event_emitter = Some(emitter);
        self
    }

    pub async fn context(&self) -> Arc<RwLock<AgentContext>> {
        self.context.clone()
    }

    pub async fn run_step(&self, step_idx: usize) -> SplicrResult<Option<BreakpointRequest>> {
        if step_idx >= self.agents.len() {
            let mut ctx = self.context.write().await;
            ctx.status = AgentStatus::Completed;
            if let Some(emitter) = &self.event_emitter {
                emitter(AgentEventPayload::WorkflowCompleted {
                    total_steps: self.agents.len(),
                    duration_ms: 0,
                });
            }
            return Ok(None);
        }

        let agent = &self.agents[step_idx];
        let role = agent.role();
        let name = agent.name().to_string();

        if let Some(emitter) = &self.event_emitter {
            emitter(AgentEventPayload::StepStarted {
                step_idx,
                role,
                name: name.clone(),
            });
        }

        let mut ctx = self.context.write().await;
        ctx.current_role = role;
        ctx.status = AgentStatus::Thinking;

        let result = match agent.execute(&mut ctx).await {
            Ok(res) => res,
            Err(e) => {
                ctx.status = AgentStatus::Failed;
                if let Some(emitter) = &self.event_emitter {
                    emitter(AgentEventPayload::Error {
                        role: Some(role),
                        message: e.to_string(),
                    });
                }
                return Err(e);
            }
        };

        let summary = result.clone().unwrap_or_else(|| "步骤执行完毕".into());
        if let Some(emitter) = &self.event_emitter {
            emitter(AgentEventPayload::StepCompleted {
                step_idx,
                role,
                summary,
            });
        }

        // 若非纯全自动模式且在编剧/配音节点，触发断点请求
        if !ctx.auto_mode && (role == AgentRole::Screenwriter || role == AgentRole::VoiceArtist) {
            ctx.status = AgentStatus::AwaitingApproval;
            let req = BreakpointRequest {
                agent: role,
                step_title: name,
                content: result.unwrap_or_default(),
                options: vec!["批准继续".to_string(), "重新生成".to_string()],
            };
            if let Some(emitter) = &self.event_emitter {
                emitter(AgentEventPayload::BreakpointRequired(req.clone()));
            }
            return Ok(Some(req));
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
