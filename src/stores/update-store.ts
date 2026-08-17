/**
 * splicr v1.0.0 · update store (Zustand)
 *
 * 设计 (M4 完整实装):
 * - 镜像后端 UpdateState 完整快照 (单源真相)
 * - 当前端 listen `updater:event` 拿到 UpdateEvent 变体时,逐项投影覆盖
 * - 组件层只读快照,业务过渡态由 useUpdate hook 驱动
 *
 * 5 阶段状态机: idle → checking → available → downloading → ready
 */

import { create } from "zustand";
import type {
  UpdateInfo,
  UpdatePhase,
  UpdateProgress,
  UpdateState,
} from "../ipc/types.gen";

interface UpdateStoreState {
  /** 完整状态快照(也写 currentVersion / downloadedPath / error) */
  snapshot: UpdateState;
  /** 便捷 setters,只覆盖单一字段 */
  setPhase: (phase: UpdatePhase) => void;
  setAvailable: (info: UpdateInfo | null) => void;
  setProgress: (progress: UpdateProgress | null) => void;
  setDownloadedPath: (path: string | null) => void;
  setError: (error: string | null) => void;
  /** 全量替换(主要用于 listen 兜底事件) */
  setSnapshot: (snap: UpdateState) => void;
  /** 重置(用户取消 / 完成后清场) */
  reset: (currentVersion: string) => void;
}

const EMPTY: UpdateState = {
  phase: "idle",
  currentVersion: "",
  available: null,
  progress: null,
  error: null,
  downloadedPath: null,
};

export const useUpdateStore = create<UpdateStoreState>()((set) => ({
  snapshot: EMPTY,
  setPhase: (phase) =>
    set((s) => ({ snapshot: { ...s.snapshot, phase, error: null } })),
  setAvailable: (info) =>
    set((s) => ({ snapshot: { ...s.snapshot, available: info } })),
  setProgress: (progress) =>
    set((s) => ({ snapshot: { ...s.snapshot, progress } })),
  setDownloadedPath: (path) =>
    set((s) => ({ snapshot: { ...s.snapshot, downloadedPath: path } })),
  setError: (error) => set((s) => ({ snapshot: { ...s.snapshot, error } })),
  setSnapshot: (snap) => set({ snapshot: snap }),
  reset: (currentVersion) =>
    set({
      snapshot: {
        ...EMPTY,
        currentVersion,
      },
    }),
}));
