/**
 * Monoloop v1.0.0 · IPC Commands 类型化包装
 *
 * 设计:
 * - 每个方法直接对应一个 Tauri command,compile-time 类型由 types.gen.ts 保障
 * - 此层不持有状态、不缓存;纯函数式 facade
 * - 全部 35 个 commands 在 M4.5 已落地 (M3.2: 17 + M4: 5 update + M4.5: 10 export/help/theme)
 */

import { callIpc } from "./client";
import type {
  AppSystemInfo,
  ConfigSnapshot,
  ExportMode,
  ExportParams,
  ExportStrategy,
  FfmpegProbe,
  HelpCategory,
  HelpTopic,
  MediaFile,
  OutputPlan,
  PipelineStatus,
  PipelineStepDef,
  PlanOptions,
  Project,
  ProjectRecord,
  ProjectSettings,
  ScanResult,
  ScriptGenerateParams,
  ScriptGenerateResult,
  SearchHit,
  SubtitleFormat,
  SubtitleItem,
  ThumbnailResult,
  CapcutDraftResult,
  DetectScenesResult,
  SubtitleGenerateParams,
  SubtitleGenerateResult,
  UpdateInfo,
  UpdateInstallResult,
  UpdateState,
  VoicePreviewParams,
  VoicePreviewResult,
} from "./types.gen";

// 类型 re-export (业务侧只用 ipc/commands 一处入口)
export type { ProjectRecord, ConfigSnapshot } from "./types.gen";

// ─────────────────────────────────────────────────────────────────────────
// app · 应用信息 (3/3)
// ─────────────────────────────────────────────────────────────────────────

export const appIpc = {
  version: () => callIpc("app_version"),
  startedAt: () => callIpc("app_started_at"),
  systemInfo: (): Promise<AppSystemInfo> => callIpc("app_system_info"),
} as const;

// ─────────────────────────────────────────────────────────────────────────
// project · 项目管理 (6/6)
// ─────────────────────────────────────────────────────────────────────────

export const projectIpc = {
  listRecent: () => callIpc("project_list_recent"),
  createBlank: (): Promise<ProjectRecord> => callIpc("project_create_blank"),
  load: (path: string): Promise<ProjectRecord> =>
    callIpc("project_load", { path }),
  save: (path: string, project: Project): Promise<void> =>
    callIpc("project_save", { path, project }),
  remove: (path: string): Promise<void> => callIpc("project_delete", { path }),
  addMedia: (
    path: string,
    project: Project,
    media: MediaFile,
  ): Promise<Project> => callIpc("project_add_media", { path, project, media }),
} as const;

// ─────────────────────────────────────────────────────────────────────────
// pipeline · 5 步流水线 (5/5)
// ─────────────────────────────────────────────────────────────────────────

export const pipelineIpc = {
  stepDefs: (): Promise<PipelineStepDef[]> => callIpc("pipeline_step_defs"),
  status: (): Promise<PipelineStatus> => callIpc("pipeline_status"),
  start: (project: Project, workdir?: string): Promise<void> =>
    callIpc("pipeline_start", { project, workdir: workdir ?? null }),
  cancel: (): Promise<void> => callIpc("pipeline_cancel"),
  reset: (): Promise<void> => callIpc("pipeline_reset"),
} as const;

// ─────────────────────────────────────────────────────────────────────────
// settings · 配置与密钥 (2/2)
// ─────────────────────────────────────────────────────────────────────────

export const settingsIpc = {
  get: (): Promise<ConfigSnapshot> => callIpc("settings_get"),
  set: (snapshot: ConfigSnapshot): Promise<void> =>
    callIpc("settings_set", { snapshot }),
} as const;

// ─────────────────────────────────────────────────────────────────────────
// update · 应用更新器 (5/5 · M4 完整实装)
// ─────────────────────────────────────────────────────────────────────────

export const updateIpc = {
  getState: (): Promise<UpdateState> => callIpc("update_get_state"),
  check: (): Promise<UpdateInfo> => callIpc("update_check"),
  download: (): Promise<string> => callIpc("update_download"),
  install: (): Promise<UpdateInstallResult> => callIpc("update_install"),
  reset: (): Promise<void> => callIpc("update_reset"),
} as const;

// ─────────────────────────────────────────────────────────────────────────
// assets · 素材资产管理 (4/4 · M3 后续完整实装)
// ─────────────────────────────────────────────────────────────────────────

export const assetsIpc = {
  scan: (dir: string, recursive = false): Promise<ScanResult> =>
    callIpc("assets_scan", { dir, recursive }),
  metadata: (path: string): Promise<FfmpegProbe> =>
    callIpc("assets_metadata", { path }),
  thumbnail: (path: string, width = 320): Promise<ThumbnailResult> =>
    callIpc("assets_thumbnail", { path, width }),
  search: (mediaPaths: string[], pattern: string): Promise<string[]> =>
    callIpc("assets_search", { mediaPaths, pattern }),
} as const;

// ─────────────────────────────────────────────────────────────────────────
// export · 导出参数规划 + 字幕渲染 + 多视频编排
// ─────────────────────────────────────────────────────────────────────────

export const exportIpc = {
  plan: (mode: ExportMode, settings?: ProjectSettings | null) =>
    callIpc("export_plan", { mode, settings: settings ?? null }),
  validateParams: (params: ExportParams) =>
    callIpc("export_validate_params", { params }),
  renderSubtitles: (items: SubtitleItem[], format: SubtitleFormat) =>
    callIpc("export_render_subtitles", { items, format }),
  capcutDraft: (projectName: string, targetDir?: string | null): Promise<CapcutDraftResult> =>
    callIpc("export_capcut_draft", { projectName, targetDir: targetDir ?? null }),
} as const;

export const detectIpc = {
  scenes: (filePath: string, threshold?: number | null): Promise<DetectScenesResult> =>
    callIpc("detect_scenes", { filePath, threshold: threshold ?? null }),
} as const;

export const subtitleIpc = {
  generate: (params: SubtitleGenerateParams): Promise<SubtitleGenerateResult> =>
    callIpc("subtitle_generate", { params }),
} as const;

export const videoIpc = {
  buildPlans: (
    sources: string[],
    strategy: ExportStrategy,
    options?: PlanOptions | null,
  ): Promise<OutputPlan[]> =>
    callIpc("video_build_plans", {
      sources,
      strategy,
      options: options ?? null,
    }),
} as const;

// ─────────────────────────────────────────────────────────────────────────
// help · 内置帮助主题 + 加权搜索 (3/3 · M5.7 接 monoloop-help)
// ─────────────────────────────────────────────────────────────────────────

export const helpIpc = {
  topics: (category?: HelpCategory | null): Promise<HelpTopic[]> =>
    callIpc("help_topics", { category: category ?? null }),
  topicGet: (id: string): Promise<HelpTopic> =>
    callIpc("help_topic_get", { id }),
  search: (query: string): Promise<SearchHit[]> =>
    callIpc("help_search", { query }),
} as const;

// ─────────────────────────────────────────────────────────────────────────
// theme · 后端文案 / Locale 切换 (3/3 · M5.6 接 monoloop-i18n)
// ─────────────────────────────────────────────────────────────────────────

export const themeIpc = {
  getLocale: (): Promise<string> => callIpc("i18n_get_locale"),
  setLocale: (locale: string): Promise<boolean> =>
    callIpc("i18n_set_locale", { locale }),
  translate: (
    key: string,
    args?: Record<string, string> | null,
  ): Promise<string> => callIpc("i18n_translate", { key, args: args ?? null }),
} as const;

// ─────────────────────────────────────────────────────────────────────────
// voice · TTS 试听与合成
// ─────────────────────────────────────────────────────────────────────────

export const voiceIpc = {
  preview: (params: VoicePreviewParams): Promise<VoicePreviewResult> =>
    callIpc("voice_preview", { params }),
  synthesize: (
    params: VoicePreviewParams,
    outputPath: string,
  ): Promise<VoicePreviewResult> =>
    callIpc("voice_synthesize", { params, outputPath }),
} as const;

// ─────────────────────────────────────────────────────────────────────────
// script · AI 独白脚本生成
// ─────────────────────────────────────────────────────────────────────────

export const scriptIpc = {
  generate: (params: ScriptGenerateParams): Promise<ScriptGenerateResult> =>
    callIpc("script_generate", { params }),
} as const;

// ─────────────────────────────────────────────────────────────────────────
// 聚合 facade
// ─────────────────────────────────────────────────────────────────────────

export const ipc = {
  app: appIpc,
  project: projectIpc,
  pipeline: pipelineIpc,
  settings: settingsIpc,
  update: updateIpc,
  assets: assetsIpc,
  export: exportIpc,
  video: videoIpc,
  help: helpIpc,
  theme: themeIpc,
  voice: voiceIpc,
  script: scriptIpc,
} as const;

export type IpcFacade = typeof ipc;
