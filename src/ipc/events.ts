/**
 * Monoloop v1.0.0 · IPC Events 类型化包装
 *
 * 设计 (README §06 + §07):
 * - 24 个 events 按业务域分组,每个方法返回一个取消订阅函数
 * - 编译期类型: payload 自动从 types.gen.ts 的 IpcEvent 联合推导
 * - 后端通过 tokio::sync::broadcast::Sender<T> 推送 → 前端 listen<T>() 订阅
 *
 * 当前阶段 (M2):
 * - 占位为主,真实实现在 M3 5 步流水线 + M4 素材导入 + M5 升级时逐个填实
 */

import { listen, type UnlistenFn } from "@tauri-apps/api/event";
import type { IpcEvent } from "./types.gen";

// ─────────────────────────────────────────────────────────────────────────
// 内部 helper: 统一包装 listen<event>,返回 unlisten 句柄
// ─────────────────────────────────────────────────────────────────────────

async function subscribe<E extends IpcEvent>(
  event: E,
  handler: (payload: unknown) => void,
): Promise<UnlistenFn> {
  return listen<unknown>(event, (e) => handler(e.payload));
}

// ─────────────────────────────────────────────────────────────────────────
// pipeline · 5 步进度推送 (6 events · M2 占位)
// ─────────────────────────────────────────────────────────────────────────

export const pipelineEvents = {
  /** 任一步开始 */
  stepStarted: (h: (p: unknown) => void) =>
    subscribe("pipeline:step_started", h),
  /** 任一步完成 */
  stepCompleted: (h: (p: unknown) => void) =>
    subscribe("pipeline:step_completed", h),
  /** 任一步失败 */
  stepFailed: (h: (p: unknown) => void) => subscribe("pipeline:step_failed", h),
  /** 整体进度 0-100 */
  progress: (h: (p: unknown) => void) => subscribe("pipeline:progress", h),
  /** 日志行流式 */
  log: (h: (p: unknown) => void) => subscribe("pipeline:log", h),
  /** 整流水线完成 */
  finished: (h: (p: unknown) => void) => subscribe("pipeline:finished", h),
} as const;

// ─────────────────────────────────────────────────────────────────────────
// assets · 素材导入进度 (4 events · M4 占位)
// ─────────────────────────────────────────────────────────────────────────

export const assetsEvents = {
  imported: (h: (p: unknown) => void) => subscribe("assets:imported", h),
  thumbnailReady: (h: (p: unknown) => void) =>
    subscribe("assets:thumbnail_ready", h),
  scanProgress: (h: (p: unknown) => void) =>
    subscribe("assets:scan_progress", h),
  removed: (h: (p: unknown) => void) => subscribe("assets:removed", h),
} as const;

// ─────────────────────────────────────────────────────────────────────────
// updater · 升级进度 (5 events · M5 占位)
// ─────────────────────────────────────────────────────────────────────────

export const updaterEvents = {
  available: (h: (p: unknown) => void) => subscribe("updater:available", h),
  downloading: (h: (p: unknown) => void) => subscribe("updater:downloading", h),
  downloadProgress: (h: (p: unknown) => void) =>
    subscribe("updater:download_progress", h),
  ready: (h: (p: unknown) => void) => subscribe("updater:ready", h),
  error: (h: (p: unknown) => void) => subscribe("updater:error", h),
} as const;

// ─────────────────────────────────────────────────────────────────────────
// app · 系统级事件 (9 events · M3+ 占位)
// ─────────────────────────────────────────────────────────────────────────

export const appEvents = {
  themeChanged: (h: (p: unknown) => void) => subscribe("app:theme_changed", h),
  localeChanged: (h: (p: unknown) => void) =>
    subscribe("app:locale_changed", h),
  windowFocus: (h: (p: unknown) => void) => subscribe("app:window_focus", h),
  configReloaded: (h: (p: unknown) => void) =>
    subscribe("app:config_reloaded", h),
  secureKeyRotated: (h: (p: unknown) => void) =>
    subscribe("app:secure_key_rotated", h),
  serviceStarted: (h: (p: unknown) => void) =>
    subscribe("app:service_started", h),
  serviceStopped: (h: (p: unknown) => void) =>
    subscribe("app:service_stopped", h),
  errorReported: (h: (p: unknown) => void) =>
    subscribe("app:error_reported", h),
  logFlushed: (h: (p: unknown) => void) => subscribe("app:log_flushed", h),
} as const;

export const events = {
  pipeline: pipelineEvents,
  assets: assetsEvents,
  updater: updaterEvents,
  app: appEvents,
} as const;

export type EventsFacade = typeof events;
