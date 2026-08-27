/**
 * splicr v1.0.1 · 设置与模型引擎中心 (深度优化 LLM 与 TTS 全厂商 API 密钥与专属参数配置)
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

interface LlmMeta {
  id: string;
  name: string;
  badge: string;
  desc: string;
  icon: string;
  defaultModel: string;
  color: string;
}

const LLM_OPTIONS: LlmMeta[] = [
  { id: "qwen", name: "通义千问 Qwen", badge: "阿里旗舰", desc: "qwen3.8-max · 原生多模态与爆点 Hook 解析", icon: "🌐", defaultModel: "qwen3.8-max", color: "from-blue-500/20 to-indigo-500/10" },
  { id: "deepseek", name: "DeepSeek", badge: "强逻辑推理", desc: "deepseek-v4-pro · 复杂剧情冲突与反转逻辑链", icon: "⚡", defaultModel: "deepseek-v4-pro", color: "from-sky-500/20 to-blue-500/10" },
  { id: "open-ai", name: "OpenAI", badge: "国际旗舰", desc: "gpt-5.6-sol · 电影级第一人称独白叙事", icon: "🟢", defaultModel: "gpt-5.6-sol", color: "from-emerald-500/20 to-teal-500/10" },
  { id: "claude", name: "Claude", badge: "文学大师", desc: "claude-sonnet-5 · 细腻情感修辞与深度影评", icon: "🟣", defaultModel: "claude-sonnet-5", color: "from-purple-500/20 to-violet-500/10" },
  { id: "gemini", name: "Gemini", badge: "百万帧感知", desc: "gemini-3.6-flash · 超长上下文全季连续梗概", icon: "🔷", defaultModel: "gemini-3.6-flash", color: "from-cyan-500/20 to-blue-500/10" },
  { id: "kimi", name: "Kimi · 月之暗面", badge: "长剧拆条", desc: "kimi-k3 · 百万字原著改编与背景设定集", icon: "🌙", defaultModel: "kimi-k3", color: "from-amber-500/20 to-orange-500/10" },
  { id: "glm5", name: "智谱 GLM", badge: "清华开源", desc: "glm-5.2 · 中文影视剧本与情感递进深度调优", icon: "🔮", defaultModel: "glm-5.2", color: "from-indigo-500/20 to-purple-500/10" },
  { id: "doubao", name: "豆包 Doubao", badge: "字节短剧", desc: "doubao-seed-2-1-pro · 抖音快手高完播率解说", icon: "📦", defaultModel: "doubao-seed-2-1-pro", color: "from-rose-500/20 to-pink-500/10" },
  { id: "hunyuan", name: "混元 Hunyuan", badge: "腾讯旗舰", desc: "hunyuan-pro · 腾讯多模态结构化剧情生成", icon: "🐧", defaultModel: "hunyuan-pro", color: "from-blue-600/20 to-cyan-500/10" },
  { id: "local", name: "本地 Ollama", badge: "私有离线", desc: "llama3.2 / qwen2.5 (127.0.0.1:11434)", icon: "💻", defaultModel: "llama3.2", color: "from-zinc-500/20 to-zinc-600/10" },
];

interface TtsMeta {
  id: "edge" | "mimo" | "open-ai" | "gpt-sovits";
  label: string;
  tag: string;
  hint: string;
  icon: string;
  needApiKey: boolean;
  defaultBaseUrl?: string;
  defaultModel?: string;
}

const TTS_OPTIONS: TtsMeta[] = [
  { id: "edge", label: "Edge TTS", tag: "免费免Key", hint: "微软官方 · 48kHz 高清采样 · 50+ 电影声优", icon: "🎙️", needApiKey: false },
  { id: "mimo", label: "MiMo TTS (小米)", tag: "小米开放平台", hint: "mimo-v2.5-tts · 情感细腻自然人声 (需填写小米开放平台 API Key)", icon: "📱", needApiKey: true, defaultBaseUrl: "https://api.mimo.xiaomi.com/v1", defaultModel: "mimo-v2.5-tts" },
  { id: "open-ai", label: "OpenAI TTS", tag: "影视级原声", hint: "tts-1-hd / alloy / onyx 电影级情绪声线 (需填写 OpenAI API Key)", icon: "💎", needApiKey: true, defaultBaseUrl: "https://api.openai.com/v1", defaultModel: "tts-1-hd" },
  { id: "gpt-sovits", label: "GPT-SoVITS", tag: "零样本克隆", hint: "本地部署 127.0.0.1:9880 · 5 秒参考音频克隆音色", icon: "🧬", needApiKey: false, defaultBaseUrl: "http://127.0.0.1:9880" },
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
  const setLocale = useSettingsStore((s) => s.setLocale);
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
      toast.error(t("settings.save_failed", locale) || "保存设置失败", {
        description: e instanceof Error ? e.message : String(e),
      });
    },
  });

  const handleSave = () => {
    saveMutation.mutate(form);
  };

  const currentLlm = LLM_OPTIONS.find((o) => o.id === form.llm_provider) || LLM_OPTIONS[0];
  const currentTts = TTS_OPTIONS.find((o) => o.id === form.tts_provider) || TTS_OPTIONS[0];

  return (
    <div className="h-full w-full overflow-y-auto bg-[var(--color-bg)] p-6 md:p-8 select-none font-sans">
      <div className="mx-auto max-w-5xl space-y-6">
        {/* 1. Header 顶栏 */}
        <header className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-[var(--color-border)] pb-5">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <span className="h-2 w-2 rounded-full bg-[var(--color-gold)] shadow-[0_0_8px_var(--color-gold)]" />
              <span className="text-[11px] font-mono font-bold tracking-wider text-[var(--color-gold)] uppercase">
                Studio Engine & AI Configuration
              </span>
            </div>
            <h1 className="text-2xl font-black tracking-tight text-[var(--color-text-primary)]">
              {t("settings.title", locale)}
            </h1>
            <p className="text-xs text-[var(--color-text-secondary)]">
              统一调度 11 大最新主流 LLM 大模型矩阵、48kHz 影视配音引擎与本地渲染配置
            </p>
          </div>

          <button
            type="button"
            onClick={handleSave}
            disabled={saveMutation.isPending || isLoading}
            className="flex items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-[#F5C842] to-[#E8933A] px-6 py-2.5 text-xs font-black text-zinc-950 shadow-[0_0_16px_rgba(245,200,66,0.3)] transition-all hover:brightness-110 active:scale-95 disabled:opacity-50"
          >
            <span>💾</span>
            <span>{saveMutation.isPending ? "保存中..." : t("settings.save", locale) || "保存设置"}</span>
          </button>
        </header>

        {/* 2. 左右结构化工作台 */}
        <div className="grid grid-cols-1 md:grid-cols-[220px_1fr] gap-6 items-start">
          {/* 左侧控制机架 (Rack Navigation) */}
          <aside className="flex md:flex-col gap-1.5 rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)] p-2 shadow-sm">
            {[
              { id: "llm" as const, label: "大模型矩阵", sub: "10+ Providers", icon: "🧠" },
              { id: "tts" as const, label: "配音与克隆", sub: "Edge / MiMo / SoVITS", icon: "🎙️" },
              { id: "theme" as const, label: "偏好与外观", sub: "Theme & Lang", icon: "🎨" },
            ].map((item) => {
              const active = activeNav === item.id;
              return (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => setActiveNav(item.id)}
                  className={`flex flex-1 md:flex-initial items-center gap-3 rounded-xl px-3.5 py-2.5 text-left transition-all border ${
                    active
                      ? "border-[var(--color-gold)]/40 bg-[var(--color-gold-muted)] text-[var(--color-gold)] shadow-sm font-bold"
                      : "border-transparent text-[var(--color-text-secondary)] hover:bg-[var(--color-surface-elevated)] hover:text-[var(--color-text-primary)]"
                  }`}
                >
                  <span className="text-base">{item.icon}</span>
                  <div className="flex flex-col min-w-0">
                    <span className="text-xs truncate">{item.label}</span>
                    <span className="text-[9px] opacity-60 font-mono">{item.sub}</span>
                  </div>
                </button>
              );
            })}
          </aside>

          {/* 右侧主配置视窗 */}
          <main className="rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)] p-5 sm:p-6 shadow-sm space-y-6">
            {/* ── Tab 1: 大语言模型矩阵 (LLM) ── */}
            {activeNav === "llm" && (
              <div className="space-y-6">
                <div className="flex items-center justify-between border-b border-[var(--color-border)] pb-3">
                  <div>
                    <h3 className="text-sm font-bold text-[var(--color-text-primary)]">
                      默认 AI 解说大语言模型
                    </h3>
                    <p className="text-xs text-[var(--color-text-secondary)] mt-0.5">
                      Multi-Agent 编剧将优先调度此模型结合多模态关键帧生成黄金 Hook 与反转独白
                    </p>
                  </div>
                  <span className="rounded-md border border-[var(--color-border)] bg-[var(--color-surface-elevated)] px-2.5 py-1 font-mono text-[10px] text-[var(--color-gold)] font-bold">
                    当前选用: {currentLlm?.name} ({currentLlm?.defaultModel})
                  </span>
                </div>

                {/* 10 大大模型卡片网格 */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {LLM_OPTIONS.map((opt) => {
                    const isSelected = form.llm_provider === opt.id;
                    return (
                      <div
                        key={opt.id}
                        onClick={() => setForm({ ...form, llm_provider: opt.id })}
                        className={`group relative flex flex-col justify-between rounded-xl border p-3.5 cursor-pointer transition-all duration-200 ${
                          isSelected
                            ? "border-[var(--color-gold)] bg-gradient-to-br " + opt.color + " shadow-md"
                            : "border-[var(--color-border)] bg-[var(--color-surface-elevated)]/60 hover:border-[var(--color-gold)]/40 hover:bg-[var(--color-surface-elevated)]"
                        }`}
                      >
                        <div className="flex items-start justify-between gap-2">
                          <div className="flex items-center gap-2">
                            <span className="text-lg">{opt.icon}</span>
                            <div>
                              <div className="text-xs font-bold text-[var(--color-text-primary)]">
                                {opt.name}
                              </div>
                              <span className="text-[9px] font-mono text-[var(--color-text-muted)]">
                                {opt.badge}
                              </span>
                            </div>
                          </div>

                          <div className="flex items-center">
                            {isSelected ? (
                              <span className="flex items-center gap-1 rounded-full bg-[var(--color-gold)] px-2 py-0.5 text-[9px] font-black text-zinc-950 shadow-sm">
                                ✓ 已激活
                              </span>
                            ) : (
                              <span className="h-3 w-3 rounded-full border border-[var(--color-border)] opacity-0 group-hover:opacity-100 transition-opacity" />
                            )}
                          </div>
                        </div>

                        <p className="text-[10px] text-[var(--color-text-secondary)] mt-2 line-clamp-1">
                          {opt.desc}
                        </p>
                      </div>
                    );
                  })}
                </div>

                {/* 密钥与代理端点参数配置卡片 */}
                <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface-elevated)]/40 p-4 space-y-4">
                  <div className="flex items-center gap-2 text-xs font-bold text-[var(--color-gold)]">
                    <span>🔑</span>
                    <span>{currentLlm?.name} · 专属参数与凭证</span>
                  </div>

                  <div className="space-y-1.5">
                    <label className="block text-xs font-semibold text-[var(--color-text-secondary)]">
                      API Key (密钥凭证)
                    </label>
                    <input
                      type="password"
                      placeholder="sk-..."
                      value={form.llm_api_key ?? ""}
                      onChange={(e) => setForm({ ...form, llm_api_key: e.target.value || null })}
                      className="w-full font-mono text-xs"
                    />
                    <p className="text-[10px] text-[var(--color-text-muted)]">
                      密钥经由本地系统加密隔离，直接直连模型 API，绝不经过任何第三方服务器
                    </p>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
                    <div className="space-y-1.5">
                      <label className="block text-xs font-semibold text-[var(--color-text-secondary)]">
                        自定义模型代号 (Model Override)
                      </label>
                      <input
                        type="text"
                        placeholder={`默认: ${currentLlm?.defaultModel}`}
                        value={form.llm_model ?? ""}
                        onChange={(e) => setForm({ ...form, llm_model: e.target.value || null })}
                        className="w-full font-mono text-xs"
                      />
                    </div>

                    <div className="space-y-1.5">
                      <label className="block text-xs font-semibold text-[var(--color-text-secondary)]">
                        自定义 Base URL (代理 / 内网转发)
                      </label>
                      <input
                        type="text"
                        placeholder="https://api.openai.com/v1"
                        value={form.llm_base_url ?? ""}
                        onChange={(e) => setForm({ ...form, llm_base_url: e.target.value || null })}
                        className="w-full font-mono text-xs"
                      />
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* ── Tab 2: TTS 语音合成与克隆 ── */}
            {activeNav === "tts" && (
              <div className="space-y-6">
                <div className="flex items-center justify-between border-b border-[var(--color-border)] pb-3">
                  <div>
                    <h3 className="text-sm font-bold text-[var(--color-text-primary)]">
                      默认语音合成引擎 (TTS Engine)
                    </h3>
                    <p className="text-xs text-[var(--color-text-secondary)] mt-0.5">
                      生成 48kHz 沉浸解说配音音频，并支持零样本音色克隆
                    </p>
                  </div>
                  <span className="rounded-md border border-[var(--color-border)] bg-[var(--color-surface-elevated)] px-2.5 py-1 font-mono text-[10px] text-[var(--color-gold)] font-bold">
                    当前选用: {currentTts?.label}
                  </span>
                </div>

                {/* 4 大 TTS 引擎卡片网格 */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {TTS_OPTIONS.map((opt) => {
                    const isSelected = form.tts_provider === opt.id;
                    return (
                      <div
                        key={opt.id}
                        onClick={() => setForm({ ...form, tts_provider: opt.id })}
                        className={`flex flex-col justify-between rounded-xl border p-3.5 cursor-pointer transition-all ${
                          isSelected
                            ? "border-[var(--color-gold)] bg-[var(--color-gold-muted)] shadow-md"
                            : "border-[var(--color-border)] bg-[var(--color-surface-elevated)]/60 hover:border-[var(--color-gold)]/40 hover:bg-[var(--color-surface-elevated)]"
                        }`}
                      >
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            <span className="text-lg">{opt.icon}</span>
                            <div>
                              <div className="text-xs font-bold text-[var(--color-text-primary)]">
                                {opt.label}
                              </div>
                              <span className="rounded bg-[var(--color-surface)] px-1.5 py-0.2 font-mono text-[9px] font-bold text-[var(--color-gold)]">
                                {opt.tag}
                              </span>
                            </div>
                          </div>

                          {isSelected && (
                            <span className="rounded-full bg-[var(--color-gold)] px-2 py-0.5 text-[9px] font-black text-zinc-950 shadow-sm">
                              ✓ 已激活
                            </span>
                          )}
                        </div>
                        <p className="text-[10px] text-[var(--color-text-secondary)] mt-2">
                          {opt.hint}
                        </p>
                      </div>
                    );
                  })}
                </div>

                {/* TTS 专属凭证与参数配置卡片 (为 Xiaomi MiMo / OpenAI / GPT-SoVITS 专属提供 API Key 与 Base URL) */}
                <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface-elevated)]/40 p-4 space-y-4">
                  <div className="flex items-center gap-2 text-xs font-bold text-[var(--color-gold)]">
                    <span>🎙️</span>
                    <span>{currentTts?.label} · 专属参数与凭证配置</span>
                  </div>

                  {currentTts?.needApiKey && (
                    <div className="space-y-1.5">
                      <label className="block text-xs font-semibold text-[var(--color-text-secondary)]">
                        {currentTts.label} API Key (密钥凭证)
                      </label>
                      <input
                        type="password"
                        placeholder={`请输入 ${currentTts.label} 的 API Key...`}
                        value={form.tts_api_key ?? ""}
                        onChange={(e) => setForm({ ...form, tts_api_key: e.target.value || null })}
                        className="w-full font-mono text-xs"
                      />
                      <p className="text-[10px] text-[var(--color-text-muted)]">
                        {currentTts.id === "mimo"
                          ? "前往小米开放平台 (MiMo Voice API) 控制台获取专属 API Key"
                          : "前往 OpenAI 开发者平台获取专属 API Key"}
                      </p>
                    </div>
                  )}

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
                    <div className="space-y-1.5">
                      <label className="block text-xs font-semibold text-[var(--color-text-secondary)]">
                        TTS 服务端点 (Base URL)
                      </label>
                      <input
                        type="text"
                        placeholder={currentTts?.defaultBaseUrl ?? "https://api.openai.com/v1"}
                        value={form.tts_base_url ?? ""}
                        onChange={(e) => setForm({ ...form, tts_base_url: e.target.value || null })}
                        className="w-full font-mono text-xs"
                      />
                    </div>

                    <div className="space-y-1.5">
                      <label className="block text-xs font-semibold text-[var(--color-text-secondary)]">
                        默认发音人代号 (Voice / Speaker)
                      </label>
                      <input
                        type="text"
                        placeholder={
                          currentTts?.id === "edge"
                            ? "zh-CN-XiaoxiaoNeural"
                            : currentTts?.id === "mimo"
                              ? "mimo_female_cinematic"
                              : currentTts?.id === "open-ai"
                                ? "alloy / onyx"
                                : "default"
                        }
                        value={form.tts_voice ?? ""}
                        onChange={(e) => setForm({ ...form, tts_voice: e.target.value || null })}
                        className="w-full font-mono text-xs"
                      />
                    </div>
                  </div>

                  {currentTts?.id === "gpt-sovits" && (
                    <div className="space-y-3 pt-2 border-t border-[var(--color-border)]">
                      <div className="space-y-1.5">
                        <label className="block text-xs font-semibold text-[var(--color-text-secondary)]">
                          参考音频路径 (Ref Audio File)
                        </label>
                        <input
                          type="text"
                          placeholder="/path/to/reference_sample.wav"
                          value={form.tts_ref_audio_path ?? ""}
                          onChange={(e) => setForm({ ...form, tts_ref_audio_path: e.target.value || null })}
                          className="w-full font-mono text-xs"
                        />
                      </div>
                      <div className="space-y-1.5">
                        <label className="block text-xs font-semibold text-[var(--color-text-secondary)]">
                          参考音频文本 (Prompt Text)
                        </label>
                        <input
                          type="text"
                          placeholder="输入 5 秒参考音频中对应的文字内容..."
                          value={form.tts_prompt_text ?? ""}
                          onChange={(e) => setForm({ ...form, tts_prompt_text: e.target.value || null })}
                          className="w-full font-mono text-xs"
                        />
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* ── Tab 3: 通用偏好与外观主题 ── */}
            {activeNav === "theme" && (
              <div className="space-y-6">
                <div className="border-b border-[var(--color-border)] pb-3">
                  <h3 className="text-sm font-bold text-[var(--color-text-primary)]">
                    外观与界面偏好 (Appearance & Language)
                  </h3>
                  <p className="text-xs text-[var(--color-text-secondary)] mt-0.5">
                    电影调光室暗黑视觉体系与全局语言
                  </p>
                </div>

                {/* 主题选择 */}
                <div className="space-y-2">
                  <label className="block text-xs font-bold text-[var(--color-text-primary)]">
                    显示主题
                  </label>
                  <div className="grid grid-cols-3 gap-3">
                    {[
                      { id: "dark" as Theme, label: "暗夜调光 (Dark)", icon: "🌙", sub: "电影香槟金调色室" },
                      { id: "light" as Theme, label: "珍珠浅灰 (Light)", icon: "☀️", sub: "明亮极简风格" },
                      { id: "system" as Theme, label: "跟随系统 (System)", icon: "💻", sub: "自适应操作系统" },
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
                              ? "border-[var(--color-gold)] bg-[var(--color-gold-muted)] text-[var(--color-gold)] shadow-md font-bold"
                              : "border-[var(--color-border)] bg-[var(--color-surface-elevated)]/60 text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] hover:border-[var(--color-gold)]/40"
                          }`}
                        >
                          <span className="text-2xl mb-1.5">{th.icon}</span>
                          <span className="text-xs font-bold">{th.label}</span>
                          <span className="text-[9px] opacity-70 mt-0.5">{th.sub}</span>
                        </button>
                      );
                    })}
                  </div>
                </div>

                {/* 界面语言 */}
                <div className="space-y-2 pt-2 border-t border-[var(--color-border)]">
                  <label className="block text-xs font-bold text-[var(--color-text-primary)]">
                    界面语言 (Interface Language)
                  </label>
                  <div className="grid grid-cols-2 gap-3">
                    {[
                      { id: "zh-CN", label: "简体中文 (Chinese)", flag: "🇨🇳" },
                      { id: "en-US", label: "English (US)", flag: "🇺🇸" },
                    ].map((l) => {
                      const active = (form.language || locale) === l.id;
                      return (
                        <button
                          key={l.id}
                          type="button"
                          onClick={() => {
                            setLocale(l.id as any);
                            setForm({ ...form, language: l.id });
                          }}
                          className={`flex items-center justify-between rounded-xl border p-3 transition-all ${
                            active
                              ? "border-[var(--color-gold)] bg-[var(--color-gold-muted)] text-[var(--color-gold)] font-bold shadow-sm"
                              : "border-[var(--color-border)] bg-[var(--color-surface-elevated)]/60 text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]"
                          }`}
                        >
                          <div className="flex items-center gap-2">
                            <span>{l.flag}</span>
                            <span className="text-xs">{l.label}</span>
                          </div>
                          {active && <span className="font-mono text-xs">✓</span>}
                        </button>
                      );
                    })}
                  </div>
                </div>
              </div>
            )}
          </main>
        </div>
      </div>
    </div>
  );
}
