/**
 * Vynaro v1.0.0 · Tauri Command 类型契约 (单源真相)
 *
 * M3+ 由 pnpm `gen:ipc` 自动生成两段:
 *   - "gen-ipc start" 标记: IpcContracts (commands/*.rs 的 #[tauri::command] 函数)
 *   - "gen-ipc-types start" 标记: pub struct/enum 类型定义
 *
 * 设计原则:
 * - 与 apps/desktop/src-tauri/src/commands/*.rs 1:1 对应
 * - 字段命名严格 camelCase (Rust 命令参数序列化策略)
 * - 错误统一从 VynaroError JSON 反序列化
 */

// ────────────────────────────────────────────────────────────────────────
// 保留类型 (手工维护 · 与 IPC 无关或 wire 格式有特殊 override)
// ────────────────────────────────────────────────────────────────────────

/** LLM 提供商 (前后端手工约定 "deepseek" 而非 serde 默认的 "deep-seek") */
export type LlmProviderKind =
  | "qwen"
  | "kimi"
  | "glm5"
  | "claude"
  | "gemini"
  | "deepseek"
  | "doubao"
  | "hunyuan"
  | "local"
  | "open-ai"
  | "qwen37";

// ────────────────────────────────────────────────────────────────────────
// 错误类型 (与 vynaro-core::VynaroError 手工 wire 格式 1:1)
// ────────────────────────────────────────────────────────────────────────

export interface VynaroError {
  kind:
    | "io"
    | "config"
    | "llm"
    | "tts"
    | "ffmpeg"
    | "project"
    | "pipeline"
    | "plugin"
    | "updater"
    | "other";
  message: string;
}

export type CommandResult<T> = T;
export type CommandError = VynaroError | { error: VynaroError };

/* >>> gen-ipc start */
export interface IpcContracts {
  greet: {
    args: { name: string };
    result: string;
  };
  // ─────── app · 3 个 ───────
  app_started_at: {
    args: void;
    result: string;
  };
  app_system_info: {
    args: void;
    result: AppSystemInfo;
  };
  app_version: {
    args: void;
    result: string;
  };
  // ─────── project · 10 个 ───────
  project_add_media: {
    args: {
      path: string;
      project: Project;
      media: MediaFile;
    };
    result: Project;
  };
  project_create_blank: {
    args: void;
    result: ProjectRecord;
  };
  project_delete: {
    args: {
      path: string;
    };
    result: void;
  };
  project_list_recent: {
    args: void;
    result: string[];
  };
  project_load: {
    args: {
      path: string;
    };
    result: ProjectRecord;
  };
  project_save: {
    args: {
      path: string;
      project: Project;
    };
    result: void;
  };
  // ─────── pipeline · 5 个 ───────
  pipeline_cancel: {
    args: void;
    result: void;
  };
  pipeline_reset: {
    args: void;
    result: void;
  };
  pipeline_start: {
    args: {
      project: Project;
      workdir: string | null;
    };
    result: void;
  };
  pipeline_status: {
    args: void;
    result: PipelineStatus;
  };
  pipeline_step_defs: {
    args: void;
    result: PipelineStepDef[];
  };
  // ─────── settings · 2 个 ───────
  settings_get: {
    args: void;
    result: ConfigSnapshot;
  };
  settings_set: {
    args: {
      snapshot: ConfigSnapshot;
    };
    result: void;
  };
  // ─────── update · 5 个 ───────
  update_check: {
    args: void;
    result: UpdateInfo;
  };
  update_download: {
    args: void;
    result: string;
  };
  update_get_state: {
    args: void;
    result: UpdateState;
  };
  update_install: {
    args: void;
    result: UpdateInstallResult;
  };
  update_reset: {
    args: void;
    result: void;
  };
  // ─────── assets · 4 个 ───────
  assets_metadata: {
    args: {
      path: string;
    };
    result: FfmpegProbe;
  };
  assets_scan: {
    args: {
      dir: string;
      recursive: boolean | null;
    };
    result: ScanResult;
  };
  assets_search: {
    args: {
      mediaPaths: string[];
      pattern: string;
    };
    result: string[];
  };
  assets_thumbnail: {
    args: {
      path: string;
      width: number | null;
    };
    result: ThumbnailResult;
  };
  // ─────── export · 4 个 ───────
  export_capcut_draft: {
    args: {
      projectName: string;
      targetDir: string | null;
    };
    result: CapcutDraftResult;
  };
  export_plan: {
    args: {
      mode: ExportMode;
      settings: ProjectSettings | null;
    };
    result: ExportPlan;
  };
  export_render_subtitles: {
    args: {
      items: SubtitleItem[];
      format: SubtitleFormat;
    };
    result: string;
  };
  export_validate_params: {
    args: {
      params: ExportParams;
    };
    result: void;
  };
  // ─────── help · 3 个 ───────
  help_search: {
    args: {
      query: string;
    };
    result: SearchHit[];
  };
  help_topic_get: {
    args: {
      id: string;
    };
    result: HelpTopic;
  };
  help_topics: {
    args: {
      category: string | null;
    };
    result: HelpTopic[];
  };
  // ─────── voice · 2 个 ───────
  voice_preview: {
    args: {
      params: VoicePreviewParams;
    };
    result: VoicePreviewResult;
  };
  voice_synthesize: {
    args: {
      params: VoicePreviewParams;
      outputPath: string;
    };
    result: VoicePreviewResult;
  };
  // ─────── script · 1 个 ───────
  script_generate: {
    args: {
      params: ScriptGenerateParams;
    };
    result: ScriptGenerateResult;
  };
  // ─────── detect · 1 个 ───────
  detect_scenes: {
    args: {
      filePath: string;
      threshold: number | null;
    };
    result: DetectScenesResult;
  };
  // ─────── subtitle · 1 个 ───────
  subtitle_generate: {
    args: {
      params: SubtitleGenerateParams;
    };
    result: SubtitleGenerateResult;
  };
  // ─────── video · 1 个 ───────
  video_build_plans: {
    args: {
      sources: string[];
      strategy: ExportStrategy;
      options: PlanOptions | null;
    };
    result: OutputPlan[];
  };
  // ─────── i18n · 3 个 ───────
  i18n_get_locale: {
    args: void;
    result: string;
  };
  i18n_set_locale: {
    args: {
      locale: string;
    };
    result: boolean;
  };
  i18n_translate: {
    args: {
      key: string;
      args: Record<string, string> | null;
    };
    result: string;
  };
}
/* <<< gen-ipc end */

/* >>> gen-ipc-types start */
// Rust 端 SystemInfo (pub struct, rename_all = "camelCase")
export interface AppSystemInfo {
  ffmpegAvailable: boolean;
  ffmpegVersion: string | null;
}

// Rust 端 DetectScenesResult (pub struct)
export interface DetectScenesResult {
  cuts: number[];
  total_cuts: number;
  probe: FfmpegProbe | null;
}

// Rust 端 CapcutDraftResult (pub struct)
export interface CapcutDraftResult {
  draft_folder: string;
  draft_id: string;
  created_at: string;
}

// Rust 端 ProjectRecord (pub struct, rename_all = "camelCase")
export interface ProjectRecord {
  path: string;
  project: Project;
}

// Rust 端 ScriptGenerateParams (pub struct)
export interface ScriptGenerateParams {
  provider: string;
  api_key: string | null;
  base_url: string | null;
  model: string | null;
  prompt: string;
  style: string | null;
  emotion_density: number | null;
  word_count_target: number | null;
}

// Rust 端 ScriptGenerateResult (pub struct)
export interface ScriptGenerateResult {
  text: string;
  word_count: number;
  estimated_duration_sec: number;
}

// Rust 端 SubtitleGenerateParams (pub struct)
export interface SubtitleGenerateParams {
  script_text: string;
  format: string;
}

// Rust 端 SubtitleGenerateResult (pub struct)
export interface SubtitleGenerateResult {
  content: string;
  format: string;
  item_count: number;
  items: SubtitleItem[];
}

// Rust 端 UpdateInstallResult (pub struct, rename_all = "camelCase")
export interface UpdateInstallResult {
  downloadedPath: string;
  note: string;
}

// Rust 端 VoicePreviewParams (pub struct)
export interface VoicePreviewParams {
  text: string;
  provider: string;
  voice: string | null;
  rate_percent: number;
  api_key: string | null;
  base_url: string | null;
  model: string | null;
  ref_audio_path: string | null;
  prompt_text: string | null;
}

// Rust 端 VoicePreviewResult (pub struct)
export interface VoicePreviewResult {
  file_path: string;
  format: string;
  bytes_written: number;
}

// Rust 端 StepDef (pub struct)
export interface PipelineStepDef {
  id: string;
  label_zh: string;
  description_zh: string;
}

// Rust 端 StepStatus (pub enum, rename_all = "kebab-case")
export type StepStatus =
  | "pending"
  | "active"
  | "done"
  | "error";

// Rust 端 PipelineState (pub enum, rename_all = "kebab-case")
export type PipelineState =
  | "idle"
  | "running"
  | "done"
  | "failed";

// Rust 端 PipelineStatus (pub struct, rename_all = "camelCase")
export interface PipelineStatus {
  state: PipelineState;
  stepStatuses: StepStatus[];
  currentStep: number;
  projectName: string | null;
}

// Rust 端 TtsProviderKind (pub enum, rename_all = "kebab-case")
export type TtsProviderKind =
  | "edge"
  | "open-ai"
  | "gpt-sovits";

// Rust 端 HelpTopic (pub struct)
export interface HelpTopic {
  id: string;
  title: string;
  summary: string | null;
  category: HelpCategory;
  keywords: string[];
  content: string;
  related: string[];
}

// Rust 端 SearchHit (pub struct)
export interface SearchHit {
  id: string;
  topic_id: string;
  title: string;
  score: number;
  snippet: string;
}

// Rust 端 HelpCategory (pub enum, rename_all = "kebab-case")
export type HelpCategory =
  | "guide"
  | "reference"
  | "shortcut"
  | "faq"
  | "troubleshooting";

// Rust 端 Locale (pub enum)
export type Locale =
  | "ZhCn"
  | "EnUs";

// Rust 端 ConfigSnapshot (pub struct)
export interface ConfigSnapshot {
  theme: string;
  language: string;
  llm_provider: string;
  auto_update: boolean;
  first_run: boolean;
  llm_api_key: string | null;
  llm_base_url: string | null;
  llm_model: string | null;
  tts_provider: string | null;
  tts_voice: string | null;
  tts_ref_audio_path: string | null;
  tts_prompt_text: string | null;
}

// Rust 端 ProjectSnapshot (pub struct)
export interface ProjectSnapshot {
  id: string;
  project_id: string;
  version_tag: string;
  kind: string;
  name: string;
  created_at: string;
  project_json: string;
}

// Rust 端 FfmpegProbe (pub struct, rename_all = "camelCase")
export interface FfmpegProbe {
  durationSeconds: number;
  width: number;
  height: number;
  videoCodec: string | null;
  audioCodec: string | null;
  sizeBytes: number;
}

// Rust 端 Project (pub struct)
export interface Project {
  id: string;
  name: string;
  created_at: string;
  updated_at: string;
  version: string;
  settings: ProjectSettings;
  media_files: MediaFile[];
  timeline: Timeline;
  scripts: ScriptSegment[];
  exports: ExportRecord[];
}

// Rust 端 ProjectSettings (pub struct)
export interface ProjectSettings {
  resolution: string;
  fps: number;
  bitrate: string;
  container: string;
  codec: string;
  four_strategy: ExportStrategy;
}

// Rust 端 MediaFile (pub struct)
export interface MediaFile {
  path: string;
  duration_seconds: number;
  resolution: string | null;
  codec: string | null;
  file_size_bytes: number;
  import_time: string;
}

// Rust 端 Timeline (pub struct)
export interface Timeline {
  tracks: Track[];
}

// Rust 端 Track (pub struct)
export interface Track {
  id: string;
  kind: TrackKind;
  clips: Clip[];
}

// Rust 端 Clip (pub struct)
export interface Clip {
  id: string;
  media_ref: string;
  start_seconds: number;
  in_seconds: number;
  out_seconds: number;
  volume: number | null;
}

// Rust 端 ScriptSegment (pub struct)
export interface ScriptSegment {
  id: string;
  step_index: number;
  text: string;
  emotion: string | null;
  start_seconds: number | null;
  end_seconds: number | null;
}

// Rust 端 ExportRecord (pub struct)
export interface ExportRecord {
  id: string;
  strategy: ExportStrategy;
  output_path: string;
  started_at: string;
  finished_at: string | null;
  success: boolean;
}

// Rust 端 TrackKind (pub enum, rename_all = "kebab-case")
export type TrackKind =
  | "video"
  | "audio"
  | "subtitle";

// Rust 端 ExportStrategy (pub enum, rename_all = "kebab-case")
export type ExportStrategy =
  | "single"
  | "concat"
  | "batch"
  | "series";

// Rust 端 ExportParams (pub struct)
export interface ExportParams {
  resolution: string;
  fps: number;
  bitrate: string;
  container: string;
  codec: string;
  include_audio: boolean;
}

// Rust 端 ExportPlan (pub struct)
export interface ExportPlan {
  mode: ExportMode;
  params: ExportParams;
  ffmpeg_args: string[];
}

// Rust 端 SubtitleItem (pub struct)
export interface SubtitleItem {
  start_seconds: number;
  end_seconds: number;
  text: string;
}

// Rust 端 ExportMode (pub enum, rename_all = "kebab-case")
export type ExportMode =
  | "quick"
  | "custom"
  | "silent";

// Rust 端 SubtitleFormat (pub enum, rename_all = "kebab-case")
export type SubtitleFormat =
  | "srt"
  | "ass"
  | "vtt";

// Rust 端 PlanOptions (pub struct)
export interface PlanOptions {
  base_name: string;
  series_context: string | null;
  episode_template: string;
}

// Rust 端 OutputPlan (pub struct)
export interface OutputPlan {
  name: string;
  ordered_sources: string[];
  episode_number: number | null;
  episode_label: string | null;
  series_context: string | null;
}

// Rust 端 AssetEntry (pub struct, rename_all = "camelCase")
export interface AssetEntry {
  path: string;
  sizeBytes: number;
  mime: string;
  kind: AssetKind;
}

// Rust 端 ScanResult (pub struct, rename_all = "camelCase")
export interface ScanResult {
  dir: string;
  total: number;
  entries: AssetEntry[];
  skipped: number;
}

// Rust 端 ThumbnailResult (pub struct, rename_all = "camelCase")
export interface ThumbnailResult {
  source: string;
  thumbnailPath: string;
  width: number;
  height: number;
}

// Rust 端 AssetKind (pub enum, rename_all = "snake_case")
export type AssetKind =
  | "video"
  | "audio"
  | "image"
  | "subtitle"
  | "other";

// Rust 端 SubtitleEntry (pub struct)
export interface SubtitleEntry {
  index: number;
  start_ms: number;
  end_ms: number;
  text: string;
  emotion_tag: string | null;
}

// Rust 端 SubtitleTrack (pub struct)
export interface SubtitleTrack {
  entries: SubtitleEntry[];
  format: SubtitleFormat;
  language: string;
}

// Rust 端 VadConfig (pub struct)
export interface VadConfig {
  min_segment_ms: number;
  silence_threshold_db: number;
  merge_gap_ms: number;
}

// Rust 端 SpeechSegment (pub struct)
export interface SpeechSegment {
  start_ms: number;
  end_ms: number;
}

// Rust 端 UpdateInfo (pub struct, rename_all = "camelCase")
export interface UpdateInfo {
  version: string;
  releaseDate: string | null;
  notes: string | null;
  downloadUrl: string | null;
  sha256: string | null;
  fileSizeBytes: number | null;
}

// Rust 端 UpdateProgress (pub struct, rename_all = "camelCase")
export interface UpdateProgress {
  downloadedBytes: number;
  totalBytes: number;
  percent: number;
}

// Rust 端 UpdateState (pub struct, rename_all = "camelCase")
export interface UpdateState {
  phase: UpdatePhase;
  currentVersion: string;
  available: UpdateInfo | null;
  progress: UpdateProgress | null;
  error: string | null;
  downloadedPath: string | null;
}

// Rust 端 UpdatePhase (pub enum, rename_all = "snake_case")
export type UpdatePhase =
  | "idle"
  | "checking"
  | "available"
  | "downloading"
  | "ready";

/* <<< gen-ipc-types end */

export type IpcCommand = keyof IpcContracts;

/**
 * 编译期契约校验: Rust 端实现必须与 IpcContracts 1:1 对应。
 * 任何增删 command 必须同时修改:
 *   - apps/desktop/src-tauri/src/commands/*.rs
 *   - apps/desktop/src/ipc/types.gen.ts (本文件)
 *   - apps/desktop/src/ipc/client.ts (callIpc 实现)
 */
export type CommandArgs<C extends IpcCommand> = IpcContracts[C]["args"];
export type CommandResultOf<C extends IpcCommand> = IpcContracts[C]["result"];

// ────────────────────────────────────────────────────────────────────────
// IPC event 类型表 (M3+ 占位 · specta 自动生成阶段尚未启用)
// 后端通过 tokio::sync::broadcast::Sender<PipelineEvent> 等推送 → 前端 listen 订阅
// ────────────────────────────────────────────────────────────────────────

export interface IpcEventPayloads {
  "pipeline:step_started": { runId: string; stepId: string };
  "pipeline:step_completed": { runId: string; stepId: string };
  "pipeline:step_failed": {
    runId: string;
    stepId: string;
    error: VynaroError;
  };
  "pipeline:progress": { runId: string; percent: number };
  "pipeline:log": {
    runId: string;
    line: string;
    level: "info" | "warn" | "error";
  };
  "pipeline:finished": { runId: string; ok: boolean };
  "assets:imported": { projectId: string; ids: string[] };
  "assets:thumbnail_ready": { assetId: string };
  "assets:scan_progress": { scanned: number; total: number };
  "assets:removed": { ids: string[] };
  "updater:available": { version: string };
  "updater:downloading": { version: string };
  "updater:download_progress": { percent: number };
  "updater:ready": { version: string };
  "updater:error": { error: VynaroError };
  "updater:event": UpdateState | UpdateInfo | UpdateProgress | string;
  "app:theme_changed": { theme: string };
  "app:locale_changed": { locale: string };
  "app:window_focus": { focused: boolean };
  "app:config_reloaded": Record<string, never>;
  "app:secure_key_rotated": Record<string, never>;
  "app:service_started": { name: string };
  "app:service_stopped": { name: string };
  "app:error_reported": { error: VynaroError };
  "app:log_flushed": { lines: number };
}

export type IpcEvent = keyof IpcEventPayloads;
// TEST MARKER
