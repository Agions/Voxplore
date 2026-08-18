//! splicr-agent · Rust Native Multi-Agent Autonomous Video Storytelling Engine
//!
//! 提供由 Director(总控导演), VisualCritic(视觉分析), Screenwriter(金牌编剧),
//! VoiceArtist(声乐调音), SoundEngineer(混音剪辑), QualityReviewer(质量验收)
//! 组成的多智能体协同与自反思工作团队。

pub mod agents;
pub mod context;
pub mod engine;
pub mod types;

pub use agents::*;
pub use context::AgentContext;
pub use engine::AgentOrchestrator;
pub use types::*;
