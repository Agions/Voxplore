/**
 * Vynaro v1.0.0 · 多视频导出策略预览 (vynaro-video · video_build_plans)
 *
 * 4 种策略:
 * - single  : 全部输入 → 1 个 OutputPlan (要求 1 个源)
 * - concat  : 全部输入 → 1 个 OutputPlan (要求 ≥2 个源,按顺序拼接)
 * - batch   : 每输入 → 1 个 OutputPlan (一一对应)
 * - series  : 按 episode_template 拆分为多集,带 series_context
 *
 * 真正接通后端 `video_build_plans` IPC,展示 OutputPlan(name + ordered_sources +
 * episode 编号 / series 上下文)。Strategy 切换时自动重算,可用于「先预览后导出」。
 */

import { useMemo, useState } from "react";
import { useTauriQuery } from "@hooks/useTauriQuery";
import type { ExportStrategy, OutputPlan } from "@ipc/types.gen";

export interface VideoPlanPreviewProps {
  /** 已导入项目的媒体文件绝对路径列表 */
  mediaPaths: string[];
  /** 初始策略 */
  defaultStrategy?: ExportStrategy;
}

// ── 策略元数据 ──────────────────────────────────────────────────────
const STRATEGY_META: Record<
  ExportStrategy,
  { label: string; hint: string; tone: string; emoji: string }
> = {
  single: {
    label: "单文件",
    hint: "1 个源 → 1 个输出",
    tone: "from-sky-500/20 to-blue-500/20 text-sky-200",
    emoji: "🎬",
  },
  concat: {
    label: "拼接",
    hint: "≥2 个源 → 1 个输出(按顺序)",
    tone: "from-violet-500/20 to-fuchsia-500/20 text-violet-200",
    emoji: "🔗",
  },
  batch: {
    label: "批处理",
    hint: "每个源 → 1 个输出",
    tone: "from-emerald-500/20 to-teal-500/20 text-emerald-200",
    emoji: "📦",
  },
  series: {
    label: "系列",
    hint: "按剧集模板拆分多集,带剧情上下文",
    tone: "from-amber-500/20 to-orange-500/20 text-amber-200",
    emoji: "📺",
  },
};

const STRATEGY_ORDER: ExportStrategy[] = [
  "single",
  "concat",
  "batch",
  "series",
];

export function VideoPlanPreview({
  mediaPaths,
  defaultStrategy = "concat",
}: VideoPlanPreviewProps) {
  const [strategy, setStrategy] = useState<ExportStrategy>(defaultStrategy);
  const [baseName, setBaseName] = useState("output");
  const [episodeTemplate, setEpisodeTemplate] = useState("EP{nn}_{title}");
  const [seriesContext, setSeriesContext] = useState("");

  const options = useMemo(
    () => ({
      base_name: baseName,
      series_context: strategy === "series" && seriesContext.trim() ? seriesContext.trim() : null,
      episode_template: episodeTemplate,
    }),
    [baseName, episodeTemplate, strategy, seriesContext],
  );

  const {
    data: plans,
    isLoading,
    error,
    refetch,
  } = useTauriQuery({
    command: "video_build_plans",
    queryKeyPrefix: "video-plan-preview",
    args: {
      sources: mediaPaths,
      strategy,
      options,
    },
  });

  return (
    <section className="rounded-2xl border border-zinc-800 bg-zinc-900/40 p-6">
      <header className="mb-4 flex items-start justify-between">
        <div className="space-y-1">
          <div className="text-[10px] font-semibold uppercase tracking-[0.2em] text-violet-400">
            Export Strategy
          </div>
          <h2 className="text-xl font-semibold text-zinc-100">视频导出策略</h2>
          <p className="text-xs text-zinc-500">
            基于 {mediaPaths.length} 个素材预览 {STRATEGY_ORDER.length} 种策略的
            OutputPlan
          </p>
        </div>
        <button
          type="button"
          onClick={() => void refetch()}
          className="rounded-md border border-zinc-700 bg-zinc-900 px-3 py-1.5 text-xs text-zinc-300 transition hover:border-zinc-500"
        >
          🔄 重新计算
        </button>
      </header>

      {/* 策略选择 */}
      <div className="mb-4 grid grid-cols-2 gap-2 md:grid-cols-4">
        {STRATEGY_ORDER.map((s) => {
          const meta = STRATEGY_META[s];
          const active = strategy === s;
          return (
            <button
              key={s}
              type="button"
              onClick={() => setStrategy(s)}
              className={`rounded-xl border p-3 text-left transition ${
                active
                  ? `border-violet-500/60 bg-gradient-to-br ${meta.tone}`
                  : "border-zinc-800 bg-zinc-950/40 text-zinc-400 hover:border-zinc-600"
              }`}
            >
              <div className="mb-1 flex items-center gap-2 text-sm font-medium">
                <span>{meta.emoji}</span>
                <span>{meta.label}</span>
              </div>
              <div className="text-[10px] leading-tight text-zinc-500">
                {meta.hint}
              </div>
            </button>
          );
        })}
      </div>

      {/* Plan options (base_name + episode_template + series_context) */}
      <div className="mb-4 grid grid-cols-1 gap-3 md:grid-cols-2">
        <label className="space-y-1 text-[11px] text-zinc-500">
          <span>输出基础名 (base_name)</span>
          <input
            type="text"
            value={baseName}
            onChange={(e) => setBaseName(e.target.value)}
            className="w-full rounded-md border border-zinc-800 bg-zinc-950/60 px-2.5 py-1.5 font-mono text-xs text-zinc-200 focus:border-violet-500 focus:outline-none"
            placeholder="output"
          />
        </label>
        <label className="space-y-1 text-[11px] text-zinc-500">
          <span>剧集模板 (episode_template)</span>
          <input
            type="text"
            value={episodeTemplate}
            onChange={(e) => setEpisodeTemplate(e.target.value)}
            className="w-full rounded-md border border-zinc-800 bg-zinc-950/60 px-2.5 py-1.5 font-mono text-xs text-zinc-200 focus:border-violet-500 focus:outline-none"
            placeholder="EP{nn}_{title}"
          />
        </label>
        {strategy === "series" && (
          <label className="space-y-1 text-[11px] text-zinc-500 md:col-span-2">
            <span>剧集上下文 (series_context) — 用于 AI 关联多集叙事</span>
            <input
              type="text"
              value={seriesContext}
              onChange={(e) => setSeriesContext(e.target.value)}
              className="w-full rounded-md border border-zinc-800 bg-zinc-950/60 px-2.5 py-1.5 font-mono text-xs text-zinc-200 focus:border-violet-500 focus:outline-none"
              placeholder="例如：斗罗大陆第一季"
            />
          </label>
        )}
      </div>

      {/* OutputPlan 列表 */}
      <div className="space-y-2">
        {isLoading && (
          <div className="rounded-lg border border-zinc-800 bg-zinc-950/40 p-4 text-center text-xs text-zinc-500">
            ⏳ 正在调用 video_build_plans…
          </div>
        )}

        {error && (
          <div className="rounded-lg border border-rose-800/50 bg-rose-950/30 p-3 text-xs text-rose-200">
            <div className="font-semibold">⚠ 策略 {strategy} 失败</div>
            <div className="mt-1 font-mono text-[10px] text-rose-300/80">
              {error.kind}: {error.message}
            </div>
          </div>
        )}

        {!isLoading && !error && plans && plans.length === 0 && (
          <div className="rounded-lg border border-zinc-800 bg-zinc-950/40 p-4 text-center text-xs text-zinc-500">
            当前策略未生成任何 OutputPlan
          </div>
        )}

        {plans && plans.length > 0 && (
          <ul className="space-y-2" data-testid="video-plan-list">
            {plans.map((p, idx) => (
              <OutputPlanCard key={`${p.name}-${idx}`} plan={p} />
            ))}
          </ul>
        )}
      </div>
    </section>
  );
}

// ── OutputPlan 卡片 ──────────────────────────────────────────────────
function OutputPlanCard({ plan }: { plan: OutputPlan }) {
  const episodeBadge =
    plan.episode_number !== null && plan.episode_number !== undefined ? (
      <span className="rounded-md bg-amber-500/20 px-1.5 py-0.5 font-mono text-[10px] text-amber-200">
        EP{String(plan.episode_number).padStart(2, "0")}
        {plan.episode_label ? ` · ${plan.episode_label}` : ""}
      </span>
    ) : null;

  return (
    <li
      className="rounded-lg border border-zinc-800 bg-zinc-950/40 p-3"
      data-testid="video-plan-card"
    >
      <div className="mb-2 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="font-mono text-sm text-zinc-100">{plan.name}</span>
          {episodeBadge}
        </div>
        <span className="text-[10px] text-zinc-500">
          {plan.ordered_sources.length} 源
        </span>
      </div>
      <ol className="space-y-0.5 text-[11px] text-zinc-400">
        {plan.ordered_sources.map((src, i) => (
          <li key={i} className="truncate font-mono">
            <span className="text-zinc-600">{i + 1}.</span> {src}
          </li>
        ))}
      </ol>
      {plan.series_context && (
        <div className="mt-2 truncate text-[10px] text-zinc-600">
          series_context:{" "}
          <span className="text-zinc-400">{plan.series_context}</span>
        </div>
      )}
    </li>
  );
}
