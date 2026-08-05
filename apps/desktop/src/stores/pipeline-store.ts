/**
 * SceneFab v2.5.0 · pipeline store (Zustand)
 *
 * 设计:
 * - state: idle | running | done | failed
 * - stepDefs: 后端返回的 5 步定义(M2 invoke pipeline_step_defs)
 * - runId: 当前 run 的 UUID (用于事件路由去重)
 * - percent: 0-100 整体进度
 */

import { create } from "zustand";
import type { PipelineState, PipelineStepDef } from "../ipc/types.gen";

interface PipelineStoreState {
  state: PipelineState;
  stepDefs: PipelineStepDef[];
  runId: string | null;
  percent: number;
  setState: (state: PipelineState) => void;
  setStepDefs: (defs: PipelineStepDef[]) => void;
  setRunId: (id: string | null) => void;
  setPercent: (percent: number) => void;
  reset: () => void;
}

export const usePipelineStore = create<PipelineStoreState>()((set) => ({
  state: "idle",
  stepDefs: [],
  runId: null,
  percent: 0,
  setState: (state) => set({ state }),
  setStepDefs: (defs) => set({ stepDefs: defs }),
  setRunId: (id) => set({ runId: id }),
  setPercent: (percent) => set({ percent }),
  reset: () => set({ state: "idle", runId: null, percent: 0 }),
}));
