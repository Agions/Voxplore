/**
 * Vynaro v2.5.0 · ui store (Zustand)
 *
 * 设计:
 * - 与"数据"无关的 UI 状态:侧栏折叠/命令面板开关/当前路由 toast 等
 * - 跨页面共享的纯前端态
 */

import { create } from "zustand";

interface UiState {
  sidebarCollapsed: boolean;
  commandPaletteOpen: boolean;
  helpPanelOpen: boolean;
  toggleSidebar: () => void;
  openCommandPalette: () => void;
  closeCommandPalette: () => void;
  toggleHelpPanel: () => void;
}

export const useUiStore = create<UiState>()((set, get) => ({
  sidebarCollapsed: false,
  commandPaletteOpen: false,
  helpPanelOpen: false,
  toggleSidebar: () => set({ sidebarCollapsed: !get().sidebarCollapsed }),
  openCommandPalette: () => set({ commandPaletteOpen: true }),
  closeCommandPalette: () => set({ commandPaletteOpen: false }),
  toggleHelpPanel: () => set({ helpPanelOpen: !get().helpPanelOpen }),
}));
