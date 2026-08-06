/**
 * Vynaro v2.5.0 · HelpPage · 帮助页主体组件 (M4.5)
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

const CATEGORY_TONE: Record<HelpCategory, string> = {
  guide: "from-blue-500/15 to-blue-500/0 border-blue-500/30 text-blue-200",
  reference:
    "from-fuchsia-500/15 to-fuchsia-500/0 border-fuchsia-500/30 text-fuchsia-200",
  troubleshooting:
    "from-amber-500/15 to-amber-500/0 border-amber-500/30 text-amber-200",
  faq: "from-emerald-500/15 to-emerald-500/0 border-emerald-500/30 text-emerald-200",
  shortcut: "from-cyan-500/15 to-cyan-500/0 border-cyan-500/30 text-cyan-200",
};

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
          <span>💡</span> Help Center
        </div>
        <h1 className="text-3xl font-extrabold tracking-tight text-[var(--color-text-primary)]">帮助与指南</h1>
        <p className="text-sm text-[var(--color-text-secondary)]">
          当前版本 v{version ?? "—"} · 快捷键速查与全量功能指南
        </p>
      </header>

      {/* 快捷键(静态 · 不在 HelpTopic 模型) */}
      <section>
        <SectionHeader
          kicker="操作"
          title="快捷键"
          subtitle="提升效率的常用组合"
        />
        <div className="grid grid-cols-1 gap-2 md:grid-cols-2">
          {SHORTCUTS.map((s, i) => (
            <div
              key={i}
              className="flex items-center justify-between rounded-xl border border-zinc-800 bg-zinc-900/30 px-4 py-3"
            >
              <span className="text-sm text-zinc-300">{s.desc}</span>
              <span className="flex items-center gap-1">
                {s.keys.map((k, idx) => (
                  <kbd
                    key={idx}
                    className="inline-flex h-6 min-w-6 items-center justify-center rounded-md border border-zinc-700 bg-zinc-950 px-2 font-mono text-[10px] text-zinc-300"
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
          kicker="学习"
          title="文档资源"
          subtitle="由后端 vynaro-help 实时提供"
        />

        {/* 分类 chip */}
        <div className="mb-4 flex flex-wrap gap-2">
          {CATEGORY_FILTERS.map((f) => {
            const active = category === f.value;
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
                {f.label}
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
            placeholder="搜索主题 (标题/关键词/正文加权)…"
            className="w-full rounded-xl border border-[var(--color-border)] bg-[var(--color-bg)] py-2.5 pl-9 pr-3 text-sm text-[var(--color-text-primary)] outline-none placeholder:text-[var(--color-text-muted)] focus:border-[var(--color-gold)]"
          />
          {searchFetching && (
            <span className="absolute right-3 top-1/2 -translate-y-1/2 text-[10px] text-zinc-500">
              搜索中…
            </span>
          )}
        </div>

        {/* 主题卡片 */}
        {topicsLoading && (
          <div className="rounded-xl border border-zinc-800 bg-zinc-900/30 px-4 py-8 text-center text-sm text-zinc-500">
            加载主题中…
          </div>
        )}

        {topicsError && (
          <div className="rounded-xl border border-rose-800/60 bg-rose-950/20 px-4 py-3 text-sm text-rose-300">
            加载失败:
            {(topicsError as { message?: string })?.message ?? "未知错误"}
          </div>
        )}

        {!topicsLoading && !topicsError && displayTopics.length === 0 && (
          <div className="rounded-xl border border-zinc-800 bg-zinc-900/30 px-4 py-8 text-center text-sm text-zinc-500">
            {searchQuery ? `没有匹配 “${searchQuery}” 的主题` : "暂无主题"}
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
  const tone = CATEGORY_TONE[topic.category] ?? CATEGORY_TONE.guide;
  const icon = CATEGORY_ICON[topic.category] ?? "📘";
  const cat = CATEGORY_LABEL[topic.category] ?? topic.category;
  return (
    <button
      type="button"
      onClick={onOpen}
      className={`group block rounded-2xl border bg-gradient-to-br p-4 text-left transition hover:scale-[1.02] hover:border-opacity-80 ${tone}`}
    >
      <div className="flex items-center justify-between">
        <div className="text-3xl">{icon}</div>
        <span className="rounded-full border border-current/30 bg-black/20 px-2 py-0.5 text-[10px] opacity-70">
          {cat}
        </span>
      </div>
      <div className="mt-4 space-y-1">
        <div className="text-sm font-semibold text-zinc-100">{topic.title}</div>
        {topic.summary && (
          <div className="text-xs text-zinc-400">{topic.summary}</div>
        )}
        {topic.keywords.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-1">
            {topic.keywords.slice(0, 3).map((k) => (
              <span
                key={k}
                className="rounded-md bg-black/30 px-1.5 py-0.5 text-[10px] text-zinc-400"
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
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/55 p-6 backdrop-blur-sm"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className="relative max-h-[80vh] w-full max-w-2xl overflow-y-auto rounded-2xl border border-zinc-800 bg-zinc-950 p-6 shadow-2xl">
        <button
          type="button"
          onClick={onClose}
          className="absolute right-4 top-4 rounded-md p-1 text-zinc-500 transition hover:bg-zinc-900 hover:text-zinc-200"
          aria-label="关闭"
        >
          ✕
        </button>
        {loading && (
          <div className="py-12 text-center text-sm text-zinc-500">加载中…</div>
        )}
        {topic && !loading && (
          <div className="space-y-4 pr-6">
            <div className="space-y-1">
              <div className="text-[10px] font-semibold uppercase tracking-[0.2em] text-violet-400">
                {CATEGORY_LABEL[topic.category] ?? topic.category}
              </div>
              <h2 className="text-2xl font-bold tracking-tight text-zinc-100">
                {topic.title}
              </h2>
              {topic.summary && (
                <p className="text-sm text-zinc-500">{topic.summary}</p>
              )}
            </div>
            {topic.content ? (
              <pre className="whitespace-pre-wrap rounded-xl border border-zinc-800 bg-zinc-900/40 p-4 text-xs leading-relaxed text-zinc-300">
                {topic.content}
              </pre>
            ) : (
              <div className="rounded-xl border border-dashed border-zinc-800 bg-zinc-900/30 p-4 text-center text-xs text-zinc-500">
                该主题暂无正文(仅元数据 · id: {topic.id})
              </div>
            )}
            {topic.related.length > 0 && (
              <div className="border-t border-zinc-800 pt-3">
                <div className="mb-2 text-[10px] font-semibold uppercase tracking-wider text-zinc-500">
                  相关主题
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {topic.related.map((rid) => (
                    <span
                      key={rid}
                      className="rounded-md bg-zinc-900 px-2 py-0.5 text-[11px] text-zinc-400"
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
