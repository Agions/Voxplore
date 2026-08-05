/**
 * SceneFab v2.5.0 · settings store (Zustand)
 *
 * 设计:
 * - 仅持久化非敏感设置(主题/语言/默认值)
 * - LLM/TTS API 密钥不放在这里,经 secure-key-manager (keyring/credential manager) 存储
 *
 * M3.3 接入 invoke settings.get / settings.set 后填充
 */

import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { LlmProviderKind, TtsProviderKind } from "../ipc/types.gen";

interface SettingsState {
  locale: string;
  llmDefaultProvider: LlmProviderKind;
  ttsDefaultProvider: TtsProviderKind;
  /** 自动保存间隔(秒) */
  autoSaveIntervalSec: number;
  setLocale: (locale: string) => void;
  setLlmDefault: (provider: LlmProviderKind) => void;
  setTtsDefault: (provider: TtsProviderKind) => void;
  setAutoSaveInterval: (sec: number) => void;
}

export const useSettingsStore = create<SettingsState>()(
  persist(
    (set) => ({
      locale: "zh-CN",
      llmDefaultProvider: "open-ai",
      ttsDefaultProvider: "edge",
      autoSaveIntervalSec: 60,
      setLocale: (locale) => set({ locale }),
      setLlmDefault: (provider) => set({ llmDefaultProvider: provider }),
      setTtsDefault: (provider) => set({ ttsDefaultProvider: provider }),
      setAutoSaveInterval: (sec) => set({ autoSaveIntervalSec: sec }),
    }),
    { name: "scenefab.settings" },
  ),
);
