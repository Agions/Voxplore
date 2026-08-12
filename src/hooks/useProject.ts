/**
 * Vynaro v1.0.0 · 当前项目 hook (M3 真实接通 Tauri 命令)
 *
 * 后端命令:
 * - open(path)    → projectIpc.load(path)      → ProjectRecord
 * - save()        → projectIpc.save(currentPath, current)
 * - saveAs(path)  → projectIpc.save(newPath, current)
 * - close()       → 清空 store + cancel pipeline
 *
 * 与 store 关系:
 * - store.current / store.currentPath 是单一真相源
 * - 同时同步 TanStack Query cache 中的 ["current-project"] / ["assets-current-project"],
 *   保持与现有 routes/production.tsx · routes/assets.tsx 的契约一致
 */

import { useCallback, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { pipelineIpc, projectIpc } from "../ipc/commands";
import { useProjectStore } from "../stores/project-store";
import type { Project } from "../ipc/types.gen";

/** 与 TanStack Query cache 中"当前项目"相关的 key(供其它页面同步读) */
const QUERY_KEYS_CURRENT_PROJECT = [
  ["current-project"],
  ["assets-current-project"],
] as const;

export interface UseProjectReturn {
  /** 当前打开的项目 (可能为 null) */
  project: Project | null;
  /** 项目磁盘路径 (save / saveAs 必需) */
  currentPath: string | null;
  /** 是否已加载项目 */
  hasProject: boolean;

  /** 加载指定路径的项目 (解析 .vynaro.json → setCurrentRecord) */
  open: (path: string) => Promise<void>;
  /** 保存到当前路径 (currentPath 必须存在) */
  save: () => Promise<void>;
  /** 另存为新路径 */
  saveAs: (path: string) => Promise<void>;
  /** 关闭项目:清空 store + 取消正在运行的流水线 */
  close: () => Promise<void>;

  /** 异步操作状态 */
  loading: boolean;
  /** 最近一次失败信息 (VynaroError 或 Error) */
  error: unknown;
}

/**
 * 当前项目 hook — M3 完整接通 Rust 端的 6 个 project 命令
 */
export function useProject(): UseProjectReturn {
  const qc = useQueryClient();
  const current = useProjectStore((s) => s.current);
  const currentPath = useProjectStore((s) => s.currentPath);
  const setCurrentRecord = useProjectStore((s) => s.setCurrentRecord);
  const setCurrent = useProjectStore((s) => s.setCurrent);
  const setCurrentPath = useProjectStore((s) => s.setCurrentPath);
  const clear = useProjectStore((s) => s.clear);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<unknown>(null);

  /** 同步"当前项目"到所有相关 query cache key */
  const syncCurrentToCache = useCallback(
    (project: Project, path?: string) => {
      const rec = { path: path ?? currentPath ?? "", project };
      qc.setQueryData(["current-project"], rec);
      qc.setQueryData(["assets-current-project"], project);
      void qc.invalidateQueries({ queryKey: ["assets-recent"] });
      void qc.invalidateQueries({ queryKey: ["pipeline-status"] });
    },
    [qc, currentPath],
  );

  const open = useCallback(
    async (path: string) => {
      setLoading(true);
      setError(null);
      try {
        const rec = await projectIpc.load(path);
        setCurrentRecord(rec.path, rec.project);
        syncCurrentToCache(rec.project);
      } catch (e) {
        setError(e);
        throw e;
      } finally {
        setLoading(false);
      }
    },
    [setCurrentRecord, syncCurrentToCache],
  );

  const save = useCallback(async () => {
    if (!current) {
      const e = new Error("没有打开的项目");
      setError(e);
      throw e;
    }
    if (!currentPath) {
      const e = new Error("项目未保存到磁盘,无法直接 save,请改用 saveAs");
      setError(e);
      throw e;
    }
    setLoading(true);
    setError(null);
    try {
      await projectIpc.save(currentPath, current);
      // 写回 updated_at,让前端显示最新时间
      const fresh: Project = {
        ...current,
        updated_at: new Date().toISOString(),
      };
      setCurrent(fresh);
      syncCurrentToCache(fresh);
    } catch (e) {
      setError(e);
      throw e;
    } finally {
      setLoading(false);
    }
  }, [current, currentPath, setCurrent, syncCurrentToCache]);

  const saveAs = useCallback(
    async (path: string) => {
      if (!current) {
        const e = new Error("没有打开的项目");
        setError(e);
        throw e;
      }
      setLoading(true);
      setError(null);
      try {
        await projectIpc.save(path, current);
        setCurrentPath(path);
        syncCurrentToCache(current);
      } catch (e) {
        setError(e);
        throw e;
      } finally {
        setLoading(false);
      }
    },
    [current, setCurrentPath, syncCurrentToCache],
  );

  const close = useCallback(async () => {
    clear();
    for (const key of QUERY_KEYS_CURRENT_PROJECT) {
      qc.removeQueries({ queryKey: key });
    }
    // 若流水线在跑,顺手 cancel (fire-and-forget,失败不影响关闭)
    try {
      await pipelineIpc.cancel();
    } catch {
      /* 关闭项目时 cancel 失败是正常的 (流水线可能本来就是 idle) */
    }
  }, [clear, qc]);

  return {
    project: current,
    currentPath,
    hasProject: current !== null,
    open,
    save,
    saveAs,
    close,
    loading,
    error,
  };
}
