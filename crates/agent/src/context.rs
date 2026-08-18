use crate::types::{AgentMessage, AgentRole, AgentStatus};
use serde::{Deserialize, Serialize};
use splicr_domain::Project;
use std::collections::HashMap;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AgentContext {
    pub session_id: String,
    pub project: Project,
    pub current_role: AgentRole,
    pub status: AgentStatus,
    pub messages: Vec<AgentMessage>,
    pub memory: HashMap<String, String>,
    pub auto_mode: bool,
}

impl AgentContext {
    pub fn new(project: Project, auto_mode: bool) -> Self {
        Self {
            session_id: uuid::Uuid::new_v4().to_string(),
            project,
            current_role: AgentRole::Director,
            status: AgentStatus::Idle,
            messages: Vec::new(),
            memory: HashMap::new(),
            auto_mode,
        }
    }

    pub fn log_thought(&mut self, role: AgentRole, thought: impl Into<String>) {
        self.messages.push(AgentMessage {
            id: uuid::Uuid::new_v4().to_string(),
            sender: role,
            receiver: None,
            thought: Some(thought.into()),
            action: None,
            observation: None,
            timestamp: chrono::Utc::now().timestamp_millis(),
        });
    }

    pub fn log_action(&mut self, role: AgentRole, action: impl Into<String>, observation: impl Into<String>) {
        self.messages.push(AgentMessage {
            id: uuid::Uuid::new_v4().to_string(),
            sender: role,
            receiver: None,
            thought: None,
            action: Some(action.into()),
            observation: Some(observation.into()),
            timestamp: chrono::Utc::now().timestamp_millis(),
        });
    }
}
