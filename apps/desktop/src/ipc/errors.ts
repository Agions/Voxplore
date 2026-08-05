/**
 * SceneFab v3.0 · SceneFabError → 用户可读
 *
 * 设计 (README §06):
 * - 后端 9 类 SceneFabError (Io/Config/Llm/Tts/Ffmpeg/Project/Pipeline/Plugin/Updater/Other)
 *   序列化为 { kind, message } 抛到前端
 * - 此层负责:
 *   1) 错误归类 (kind → 人类可读 category,用于 UI 提示与埋点)
 *   2) i18n key 派生 (category → t() 的命名空间)
 *   3) 是否可重试 (Llm/Tts/Ffmpeg/Io 一般可重试,Config/Project 一般不可)
 *   4) 安全脱敏 (message 中的密钥/api_key/token 截断显示)
 */

import type { SceneFabError } from "./types.gen";

/** 错误归类:决定 i18n 命名空间与是否弹 toast */
export type ErrorCategory =
  | "io" // 文件/网络 I/O
  | "config" // 配置错误 (用户可改)
  | "llm" // LLM 调用失败 (可重试)
  | "tts" // TTS 合成失败 (可重试)
  | "ffmpeg" // 视频处理失败 (可重试)
  | "project" // 项目结构错误
  | "pipeline" // 流水线编排错误
  | "plugin" // 插件加载/调用错误
  | "updater" // 升级错误
  | "other"; // 兜底

export const ERROR_CATEGORY: Record<SceneFabError["kind"], ErrorCategory> = {
  io: "io",
  config: "config",
  llm: "llm",
  tts: "tts",
  ffmpeg: "ffmpeg",
  project: "project",
  pipeline: "pipeline",
  plugin: "plugin",
  updater: "updater",
  other: "other",
};

/** 是否可重试 (调用方按这个决定 UI 是否显示 "重试" 按钮) */
export const RETRYABLE: Record<ErrorCategory, boolean> = {
  io: true,
  config: false,
  llm: true,
  tts: true,
  ffmpeg: true,
  project: false,
  pipeline: false,
  plugin: false,
  updater: true,
  other: false,
};

/** i18n key 前缀 (用于 t(`errors.${category}.${subKey}`)) */
export function i18nKey(err: SceneFabError, subKey = "title"): string {
  return `errors.${ERROR_CATEGORY[err.kind]}.${subKey}`;
}

/** 脱敏:截断可能的密钥/api_key/token 片段,避免直接暴露到 UI/log */
export function safeMessage(err: SceneFabError): string {
  let msg = err.message;
  // 截断常见敏感模式
  msg = msg.replace(
    /(api[_-]?key|secret|token|password|bearer)\s*[=:]\s*\S+/gi,
    "$1=<redacted>",
  );
  // 截断过长的堆栈(只保留前 4 行)
  const lines = msg.split(/\r?\n/);
  if (lines.length > 4) {
    msg = `${lines.slice(0, 4).join("\n")}\n…(${lines.length - 4} more lines)`;
  }
  return msg;
}

/** 组合 helper:给 UI 一行内可见的"分类:摘要" */
export function formatError(err: SceneFabError): string {
  const cat = ERROR_CATEGORY[err.kind];
  return `[${cat}] ${safeMessage(err)}`;
}

/** 类型守卫:把任意 thrown 值还原成 SceneFabError */
export function asSceneFabError(err: unknown): SceneFabError {
  if (
    err &&
    typeof err === "object" &&
    "kind" in err &&
    "message" in err &&
    typeof (err as { kind: unknown }).kind === "string" &&
    typeof (err as { message: unknown }).message === "string"
  ) {
    return err as SceneFabError;
  }
  return {
    kind: "other",
    message: err instanceof Error ? err.message : String(err),
  };
}
