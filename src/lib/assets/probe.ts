/**
 * Vynaro v1.0.0 · 素材 probe 转换 (纯函数,可单测)
 *
 * 设计:
 * - 不依赖 React/Store/IPC
 * - 由 useAssets.ts 调用,也由测试单独验证
 */

import type { FfmpegProbe, MediaFile } from "@ipc/types.gen";

/** 把 path 转成最小可用的 MediaFile (fallback,probe 失败时使用) */
export function pathToMediaFileEmpty(path: string): MediaFile {
  return {
    path,
    duration_seconds: 0,
    resolution: null,
    codec: null,
    file_size_bytes: 0,
    import_time: new Date().toISOString(),
  };
}

/** 把 probe 结果填进 MediaFile (不修改 path / import_time) */
export function applyProbe(mf: MediaFile, probe: FfmpegProbe): MediaFile {
  return {
    ...mf,
    duration_seconds: probe.durationSeconds,
    resolution:
      probe.width > 0 && probe.height > 0
        ? `${probe.width}x${probe.height}`
        : mf.resolution,
    codec: probe.videoCodec ?? probe.audioCodec ?? mf.codec,
    file_size_bytes: probe.sizeBytes || mf.file_size_bytes,
  };
}

/** 文件路径 basename (跨平台分隔符) */
export function basename(path: string): string {
  return path.split(/[/\\]/).pop() ?? path;
}

// formatBytes 已迁到 ../format/bytes.ts (统一支持 null/undefined)
// 这里 re-export 方便现有 import "@lib/assets/probe" 调用方无感升级
export { formatBytes } from "../format/bytes";
