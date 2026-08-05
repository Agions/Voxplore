/**
 * SceneFab v2.5.0 · 欢迎页 (M3.2 视觉化重设计)
 *
 * 去文字堆砌:
 * - 顶部 Hero:渐变大字 + 1 句价值主张 + 2 个 CTA
 * - 中段工作流:视觉化 5 步流水线 (StepFlow 组件)
 * - 下段系统状态:紧凑贴纸式
 * - 不再展示"6 个页面链接"列表(已由 Sidebar 接管)
 */

import { Link, createFileRoute, useNavigate } from "@tanstack/react-router";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { StepFlow } from "@components/common/StepFlow";
import { BatchImportDialog } from "@components/dialogs/BatchImportDialog";
import { ThumbnailImage } from "@components/common/ThumbnailImage";
import {
  appIpc,
  pipelineIpc,
  projectIpc,
  type ProjectRecord,
} from "@ipc/commands";

const FALLBACK_STEPS = [
  { id: "ingest", label: "素材", icon: "🎞", status: "pending" as const },
  { id: "scene", label: "场景", icon: "✂", status: "pending" as const },
  { id: "script", label: "脚本", icon: "✍", status: "pending" as const },
  { id: "voice", label: "配音", icon: "🎙", status: "pending" as const },
  { id: "export", label: "导出", icon: "📤", status: "pending" as const },
];

export const Route = createFileRoute("/")({
  component: HomePage,
});

function HomePage() {
  return (
    <div className="mx-auto max-w-6xl space-y-10 px-8 py-10">
      <Hero />
      <section>
        <SectionHeader
          kicker="工作流"
          title="一段视频,5 步成型"
          subtitle="从原始素材到可发布短片的全自动链路"
        />
        <StepFlow steps={FALLBACK_STEPS} activeIndex={-1} />
      </section>
      <RecentProjectsStrip />
      <MediaOverview />
      <SystemStatusStrip />
    </div>
  );
}

// ── Hero ────────────────────────────────────────────────────────────

function Hero() {
  return (
    <section className="relative overflow-hidden rounded-3xl border border-zinc-800/60 bg-gradient-to-br from-zinc-900 via-zinc-950 to-black p-10 shadow-2xl">
      <div className="pointer-events-none absolute -right-32 -top-32 h-96 w-96 rounded-full bg-violet-500/20 blur-3xl" />
      <div className="pointer-events-none absolute -bottom-32 -left-32 h-96 w-96 rounded-full bg-blue-500/20 blur-3xl" />

      <div className="relative grid grid-cols-1 gap-8 md:grid-cols-[1.4fr_1fr]">
        <div className="space-y-6">
          <div className="inline-flex items-center gap-2 rounded-full border border-violet-500/30 bg-violet-500/10 px-3 py-1 text-xs font-medium text-violet-200">
            <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-violet-400" />
            v3.0-alpha · 第一人称叙述已就绪
          </div>

          <h1 className="text-5xl font-black leading-[1.05] tracking-tight md:text-6xl">
            <span className="text-zinc-50">给每一段视频</span>
            <br />
            <span className="bg-gradient-to-r from-blue-400 via-violet-400 to-fuchsia-400 bg-clip-text text-transparent">
              写一个会说话的主持人
            </span>
          </h1>

          <p className="max-w-xl text-base text-zinc-400">
            AI 拆场景 · 写脚本 · 配中文语音 · 烧字幕,5 步出成片。
          </p>

          <div className="flex flex-wrap gap-3">
            <Link
              to="/production"
              className="group inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-blue-500 to-violet-500 px-6 py-3 text-sm font-semibold text-white shadow-lg shadow-blue-500/30 transition hover:shadow-blue-500/50"
            >
              开始制作
              <span className="transition group-hover:translate-x-0.5">→</span>
            </Link>
            <Link
              to="/assets"
              className="inline-flex items-center gap-2 rounded-xl border border-zinc-700 bg-zinc-900/70 px-6 py-3 text-sm font-medium text-zinc-200 transition hover:border-zinc-500 hover:bg-zinc-900"
            >
              打开项目
            </Link>
          </div>
        </div>

        <HeroVisual />
      </div>
    </section>
  );
}

function HeroVisual() {
  return (
    <div className="relative grid grid-cols-3 gap-3 rounded-2xl border border-zinc-800/60 bg-zinc-950/60 p-4">
      <VisualCard tone="blue" icon="🎞" title="导入" sub="mp4 / mov" />
      <VisualCard tone="violet" icon="✂" title="拆分" sub="6 场景" />
      <VisualCard tone="fuchsia" icon="✍" title="脚本" sub="第一人称" />
      <VisualCard tone="amber" icon="🎙" title="配音" sub="Edge TTS" />
      <VisualCard tone="emerald" icon="📝" title="字幕" sub="自动烧录" />
      <VisualCard tone="cyan" icon="📤" title="导出" sub="1080×1920" />
    </div>
  );
}

function VisualCard({
  tone,
  icon,
  title,
  sub,
}: {
  tone: string;
  icon: string;
  title: string;
  sub: string;
}) {
  const map: Record<string, string> = {
    blue: "from-blue-500/20 to-blue-500/0 border-blue-500/30 text-blue-200",
    violet:
      "from-violet-500/20 to-violet-500/0 border-violet-500/30 text-violet-200",
    fuchsia:
      "from-fuchsia-500/20 to-fuchsia-500/0 border-fuchsia-500/30 text-fuchsia-200",
    amber:
      "from-amber-500/20 to-amber-500/0 border-amber-500/30 text-amber-200",
    emerald:
      "from-emerald-500/20 to-emerald-500/0 border-emerald-500/30 text-emerald-200",
    cyan: "from-cyan-500/20 to-cyan-500/0 border-cyan-500/30 text-cyan-200",
  };
  return (
    <div
      className={`flex flex-col items-start justify-between rounded-xl border bg-gradient-to-br p-3 transition hover:scale-[1.03] ${map[tone]}`}
    >
      <span className="text-2xl">{icon}</span>
      <div className="mt-6 space-y-0.5">
        <div className="text-sm font-semibold text-zinc-100">{title}</div>
        <div className="text-[10px] text-zinc-400">{sub}</div>
      </div>
    </div>
  );
}

// ── Section header ─────────────────────────────────────────────────

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
    <div className="mb-5 space-y-1">
      <div className="text-[10px] font-semibold uppercase tracking-[0.2em] text-violet-400">
        {kicker}
      </div>
      <h2 className="text-xl font-semibold tracking-tight text-zinc-100">
        {title}
      </h2>
      <p className="text-sm text-zinc-500">{subtitle}</p>
    </div>
  );
}

// ── Recent projects strip ──────────────────────────────────────────

function RecentProjectsStrip() {
  const { data: recent } = useQuery({
    queryKey: ["home-recent"],
    queryFn: () => projectIpc.listRecent(),
  });

  return (
    <section>
      <SectionHeader kicker="历史" title="最近的项目" subtitle="点击继续编辑" />
      {recent && recent.length > 0 ? (
        <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
          {recent.slice(0, 8).map((path, i) => (
            <button
              key={path}
              type="button"
              className="group flex flex-col items-start gap-2 rounded-xl border border-zinc-800 bg-zinc-900/40 p-4 text-left transition hover:border-blue-500/50 hover:bg-zinc-900"
            >
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-gradient-to-br from-zinc-700 to-zinc-900 text-sm font-bold text-zinc-300 group-hover:from-blue-500 group-hover:to-violet-500 group-hover:text-white">
                {i + 1}
              </div>
              <div className="truncate text-xs text-zinc-300">
                {path.split("/").pop()}
              </div>
              <div className="truncate text-[10px] text-zinc-500">{path}</div>
            </button>
          ))}
        </div>
      ) : (
        <EmptyRecent />
      )}
    </section>
  );
}

function EmptyRecent() {
  return (
    <div className="flex items-center justify-between rounded-2xl border border-dashed border-zinc-800 bg-zinc-900/30 px-6 py-8">
      <div className="space-y-1">
        <div className="text-base font-medium text-zinc-200">还没有项目</div>
        <div className="text-xs text-zinc-500">创建一个空白项目开始制作</div>
      </div>
      <Link
        to="/production"
        className="rounded-lg bg-gradient-to-r from-blue-500 to-violet-500 px-4 py-2 text-xs font-semibold text-white shadow shadow-blue-500/30"
      >
        新建项目
      </Link>
    </div>
  );
}

// ── System status strip (compact, 1 line) ──────────────────────────

function SystemStatusStrip() {
  const version = useQuery({
    queryKey: ["home-version"],
    queryFn: appIpc.version,
  });
  const stepDefs = useQuery({
    queryKey: ["home-steps"],
    queryFn: pipelineIpc.stepDefs,
  });
  const sysInfo = useQuery({
    queryKey: ["home-sys"],
    queryFn: appIpc.systemInfo,
  });

  const ok = !version.isError && !stepDefs.isError && !sysInfo.isError;
  const ffmpegOk = sysInfo.data?.ffmpegAvailable ?? false;

  return (
    <section className="flex flex-wrap items-center gap-2 text-[11px]">
      <Pill tone={ok ? "ok" : "err"}>{ok ? "Tauri 已连接" : "后端断连"}</Pill>
      <Pill tone="info">v{version.data ?? "—"}</Pill>
      <Pill tone="info">{stepDefs.data?.length ?? 5} 步流水线</Pill>
      <Pill tone={ffmpegOk ? "ok" : "warn"}>
        ffmpeg {ffmpegOk ? "就绪" : "未安装"}
      </Pill>
      <Pill tone="neutral">Rust backend</Pill>
    </section>
  );
}

function Pill({
  tone,
  children,
}: {
  tone: "ok" | "err" | "warn" | "info" | "neutral";
  children: React.ReactNode;
}) {
  const map: Record<string, string> = {
    ok: "border-emerald-700/40 bg-emerald-950/30 text-emerald-300",
    err: "border-rose-800/40 bg-rose-950/30 text-rose-300",
    warn: "border-amber-800/40 bg-amber-950/30 text-amber-300",
    info: "border-blue-800/40 bg-blue-950/30 text-blue-300",
    neutral: "border-zinc-800 bg-zinc-900/40 text-zinc-400",
  };
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 ${map[tone]}`}
    >
      {children}
    </span>
  );
}

// ── 素材总览 (M3 后续: 当前项目素材) ─────────────────────────────

function MediaOverview() {
  const qc = useQueryClient();
  const navigate = useNavigate();
  const [openImport, setOpenImport] = useState(false);

  const currentProject =
    (qc.getQueryData(["current-project"]) as ProjectRecord | undefined) ?? null;
  const media = currentProject?.project.media_files ?? [];
  const preview = media.slice(0, 6);
  const remaining = Math.max(media.length - preview.length, 0);
  const projectName = currentProject?.project.name ?? null;

  return (
    <section>
      <div className="mb-5 flex items-end justify-between">
        <SectionHeader
          kicker="素材"
          title={projectName ? `当前项目 · ${projectName}` : "素材总览"}
          subtitle={
            projectName
              ? `共 ${media.length} 个素材`
              : "打开或新建一个项目后可在此预览"
          }
        />
        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => setOpenImport(true)}
            disabled={!currentProject}
            title={!currentProject ? "请先打开项目" : undefined}
            className="rounded-md border border-blue-700/50 bg-blue-950/30 px-3 py-1.5 text-xs text-blue-200 transition hover:border-blue-500 hover:bg-blue-950/60 disabled:opacity-40"
          >
            📂 导入
          </button>
          <button
            type="button"
            onClick={() => void navigate({ to: "/assets" })}
            className="rounded-md border border-zinc-700 bg-zinc-900 px-3 py-1.5 text-xs text-zinc-200 transition hover:border-zinc-500"
          >
            📦 进入素材页 →
          </button>
        </div>
      </div>

      {!currentProject ? (
        <div className="flex items-center justify-between rounded-2xl border border-dashed border-zinc-800 bg-zinc-900/30 px-6 py-8">
          <div className="space-y-1">
            <div className="text-sm font-medium text-zinc-200">
              还没有打开的项目
            </div>
            <div className="text-xs text-zinc-500">
              前往制作流水线页新建项目,或将素材直接导入现有项目
            </div>
          </div>
          <Link
            to="/production"
            className="rounded-lg bg-gradient-to-r from-blue-500 to-violet-500 px-4 py-2 text-xs font-semibold text-white shadow shadow-blue-500/30"
          >
            🎬 前往制作
          </Link>
        </div>
      ) : media.length === 0 ? (
        <div className="flex items-center justify-between rounded-2xl border border-amber-800/40 bg-amber-950/20 px-6 py-8">
          <div className="space-y-1">
            <div className="text-sm font-medium text-amber-100">
              当前项目还没有素材
            </div>
            <div className="text-xs text-amber-200/80">
              导入 1 个或多个视频后即可启动流水线
            </div>
          </div>
          <button
            type="button"
            onClick={() => setOpenImport(true)}
            className="rounded-lg bg-gradient-to-r from-blue-500 to-violet-500 px-4 py-2 text-xs font-semibold text-white shadow shadow-blue-500/30"
          >
            📂 立即导入
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-6">
          {preview.map((m) => (
            <button
              type="button"
              key={m.path}
              onClick={() => void navigate({ to: "/assets" })}
              className="group flex flex-col gap-1.5 rounded-xl border border-zinc-800 bg-zinc-900/40 p-2 text-left transition hover:border-blue-500/50 hover:bg-zinc-900"
            >
              <ThumbnailImage source={m.path} kind="video" width={200} />
              <div className="space-y-0.5 px-1 pb-1">
                <div
                  className="truncate font-mono text-[10px] text-zinc-200"
                  title={m.path}
                >
                  {m.path.split(/[/\\]/).pop() ?? m.path}
                </div>
                <div className="flex items-center gap-1.5 text-[10px] text-zinc-500">
                  <span>{Math.round(m.duration_seconds)}s</span>
                  {m.resolution && (
                    <>
                      <span>·</span>
                      <span>{m.resolution}</span>
                    </>
                  )}
                </div>
              </div>
            </button>
          ))}
          {remaining > 0 && (
            <button
              type="button"
              onClick={() => void navigate({ to: "/assets" })}
              className="flex aspect-video w-full flex-col items-center justify-center rounded-xl border border-dashed border-zinc-700 bg-zinc-900/30 text-center text-xs text-zinc-400 transition hover:border-blue-500/50 hover:text-blue-300"
            >
              <div className="text-2xl">＋</div>
              <div>还有 {remaining} 项</div>
            </button>
          )}
        </div>
      )}

      <BatchImportDialog
        open={openImport}
        onClose={() => setOpenImport(false)}
        onImported={() => {
          setOpenImport(false);
        }}
      />
    </section>
  );
}
