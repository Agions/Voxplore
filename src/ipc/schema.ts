/**
 * Monoloop v1.0.0 · IPC 命令 / 事件名称常量
 *
 * 设计:
 * - 单一来源: Rust 端 command 名与 event 名,这里只导出可读的"引用常量"
 * - 用于: log/埋点/i18n 错误信息等需要"人类可读"标识的地方
 * - 不替代 types.gen.ts 的 IpcCommand/IpcEvent 联合类型
 *   (类型依旧是真正的单一来源,常量只是别名)
 */

import type { IpcCommand, IpcEvent } from "./types.gen";

// ─────────────────────────────────────────────────────────────────────────
// 命令常量
// ─────────────────────────────────────────────────────────────────────────

export const CMD = {
  appVersion: "app_version" satisfies IpcCommand,
  appStartedAt: "app_started_at" satisfies IpcCommand,
  projectListRecent: "project_list_recent" satisfies IpcCommand,
  projectCreateBlank: "project_create_blank" satisfies IpcCommand,
  pipelineStepDefs: "pipeline_step_defs" satisfies IpcCommand,
} as const;

export type Cmd = (typeof CMD)[keyof typeof CMD];

// ─────────────────────────────────────────────────────────────────────────
// 事件常量
// ─────────────────────────────────────────────────────────────────────────

export const EVT = {
  pipelineStepStarted: "pipeline:step_started" satisfies IpcEvent,
  pipelineStepCompleted: "pipeline:step_completed" satisfies IpcEvent,
  pipelineStepFailed: "pipeline:step_failed" satisfies IpcEvent,
  pipelineProgress: "pipeline:progress" satisfies IpcEvent,
  pipelineLog: "pipeline:log" satisfies IpcEvent,
  pipelineFinished: "pipeline:finished" satisfies IpcEvent,
  assetsImported: "assets:imported" satisfies IpcEvent,
  assetsThumbnailReady: "assets:thumbnail_ready" satisfies IpcEvent,
  assetsScanProgress: "assets:scan_progress" satisfies IpcEvent,
  assetsRemoved: "assets:removed" satisfies IpcEvent,
  updaterAvailable: "updater:available" satisfies IpcEvent,
  updaterDownloading: "updater:downloading" satisfies IpcEvent,
  updaterDownloadProgress: "updater:download_progress" satisfies IpcEvent,
  updaterReady: "updater:ready" satisfies IpcEvent,
  updaterError: "updater:error" satisfies IpcEvent,
  appThemeChanged: "app:theme_changed" satisfies IpcEvent,
  appLocaleChanged: "app:locale_changed" satisfies IpcEvent,
  appWindowFocus: "app:window_focus" satisfies IpcEvent,
  appConfigReloaded: "app:config_reloaded" satisfies IpcEvent,
  appSecureKeyRotated: "app:secure_key_rotated" satisfies IpcEvent,
  appServiceStarted: "app:service_started" satisfies IpcEvent,
  appServiceStopped: "app:service_stopped" satisfies IpcEvent,
  appErrorReported: "app:error_reported" satisfies IpcEvent,
  appLogFlushed: "app:log_flushed" satisfies IpcEvent,
} as const;

export type Evt = (typeof EVT)[keyof typeof EVT];
