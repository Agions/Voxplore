// splicr v1.0.0 · Tauri 入口
//
// 业务覆盖:
//! - app: app_version / app_started_at / app_system_info
//! - project: project_list_recent / project_create_blank / project_load /
//!   project_save / project_delete / project_add_media
//! - pipeline: pipeline_step_defs / pipeline_status / pipeline_start /
//!   pipeline_cancel / pipeline_reset
//! - settings: settings_get / settings_set
//! - update: update_get_state / update_check / update_download /
//!   update_install / update_reset
//! - assets: assets_scan / assets_metadata / assets_thumbnail /
//!   assets_search (M3 后续完整实装)
//! - export: export_plan / export_validate_params / export_render_subtitles /
//!   video_build_plans
//! - help: help_topics / help_topic_get / help_search (M5.7 接 splicr-help)
//! - theme: i18n_get_locale / i18n_set_locale / i18n_translate (M5.6 接 splicr-i18n)
//
// PipelineService + UpdateService + AssetService 在 AppContext::new() 后注册进 ServiceContainer。
// Translator + HelpRegistry 通过 .manage() 直注,提供轻量全局状态。

#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

mod commands;

use std::sync::Arc;

use splicr_compose::service::PipelineService;
use splicr_core::AppContext;
use splicr_core::HelpRegistry;
use splicr_core::Translator;
use splicr_storage::AssetService;
use splicr_update::UpdateService;

/// 占位命令 — 保留以便兼容 Gate 0 冒烟测试
#[tauri::command]
fn greet(name: &str) -> String {
    format!("Hello, {name}! 你正在使用 splicr v1.0.0")
}

/// Tauri 入口（mobile 端另开 entry point）
#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    // 初始化 logging (OnceLock idem-potent 调度)
    splicr_core::init_logging();

    // 构造 AppContext + 在同步上下文中启动 runtime
    let (ctx, services_count) = tokio::runtime::Builder::new_multi_thread()
        .enable_all()
        .build()
        .expect("tokio runtime for app context")
        .block_on(async {
            let ctx = AppContext::new().await;
            // 注入 PipelineService (M3.2 真实运行时)
            ctx.services
                .register(Arc::new(PipelineService::new()))
                .await;
            // 注入 UpdateService
            ctx.services
                .register(Arc::new(UpdateService::new(
                    ctx.version.to_string(),
                    "Agions/splicr",
                )))
                .await;
            // 注入 AssetService (M3 后续完整实装)
            ctx.services.register(Arc::new(AssetService::new())).await;
            // 在 async 上下文里拿到注册计数 (留给 sync 入口打 log 用)
            let count = ctx.services.len().await;
            (ctx, count)
        });

    tracing::info!(
        version = %ctx.version,
        debug = ctx.debug,
        services = services_count,
        "splicr v1.0.0 starting"
    );

    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_dialog::init())
        .manage(ctx)
        // 轻量全局状态
        .manage(Translator::with_backend_defaults())
        .manage(HelpRegistry::with_defaults())
        .invoke_handler(tauri::generate_handler![
            greet,
            commands::app::app_version,
            commands::app::app_started_at,
            commands::app::app_system_info,
            commands::project::project_list_recent,
            commands::project::project_create_blank,
            commands::project::project_load,
            commands::project::project_save,
            commands::project::project_delete,
            commands::project::project_add_media,
            commands::pipeline::pipeline_step_defs,
            commands::pipeline::pipeline_status,
            commands::pipeline::pipeline_start,
            commands::pipeline::pipeline_cancel,
            commands::pipeline::pipeline_reset,
            commands::settings::settings_get,
            commands::settings::settings_set,
            commands::update::update_get_state,
            commands::update::update_check,
            commands::update::update_download,
            commands::update::update_install,
            commands::update::update_reset,
            commands::assets::assets_scan,
            commands::assets::assets_metadata,
            commands::assets::assets_thumbnail,
            commands::assets::assets_search,
            commands::export::export_plan,
            commands::export::export_validate_params,
            commands::export::export_render_subtitles,
            commands::export::video_build_plans,
            commands::help::help_topics,
            commands::help::help_topic_get,
            commands::help::help_search,
            commands::theme::i18n_get_locale,
            commands::theme::i18n_set_locale,
            commands::theme::i18n_translate,
            commands::voice::voice_preview,
            commands::voice::voice_synthesize,
            commands::script::script_generate,
            commands::detect::detect_scenes,
            commands::subtitle::subtitle_generate,
            commands::export::export_capcut_draft,
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
