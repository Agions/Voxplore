/**
 * SceneFab v2.5.0 · theme store (Zustand)
 *
 * 设计:
 * - 单一字段: `theme` (light / dark / system)
 * - 持久化: localStorage key = "scenefab.theme"
 * - M3.3 通过 settings.update → invoke settings.set 同步到后端
 */

import { create } from "zustand";
import { persist } from "zustand/middleware";

export type Theme = "light" | "dark" | "system";

interface ThemeState {
  theme: Theme;
  setTheme: (theme: Theme) => void;
  toggle: () => void;
}

export const useThemeStore = create<ThemeState>()(
  persist(
    (set, get) => ({
      theme: "system",
      setTheme: (theme) => set({ theme }),
      toggle: () => set({ theme: get().theme === "dark" ? "light" : "dark" }),
    }),
    { name: "scenefab.theme" },
  ),
);
