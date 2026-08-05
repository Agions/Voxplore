/**
 * Vynaro v2.5.0 · 真实接通后端的流水线 hook (M3.2)
 *
 * 数据源:Tauri 后端 PipelineService (state + step_statuses)
 * 实时性:listen "pipeline:event" + 主动 refetch pipeline_status
 * 控制:start / cancel / reset 三个命令
 */

import { useCallback, useEffect } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { listen, type UnlistenFn } from "@tauri-apps/api/event";
import { pipelineIpc } from "../ipc/commands";
import {
  computePercent,
  deriveSteps,
  findActiveIndex,
  type PipelineStepView,
} from "../lib/pipeline/derive";
import type { PipelineState, PipelineStatus, Project } from "../ipc/types.gen";

// PipelineStepView 类型 re-export (业务侧只引用 usePipeline 一处)
export type { PipelineStepView };

export interface UsePipelineReturn {
  state: PipelineState;
  steps: PipelineStepView[];
  activeIndex: number;
  /** 0-100 整体进度 */
  percent: number;
  projectName: string | null;
  start: (project: Project, workdir?: string) => Promise<void>;
  cancel: () => Promise<void>;
  reset: () => Promise<void>;
  refetch: () => void;
}

export function usePipeline(
  stepDefs: { id: string; label_zh: string }[],
): UsePipelineReturn {
  const qc = useQueryClient();
  const { data: status, refetch } = useQuery<PipelineStatus>({
    queryKey: ["pipeline-status"],
    queryFn: pipelineIpc.status,
    // 后端 running 时 800ms 拉一次;其他状态 5s 一次;event 来时立即刷新
    refetchInterval: (q) => {
      const s = q.state.data;
      return s?.state === "running" ? 800 : 5000;
    },
  });

  // listen to backend broadcast (pipeline:event)
  useEffect(() => {
    let unlisten: UnlistenFn | undefined;
    let mounted = true;
    (async () => {
      try {
        unlisten = await listen("pipeline:event", () => {
          if (mounted) {
            void qc.invalidateQueries({ queryKey: ["pipeline-status"] });
          }
        });
      } catch (e) {
        // webview only: ignore
        console.debug("listen pipeline:event unavailable", e);
      }
    })();
    return () => {
      mounted = false;
      if (unlisten) unlisten();
    };
  }, [qc]);

  const start = useCallback(
    async (project: Project, workdir?: string) => {
      await pipelineIpc.start(project, workdir);
      void refetch();
    },
    [refetch],
  );

  const cancel = useCallback(async () => {
    await pipelineIpc.cancel();
    void refetch();
  }, [refetch]);

  const reset = useCallback(async () => {
    await pipelineIpc.reset();
    void qc.invalidateQueries({ queryKey: ["pipeline-status"] });
  }, [qc]);

  const steps: PipelineStepView[] = deriveSteps(stepDefs, status);
  const activeIndex = findActiveIndex(steps);
  const percent = computePercent(status, steps.length);

  return {
    state: status?.state ?? "idle",
    steps,
    activeIndex,
    percent,
    projectName: status?.projectName ?? null,
    start,
    cancel,
    reset,
    refetch: () => {
      void refetch();
    },
  };
}

/** 全局快捷键注册 (注意 SSR 安全) */
export function usePipelineHotkeys(
  startFn: (e: KeyboardEvent) => void,
  cancelFn: (e: KeyboardEvent) => void,
) {
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      const mod = e.metaKey || e.ctrlKey;
      if (!mod) return;
      // ⌘R / Ctrl+R
      if (e.key === "r" || e.key === "R") {
        e.preventDefault();
        startFn(e);
      }
      // ⌘. / Ctrl+.
      if (e.key === ".") {
        e.preventDefault();
        cancelFn(e);
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [startFn, cancelFn]);
}
