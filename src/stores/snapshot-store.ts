/**
 * Vynaro v1.0.1 · snapshot store (Zustand)
 *
 * 管理工程版本历史抽屉 (Snapshot Drawer) 开合状态与当前快照数据
 */

import { create } from "zustand";
import type { ProjectSnapshot } from "../ipc/types.gen";

interface SnapshotState {
  /** 抽屉开合状态 */
  isDrawerOpen: boolean;
  /** 当前选中的快照 */
  selectedSnapshot: ProjectSnapshot | null;
  /** 快照列表 */
  snapshots: ProjectSnapshot[];

  openDrawer: () => void;
  closeDrawer: () => void;
  toggleDrawer: () => void;
  setSelectedSnapshot: (snapshot: ProjectSnapshot | null) => void;
  setSnapshots: (snapshots: ProjectSnapshot[]) => void;
}

export const useSnapshotStore = create<SnapshotState>()((set) => ({
  isDrawerOpen: false,
  selectedSnapshot: null,
  snapshots: [],

  openDrawer: () => set({ isDrawerOpen: true }),
  closeDrawer: () => set({ isDrawerOpen: false, selectedSnapshot: null }),
  toggleDrawer: () => set((state) => ({ isDrawerOpen: !state.isDrawerOpen })),
  setSelectedSnapshot: (snapshot) => set({ selectedSnapshot: snapshot }),
  setSnapshots: (snapshots) => set({ snapshots }),
}));
