//! src-tauri 命令 · pipeline 7 步定义 + 运行时 (M3.2)
//!
//! 支持的 commands:
//! - `pipeline_step_defs` 查询预置 7 步元数据
//! - 启动 (`pipeline_start`) 把 7 步流水线 spawn 成 tokio 任务,立刻返回
//! - 取消 (`pipeline_cancel`) / 重设 (`pipeline_reset`) / 状态查询 (`pipeline_status`)

use std::path::PathBuf;
use std::sync::Arc;

use splicr_compose::executors::PipelineDeps;
use splicr_compose::service::{PipelineService, PipelineStatus};
use splicr_compose::{Project, StepDef, STEPS};
use splicr_core::services::{ConfigService, ConfigSnapshot};
use splicr_core::AppContext;
use splicr_detect::Ffmpeg;
use splicr_script::factory;
use splicr_script::LlmProviderKind;
use splicr_voice::engine;
use splicr_voice::{
    EdgeTtsOptions, GptSovitsOptions, MimoTtsOptions, OpenAiTtsOptions, TtsEngineConfig,
    TtsProviderKind,
};
use tauri::{Emitter, State};

/// 5 步定义查询
#[tauri::command]
pub fn pipeline_step_defs() -> Vec<StepDef> {
    STEPS.to_vec()
}

/// 状态快照 (前端 polling)
#[tauri::command]
pub async fn pipeline_status(state: State<'_, AppContext>) -> Result<PipelineStatus, String> {
    let svc = state
        .service::<PipelineService>()
        .await
        .map_err(|e| e.to_string())?;
    Ok(svc.status().await)
}

/// 启动流水线 (后台任务 + 事件桥接)
#[tauri::command]
pub async fn pipeline_start(
    app: tauri::AppHandle,
    state: State<'_, AppContext>,
    project: Project,
    workdir: Option<String>,
) -> Result<(), String> {
    let svc = state
        .service::<PipelineService>()
        .await
        .map_err(|e| e.to_string())?;

    // 取配置
    let config_svc = state
        .service::<ConfigService>()
        .await
        .map_err(|e| e.to_string())?;
    let config = config_svc.snapshot().await;

    // 构造依赖
    let deps = build_deps(config, workdir).map_err(|e| e.to_string())?;
    svc.start(project, Arc::new(deps))
        .await
        .map_err(|e| e.to_string())?;

    // 事件桥接:一次性 task,把 broadcast → Tauri event
    let mut rx = svc.subscribe();
    let app_clone = app.clone();
    tokio::spawn(async move {
        loop {
            match rx.recv().await {
                Ok(event) => {
                    if let Err(e) = app_clone.emit("pipeline:event", &event) {
                        tracing::warn!("emit pipeline:event 失败: {e}");
                    }
                }
                Err(tokio::sync::broadcast::error::RecvError::Lagged(skipped)) => {
                    tracing::warn!("pipeline 事件接收 lagged, 跳过 {skipped}");
                }
                Err(tokio::sync::broadcast::error::RecvError::Closed) => break,
            }
        }
    });

    Ok(())
}

/// 取消 (下一步边界生效)
#[tauri::command]
pub async fn pipeline_cancel(state: State<'_, AppContext>) -> Result<(), String> {
    let svc = state
        .service::<PipelineService>()
        .await
        .map_err(|e| e.to_string())?;
    svc.cancel();
    Ok(())
}

/// 重置回 Idle
#[tauri::command]
pub async fn pipeline_reset(state: State<'_, AppContext>) -> Result<(), String> {
    let svc = state
        .service::<PipelineService>()
        .await
        .map_err(|e| e.to_string())?;
    svc.reset().await;
    Ok(())
}

// ── helpers ───────────────────────────────────────────────────────────

fn build_deps(
    config: ConfigSnapshot,
    workdir: Option<String>,
) -> Result<PipelineDeps, Box<dyn std::error::Error + Send + Sync>> {
    // LLM
    let llm = match LlmProviderKind::from_str(&config.llm_provider) {
        Some(kind) => {
            let api_key = config.llm_api_key.clone().unwrap_or_default();
            let base_url = config.llm_base_url.clone();
            let model = config.llm_model.clone();
            let provider = factory(kind, api_key);
            // 允许前端覆盖 base_url/model (本地 / 代理)
            if let (Some(_), Some(_)) = (base_url.as_ref(), model.as_ref()) {
                // 注: 11 个 Provider 大多支持 base_url/model 字段覆盖,这里不再扩展
            }
            Some(provider)
        }
        None => None,
    };

    // TTS
    let tts = match config
        .tts_provider
        .as_deref()
        .and_then(TtsProviderKind::from_str)
    {
        Some(TtsProviderKind::Edge) => Some(engine(TtsEngineConfig::Edge(EdgeTtsOptions {
            voice: config
                .tts_voice
                .clone()
                .unwrap_or_else(|| "zh-CN-XiaoxiaoNeural".into()),
        }))),
        Some(TtsProviderKind::OpenAi) => Some(engine(TtsEngineConfig::OpenAi(OpenAiTtsOptions {
            api_key: config
                .tts_api_key
                .clone()
                .or_else(|| config.llm_api_key.clone())
                .unwrap_or_default(),
            base_url: config
                .tts_base_url
                .clone()
                .or_else(|| config.llm_base_url.clone())
                .unwrap_or_else(|| "https://api.openai.com".into()),
            model: config.llm_model.clone().unwrap_or_else(|| "tts-1".into()),
            voice: config.tts_voice.clone().unwrap_or_else(|| "alloy".into()),
        }))),
        Some(TtsProviderKind::Mimo) => Some(engine(TtsEngineConfig::Mimo(MimoTtsOptions {
            api_key: config
                .tts_api_key
                .clone()
                .or_else(|| config.llm_api_key.clone())
                .unwrap_or_default(),
            base_url: config
                .tts_base_url
                .clone()
                .or_else(|| config.llm_base_url.clone())
                .unwrap_or_else(|| "https://api.xiaomimimo.com/v1".into()),
            model: config
                .tts_voice
                .clone()
                .unwrap_or_else(|| "mimo-v2.5-tts".into()),
            voice: config.tts_voice.clone().unwrap_or_else(|| "default".into()),
        }))),
        Some(TtsProviderKind::GptSovits) => {
            Some(engine(TtsEngineConfig::GptSovits(GptSovitsOptions {
                base_url: config
                    .tts_base_url
                    .clone()
                    .or_else(|| config.llm_base_url.clone())
                    .unwrap_or_else(|| "http://127.0.0.1:9880".into()),
                ref_audio_path: config.tts_ref_audio_path.clone().unwrap_or_default(),
                prompt_text: config.tts_prompt_text.clone().unwrap_or_default(),
                prompt_lang: "zh".into(),
            })))
        }
        None => None,
    };

    // FFmpeg (可选,缺失也能启动流水线,相关步骤会报错)
    let ffmpeg = Ffmpeg::discover().ok().map(Arc::new);

    Ok(PipelineDeps {
        llm,
        tts,
        ffmpeg,
        workdir: workdir
            .map(PathBuf::from)
            .unwrap_or_else(|| std::env::temp_dir().join("splicr-workdir")),
    })
}

trait ProviderKindExt {
    fn from_str(s: &str) -> Option<Self>
    where
        Self: Sized;
}

impl ProviderKindExt for LlmProviderKind {
    fn from_str(s: &str) -> Option<Self> {
        match s {
            "qwen" => Some(Self::Qwen),
            "kimi" => Some(Self::Kimi),
            "glm5" => Some(Self::Glm5),
            "claude" => Some(Self::Claude),
            "gemini" => Some(Self::Gemini),
            "deepseek" => Some(Self::DeepSeek),
            "doubao" => Some(Self::Doubao),
            "hunyuan" => Some(Self::Hunyuan),
            "local" => Some(Self::Local),
            "open-ai" | "openai" => Some(Self::OpenAi),
            "qwen37" => Some(Self::Qwen37),
            _ => None,
        }
    }
}

impl ProviderKindExt for TtsProviderKind {
    fn from_str(s: &str) -> Option<Self> {
        match s {
            "edge" => Some(Self::Edge),
            "open-ai" | "openai" => Some(Self::OpenAi),
            "gpt-sovits" => Some(Self::GptSovits),
            _ => None,
        }
    }
}

// ── 抑制编译警告 ──────────────────────────────────────────────────────

#[allow(dead_code)]
fn _silence_unused(_config: ConfigSnapshot) {}
