/**
 * SceneFab v2.5.0 · 设置页 (M3.2 接通后端 · M4.5 Locale 切换)
 *
 * 真实接入 settings_get / settings_set + i18n_get_locale / i18n_set_locale
 * - LLM 11 个 Provider (与 Rust 1:1)
 * - TTS 3 个引擎 (Edge / OpenAI / GPT-SoVITS)
 * - API Key 走 ConfigSnapshot (生产环境走 keyring · 此处先内存)
 * - 语言 Locale 切换走 scenefab-i18n,emit `app:locale_changed` 全局通知
 */

import { createFileRoute } from "@tanstack/react-router";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { settingsIpc, themeIpc, type ConfigSnapshot } from "@ipc/commands";
import { useTauriEvent } from "@hooks/useTauriEvent";
import { toast } from "sonner";

export const Route = createFileRoute("/settings")({
  component: SettingsPage,
});

const LLM_OPTIONS: Array<{
  id: string;
  label: string;
  hint: string;
}> = [
  { id: "qwen", label: "通义千问 Qwen", hint: "阿里 · OpenAI 兼容" },
  { id: "kimi", label: "Kimi · Moonshot", hint: "月之暗面 · 长上下文" },
  { id: "glm5", label: "智谱 GLM5", hint: "国产主力" },
  { id: "claude", label: "Claude", hint: "Anthropic 原生" },
  { id: "gemini", label: "Gemini", hint: "Google 原生" },
  { id: "deepseek", label: "DeepSeek", hint: "国产开源强模" },
  { id: "doubao", label: "豆包 Doubao", hint: "字节跳动" },
  { id: "hunyuan", label: "混元 Hunyuan", hint: "腾讯" },
  { id: "open-ai", label: "OpenAI", hint: "GPT-4o / GPT-4-Turbo" },
  { id: "local", label: "本地 (Ollama)", hint: "自部署 / 代理" },
  { id: "qwen37", label: "Qwen 3.7 实验版", hint: "OpenAI 兼容" },
];

const TTS_OPTIONS: Array<{
  id: "edge" | "open-ai" | "gpt-sovits";
  label: string;
  hint: string;
}> = [
  { id: "edge", label: "Edge TTS", hint: "微软免费 · 无需密钥" },
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
  tts_voice: null,
  tts_ref_audio_path: null,
  tts_prompt_text: null,
};

function SettingsPage() {
  const qc = useQueryClient();
  const { data: remote, isLoading } = useQuery({
    queryKey: ["settings-snapshot"],
    queryFn: settingsIpc.get,
  });

  const [local, setLocal] = useState<ConfigSnapshot>(DEFAULT_SNAPSHOT);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (remote) {
      // 合并后端值与本地默认值,避免 null
      setLocal({
        ...DEFAULT_SNAPSHOT,
        ...remote,
        llm_api_key: remote.llm_api_key ?? null,
        llm_base_url: remote.llm_base_url ?? null,
        llm_model: remote.llm_model ?? null,
        tts_provider: remote.tts_provider ?? null,
        tts_voice: remote.tts_voice ?? null,
        tts_ref_audio_path: remote.tts_ref_audio_path ?? null,
        tts_prompt_text: remote.tts_prompt_text ?? null,
      });
    }
  }, [remote]);

  const save = useMutation({
    mutationFn: (snap: ConfigSnapshot) => settingsIpc.set(snap),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["settings-snapshot"] });
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    },
  });

  const update = <K extends keyof ConfigSnapshot>(
    key: K,
    val: ConfigSnapshot[K],
  ) => {
    setLocal((prev) => ({ ...prev, [key]: val }));
  };

  const ttsProvider = (local.tts_provider ?? "edge") as
    "edge" | "open-ai" | "gpt-sovits";

  return (
    <div className="mx-auto max-w-3xl space-y-8 px-8 py-10">
      <header className="flex items-start justify-between">
        <div className="space-y-1">
          <div className="text-[10px] font-semibold uppercase tracking-[0.2em] text-violet-400">
            Settings
          </div>
          <h1 className="text-3xl font-bold tracking-tight">设置</h1>
          <p className="text-sm text-zinc-500">
            {isLoading ? "加载中..." : "配置 LLM / TTS / 主题 / 语言"}
          </p>
        </div>
        {saved && (
          <span className="inline-flex items-center gap-2 rounded-full border border-emerald-700/40 bg-emerald-950/30 px-3 py-1 text-xs text-emerald-300">
            ✓ 已保存
          </span>
        )}
      </header>

      {/* LLM */}
      <Section title="大语言模型" subtitle="脚本生成的智能引擎">
        <FieldRow label="Provider">
          <select
            value={local.llm_provider}
            onChange={(e) => update("llm_provider", e.target.value)}
            className="w-full rounded-lg border border-zinc-800 bg-zinc-950 px-3 py-2 text-sm text-zinc-100 outline-none focus:border-violet-500"
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
            className="w-full rounded-lg border border-zinc-800 bg-zinc-950 px-3 py-2 text-sm text-zinc-100 outline-none focus:border-violet-500"
          />
        </FieldRow>
        <FieldRow label="Base URL" hint="可选 · 自定义代理或本地端点">
          <input
            type="text"
            placeholder="https://api.openai.com"
            value={local.llm_base_url ?? ""}
            onChange={(e) => update("llm_base_url", e.target.value || null)}
            className="w-full rounded-lg border border-zinc-800 bg-zinc-950 px-3 py-2 text-sm text-zinc-100 outline-none focus:border-violet-500"
          />
        </FieldRow>
        <FieldRow label="Model" hint="默认使用 Provider 推荐模型">
          <input
            type="text"
            placeholder="gpt-4o"
            value={local.llm_model ?? ""}
            onChange={(e) => update("llm_model", e.target.value || null)}
            className="w-full rounded-lg border border-zinc-800 bg-zinc-950 px-3 py-2 text-sm text-zinc-100 outline-none focus:border-violet-500"
          />
        </FieldRow>
      </Section>

      {/* TTS */}
      <Section title="语音合成" subtitle="第一步人称叙述的配音引擎">
        <FieldRow label="TTS 引擎">
          <div className="grid grid-cols-1 gap-2 md:grid-cols-3">
            {TTS_OPTIONS.map((opt) => {
              const active = ttsProvider === opt.id;
              return (
                <button
                  key={opt.id}
                  type="button"
                  onClick={() => update("tts_provider", opt.id)}
                  className={`rounded-xl border p-3 text-left transition ${
                    active
                      ? "border-violet-500/60 bg-violet-500/10"
                      : "border-zinc-800 bg-zinc-950 hover:border-zinc-700"
                  }`}
                >
                  <div className="text-sm font-medium text-zinc-100">
                    {opt.label}
                  </div>
                  <div className="text-[10px] text-zinc-500">{opt.hint}</div>
                </button>
              );
            })}
          </div>
        </FieldRow>
        <FieldRow label="Voice / Model">
          <input
            type="text"
            placeholder={
              ttsProvider === "edge"
                ? "zh-CN-XiaoxiaoNeural"
                : ttsProvider === "open-ai"
                  ? "alloy"
                  : "default"
            }
            value={local.tts_voice ?? ""}
            onChange={(e) => update("tts_voice", e.target.value || null)}
            className="w-full rounded-lg border border-zinc-800 bg-zinc-950 px-3 py-2 text-sm text-zinc-100 outline-none focus:border-violet-500"
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
                className="w-full rounded-lg border border-zinc-800 bg-zinc-950 px-3 py-2 text-sm text-zinc-100 outline-none focus:border-violet-500"
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
                className="w-full rounded-lg border border-zinc-800 bg-zinc-950 px-3 py-2 text-sm text-zinc-100 outline-none focus:border-violet-500"
              />
            </FieldRow>
          </>
        )}
      </Section>

      {/* Appearance */}
      <Section title="外观与语言">
        <FieldRow label="主题">
          <select
            value={local.theme}
            onChange={(e) => update("theme", e.target.value)}
            className="w-full rounded-lg border border-zinc-800 bg-zinc-950 px-3 py-2 text-sm text-zinc-100 outline-none focus:border-violet-500"
          >
            <option value="light">亮色</option>
            <option value="dark">暗色</option>
            <option value="system">跟随系统</option>
          </select>
        </FieldRow>
        <FieldRow label="语言" hint="后端文案 · scenefab-i18n 实时生效">
          <LocaleSwitcher
            currentLocale={local.language}
            onChange={(loc) => update("language", loc)}
          />
        </FieldRow>
        <FieldRow label="自动更新" hint="启动时检查新版本">
          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={local.auto_update}
              onChange={(e) => update("auto_update", e.target.checked)}
              className="h-4 w-4 rounded border-zinc-700 bg-zinc-950"
            />
            <span className="text-sm text-zinc-300">启用自动检查</span>
          </label>
        </FieldRow>
      </Section>

      {/* Save */}
      <div className="flex items-center justify-end gap-3 border-t border-zinc-800 pt-6">
        <button
          type="button"
          onClick={() => save.mutate(local)}
          disabled={save.isPending}
          className="rounded-xl bg-gradient-to-r from-blue-500 to-violet-500 px-6 py-2.5 text-sm font-semibold text-white shadow-lg shadow-blue-500/30 transition hover:shadow-blue-500/50 disabled:opacity-50"
        >
          {save.isPending ? "保存中..." : "保存设置"}
        </button>
      </div>
    </div>
  );
}

// ── LocaleSwitcher · 后端 Locale 切换器 (M4.5 接 scenefab-i18n) ──
function LocaleSwitcher({
  currentLocale,
  onChange,
}: {
  currentLocale: string;
  onChange: (locale: string) => void;
}) {
  // 启动时拉一次后端 locale(后端是 single source of truth)
  const { data: backendLocale } = useQuery({
    queryKey: ["i18n-current-locale"],
    queryFn: themeIpc.getLocale,
    staleTime: 30_000,
  });

  // 监听后端 emit 的 app:locale_changed,跨窗口/多端同步
  useTauriEvent<{ locale: string }>("app:locale_changed", (e) => {
    onChange(e.payload.locale);
  });

  // 启动时把后端 locale 同步到 ConfigSnapshot.language
  useEffect(() => {
    if (backendLocale && backendLocale !== currentLocale) {
      onChange(backendLocale);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [backendLocale]);

  const switchLocale = async (loc: string) => {
    if (loc === currentLocale) return;
    try {
      const ok = await themeIpc.setLocale(loc);
      if (ok) {
        onChange(loc);
        toast.success(`已切换到 ${loc}`);
      } else {
        toast.error(`不支持的 Locale: ${loc}`, {
          description: "当前仅支持 zh-CN / en-US",
        });
      }
    } catch (e) {
      toast.error("切换语言失败", {
        description: e instanceof Error ? e.message : String(e),
      });
    }
  };

  const OPTIONS: Array<{ value: string; label: string; flag: string }> = [
    { value: "zh-CN", label: "简体中文", flag: "🇨🇳" },
    { value: "en-US", label: "English", flag: "🇺🇸" },
  ];

  return (
    <div className="grid grid-cols-2 gap-2">
      {OPTIONS.map((opt) => {
        const active = currentLocale === opt.value;
        return (
          <button
            key={opt.value}
            type="button"
            onClick={() => void switchLocale(opt.value)}
            className={`flex items-center gap-2 rounded-xl border p-2.5 text-left transition ${
              active
                ? "border-violet-500/60 bg-violet-500/10"
                : "border-zinc-800 bg-zinc-950 hover:border-zinc-700"
            }`}
          >
            <span className="text-lg">{opt.flag}</span>
            <div className="flex-1">
              <div className="text-sm font-medium text-zinc-100">
                {opt.label}
              </div>
              <div className="text-[10px] text-zinc-500">{opt.value}</div>
            </div>
            {active && (
              <span className="text-[10px] font-semibold text-violet-300">
                ✓
              </span>
            )}
          </button>
        );
      })}
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
    <section className="rounded-2xl border border-zinc-800 bg-zinc-900/40 p-6">
      <div className="mb-5 space-y-1">
        <h2 className="text-base font-semibold text-zinc-100">{title}</h2>
        {subtitle && <p className="text-xs text-zinc-500">{subtitle}</p>}
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
        <label className="text-xs font-medium uppercase tracking-wider text-zinc-400">
          {label}
        </label>
        {hint && <p className="text-[10px] text-zinc-600">{hint}</p>}
      </div>
      <div>{children}</div>
    </div>
  );
}
