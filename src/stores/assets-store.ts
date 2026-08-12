/**
 * Monoloop v1.0.0 · assets store (Zustand)
 *
 * 设计:
 * - ids: 当前项目素材 id 列表
 * - 真实素材元数据通过 invoke assets.list 拉取,放在 TanStack Query cache
 *
 * M4 接入后,这里只持有"轻量引用 + 选中状态"。
 */

import { create } from "zustand";

interface AssetsState {
  ids: string[];
  selectedIds: string[];
  setIds: (ids: string[]) => void;
  setSelected: (ids: string[]) => void;
  toggleSelected: (id: string) => void;
  clear: () => void;
}

export const useAssetsStore = create<AssetsState>()((set, get) => ({
  ids: [],
  selectedIds: [],
  setIds: (ids) => set({ ids }),
  setSelected: (ids) => set({ selectedIds: ids }),
  toggleSelected: (id) => {
    const cur = get().selectedIds;
    set({
      selectedIds: cur.includes(id)
        ? cur.filter((x) => x !== id)
        : [...cur, id],
    });
  },
  clear: () => set({ ids: [], selectedIds: [] }),
}));
