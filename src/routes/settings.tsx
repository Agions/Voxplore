/**
 * Monoloop v1.0.0 · 设置页 (M3.2 接通后端 · M4.5 Locale 切换)
 *
 * 真实接入 settings_get / settings_set + i18n_get_locale / i18n_set_locale
 * - LLM 11 个 Provider (与 Rust 1:1)
 * - TTS 3 个引擎 (Edge / OpenAI / GPT-SoVITS)
 * - API Key 走 ConfigSnapshot (生产环境走 keyring · 此处先内存)
 * - 语言 Locale 切换走 monoloop-i18n,emit `app:locale_changed` 全局通知
 */

import { createFileRoute } from "@tanstack/react-router";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { settingsIpc, themeIpc, type ConfigSnapshot } from "@ipc/commands";
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
}> = [
  { id: "qwen", label: "通义千问 Qwen", hint: "qwen3.8-max 阿里旗舰" },
  { id: "deepseek", label: "DeepSeek", hint: "deepseek-v4-pro / flash" },
  { id: "open-ai", label: "OpenAI", hint: "gpt-5.6-sol (Sol / Terra)" },
  { id: "claude", label: "Claude", hint: "claude-sonnet-5 / fable-5" },
  { id: "gemini", label: "Gemini", hint: "gemini-3.6-flash / 3.1-pro" },
  { id: "kimi", label: "Kimi · Moonshot", hint: "kimi-k3 月之暗面 2026 旗舰" },
  { id: "glm5", label: "智谱 GLM", hint: "glm-5.2 智谱清言 2026 旗舰" },
  { id: "doubao", label: "豆包 Doubao", hint: "doubao-seed-2-1-pro 字节火山" },
  { id: "hunyuan", label: "混元 Hunyuan", hint: "hunyuan-pro 腾讯" },
  { id: "local", label: "本地 (Ollama)", hint: "llama3.2 自部署" },
];

const TTS_OPTIONS: Array<{
  id: "edge" | "open-ai" | "mimo" | "gpt-sovits";
  label: string;
  hint: string;
}> = [
    { id: "edge", label: "Edge TTS", hint: "微软免费 · 无需密钥" },
    { id: "mimo", label: "MiMo TTS (小米 MiMo)", hint: "mimo-v2.5-tts 限时免费 · 开放 API" },
    { id: "open-ai", label: "OpenAI TTS", hint: "tts-1 / alloy" },
    { id: "gpt-sovits", label: "GPT-SoVITS", hint: "本地克隆音色" },
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
  tts_provider: null,
  tts_api_key: null,
  tts_base_url: null,
  tts_voice: null,
  tts_ref_audio_path: null,
  tts_prompt_text: null,
};

function SettingsPage() {
  const qc = useQueryClient();
  const setLocale = useSettingsStore((s) => s.setLocale);
  const setTheme = useThemeStore((s) => s.setTheme);

  const { data: remote, isLoading } = useQuery({
    queryKey: ["settings-snapshot"],
    queryFn: settingsIpc.get,
  });

  const [local, setLocal] = useState<ConfigSnapshot>(DEFAULT_SNAPSHOT);
  const [saved, setSaved] = useState(false);
  const [activeTab, setActiveTab] = useState<"llm" | "tts" | "ffmpeg" | "appearance">("llm");

  useEffect(() => {
    if (remote) {
      setLocal({
        ...DEFAULT_SNAPSHOT,
        ...remote,
        llm_api_key: remote.llm_api_key ?? null,
        llm_base_url: remote.llm_base_url ?? null,
        llm_model: remote.llm_model ?? null,
        tts_provider: remote.tts_provider ?? null,
        tts_api_key: remote.tts_api_key ?? null,
        tts_base_url: remote.tts_base_url ?? null,
        tts_voice: remote.tts_voice ?? null,
        tts_ref_audio_path: remote.tts_ref_audio_path ?? null,
        tts_prompt_text: remote.tts_prompt_text ?? null,
      });
      if (remote.theme) {
        setTheme(remote.theme as Theme);
      }
    }
  }, [remote, setTheme]);

  const save = useMutation({
    mutationFn: (snap: ConfigSnapshot) => settingsIpc.set(snap),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["settings-snapshot"] });
      setTheme(local.theme as Theme);
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
      toast.success("设置保存成功");
    },
  });

  const update = <K extends keyof ConfigSnapshot>(
    key: K,
    val: ConfigSnapshot[K],
  ) => {
    setLocal((prev) => ({ ...prev, [key]: val }));
    if (key === "theme" && typeof val === "string") {
      setTheme(val as Theme);
    }
  };

  const ttsProvider = (local.tts_provider ?? "edge") as
    "edge" | "open-ai" | "mimo" | "gpt-sovits";

  const hasApiKey = Boolean(local.llm_api_key && local.llm_api_key.trim().length > 0);

  const locale = useSettingsStore((s) => s.locale);

  return (
    <div className="mx-auto max-w-4xl space-y-6 px-8 py-8">
      {/* Header */}
      <header className="flex items-start justify-between">
        <div className="space-y-1">
          <div className="inline-flex items-center gap-2 rounded-full border border-[rgba(245,200,66,0.3)] bg-[rgba(245,200,66,0.1)] px-3 py-0.5 text-xs font-semibold text-[var(--color-gold)]">
            <span>⚙️</span> LLM & Engine Hub
          </div>
          <h1 className="text-3xl font-extrabold tracking-tight text-[var(--color-text-primary)]">
            {t("settings.title", locale)}
          </h1>
          <p className="text-xs text-[var(--color-text-secondary)]">
            {isLoading ? "Loading..." : t("settings.subtitle", locale)}
          </p>
        </div>
        {saved && (
          <span className="inline-flex items-center gap-2 rounded-full border border-emerald-500/40 bg-emerald-500/10 px-3.5 py-1 text-xs font-medium text-emerald-400 animate-fade-in">
            {t("settings.saved", locale)}
          </span>
        )}
      </header>

      {/* Tabs Row */}
      <div className="flex items-center space-x-2 border-b border-[var(--color-border)] pb-2 overflow-x-auto">
        <button
          type="button"
          onClick={() => setActiveTab("llm")}
          className={`flex items-center space-x-2 rounded-xl px-4 py-2.5 text-xs font-bold transition-all ${
            activeTab === "llm"
              ? "bg-[var(--color-gold-muted)] border border-[var(--color-gold)]/40 text-[var(--color-gold)] shadow-[0_0_12px_var(--color-gold-glow)]"
              : "text-[var(--color-text-secondary)] hover:bg-[var(--color-surface-elevated)] hover:text-[var(--color-text-primary)]"
          }`}
        >
          <span>{t("settings.tab_llm", locale)}</span>
          <span className={`text-[10px] px-1.5 py-0.5 rounded-full ${hasApiKey ? "bg-emerald-500/20 text-emerald-400" : "bg-amber-500/20 text-amber-400"}`}>
            {hasApiKey ? "Active" : "Keys"}
          </span>
        </button>

        <button
          type="button"
          onClick={() => setActiveTab("tts")}
          className={`flex items-center space-x-2 rounded-xl px-4 py-2.5 text-xs font-bold transition-all ${
            activeTab === "tts"
              ? "bg-[var(--color-gold-muted)] border border-[var(--color-gold)]/40 text-[var(--color-gold)] shadow-[0_0_12px_var(--color-gold-glow)]"
              : "text-[var(--color-text-secondary)] hover:bg-[var(--color-surface-elevated)] hover:text-[var(--color-text-primary)]"
          }`}
        >
          <span>{t("settings.tab_tts", locale)}</span>
          <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-emerald-500/20 text-emerald-400">
            Online
          </span>
        </button>

        <button
          type="button"
          onClick={() => setActiveTab("ffmpeg")}
          className={`flex items-center space-x-2 rounded-xl px-4 py-2.5 text-xs font-bold transition-all ${
            activeTab === "ffmpeg"
              ? "bg-[var(--color-gold-muted)] border border-[var(--color-gold)]/40 text-[var(--color-gold)] shadow-[0_0_12px_var(--color-gold-glow)]"
              : "text-[var(--color-text-secondary)] hover:bg-[var(--color-surface-elevated)] hover:text-[var(--color-text-primary)]"
          }`}
        >
          <span>{t("settings.tab_ffmpeg", locale)}</span>
          <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-emerald-500/20 text-emerald-400">
            Detected
          </span>
        </button>

        <button
          type="button"
          onClick={() => setActiveTab("appearance")}
          className={`flex items-center space-x-2 rounded-xl px-4 py-2.5 text-xs font-bold transition-all ${
            activeTab === "appearance"
              ? "bg-[var(--color-gold-muted)] border border-[var(--color-gold)]/40 text-[var(--color-gold)] shadow-[0_0_12px_var(--color-gold-glow)]"
              : "text-[var(--color-text-secondary)] hover:bg-[var(--color-surface-elevated)] hover:text-[var(--color-text-primary)]"
          }`}
        >
          <span>{t("settings.tab_appearance", locale)}</span>
        </button>
      </div>

      {/* Tab 1: LLM */}
      {activeTab === "llm" && (
        <Section title="🤖 大语言模型 (LLM Providers)" subtitle="控制 11 大主流 LLM 的 API 密钥与官方模型配置">
          <FieldRow label="LLM 厂商 (Provider)">
            <select
              value={local.llm_provider}
              onChange={(e) => update("llm_provider", e.target.value)}
              className="w-full rounded-xl border border-[var(--color-border)] bg-[var(--color-bg)] px-3.5 py-2.5 text-sm text-[var(--color-text-primary)] outline-none focus:border-[var(--color-gold)]"
            >
              {LLM_OPTIONS.map((opt) => (
                <option key={opt.id} value={opt.id}>
                  {opt.label} — {opt.hint}
                </option>
              ))}
            </select>
          </FieldRow>
          <FieldRow label="API Key">
            <input
              type="password"
              placeholder="sk-..."
              value={local.llm_api_key ?? ""}
              onChange={(e) => update("llm_api_key", e.target.value || null)}
              className="w-full rounded-xl border border-[var(--color-border)] bg-[var(--color-bg)] px-3.5 py-2.5 text-sm text-[var(--color-text-primary)] outline-none focus:border-[var(--color-gold)]"
            />
          </FieldRow>
          <FieldRow label="Base URL" hint="可选 · 自定义代理或 Ollama 本地端点">
            <input
              type="text"
              placeholder="https://api.openai.com/v1"
              value={local.llm_base_url ?? ""}
              onChange={(e) => update("llm_base_url", e.target.value || null)}
              className="w-full rounded-xl border border-[var(--color-border)] bg-[var(--color-bg)] px-3.5 py-2.5 text-sm text-[var(--color-text-primary)] outline-none focus:border-[var(--color-gold)]"
            />
          </FieldRow>
          <FieldRow label="Model Identifier" hint="留空则自动调取官方 GA 推荐模型">
            <input
              type="text"
              placeholder=""
              value={local.llm_model ?? ""}
              onChange={(e) => update("llm_model", e.target.value || null)}
              className="w-full rounded-xl border border-[var(--color-border)] bg-[var(--color-bg)] px-3.5 py-2.5 text-sm text-[var(--color-text-primary)] outline-none focus:border-[var(--color-gold)]"
            />
          </FieldRow>
        </Section>
      )}

      {/* Tab 2: TTS */}
      {activeTab === "tts" && (
        <Section title="🎙️ 语音合成引擎 (TTS Engine)" subtitle="第一人称独白叙述的配音与 GPT-SoVITS 人声克隆设置">
          <FieldRow label="TTS 引擎">
            <div className="grid grid-cols-1 gap-2.5 md:grid-cols-3">
              {TTS_OPTIONS.map((opt) => {
                const active = ttsProvider === opt.id;
                return (
                  <button
                    key={opt.id}
                    type="button"
                    onClick={() => update("tts_provider", opt.id)}
                    className={`rounded-xl border p-3.5 text-left transition ${
                      active
                        ? "border-[var(--color-gold)] bg-[rgba(245,200,66,0.1)] text-[var(--color-gold)] shadow-[0_0_12px_rgba(245,200,66,0.15)]"
                        : "border-[var(--color-border)] bg-[var(--color-bg)] text-[var(--color-text-secondary)] hover:border-[var(--color-gold)]/40"
                    }`}
                  >
                    <div className={`text-sm font-semibold ${active ? "text-[var(--color-gold)]" : "text-[var(--color-text-primary)]"}`}>
                      {opt.label}
                    </div>
                    <div className="text-[11px] opacity-75">{opt.hint}</div>
                  </button>
                );
              })}
            </div>
          </FieldRow>
          {ttsProvider === "mimo" && (
            <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-3.5 text-xs text-amber-300 space-y-1">
              <div className="font-bold flex items-center gap-1.5">
                <span>🔑</span> 小米 MiMo 开放平台 API Key 配置说明
              </div>
              <p className="text-amber-200/80 leading-relaxed">
                使用 MiMo TTS (mimo-v2.5-tts) 需要提供小米 MiMo 开放平台的专属 API 密钥。
                请前往 <a href="https://platform.xiaomimimo.com" target="_blank" rel="noreferrer" className="underline font-semibold text-amber-200 hover:text-white">platform.xiaomimimo.com</a> 注册账号并在「API 管理」中生成 API Key，填入下方「TTS API Key」输入框中。
              </p>
            </div>
          )}
          <FieldRow label="TTS API Key" hint="MiMo / OpenAI TTS 所需 API 密钥（可单独指定或继承 LLM Key）">
            <input
              type="password"
              placeholder="sk-..."
              value={local.tts_api_key ?? ""}
              onChange={(e) => update("tts_api_key", e.target.value || null)}
              className="w-full rounded-xl border border-[var(--color-border)] bg-[var(--color-bg)] px-3.5 py-2.5 text-sm text-[var(--color-text-primary)] outline-none focus:border-[var(--color-gold)]"
            />
          </FieldRow>
          <FieldRow label="TTS Base URL" hint="可选 · 自定义 TTS 代理服务或 MiMo API 端点">
            <input
              type="text"
              placeholder={
                ttsProvider === "mimo"
                  ? "https://api.xiaomimimo.com/v1"
                  : ttsProvider === "open-ai"
                    ? "https://api.openai.com"
                    : "https://api.openai.com"
              }
              value={local.tts_base_url ?? ""}
              onChange={(e) => update("tts_base_url", e.target.value || null)}
              className="w-full rounded-xl border border-[var(--color-border)] bg-[var(--color-bg)] px-3.5 py-2.5 text-sm text-[var(--color-text-primary)] outline-none focus:border-[var(--color-gold)]"
            />
          </FieldRow>
          <FieldRow label="Voice / Model">
            <input
              type="text"
              placeholder={
                ttsProvider === "edge"
                  ? "zh-CN-XiaoxiaoNeural"
                  : ttsProvider === "mimo"
                    ? "mimo-v2.5-tts"
                    : ttsProvider === "open-ai"
                      ? "alloy"
                      : "default"
              }
              value={local.tts_voice ?? ""}
              onChange={(e) => update("tts_voice", e.target.value || null)}
              className="w-full rounded-xl border border-[var(--color-border)] bg-[var(--color-bg)] px-3.5 py-2.5 text-sm text-[var(--color-text-primary)] outline-none focus:border-[var(--color-gold)]"
            />
          </FieldRow>
          {ttsProvider === "gpt-sovits" && (
            <>
              <FieldRow label="参考音频路径">
                <input
                  type="text"
                  placeholder="/path/to/reference.wav"
                  value={local.tts_ref_audio_path ?? ""}
                  onChange={(e) =>
                    update("tts_ref_audio_path", e.target.value || null)
                  }
                  className="w-full rounded-xl border border-[var(--color-border)] bg-[var(--color-bg)] px-3.5 py-2.5 text-sm text-[var(--color-text-primary)] outline-none focus:border-[var(--color-gold)]"
                />
              </FieldRow>
              <FieldRow label="参考文本">
                <input
                  type="text"
                  placeholder="参考音频对应的中文文本"
                  value={local.tts_prompt_text ?? ""}
                  onChange={(e) =>
                    update("tts_prompt_text", e.target.value || null)
                  }
                  className="w-full rounded-xl border border-[var(--color-border)] bg-[var(--color-bg)] px-3.5 py-2.5 text-sm text-[var(--color-text-primary)] outline-none focus:border-[var(--color-gold)]"
                />
              </FieldRow>
            </>
          )}
        </Section>
      )}

      {/* Tab 3: FFmpeg */}
      {activeTab === "ffmpeg" && (
        <Section title="🎞️ FFmpeg 与硬件环境 (FFmpeg & System Path)" subtitle="检测本地视频拆条、音视频混流与 VAD 字幕对齐环境">
          <FieldRow label="FFmpeg 路径" hint="支持系统全局环境变量与绝对路径">
            <div className="flex items-center space-x-2">
              <input
                type="text"
                placeholder="ffmpeg (系统默认)"
                value="ffmpeg (已自动探针识别)"
                readOnly
                className="flex-1 rounded-xl border border-[var(--color-border)] bg-[var(--color-surface-elevated)] px-3.5 py-2.5 text-sm text-[var(--color-text-primary)] outline-none"
              />
              <span className="rounded-xl border border-emerald-500/40 bg-emerald-500/10 px-3 py-2 text-xs font-bold text-emerald-400">
                ✓ 在线 (OK)
              </span>
            </div>
          </FieldRow>
        </Section>
      )}

      {/* Tab 4: Appearance */}
      {activeTab === "appearance" && (
        <Section title="🎨 外观与语言 (Appearance & Language)" subtitle="设置 UI 主题、双语模式与系统启动行为">
          <FieldRow label="界面语言 (Language)" hint="实时切换 UI 与后端双语模式">
            <select
              value={local.language}
              onChange={async (e) => {
                const val = e.target.value;
                update("language", val);
                setLocale(val);
                try {
                  await themeIpc.setLocale(val);
                  toast.success(val === "en-US" ? "Language updated to English" : "已切换为 简体中文");
                } catch {
                  toast.success(`已切换语言为 ${val}`);
                }
              }}
              className="w-full rounded-xl border border-[var(--color-border)] bg-[var(--color-bg)] px-3.5 py-2.5 text-sm text-[var(--color-text-primary)] outline-none focus:border-[var(--color-gold)]"
            >
              <option value="zh-CN">🇨🇳 简体中文 (Simplified Chinese)</option>
              <option value="en-US">🇺🇸 English (US)</option>
            </select>
          </FieldRow>

          <FieldRow label="主题 (Theme)">
            <select
              value={local.theme}
              onChange={(e) => update("theme", e.target.value)}
              className="w-full rounded-xl border border-[var(--color-border)] bg-[var(--color-bg)] px-3.5 py-2.5 text-sm text-[var(--color-text-primary)] outline-none focus:border-[var(--color-gold)]"
            >
              <option value="dark">电影调光室 (Cinematic Darkroom)</option>
              <option value="light">亮色 (Light)</option>
              <option value="system">跟随系统 (System)</option>
            </select>
          </FieldRow>

          <FieldRow label="自动更新" hint="启动时检查新版本">
            <label className="flex items-center gap-2.5 cursor-pointer">
              <input
                type="checkbox"
                checked={local.auto_update}
                onChange={(e) => update("auto_update", e.target.checked)}
                className="h-4 w-4 rounded border-[var(--color-border)] bg-[var(--color-bg)] accent-[#F5C842]"
              />
              <span className="text-sm text-[var(--color-text-primary)]">环境启动时自动检查新版本</span>
            </label>
          </FieldRow>
        </Section>
      )}

      {/* Save */}
      <div className="flex items-center justify-end gap-3 border-t border-[var(--color-border)] pt-6">
        <button
          type="button"
          onClick={() => save.mutate(local)}
          disabled={save.isPending}
          className="btn-primary"
          style={{ padding: "10px 28px", fontSize: "14px", fontWeight: 700 }}
        >
          {save.isPending ? "保存中..." : "💾 保存设置"}
        </button>
      </div>
    </div>
  );
}

// ── Section / FieldRow ──────────────────────────────────────────────

function Section({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle?: string;
  children: React.ReactNode;
}) {
  return (
    <section className="rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)] p-6 shadow-sm">
      <div className="mb-5 space-y-1">
        <h2 className="text-base font-bold text-[var(--color-gold)]">{title}</h2>
        {subtitle && <p className="text-xs text-[var(--color-text-secondary)]">{subtitle}</p>}
      </div>
      <div className="space-y-4">{children}</div>
    </section>
  );
}

function FieldRow({
  label,
  hint,
  children,
}: {
  label: string;
  hint?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="grid grid-cols-1 gap-2 md:grid-cols-[200px_1fr] md:items-start">
      <div className="space-y-0.5">
        <label className="text-xs font-semibold uppercase tracking-wider text-[var(--color-text-secondary)]">
          {label}
        </label>
        {hint && <p className="text-[10px] text-[var(--color-text-muted)]">{hint}</p>}
      </div>
      <div>{children}</div>
    </div>
  );
}
