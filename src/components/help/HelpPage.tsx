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
    <div className="mx-auto max-w-5xl space-y-12 px-8 py-12">
      <header className="space-y-2">
        <div className="inline-flex items-center gap-2 rounded-full border border-[rgba(245,200,66,0.3)] bg-[rgba(245,200,66,0.1)] px-3 py-0.5 text-xs font-semibold text-[var(--color-gold)]">
          <span>💡</span> {t("help.title", locale)}
        </div>
        <h1 className="text-3xl font-extrabold tracking-tight text-[var(--color-text-primary)]">
          {t("help.title", locale)}
        </h1>
        <p className="text-sm text-[var(--color-text-secondary)]">
          {t("help.subtitle", locale)} · v{version ?? "1.0.0"}
        </p>
      </header>

      {/* 快捷键(静态 · 不在 HelpTopic 模型) */}
      <section>
        <SectionHeader
          kicker={locale === "en-US" ? "Shortcuts" : "快捷键"}
          title={t("help.shortcuts_title", locale)}
          subtitle={locale === "en-US" ? "Boost your productivity with quick hotkeys" : "提升效率的常用组合键"}
        />
        <div className="grid grid-cols-1 gap-2.5 md:grid-cols-2">
          {SHORTCUTS.map((s, i) => (
            <div
              key={i}
              className="flex items-center justify-between rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] px-4 py-3 shadow-sm"
            >
              <span className="text-xs font-medium text-[var(--color-text-primary)]">{s.desc}</span>
              <span className="flex items-center gap-1">
                {s.keys.map((k, idx) => (
                  <kbd
                    key={idx}
                    className="inline-flex h-6 min-w-6 items-center justify-center rounded-md border border-[var(--color-border)] bg-[var(--color-bg)] px-2 font-mono text-[10px] font-bold text-[var(--color-gold)]"
                  >
                    {k}
                  </kbd>
                ))}
              </span>
            </div>
          ))}
        </div>
      </section>

      {/* 文档(从 help_topics IPC 拉取 + help_search 全文搜索) */}
      <section>
        <SectionHeader
          kicker={locale === "en-US" ? "Tutorials" : "教程"}
          title={locale === "en-US" ? "Documentation & Guides" : "文档与教程指南"}
          subtitle={locale === "en-US" ? "Real-time tutorials powered by Vynaro Help engine" : "由后端 vynaro-help 实时提供"}
        />

        {/* 分类 chip */}
        <div className="mb-4 flex flex-wrap gap-2">
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
                className={`rounded-full border px-3.5 py-1 text-xs font-semibold transition ${active
                    ? "border-[var(--color-gold)] bg-[rgba(245,200,66,0.12)] text-[var(--color-gold)]"
                    : "border-[var(--color-border)] bg-[var(--color-surface)] text-[var(--color-text-secondary)] hover:border-[var(--color-gold)]/40 hover:text-[var(--color-text-primary)]"
                  }`}
              >
                {labelStr}
              </button>
            );
          })}
        </div>

        {/* 搜索框 */}
        <div className="relative mb-6">
          <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-sm text-[var(--color-text-secondary)]">
            🔍
          </span>
          <input
            type="text"
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            placeholder={t("help.search_placeholder", locale)}
            className="w-full rounded-xl border border-[var(--color-border)] bg-[var(--color-bg)] py-2.5 pl-9 pr-3 text-sm text-[var(--color-text-primary)] outline-none placeholder:text-[var(--color-text-muted)] focus:border-[var(--color-gold)]"
          />
          {searchFetching && (
            <span className="absolute right-3 top-1/2 -translate-y-1/2 text-[10px] text-[var(--color-gold)]">
              Searching...
            </span>
          )}
        </div>

        {/* 主题卡片 */}
        {topicsLoading && (
          <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] px-4 py-8 text-center text-sm text-[var(--color-text-muted)]">
            Loading tutorials...
          </div>
        )}

        {topicsError && (
          <div className="rounded-xl border border-rose-500/40 bg-rose-500/10 px-4 py-3 text-sm text-rose-400">
            加载失败:
            {(topicsError as { message?: string })?.message ?? "未知错误"}
          </div>
        )}

        {!topicsLoading && !topicsError && displayTopics.length === 0 && (
          <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] px-4 py-8 text-center text-sm text-[var(--color-text-muted)]">
            {searchQuery ? `没有匹配 “${searchQuery}” 的主题` : t("help.no_topics", locale)}
          </div>
        )}

        <div className="grid grid-cols-1 gap-3 md:grid-cols-2 lg:grid-cols-3">
          {displayTopics.map((t) => (
            <TopicCard
              key={t.id}
              topic={t}
              onOpen={() => setOpenTopicId(t.id)}
            />
          ))}
        </div>
      </section>

      {/* 反馈 */}
      <section className="rounded-2xl border border-zinc-800 bg-gradient-to-br from-zinc-900/60 to-zinc-950/60 p-6">
        <div className="flex flex-col items-start justify-between gap-4 md:flex-row md:items-center">
          <div className="space-y-1">
            <div className="text-sm font-semibold text-zinc-100">遇到问题?</div>
            <div className="text-xs text-zinc-500">
              查看日志或反馈给我们,有助于 Vynaro 越变越好
            </div>
          </div>
          <div className="flex gap-2">
            <a
              href="https://github.com/Agions/vynaro/issues"
              target="_blank"
              rel="noreferrer"
              className="rounded-lg border border-zinc-700 bg-zinc-900 px-4 py-2 text-xs text-zinc-200 transition hover:border-zinc-500"
            >
              提交 Issue
            </a>
            <a
              href="https://github.com/Agions/vynaro"
              target="_blank"
              rel="noreferrer"
              className="rounded-lg border border-zinc-700 bg-zinc-900 px-4 py-2 text-xs text-zinc-200 transition hover:border-zinc-500"
            >
              访问 GitHub 仓库
            </a>
          </div>
        </div>
      </section>

      {/* 详情 modal */}
      {openTopicId && (
        <TopicModal
          topic={openTopic ?? null}
          loading={topicLoading}
          onClose={() => setOpenTopicId(null)}
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
}: {
  topic: HelpTopic | null;
  loading: boolean;
  onClose: () => void;
}) {
  // Esc 关闭
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 p-6 backdrop-blur-md animate-fade-in"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className="relative max-h-[85vh] w-full max-w-2xl overflow-y-auto rounded-3xl border border-[var(--color-gold)] bg-[var(--color-surface)] p-6 shadow-[0_0_36px_var(--color-gold-glow)]">
        <button
          type="button"
          onClick={onClose}
          className="absolute right-4 top-4 flex h-8 w-8 items-center justify-center rounded-xl border border-[var(--color-border)] text-[var(--color-text-secondary)] hover:border-[var(--color-gold)] hover:text-[var(--color-gold)] transition"
          aria-label="关闭"
        >
          ✕
        </button>
        {loading && (
          <div className="py-12 text-center text-xs text-[var(--color-gold)]">加载主题详情中...</div>
        )}
        {topic && !loading && (
          <div className="space-y-4 pr-6">
            <div className="space-y-1">
              <div className="text-[10px] font-mono font-bold uppercase tracking-[0.2em] text-[var(--color-gold)]">
                {CATEGORY_LABEL[topic.category] ?? topic.category}
              </div>
              <h2 className="text-xl font-extrabold tracking-tight text-[var(--color-text-primary)]">
                {topic.title}
              </h2>
              {topic.summary && (
                <p className="text-xs text-[var(--color-text-secondary)]">{topic.summary}</p>
              )}
            </div>
            {topic.content ? (
              <pre className="whitespace-pre-wrap rounded-2xl border border-[var(--color-border)] bg-[var(--color-bg)] p-4 font-mono text-xs leading-relaxed text-[var(--color-text-primary)]">
                {topic.content}
              </pre>
            ) : (
              <div className="rounded-xl border border-dashed border-[var(--color-border)] bg-[var(--color-bg)] p-4 text-center text-xs text-[var(--color-text-muted)]">
                该主题暂无正文 (仅元数据 · id: {topic.id})
              </div>
            )}
            {topic.related.length > 0 && (
              <div className="border-t border-[var(--color-border)] pt-3">
                <div className="mb-2 text-[10px] font-bold uppercase tracking-wider text-[var(--color-gold)]">
                  相关关联主题
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {topic.related.map((rid) => (
                    <span
                      key={rid}
                      className="rounded-md border border-[var(--color-border)] bg-[var(--color-surface-elevated)] px-2 py-0.5 font-mono text-[11px] text-[var(--color-text-secondary)]"
                    >
                      {rid}
                    </span>
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
