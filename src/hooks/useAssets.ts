/**
 * Vynaro v1.0.0 · 素材 hook (M3 后续完整实装)
 *
 * 数据源:
 * - 单一真相源 = project.media_files (从 useProjectStore.current 派生)
 * - ids = media_files.map(m => m.path) (用文件路径作为稳定 ID)
 * - selectedIds 仍由 useAssetsStore 持有(本地 UI 状态)
 *
 * 后端命令:
 * - scan(dir, recursive)  → assetsIpc.scan · 扫描目录
 * - probe(path)           → assetsIpc.metadata · 抽取 metadata
 * - thumbnail(path, w?)   → assetsIpc.thumbnail · 生成首帧图
 * - search(media, pat)    → assetsIpc.search · substring 过滤
 * - importFromPaths(paths) → 先 probe 真实填充,再 projectIpc.addMedia
 * - remove(ids)            → 在前端 project.media_files 过滤后,projectIpc.save 落盘
 *
 * 注意:
 * - 必须先有 current project + currentPath (无 project → 抛错)
 * - M3 后续接入 ffmpeg probe 后,import 真实写入 duration/resolution/codec/size
 */

import { useCallback, useEffect, useMemo, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { assetsIpc, projectIpc } from "../ipc/commands";
import { useAssetsStore } from "../stores/assets-store";
import { useProjectStore } from "../stores/project-store";
import { pathToMediaFileEmpty, applyProbe } from "../lib/assets/probe";
import type {
  AssetEntry,
  FfmpegProbe,
  MediaFile,
  Project,
  ScanResult,
  ThumbnailResult,
} from "../ipc/types.gen";

/** QueryClient 缓存中的项目记录结构 (必须与 ProjectRecord 一致) */
interface CachedProjectRecord {
  path: string;
  project: Project;
}

export interface UseAssetsReturn {
  /** 当前项目下素材 ID 列表 (path 作为 ID) */
  ids: string[];
  /** 当前项目下素材完整列表 */
  items: MediaFile[];
  /** 是否为空 */
  isEmpty: boolean;

  /**
   * 扫描目录,返回可导入素材条目列表
   * - 不修改项目,纯探测
   * - 用于"批量导入"对话框
   */
  scan: (dir: string, recursive?: boolean) => Promise<ScanResult>;

  /**
   * 探测单个素材的 metadata
   * - duration / resolution / codec / size
   * - 用于导入前的 preview
   */
  probe: (path: string) => Promise<FfmpegProbe>;

  /**
   * 生成首帧缩略图
   * - 写入 ~/.cache/vynaro/thumb/<sha256>.jpg
   * - 返回本地路径,前端用 file:// 或 convertFileSrc 加载
   */
  thumbnail: (path: string, width?: number) => Promise<ThumbnailResult>;

  /**
   * 在已有 media 列表中按 substring 过滤
   */
  search: (mediaPaths: string[], pattern: string) => Promise<string[]>;

  /**
   * 把一组本地文件路径导入到当前项目
   * - 串行调用:probe metadata → 填充 MediaFile → projectIpc.addMedia
   * - 要求:有 current project + currentPath
   */
  importFromPaths: (paths: string[]) => Promise<MediaFile[]>;

  /**
   * 一次性导入 ScanResult 中的全部 entries
   * - 比 importFromPaths 效率高,避免逐个 probe 重复 IO
   */
  importFromScan: (scan: ScanResult) => Promise<MediaFile[]>;

  /**
   * 按 id 列表从当前项目删除素材
   * - 要求:有 current project + currentPath
   */
  remove: (ids: string[]) => Promise<MediaFile[]>;

  /** 异步操作状态 */
  loading: boolean;
  /** 最近一次失败信息 (VynaroError 或 Error) */
  error: unknown;
}

/**
 * 素材 hook — M3 后续完整接通 assets 4 个 Tauri command
 *
 * 注意:
 * - pathToMediaFileEmpty / applyProbe 已迁到 ../lib/assets/probe.ts (纯函数,可单测)
 */
export function useAssets(): UseAssetsReturn {
  const qc = useQueryClient();

  // 主数据源: useProjectStore
  const storeProject = useProjectStore((s) => s.current);
  const storePath = useProjectStore((s) => s.currentPath);
  const setCurrentRecord = useProjectStore((s) => s.setCurrentRecord);
  const setCurrent = useProjectStore((s) => s.setCurrent);

  // ✅ 关键修复: 当 store 为空时从 QueryClient 缓存回退
  // 这样即使调用方没有手动 setCurrentRecord，导入也能正常工作
  const cachedRec = qc.getQueryData<CachedProjectRecord>(["current-project"]);
  const current = storeProject ?? cachedRec?.project ?? null;
  const currentPath = storePath ?? cachedRec?.path ?? null;

  // 如果 store 为空但 cache 有数据，在 effect 里同步（避免 render 期间 setState）
  useEffect(() => {
    if (!storeProject && cachedRec) {
      setCurrentRecord(cachedRec.path, cachedRec.project);
    }
  }, [storeProject, cachedRec, setCurrentRecord]);

  const setIds = useAssetsStore((s) => s.setIds);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<unknown>(null);

  // 派生:当前项目的素材列表 (单一真相源)
  const items = useMemo<MediaFile[]>(
    () => current?.media_files ?? [],
    [current?.media_files],
  );
  const ids = useMemo<string[]>(() => items.map((m) => m.path), [items]);
  const isEmpty = ids.length === 0;

  /** 把更新后的 project 同步到 store + 所有相关 query cache key */
  const syncProject = useCallback(
    (project: typeof current) => {
      if (!project) return;
      setCurrent(project);
      const pathIds = project.media_files.map((m) => m.path);
      setIds(pathIds);
      // ✅ 保持 ProjectRecord {path, project} 结构，避免覆盖掉 path 字段
      const existingRec = qc.getQueryData<CachedProjectRecord>(["current-project"]);
      const rec: CachedProjectRecord = { path: existingRec?.path ?? currentPath ?? "", project };
      for (const key of [
        ["current-project"],
        ["assets-current-project"],
      ] as const) {
        qc.setQueryData(key, rec);
      }
    },
    [setCurrent, setIds, qc, currentPath],
  );

  // ─── 4 个新 actions (scan / probe / thumbnail / search) ──────

  const scan = useCallback(
    async (dir: string, recursive = false): Promise<ScanResult> => {
      return assetsIpc.scan(dir, recursive);
    },
    [],
  );

  const probe = useCallback(async (path: string): Promise<FfmpegProbe> => {
    return assetsIpc.metadata(path);
  }, []);

  const thumbnail = useCallback(
    async (path: string, width = 320): Promise<ThumbnailResult> => {
      return assetsIpc.thumbnail(path, width);
    },
    [],
  );

  const search = useCallback(
    async (mediaPaths: string[], pattern: string): Promise<string[]> => {
      return assetsIpc.search(mediaPaths, pattern);
    },
    [],
  );

  // ─── 现有 actions (import / remove) 升级 ─────────────────────

  const importFromPaths = useCallback(
    async (paths: string[]): Promise<MediaFile[]> => {
      if (paths.length === 0) return [];

      setLoading(true);
      setError(null);
      try {
        let proj = current;
        let path = currentPath;

        // 如果当前没有项目，自动创建默认解说工程，避免报 "未打开项目,无法导入素材"
        if (!proj || !path) {
          const rec = await projectIpc.createBlank();
          proj = rec.project;
          path = rec.path;
          setCurrentRecord(path, proj);
          qc.setQueryData(["current-project"], rec);
          qc.setQueryData(["assets-current-project"], proj);
          void qc.invalidateQueries({ queryKey: ["assets-recent"] });
        }

        const added: MediaFile[] = [];
        for (const p of paths) {
          let mf = pathToMediaFileEmpty(p);
          // 尝试 probe metadata;失败回退空字段
          try {
            const probeRes = await assetsIpc.metadata(p);
            mf = applyProbe(mf, probeRes);
          } catch {
            // probe 失败不阻塞导入
          }
          proj = await projectIpc.addMedia(path, proj, mf);
          added.push(mf);
        }
        syncProject(proj);
        return added;
      } catch (e) {
        setError(e);
        throw e;
      } finally {
        setLoading(false);
      }
    },
    [current, currentPath, syncProject, setCurrentRecord, qc],
  );

  const importFromScan = useCallback(
    async (scan: ScanResult): Promise<MediaFile[]> => {
      return importFromPaths(scan.entries.map((e: AssetEntry) => e.path));
    },
    [importFromPaths],
  );

  const remove = useCallback(
    async (idsToRemove: string[]): Promise<MediaFile[]> => {
      if (!current) {
        const e = new Error("未打开项目,无法删除素材");
        setError(e);
        throw e;
      }
      if (!currentPath) {
        const e = new Error("项目未保存到磁盘,无法删除素材");
        setError(e);
        throw e;
      }
      if (idsToRemove.length === 0) return [];

      setLoading(true);
      setError(null);
      try {
        const removeSet = new Set(idsToRemove);
        const removed: MediaFile[] = [];
        const remaining = current.media_files.filter((m) => {
          if (removeSet.has(m.path)) {
            removed.push(m);
            return false;
          }
          return true;
        });
        const updated = {
          ...current,
          media_files: remaining,
          updated_at: new Date().toISOString(),
        };
        await projectIpc.save(currentPath, updated);
        syncProject(updated);
        return removed;
      } catch (e) {
        setError(e);
        throw e;
      } finally {
        setLoading(false);
      }
    },
    [current, currentPath, syncProject],
  );

  return {
    ids,
    items,
    isEmpty,
    scan,
    probe,
    thumbnail,
    search,
    importFromPaths,
    importFromScan,
    remove,
    loading,
    error,
  };
}
