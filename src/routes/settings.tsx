/**
 * splicr v1.0.1 · 设置与模型引擎中心 (全模型矩阵 + API 密钥管理 + TTS 引擎配置)
 */

import { createFileRoute } from "@tanstack/react-router";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { settingsIpc, type ConfigSnapshot } from "@ipc/commands";
import { useSettingsStore } from "@stores/settings-store";
import { useThemeStore, type Theme } from "@stores/theme-store";
import { t } from "@lib/i18n";
import { toast } from "sonner";

export const Route = createFileRoute("/settings")({
  component: SettingsPage,
});

const LLM_OPTIONS: Array<{
  id: string;
  label: string;
  hint: string;
  provider: string;
}> = [
  { id: "qwen", label: "通义千问 Qwen", hint: "qwen3.8-max 阿里旗舰", provider: "Aliyun DashScope" },
  { id: "deepseek", label: "DeepSeek", hint: "deepseek-v4-pro / r1", provider: "DeepSeek Official" },
  { id: "open-ai", label: "OpenAI", hint: "gpt-5.6-sol / 4o", provider: "OpenAI Official" },
  { id: "claude", label: "Claude", hint: "claude-sonnet-5 / 3.5", provider: "Anthropic" },
  { id: "gemini", label: "Gemini", hint: "gemini-3.6-flash / 3.1", provider: "Google DeepMind" },
  { id: "kimi", label: "Kimi · Moonshot", hint: "kimi-k3 月之暗面", provider: "Moonshot AI" },
  { id: "glm5", label: "智谱 GLM", hint: "glm-5.2 智谱清言", provider: "Zhipu AI" },
  { id: "doubao", label: "豆包 Doubao", hint: "doubao-seed-2-1-pro", provider: "ByteDance Volcengine" },
  { id: "hunyuan", label: "混元 Hunyuan", hint: "hunyuan-pro 腾讯", provider: "Tencent Cloud" },
  { id: "local", label: "本地 (Ollama)", hint: "llama3.2 / qwen2.5", provider: "127.0.0.1:11434" },
];

const TTS_OPTIONS: Array<{
  id: "edge" | "open-ai" | "mimo" | "gpt-sovits";
  label: string;
  hint: string;
}> = [
  { id: "edge", label: "Edge TTS", hint: "微软免费 · 无需密钥 · 50+ 官方声优" },
  { id: "mimo", label: "MiMo TTS (小米 MiMo)", hint: "mimo-v2.5-tts 限时免费 · 开放 API" },
  { id: "open-ai", label: "OpenAI TTS", hint: "tts-1-hd / alloy / onyx 影视级配音" },
  { id: "gpt-sovits", label: "GPT-SoVITS", hint: "本地零样本声音克隆 (127.0.0.1:9880)" },
];

const DEFAULT_SNAPSHOT: ConfigSnapshot = {
  theme: "dark",
  language: "zh-CN",
  llm_provider: "open-ai",
  auto_update: true,
  first_run: true,
  llm_api_key: null,
  llm_base_url: null,
  llm_model: null,
  tts_provider: "edge",
  tts_api_key: null,
  tts_base_url: null,
  tts_voice: null,
  tts_ref_audio_path: null,
  tts_prompt_text: null,
};

function SettingsPage() {
  const qc = useQueryClient();
  const locale = useSettingsStore((s) => s.locale);
  const currentTheme = useThemeStore((s) => s.theme);
  const setTheme = useThemeStore((s) => s.setTheme);

  const [activeNav, setActiveNav] = useState<"llm" | "tts" | "theme">("llm");
  const [form, setForm] = useState<ConfigSnapshot>(DEFAULT_SNAPSHOT);

  const { data: snapshot, isLoading } = useQuery({
    queryKey: ["settings-snapshot"],
    queryFn: () => settingsIpc.get(),
  });

  useEffect(() => {
    if (snapshot) {
      setForm(snapshot);
    }
  }, [snapshot]);

  const saveMutation = useMutation({
    mutationFn: (snap: ConfigSnapshot) => settingsIpc.set(snap),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["settings-snapshot"] });
      void qc.invalidateQueries({ queryKey: ["app-config-settings"] });
      toast.success(t("settings.saved", locale) || "设置保存成功");
    },
    onError: (e) => {
      toast.error(t("settings.save_failed", locale) || "保存失败", {
        description: e instanceof Error ? e.message : String(e),
      });
    },
  });

  const handleSave = () => {
    saveMutation.mutate(form);
  };

  return (
    <div className="mx-auto max-w-5xl space-y-7 px-8 py-8 select-none font-sans">
      {/* 1. Header */}
      <header className="flex items-center justify-between border-b border-[var(--color-border)] pb-5">
        <div>
          <div className="text-[10px] font-mono font-bold tracking-[0.2em] text-[var(--color-gold)] uppercase">
            SYSTEM & MODEL ENGINE PREFERENCES
          </div>
          <h1 className="text-2xl font-black text-[var(--color-text-primary)]">
            {t("settings.title", locale)}
          </h1>
          <p className="text-xs text-[var(--color-text-secondary)] mt-0.5">
            配置 11 大大模型 API 密钥、Edge-TTS / GPT-SoVITS 声音克隆与全局渲染预设
          </p>
        </div>

        <button
          type="button"
          onClick={handleSave}
          disabled={saveMutation.isPending || isLoading}
          className="flex items-center gap-1.5 rounded-xl bg-gradient-to-r from-[#F5C842] to-[#E8933A] px-5 py-2 text-xs font-black text-zinc-950 shadow-md transition-all hover:scale-105 hover:brightness-110 disabled:opacity-50"
        >
          <span>💾</span>
          <span>{saveMutation.isPending ? "保存中..." : t("settings.save", locale) || "保存设置"}</span>
        </button>
      </header>

      {/* 2. 左右双栏布局 */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        {/* 左侧导航栏 */}
        <aside className="space-y-1.5">
          {[
            { id: "llm" as const, label: "大模型矩阵 (LLM)", icon: "🧠" },
            { id: "tts" as const, label: "配音与克隆 (TTS)", icon: "🎙️" },
            { id: "theme" as const, label: "通用偏好与主题", icon: "🎨" },
          ].map((item) => (
            <button
              key={item.id}
              type="button"
              onClick={() => setActiveNav(item.id)}
              className={`flex w-full items-center gap-2.5 rounded-xl px-3.5 py-2.5 text-xs font-bold transition-all text-left ${
                activeNav === item.id
                  ? "bg-[var(--color-gold-muted)] border border-[var(--color-gold)]/40 text-[var(--color-gold)] shadow-sm"
                  : "text-[var(--color-text-secondary)] hover:bg-[var(--color-surface-elevated)] hover:text-[var(--color-text-primary)]"
              }`}
            >
              <span>{item.icon}</span>
              <span>{item.label}</span>
            </button>
          ))}
        </aside>

        {/* 右侧设置主面板 */}
        <main className="md:col-span-3 rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)]/90 p-6 space-y-6 shadow-sm backdrop-blur-sm">
          {activeNav === "llm" && (
            <div className="space-y-5">
              <div>
                <h3 className="text-sm font-bold text-[var(--color-text-primary)]">默认 AI 解说大模型</h3>
                <p className="text-xs text-[var(--color-text-secondary)] mt-0.5">
                  Multi-Agent 编剧将优先调度此模型生成黄金 Hook 与反转独白
                </p>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                {LLM_OPTIONS.map((opt) => {
                  const selected = form.llm_provider === opt.id;
                  return (
                    <div
                      key={opt.id}
                      onClick={() => setForm({ ...form, llm_provider: opt.id })}
                      className={`flex flex-col justify-between rounded-xl border p-3 cursor-pointer transition-all ${
                        selected
                          ? "border-[var(--color-gold)] bg-[var(--color-gold-muted)] shadow-sm"
                          : "border-[var(--color-border)] bg-[var(--color-bg)]/80 hover:border-zinc-700"
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <span className={`text-xs font-bold ${selected ? "text-[var(--color-gold)]" : "text-zinc-200"}`}>
                          {opt.label}
                        </span>
                        {selected && <span className="text-[10px] text-[var(--color-gold)] font-mono">✓ 默认</span>}
                      </div>
                      <p className="text-[10px] text-zinc-500 mt-1">{opt.hint}</p>
                    </div>
                  );
                })}
              </div>

              <div className="space-y-3 pt-2 border-t border-[var(--color-border)]">
                <div>
                  <label className="block text-xs font-bold text-[var(--color-text-primary)] mb-1">
                    API Key (密钥凭证)
                  </label>
                  <input
                    type="password"
                    placeholder="sk-..."
                    value={form.llm_api_key ?? ""}
                    onChange={(e) => setForm({ ...form, llm_api_key: e.target.value || null })}
                    className="w-full rounded-xl border border-[var(--color-border)] bg-[var(--color-bg)] px-3 py-2 text-xs font-mono text-zinc-200 outline-none focus:border-[var(--color-gold)]"
                  />
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs font-bold text-[var(--color-text-primary)] mb-1">
                      自定义模型代号 (Model Override)
                    </label>
                    <input
                      type="text"
                      placeholder="默认官方预设"
                      value={form.llm_model ?? ""}
                      onChange={(e) => setForm({ ...form, llm_model: e.target.value || null })}
                      className="w-full rounded-xl border border-[var(--color-border)] bg-[var(--color-bg)] px-3 py-2 text-xs font-mono text-zinc-200 outline-none focus:border-[var(--color-gold)]"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-bold text-[var(--color-text-primary)] mb-1">
                      自定义 Base URL (代理端点)
                    </label>
                    <input
                      type="text"
                      placeholder="https://api.openai.com/v1"
                      value={form.llm_base_url ?? ""}
                      onChange={(e) => setForm({ ...form, llm_base_url: e.target.value || null })}
                      className="w-full rounded-xl border border-[var(--color-border)] bg-[var(--color-bg)] px-3 py-2 text-xs font-mono text-zinc-200 outline-none focus:border-[var(--color-gold)]"
                    />
                  </div>
                </div>
              </div>
            </div>
          )}

          {activeNav === "tts" && (
            <div className="space-y-5">
              <div>
                <h3 className="text-sm font-bold text-[var(--color-text-primary)]">默认语音合成引擎 (TTS Engine)</h3>
                <p className="text-xs text-[var(--color-text-secondary)] mt-0.5">
                  生成 48kHz 沉浸解说配音音频，并支持零样本音色克隆
                </p>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                {TTS_OPTIONS.map((opt) => {
                  const selected = form.tts_provider === opt.id;
                  return (
                    <div
                      key={opt.id}
                      onClick={() => setForm({ ...form, tts_provider: opt.id })}
                      className={`flex flex-col justify-between rounded-xl border p-3 cursor-pointer transition-all ${
                        selected
                          ? "border-[var(--color-gold)] bg-[var(--color-gold-muted)] shadow-sm"
                          : "border-[var(--color-border)] bg-[var(--color-bg)]/80 hover:border-zinc-700"
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <span className={`text-xs font-bold ${selected ? "text-[var(--color-gold)]" : "text-zinc-200"}`}>
                          {opt.label}
                        </span>
                        {selected && <span className="text-[10px] text-[var(--color-gold)] font-mono">✓ 默认</span>}
                      </div>
                      <p className="text-[10px] text-zinc-500 mt-1">{opt.hint}</p>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {activeNav === "theme" && (
            <div className="space-y-5">
              <div>
                <h3 className="text-sm font-bold text-[var(--color-text-primary)]">外观与界面主题</h3>
                <p className="text-xs text-[var(--color-text-secondary)] mt-0.5">
                  沉浸式电影调光暗黑模式与双模适配
                </p>
              </div>

              <div className="grid grid-cols-3 gap-3">
                {[
                  { id: "dark" as Theme, label: "暗夜调光 (Dark)", icon: "🌙" },
                  { id: "light" as Theme, label: "明亮模式 (Light)", icon: "☀️" },
                  { id: "system" as Theme, label: "跟随系统 (System)", icon: "💻" },
                ].map((th) => {
                  const active = currentTheme === th.id;
                  return (
                    <button
                      key={th.id}
                      type="button"
                      onClick={() => {
                        setTheme(th.id);
                        setForm({ ...form, theme: th.id });
                      }}
                      className={`flex flex-col items-center justify-center rounded-xl border p-4 transition-all ${
                        active
                          ? "border-[var(--color-gold)] bg-[var(--color-gold-muted)] text-[var(--color-gold)] shadow-sm font-bold"
                          : "border-[var(--color-border)] bg-[var(--color-bg)]/80 text-zinc-400 hover:text-zinc-200"
                      }`}
                    >
                      <span className="text-2xl mb-1.5">{th.icon}</span>
                      <span className="text-xs">{th.label}</span>
                    </button>
                  );
                })}
              </div>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
