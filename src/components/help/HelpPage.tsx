/**
 * splicr v1.0.1 · HelpPage · 电影调光室风格 官方帮助与交互式知识库中心
 */

import { useMemo, useState, useEffect } from "react";
import { useTauriQuery } from "@hooks/useTauriQuery";
import type { HelpCategory, HelpTopic, SearchHit } from "@ipc/types.gen";

interface Shortcut {
  keys: string[];
  desc: string;
}

const SHORTCUTS: Shortcut[] = [
  { keys: ["⌘", "K"], desc: "命令面板" },
  { keys: ["⌘", "R"], desc: "启动流水线" },
  { keys: ["⌘", "."], desc: "取消流水线" },
  { keys: ["⌘", "S"], desc: "保存当前创作项目" },
  { keys: ["⌘", "N"], desc: "新建空白解说工程" },
  { keys: ["⌘", ","], desc: "打开模型与引擎设置" },
  { keys: ["Esc"], desc: "关闭当前弹窗或中断" },
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
  shortcut: "⌨️",
};

export function HelpPage() {
  const [selectedCat, setSelectedCat] = useState<HelpCategory | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [debouncedQuery, setDebouncedQuery] = useState("");
  const [activeTopicId, setActiveTopicId] = useState<string | null>(null);

  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedQuery(searchQuery.trim());
    }, 200);
    return () => clearTimeout(timer);
  }, [searchQuery]);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setActiveTopicId(null);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  const { data: topics, isError, error } = useTauriQuery({
    command: "help_topics",
    args: { category: selectedCat },
    queryKeyPrefix: "help-topics",
  });

  const { data: searchResults } = useTauriQuery({
    command: "help_search",
    args: { query: debouncedQuery },
    queryKeyPrefix: "help-search",
    enabled: debouncedQuery.length > 0,
  });

  const { data: activeTopic } = useTauriQuery({
    command: "help_topic_get",
    args: { id: activeTopicId ?? "" },
    queryKeyPrefix: "help-topic-detail",
    enabled: activeTopicId !== null,
  });

  const displayTopics = useMemo<HelpTopic[]>(() => {
    if (debouncedQuery.length > 0) {
      if (!searchResults || searchResults.length === 0) return [];
      const hits = searchResults as SearchHit[];
      const hitIds = new Set(hits.map((h) => h.topic_id));
      const allTopics = (topics as HelpTopic[]) ?? [];
      return allTopics.filter((t) => hitIds.has(t.id));
    }
    return (topics as HelpTopic[]) ?? [];
  }, [debouncedQuery, searchResults, topics]);

  if (isError) {
    return (
      <div className="mx-auto max-w-6xl p-8 text-rose-400">
        加载失败: {error instanceof Error ? error.message : String(error)}
      </div>
    );
  }

  return (
    <div className="h-full w-full overflow-y-auto bg-[var(--color-bg)] p-6 md:p-8 select-none font-sans">
      <div className="mx-auto max-w-6xl space-y-6">
        {/* 1. Header Banner */}
        <div className="relative overflow-hidden rounded-3xl border border-[var(--color-border)] bg-[var(--color-surface)] p-6 sm:p-8 shadow-xl">
          <div className="absolute -top-16 -right-16 h-64 w-80 bg-gradient-to-bl from-[var(--color-gold-muted)] via-[var(--color-amber-muted)] to-transparent blur-3xl pointer-events-none" />
          <div className="relative z-10 space-y-3">
            <div className="text-[10px] font-mono font-bold tracking-[0.2em] text-[var(--color-gold)] uppercase">
              KNOWLEDGE BASE & ARCHITECTURE GUIDE
            </div>
            <h1 className="text-3xl font-black tracking-tight text-[var(--color-text-primary)]">
              官方帮助与技术架构指南
            </h1>
            <p className="text-xs text-[var(--color-text-secondary)] max-w-xl">
              探索 Rust Native Multi-Agent 影视解说引擎、5 轨毫秒级对齐与剪映草稿交付的全流程文档
            </p>

            <div className="pt-2">
              <input
                type="text"
                placeholder="搜索主题、命令或常见问题 (例如: 快速上手, 流水线, LLM)..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full md:w-96 text-xs"
              />
            </div>
          </div>
        </div>

        {/* 2. 快捷键矩阵快速入口 */}
        <section className="rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)] p-5 space-y-3 shadow-sm">
          <div className="flex items-center gap-2 border-b border-[var(--color-border)] pb-2.5">
            <span className="text-base">⌨️</span>
            <h3 className="text-xs font-bold text-[var(--color-gold)]">全域效率快捷键速查</h3>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {SHORTCUTS.map((s, idx) => (
              <div
                key={idx}
                className="flex items-center justify-between rounded-xl border border-[var(--color-border)] bg-[var(--color-surface-elevated)]/60 px-3 py-2 text-xs"
              >
                <span className="text-[var(--color-text-secondary)] text-[11px] truncate">{s.desc}</span>
                <div className="flex items-center gap-1 shrink-0">
                  {s.keys.map((k, i) => (
                    <kbd
                      key={i}
                      className="rounded bg-[var(--color-surface)] border border-[var(--color-border)] px-1.5 py-0.5 font-mono text-[10px] text-[var(--color-gold)] font-bold shadow-sm"
                    >
                      {k}
                    </kbd>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* 3. 分类过滤与卡片网格 */}
        <section className="space-y-4">
          <div className="flex items-center gap-2 overflow-x-auto pb-1">
            {CATEGORY_FILTERS.map((cat) => {
              const active = selectedCat === cat.value;
              return (
                <button
                  key={String(cat.value)}
                  type="button"
                  onClick={() => setSelectedCat(cat.value)}
                  className={`rounded-xl px-4 py-1.5 text-xs font-bold transition-all shrink-0 border ${
                    active
                      ? "bg-[var(--color-gold-muted)] border-[var(--color-gold)] text-[var(--color-gold)] shadow-sm"
                      : "border-[var(--color-border)] bg-[var(--color-surface)] text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]"
                  }`}
                >
                  {cat.label}
                </button>
              );
            })}
          </div>

          {displayTopics.length > 0 ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3.5">
              {displayTopics.map((topic) => (
                <button
                  key={topic.id}
                  type="button"
                  onClick={() => setActiveTopicId(topic.id)}
                  className="group flex flex-col justify-between rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)] p-4 transition-all hover:border-[var(--color-gold)]/60 hover:shadow-md cursor-pointer text-left"
                >
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-xl">{CATEGORY_ICON[topic.category] ?? "📄"}</span>
                      <span className="rounded bg-[var(--color-surface-elevated)] border border-[var(--color-border)] px-2 py-0.5 text-[9px] font-mono text-[var(--color-gold)] font-bold">
                        {CATEGORY_LABEL[topic.category] ?? topic.category}
                      </span>
                    </div>
                    <h3 className="text-xs font-bold text-[var(--color-text-primary)] group-hover:text-[var(--color-gold)] line-clamp-1">
                      {topic.title}
                    </h3>
                    <p className="text-[11px] text-[var(--color-text-secondary)] line-clamp-2 leading-relaxed">
                      {topic.summary}
                    </p>
                  </div>
                  <div className="flex items-center justify-between pt-3 mt-3 border-t border-[var(--color-border)] text-[11px] text-[var(--color-gold)] font-bold">
                    <span>阅读完整文档</span>
                    <span className="transition-transform group-hover:translate-x-1">➔</span>
                  </div>
                </button>
              ))}
            </div>
          ) : (
            <div className="rounded-2xl border border-dashed border-[var(--color-border)] bg-[var(--color-surface)] p-10 text-center text-xs text-[var(--color-text-muted)]">
              没有匹配的主题文档
            </div>
          )}
        </section>

        {/* 4. 详情 Modal 对话框 */}
        {activeTopicId && (
          <div
            onClick={() => setActiveTopicId(null)}
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-md p-4 animate-fade-in"
          >
            <div
              onClick={(e) => e.stopPropagation()}
              className="relative w-full max-w-2xl max-h-[80vh] overflow-y-auto rounded-3xl border border-[var(--color-gold)]/40 bg-[var(--color-surface)] p-6 space-y-4 shadow-2xl text-[var(--color-text-primary)]"
            >
              <div className="flex items-center justify-between border-b border-[var(--color-border)] pb-3">
                <h2 className="text-lg font-black text-[var(--color-text-primary)]">{activeTopic?.title ?? "文档加载中..."}</h2>
                <button
                  type="button"
                  onClick={() => setActiveTopicId(null)}
                  className="flex h-7 w-7 items-center justify-center rounded-full bg-[var(--color-surface-elevated)] border border-[var(--color-border)] text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] hover:border-[var(--color-gold)] transition-colors"
                >
                  ✕
                </button>
              </div>
              <div className="text-xs text-[var(--color-text-secondary)] leading-relaxed space-y-3 whitespace-pre-wrap font-sans">
                {activeTopic?.content ?? activeTopic?.summary ?? "正在载入知识库内容..."}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
