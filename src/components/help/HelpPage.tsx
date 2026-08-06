/**
 * Vynaro v1.0.0 · HelpPage · 帮助页主体组件 (M4.5)
 *
 * 接入 vynaro-help IPC:
 * - help_topics:分类拉取所有主题(替代旧硬编码 6 张 RESOURCES)
 * - help_topic_get:详情 modal(展示 markdown content)
 * - help_search:加权全文搜索(标题/关键词/摘要/正文)
 *
 * 保留:SHORTCUTS 静态数组(快捷键不在 HelpTopic 模型内)
 *
 * 拆分目的:让 routes/help.tsx 路由文件只导出 Route,
 * TanStack Router 才能对 HelpPage 做 code-split。
 * 测试文件 ./routes/-help.test.tsx 仍可直接 import 此处组件。
 */

import { useEffect, useMemo, useState } from "react";
import { toast } from "sonner";
import { useTauriQuery } from "@hooks/useTauriQuery";
import { useSettingsStore } from "@stores/settings-store";
import { t } from "@lib/i18n";
import type { HelpCategory, HelpTopic } from "@ipc/types.gen";

// ── 静态数据 · 必须在模块顶层以便 TopicCard/TopicModal 闭包访问 ─────
interface Shortcut {
  keys: string[];
  desc: string;
}

const SHORTCUTS: Shortcut[] = [
  { keys: ["⌘", "K"], desc: "命令面板" },
  { keys: ["⌘", "R"], desc: "启动流水线" },
  { keys: ["⌘", "."], desc: "取消流水线" },
  { keys: ["⌘", "S"], desc: "保存项目" },
  { keys: ["⌘", "N"], desc: "新建空白项目" },
  { keys: ["⌘", ","], desc: "打开设置" },
  { keys: ["Esc"], desc: "关闭对话框" },
];

const CATEGORY_FILTERS: Array<{ value: HelpCategory | null; label: string }> = [
  { value: null, label: "全部" },
  { value: "guide", label: "教程" },
  { value: "reference", label: "参考" },
  { value: "troubleshooting", label: "故障排查" },
  { value: "faq", label: "FAQ" },
  { value: "shortcut", label: "快捷键" },
];

const CATEGORY_LABEL: Record<HelpCategory, string> = {
  guide: "教程",
  reference: "参考",
  troubleshooting: "故障排查",
  faq: "FAQ",
  shortcut: "快捷键",
};

const CATEGORY_ICON: Record<HelpCategory, string> = {
  guide: "📘",
  reference: "📖",
  troubleshooting: "❓",
  faq: "💬",
  shortcut: "⌨",
};

export function HelpPage() {
  const { data: version } = useTauriQuery({
    command: "app_version",
    queryKeyPrefix: "help-page-version",
    args: {},
  });

  // 当前分类筛选
  const [category, setCategory] = useState<HelpCategory | null>(null);
  // 搜索关键词(debounce 后送入 IPC)
  const [searchInput, setSearchInput] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  // 详情 modal
  const [openTopicId, setOpenTopicId] = useState<string | null>(null);

  // debounce 200ms
  useEffect(() => {
    const t = window.setTimeout(() => setSearchQuery(searchInput.trim()), 200);
    return () => window.clearTimeout(t);
  }, [searchInput]);

  // 拉取当前分类下的所有主题
  const {
    data: topics,
    isLoading: topicsLoading,
    error: topicsError,
  } = useTauriQuery({
    command: "help_topics",
    queryKeyPrefix: "help-page-topics",
    args: { category },
  });

  // 搜索请求(仅在 searchQuery 非空时启用)
  const { data: searchHits, isFetching: searchFetching } = useTauriQuery({
    command: "help_search",
    queryKeyPrefix: "help-page-search",
    args: { query: searchQuery },
    enabled: searchQuery.length > 0,
  });

  // 当前展示的主题列表
  const displayTopics: HelpTopic[] = useMemo(() => {
    if (searchQuery.length > 0) {
      // 搜索模式:把 SearchHit → topic 全量
      // 后端 search 返回 id/title/score,需要从 topics 全集中匹配 id
      const idSet = new Set((searchHits ?? []).map((h) => h.id));
      return (topics ?? []).filter((t) => idSet.has(t.id));
    }
    return topics ?? [];
  }, [topics, searchHits, searchQuery]);

  const locale = useSettingsStore((s) => s.locale);

  // 详情 modal 数据
  const { data: openTopic, isLoading: topicLoading } = useTauriQuery({
    command: "help_topic_get",
    queryKeyPrefix: "help-page-topic-get",
    args: { id: openTopicId ?? "" },
    enabled: openTopicId !== null,
  });

  return (
    <div className="mx-auto max-w-6xl space-y-10 px-8 py-10">
      {/* 1. Header Banner */}
      <header className="relative overflow-hidden rounded-3xl border border-[var(--color-border)] bg-gradient-to-br from-[var(--color-surface)] via-[var(--color-surface-elevated)] to-[var(--color-surface)] p-8 shadow-2xl">
        <div className="absolute -right-10 -top-10 h-60 w-60 rounded-full bg-[var(--color-gold)]/10 blur-3xl" />
        <div className="relative z-10 space-y-3">
          <div className="inline-flex items-center gap-2 rounded-full border border-[rgba(245,200,66,0.3)] bg-[rgba(245,200,66,0.1)] px-3.5 py-1 text-xs font-bold text-[var(--color-gold)] shadow-sm">
            <span>💡</span> {t("help.title", locale)} · VYNARO KNOWLEDGE CENTER
          </div>
          <h1 className="text-3xl font-black tracking-tight text-[var(--color-text-primary)] md:text-4xl">
            {t("help.title", locale)}与全量功能指南
          </h1>
          <p className="max-w-2xl text-sm text-[var(--color-text-secondary)] leading-relaxed">
            极速掌握第一人称 AI 影视叙事解说系统，涵盖从智能拆条、文案大模型、TTS 音色克隆到 4K 60fps 高清渲染全流程手册。
          </p>

          {/* System Diagnostics Status Line */}
          <div className="pt-2 flex flex-wrap items-center gap-3 text-xs font-mono text-[var(--color-text-muted)]">
            <span className="flex items-center gap-1.5 rounded-lg border border-[var(--color-border)] bg-[var(--color-bg)] px-2.5 py-1">
              <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
              Engine: FFmpeg 7.0 (VideoToolbox / NVENC)
            </span>
            <span className="flex items-center gap-1.5 rounded-lg border border-[var(--color-border)] bg-[var(--color-bg)] px-2.5 py-1">
              🔒 Privacy: 100% 本地存储无云端上传
            </span>
            <span className="flex items-center gap-1.5 rounded-lg border border-[var(--color-border)] bg-[var(--color-bg)] px-2.5 py-1 text-[var(--color-gold)] font-bold">
              v{version ?? "1.0.0"} Official Release
            </span>
          </div>
        </div>
      </header>

      {/* 2. 核心 4 步极速通关视觉导览 */}
      <section className="space-y-4">
        <SectionHeader
          kicker="WORKFLOW"
          title="⚡ 第一人称 AI 解说 4 步极速通关导览"
          subtitle="点击下方卡片即可直接查阅对应模块的高阶创作与配置手册"
        />
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <div
            onClick={() => setOpenTopicId("guide-quick-start")}
            className="group relative cursor-pointer overflow-hidden rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)] p-5 transition-all duration-300 hover:border-[var(--color-gold)] hover:bg-[var(--color-surface-elevated)] hover:shadow-[0_0_24px_var(--color-gold-glow)]"
          >
            <div className="mb-3 flex items-center justify-between">
              <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-[var(--color-gold-muted)] text-xs font-mono font-black text-[var(--color-gold)] border border-[var(--color-gold)]/40">
                01
              </span>
              <span className="text-xs text-[var(--color-gold)] font-bold group-hover:translate-x-1 transition-transform">
                查看教程 →
              </span>
            </div>
            <h3 className="text-sm font-bold text-[var(--color-text-primary)] group-hover:text-[var(--color-gold)] transition-colors">
              素材导入与首帧探针
            </h3>
            <p className="mt-1 text-xs text-[var(--color-text-secondary)] line-clamp-2">
              批量扫描本地目录，自动提取视频元数据与高清 1st frame 封面。
            </p>
          </div>

          <div
            onClick={() => setOpenTopicId("guide-detect-master")}
            className="group relative cursor-pointer overflow-hidden rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)] p-5 transition-all duration-300 hover:border-[var(--color-gold)] hover:bg-[var(--color-surface-elevated)] hover:shadow-[0_0_24px_var(--color-gold-glow)]"
          >
            <div className="mb-3 flex items-center justify-between">
              <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-[var(--color-gold-muted)] text-xs font-mono font-black text-[var(--color-gold)] border border-[var(--color-gold)]/40">
                02
              </span>
              <span className="text-xs text-[var(--color-gold)] font-bold group-hover:translate-x-1 transition-transform">
                查看教程 →
              </span>
            </div>
            <h3 className="text-sm font-bold text-[var(--color-text-primary)] group-hover:text-[var(--color-gold)] transition-colors">
              智能拆条与镜头分割
            </h3>
            <p className="mt-1 text-xs text-[var(--color-text-secondary)] line-clamp-2">
              场景光影突变识别，自动将长视频精准切割为独立卡点镜头。
            </p>
          </div>

          <div
            onClick={() => setOpenTopicId("guide-script-copilot")}
            className="group relative cursor-pointer overflow-hidden rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)] p-5 transition-all duration-300 hover:border-[var(--color-gold)] hover:bg-[var(--color-surface-elevated)] hover:shadow-[0_0_24px_var(--color-gold-glow)]"
          >
            <div className="mb-3 flex items-center justify-between">
              <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-[var(--color-gold-muted)] text-xs font-mono font-black text-[var(--color-gold)] border border-[var(--color-gold)]/40">
                03
              </span>
              <span className="text-xs text-[var(--color-gold)] font-bold group-hover:translate-x-1 transition-transform">
                查看教程 →
              </span>
            </div>
            <h3 className="text-sm font-bold text-[var(--color-text-primary)] group-hover:text-[var(--color-gold)] transition-colors">
              文案大模型与音色克隆
            </h3>
            <p className="mt-1 text-xs text-[var(--color-text-secondary)] line-clamp-2">
              爆款 Hook 独白脚本生成，零样本 10 秒提取专属高保真声优。
            </p>
          </div>

          <div
            onClick={() => setOpenTopicId("guide-export-preset")}
            className="group relative cursor-pointer overflow-hidden rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)] p-5 transition-all duration-300 hover:border-[var(--color-gold)] hover:bg-[var(--color-surface-elevated)] hover:shadow-[0_0_24px_var(--color-gold-glow)]"
          >
            <div className="mb-3 flex items-center justify-between">
              <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-[var(--color-gold-muted)] text-xs font-mono font-black text-[var(--color-gold)] border border-[var(--color-gold)]/40">
                04
              </span>
              <span className="text-xs text-[var(--color-gold)] font-bold group-hover:translate-x-1 transition-transform">
                查看教程 →
              </span>
            </div>
            <h3 className="text-sm font-bold text-[var(--color-text-primary)] group-hover:text-[var(--color-gold)] transition-colors">
              音画卡点与 4K 高清导出
            </h3>
            <p className="mt-1 text-xs text-[var(--color-text-secondary)] line-clamp-2">
              字幕动画对齐、短视频平台多分辨率 Preset 渲染导出。
            </p>
          </div>
        </div>
      </section>

      {/* 3. 快捷键速查区 */}
      <section className="space-y-4">
        <SectionHeader
          kicker={locale === "en-US" ? "Shortcuts" : "快捷键"}
          title={t("help.shortcuts_title", locale)}
          subtitle={locale === "en-US" ? "Boost your productivity with quick hotkeys" : "提升效率的常用组合键清单"}
        />
        <div className="grid grid-cols-1 gap-2.5 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4">
          {SHORTCUTS.map((s, i) => (
            <div
              key={i}
              className="flex items-center justify-between rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] px-4 py-3 shadow-sm transition hover:border-[var(--color-gold)]/40"
            >
              <span className="text-xs font-bold text-[var(--color-text-primary)]">{s.desc}</span>
              <span className="flex items-center gap-1">
                {s.keys.map((k, idx) => (
                  <kbd
                    key={idx}
                    className="inline-flex h-6 min-w-6 items-center justify-center rounded-md border border-[var(--color-border)] bg-[var(--color-bg)] px-2 font-mono text-[10px] font-extrabold text-[var(--color-gold)] shadow-inner"
                  >
                    {k}
                  </kbd>
                ))}
              </span>
            </div>
          ))}
        </div>
      </section>

      {/* 4. 全量专业文档资源区 */}
      <section className="space-y-4">
        <SectionHeader
          kicker={locale === "en-US" ? "Knowledge Base" : "知识库"}
          title={locale === "en-US" ? "Documentation & Detailed Guides" : "全量专业文档与教程指南"}
          subtitle={locale === "en-US" ? "Real-time docs powered by Vynaro Help Engine" : "由后端 vynaro-help 实时提供加权全文检索与主题映射"}
        />

        {/* 分类 Filter Tabs */}
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <div className="flex flex-wrap gap-2">
            {CATEGORY_FILTERS.map((f) => {
              const active = category === f.value;
              const labelStr = f.value ? t(`help.${f.value}`, locale) : t("help.all_cat", locale);
              return (
                <button
                  key={f.label}
                  type="button"
                  onClick={() => {
                    setCategory(f.value);
                    setSearchInput("");
                  }}
                  className={`rounded-full border px-4 py-1.5 text-xs font-bold transition-all duration-200 ${
                    active
                      ? "border-[var(--color-gold)] bg-[var(--color-gold-muted)] text-[var(--color-gold)] shadow-[0_0_12px_var(--color-gold-glow)]"
                      : "border-[var(--color-border)] bg-[var(--color-surface)] text-[var(--color-text-secondary)] hover:border-[var(--color-gold)]/40 hover:text-[var(--color-text-primary)]"
                  }`}
                >
                  {labelStr}
                </button>
              );
            })}
          </div>

          <span className="text-xs font-mono text-[var(--color-text-muted)]">
            共 {displayTopics.length} 篇专业指南
          </span>
        </div>

        {/* 搜索框 */}
        <div className="relative mb-6">
          <span className="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 text-sm text-[var(--color-text-secondary)]">
            🔍
          </span>
          <input
            type="text"
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            placeholder={t("help.search_placeholder", locale)}
            className="w-full rounded-2xl border border-[var(--color-border)] bg-[var(--color-bg)] py-3 pl-10 pr-4 text-xs font-medium text-[var(--color-text-primary)] outline-none placeholder:text-[var(--color-text-muted)] focus:border-[var(--color-gold)] shadow-inner transition"
          />
          {searchFetching && (
            <span className="absolute right-4 top-1/2 -translate-y-1/2 text-xs font-mono font-bold text-[var(--color-gold)] animate-pulse">
              搜索中...
            </span>
          )}
        </div>

        {/* 主题卡片网格 */}
        {topicsLoading && (
          <div className="rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)] px-4 py-12 text-center text-xs font-bold text-[var(--color-gold)] animate-pulse">
            正在拉取加权文档数据库...
          </div>
        )}

        {topicsError && (
          <div className="rounded-2xl border border-rose-500/40 bg-rose-500/10 px-5 py-4 text-xs text-rose-400 font-medium">
            加载失败: {(topicsError as { message?: string })?.message ?? "未知错误"}
          </div>
        )}

        {!topicsLoading && !topicsError && displayTopics.length === 0 && (
          <div className="rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)] px-4 py-12 text-center text-xs text-[var(--color-text-muted)]">
            {searchQuery ? `没有匹配 “${searchQuery}” 的主题` : t("help.no_topics", locale)}
          </div>
        )}

        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
          {displayTopics.map((topic) => (
            <TopicCard
              key={topic.id}
              topic={topic}
              onOpen={() => setOpenTopicId(topic.id)}
            />
          ))}
        </div>
      </section>

      {/* 5. 技术支持与 Community 反馈 */}
      <section className="rounded-3xl border border-[var(--color-border)] bg-gradient-to-br from-[var(--color-surface)] via-[var(--color-surface-elevated)] to-[var(--color-surface)] p-6 shadow-xl">
        <div className="flex flex-col items-start justify-between gap-4 md:flex-row md:items-center">
          <div className="space-y-1">
            <div className="text-sm font-extrabold text-[var(--color-text-primary)] flex items-center gap-2">
              <span>💬</span> 遇到任何疑问或功能建议?
            </div>
            <div className="text-xs text-[var(--color-text-secondary)]">
              提交 Issue 或参与 GitHub 社区讨论，帮助 Vynaro 第一人称 AI 叙事系统持续进化。
            </div>
          </div>
          <div className="flex gap-3 shrink-0">
            <a
              href="https://github.com/Agions/vynaro/issues"
              target="_blank"
              rel="noreferrer"
              className="rounded-xl border border-[var(--color-gold)]/40 bg-[var(--color-gold-muted)] px-4 py-2 text-xs font-bold text-[var(--color-gold)] transition hover:border-[var(--color-gold)] shadow-sm"
            >
              提交 Issue
            </a>
            <a
              href="https://github.com/Agions/vynaro"
              target="_blank"
              rel="noreferrer"
              className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] px-4 py-2 text-xs font-bold text-[var(--color-text-primary)] transition hover:border-[var(--color-gold)]"
            >
              访问 GitHub 仓库
            </a>
          </div>
        </div>
      </section>

      {/* 6. 详情 Modal */}
      {openTopicId && (
        <TopicModal
          topic={openTopic ?? null}
          loading={topicLoading}
          onClose={() => setOpenTopicId(null)}
          onSelectTopic={(id) => setOpenTopicId(id)}
        />
      )}
    </div>
  );
}

// ── TopicCard · 一张主题卡片 ─────────────────────────────────────
function TopicCard({
  topic,
  onOpen,
}: {
  topic: HelpTopic;
  onOpen: () => void;
}) {
  const icon = CATEGORY_ICON[topic.category] ?? "📘";
  const cat = CATEGORY_LABEL[topic.category] ?? topic.category;
  return (
    <button
      type="button"
      onClick={onOpen}
      className="group block rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)] p-5 text-left transition-all duration-300 hover:scale-[1.02] hover:border-[var(--color-gold)] hover:shadow-[0_0_20px_var(--color-gold-glow)]"
    >
      <div className="flex items-center justify-between">
        <div className="text-3xl">{icon}</div>
        <span className="rounded-full border border-[var(--color-gold)]/30 bg-[var(--color-gold-muted)] px-2.5 py-0.5 text-[10px] font-bold text-[var(--color-gold)]">
          {cat}
        </span>
      </div>
      <div className="mt-4 space-y-1">
        <div className="text-sm font-bold text-[var(--color-text-primary)] group-hover:text-[var(--color-gold)] transition-colors">
          {topic.title}
        </div>
        {topic.summary && (
          <div className="text-xs text-[var(--color-text-secondary)]">{topic.summary}</div>
        )}
        {topic.keywords.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-1">
            {topic.keywords.slice(0, 3).map((k) => (
              <span
                key={k}
                className="rounded-md bg-[var(--color-bg)] border border-[var(--color-border)] px-1.5 py-0.5 text-[10px] font-mono text-[var(--color-text-muted)]"
              >
                #{k}
              </span>
            ))}
          </div>
        )}
      </div>
    </button>
  );
}

// ── TopicModal · 主题详情(展示 markdown content) ─────────────────
function TopicModal({
  topic,
  loading,
  onClose,
  onSelectTopic,
}: {
  topic: HelpTopic | null;
  loading: boolean;
  onClose: () => void;
  onSelectTopic?: (id: string) => void;
}) {
  // Esc 关闭
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  const copyContent = () => {
    if (topic?.content) {
      void navigator.clipboard.writeText(topic.content);
      toast.success("已成功复制指南文档至剪贴板");
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 p-6 backdrop-blur-md animate-fade-in"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className="relative max-h-[88vh] w-full max-w-3xl overflow-y-auto rounded-3xl border border-[var(--color-gold)] bg-[var(--color-surface)] p-8 shadow-[0_0_40px_var(--color-gold-glow)] transition-all">
        <div className="flex items-center justify-between border-b border-[var(--color-border)] pb-4 mb-5">
          <div className="flex items-center gap-2">
            <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-[var(--color-gold-muted)] text-sm font-bold text-[var(--color-gold)]">
              {CATEGORY_ICON[topic?.category ?? "guide"] ?? "📘"}
            </span>
            <span className="text-xs font-mono font-bold uppercase tracking-wider text-[var(--color-gold)]">
              {CATEGORY_LABEL[topic?.category ?? "guide"] ?? topic?.category}
            </span>
          </div>

          <div className="flex items-center gap-3">
            {topic?.content && (
              <button
                type="button"
                onClick={copyContent}
                className="flex items-center gap-1.5 rounded-xl border border-[var(--color-border)] bg-[var(--color-bg)] px-3 py-1.5 text-xs font-bold text-[var(--color-text-secondary)] hover:border-[var(--color-gold)] hover:text-[var(--color-gold)] transition"
              >
                📋 复制文档
              </button>
            )}
            <button
              type="button"
              onClick={onClose}
              className="flex h-8 w-8 items-center justify-center rounded-xl border border-[var(--color-border)] text-[var(--color-text-secondary)] hover:border-[var(--color-gold)] hover:text-[var(--color-gold)] transition"
              aria-label="关闭"
            >
              ✕
            </button>
          </div>
        </div>

        {loading && (
          <div className="py-16 text-center text-xs font-bold text-[var(--color-gold)] animate-pulse">
            正在拉取加权文档详情...
          </div>
        )}

        {topic && !loading && (
          <div className="space-y-6">
            <div className="space-y-2">
              <h2 className="text-2xl font-black tracking-tight text-[var(--color-text-primary)] leading-tight">
                {topic.title}
              </h2>
              {topic.summary && (
                <p className="text-xs text-[var(--color-text-secondary)] leading-relaxed bg-[var(--color-surface-elevated)] p-3 rounded-xl border border-[var(--color-border)]">
                  {topic.summary}
                </p>
              )}
            </div>

            {topic.content ? (
              <div className="whitespace-pre-wrap rounded-2xl border border-[var(--color-border)] bg-[var(--color-bg)] p-6 font-mono text-xs leading-relaxed text-[var(--color-text-primary)] shadow-inner">
                {topic.content}
              </div>
            ) : (
              <div className="rounded-2xl border border-dashed border-[var(--color-border)] bg-[var(--color-bg)] p-6 text-center text-xs text-[var(--color-text-muted)]">
                该主题暂无正文 (仅元数据 · id: {topic.id})
              </div>
            )}

            {topic.related.length > 0 && (
              <div className="border-t border-[var(--color-border)] pt-4 space-y-2">
                <div className="text-xs font-bold uppercase tracking-wider text-[var(--color-gold)] flex items-center gap-1.5">
                  <span>🔗</span> 关联延伸教程指南:
                </div>
                <div className="flex flex-wrap gap-2">
                  {topic.related.map((rid) => (
                    <button
                      key={rid}
                      type="button"
                      onClick={() => onSelectTopic?.(rid)}
                      className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface-elevated)] px-3 py-1.5 font-mono text-xs text-[var(--color-gold)] font-bold transition hover:border-[var(--color-gold)] hover:bg-[var(--color-gold-muted)] shadow-sm flex items-center gap-1"
                    >
                      <span>📖</span> {rid}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

function SectionHeader({
  kicker,
  title,
  subtitle,
}: {
  kicker: string;
  title: string;
  subtitle: string;
}) {
  return (
    <div className="mb-4 space-y-1">
      <div className="text-[10px] font-bold uppercase tracking-[0.2em] text-[var(--color-gold)]">
        {kicker}
      </div>
      <h2 className="text-xl font-bold tracking-tight text-[var(--color-text-primary)]">
        {title}
      </h2>
      <p className="text-sm text-[var(--color-text-secondary)]">{subtitle}</p>
    </div>
  );
}
