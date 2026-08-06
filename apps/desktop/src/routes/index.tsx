/**
 * Vynaro v2.5.0 · 首页 Dashboard (根据 Image 1 设计原图高保真像素级重构)
 *
 * 核心页面布局结构 (与 Image 1 UI 100% 对齐):
 * 1. 顶部 Welcome Banner: Welcome back, Creator! Ready to craft your next masterpiece?
 * 2. Recent Video Projects 区域: 3 张带金色发光边框、进度条与 ▶ 播放按钮的项目卡片
 * 3. 7-Step AI Narrative Pipeline 区域: 视觉化 7 步横向流水线面板 (1-3 100%, 4 85% In Progress 高亮, 5-7 待处理)
 * 4. Quick Actions 区域: 4 块核心快捷按钮 (实心金 "New Project" + 3 个暗黑玻璃按钮)
 */

import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { BatchImportDialog } from "@components/dialogs/BatchImportDialog";
import { ThumbnailImage } from "@components/common/ThumbnailImage";
import {
  appIpc,
  pipelineIpc,
  projectIpc,
} from "@ipc/commands";

export const Route = createFileRoute("/")({
  component: HomePage,
});

function HomePage() {
  return (
    <div className="mx-auto max-w-6xl space-y-8 px-8 py-8">
      {/* 1. 顶部 Header */}
      <WelcomeHeader />

      {/* 2. 最近视频项目卡片 */}
      <RecentProjectsSection />

      {/* 3. 7 步 AI 叙事流水线 */}
      <PipelineSection />

      {/* 4. 快捷操作栏 */}
      <QuickActionsSection />

      {/* 5. 底栏系统探针状态 */}
      <SystemStatusStrip />
    </div>
  );
}

// ── 1. Welcome Header ──────────────────────────────────────────────

function WelcomeHeader() {
  return (
    <div className="space-y-1">
      <h1 className="text-3xl font-extrabold tracking-tight text-zinc-100">
        Welcome back, Creator!{" "}
        <span className="bg-gradient-to-r from-[#F5C842] via-[#F9D76B] to-[#E8933A] bg-clip-text text-transparent font-normal">
          Ready to craft your next masterpiece?
        </span>
      </h1>
      <p className="text-xs text-zinc-400 font-medium tracking-wide">
        With a futuristic, cinematic AI video narrative engine
      </p>
    </div>
  );
}

// ── 2. Recent Video Projects ───────────────────────────────────────

interface SampleProject {
  id: string;
  title: string;
  lastEdited: string;
  progress: number;
  thumbnail: string;
}

const SAMPLE_PROJECTS: SampleProject[] = [
  {
    id: "neon-odyssey",
    title: "The Neon Odyssey",
    lastEdited: "Jan 15, 2026, 09:12 AM",
    progress: 70,
    thumbnail: "/abs/neon.mp4",
  },
  {
    id: "chronicles-sol",
    title: "Chronicles of Sol",
    lastEdited: "Jan 15, 2026, 09:12 AM",
    progress: 45,
    thumbnail: "/abs/sol.mp4",
  },
  {
    id: "echoes-tomorrow",
    title: "Echoes of Tomorrow",
    lastEdited: "Jan 15, 2026, 09:12 AM",
    progress: 92,
    thumbnail: "/abs/echoes.mp4",
  },
];

function RecentProjectsSection() {
  const navigate = useNavigate();
  const { data: recentPaths } = useQuery({
    queryKey: ["home-recent-projects"],
    queryFn: () => projectIpc.listRecent(),
  });

  return (
    <section className="space-y-3">
      {/* Header with See All */}
      <div className="flex items-center justify-between">
        <h2 className="text-base font-semibold text-zinc-100 tracking-tight">
          Recent Video Projects
        </h2>
        <button
          type="button"
          onClick={() => void navigate({ to: "/assets" })}
          className="text-xs font-medium text-zinc-400 transition hover:text-[#F5C842]"
        >
          See All →
        </button>
      </div>

      {/* 3 Grid Project Cards */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        {SAMPLE_PROJECTS.map((proj, idx) => {
          // If real paths exist, use real path for title fallback
          const realPath = recentPaths?.[idx];
          const displayTitle = realPath ? realPath.split(/[/\\]/).pop() : proj.title;

          return (
            <div
              key={proj.id}
              onClick={() => void navigate({ to: "/production" })}
              className="group relative cursor-pointer overflow-hidden rounded-2xl border border-[#F5C842]/40 bg-[#161619] p-4 transition-all duration-300 hover:border-[#F5C842] hover:bg-[#1E1E22] hover:shadow-[0_0_24px_rgba(245,200,66,0.18)]"
            >
              {/* Thumbnail Container */}
              <div className="relative mb-3.5 h-28 w-full overflow-hidden rounded-xl bg-zinc-950/80 border border-zinc-800">
                <div className="absolute inset-0 bg-gradient-to-t from-[#161619] via-transparent to-transparent z-10 opacity-70" />
                <ThumbnailImage source={realPath ?? proj.thumbnail} kind="video" width={320} />
              </div>

              {/* Title & Metadata */}
              <div className="mb-3 space-y-0.5">
                <h3 className="truncate text-sm font-semibold text-zinc-100 group-hover:text-[#F5C842] transition-colors">
                  {displayTitle}
                </h3>
                <p className="text-[11px] text-zinc-500 font-mono">
                  Last edited: {proj.lastEdited}
                </p>
              </div>

              {/* Progress Bar & Play Button */}
              <div className="flex items-center justify-between gap-3">
                <div className="flex-1 space-y-1">
                  <div className="h-1.5 w-full overflow-hidden rounded-full bg-zinc-800">
                    <div
                      className="h-full rounded-full bg-gradient-to-r from-[#F5C842] to-[#E8933A] shadow-[0_0_8px_rgba(245,200,66,0.5)] transition-all duration-500"
                      style={{ width: `${proj.progress}%` }}
                    />
                  </div>
                </div>

                <span className="font-mono text-xs font-bold text-zinc-400 group-hover:text-[#F5C842]">
                  {proj.progress}%
                </span>

                {/* Golden Round Play Button */}
                <button
                  type="button"
                  className="flex h-7 w-7 items-center justify-center rounded-full bg-[#F5C842] text-zinc-950 font-bold shadow-[0_0_10px_rgba(245,200,66,0.4)] transition-transform duration-200 group-hover:scale-110"
                >
                  ▶
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}

// ── 3. 7-Step AI Narrative Pipeline Card ───────────────────────────

interface PipelineStepItem {
  num: number;
  label: string;
  status: "completed" | "in_progress" | "pending";
  percent?: number;
  icon: string;
}

const PIPELINE_STEPS: PipelineStepItem[] = [
  { num: 1, label: "Ingest", status: "completed", percent: 100, icon: "📥" },
  { num: 2, label: "Analyze", status: "completed", percent: 100, icon: "🔍" },
  { num: 3, label: "Scene Detection", status: "completed", percent: 100, icon: "✂️" },
  { num: 4, label: "Narrative Mapping", status: "in_progress", percent: 85, icon: "≡" },
  { num: 5, label: "Clip Selection", status: "pending", icon: "🎬" },
  { num: 6, label: "Transitions & FX", status: "pending", icon: "🔀" },
  { num: 7, label: "Final Output", status: "pending", icon: "📤" },
];

function PipelineSection() {
  const navigate = useNavigate();

  return (
    <section className="rounded-2xl border border-zinc-800 bg-[#161619]/90 p-6 backdrop-blur-xl shadow-xl">
      <div className="mb-6 flex items-center justify-between">
        <h2 className="text-base font-semibold text-zinc-100 tracking-tight">
          7-Step AI Narrative Pipeline
        </h2>
        <span className="font-mono text-xs text-[#F5C842] bg-[#F5C842]/10 border border-[#F5C842]/30 px-3 py-1 rounded-full font-medium">
          Step 4 / 7 Active
        </span>
      </div>

      {/* Horizontal Stepper Row */}
      <div className="relative flex items-center justify-between gap-2 overflow-x-auto pb-2">
        {PIPELINE_STEPS.map((step, index) => {
          const isCompleted = step.status === "completed";
          const isInProgress = step.status === "in_progress";

          return (
            <div key={step.num} className="flex flex-1 items-center">
              {/* Step Card Element */}
              <div
                onClick={() => void navigate({ to: "/production" })}
                className={`relative flex flex-col items-center justify-center flex-1 cursor-pointer rounded-xl p-3.5 text-center transition-all duration-300 ${
                  isInProgress
                    ? "border border-[#F5C842] bg-[#F5C842]/15 shadow-[0_0_20px_rgba(245,200,66,0.3)] scale-105"
                    : isCompleted
                      ? "border border-[#F5C842]/40 bg-[#1E1E22] hover:border-[#F5C842]"
                      : "border border-zinc-800/80 bg-zinc-950/40 opacity-50 hover:opacity-80"
                }`}
              >
                {/* Step Icon Badge */}
                <div
                  className={`mb-2 flex h-10 w-10 items-center justify-center rounded-xl font-bold text-base transition-all ${
                    isInProgress
                      ? "border border-[#F5C842] bg-[#F5C842] text-zinc-950 shadow-[0_0_12px_rgba(245,200,66,0.5)]"
                      : isCompleted
                        ? "border border-[#F5C842]/50 bg-[#F5C842]/20 text-[#F5C842]"
                        : "border border-zinc-800 bg-zinc-900 text-zinc-500"
                  }`}
                >
                  {isCompleted ? "✓" : step.icon}
                </div>

                {/* Step Label & Number */}
                <div className="space-y-1">
                  <span className="block text-xs font-semibold text-zinc-200">
                    {step.num}. {step.label}
                  </span>

                  {/* Status Pill */}
                  {isCompleted && (
                    <span className="inline-block rounded-md bg-[#F5C842]/15 border border-[#F5C842]/30 px-2 py-0.5 font-mono text-[10px] text-[#F5C842] font-semibold">
                      Completed 100%
                    </span>
                  )}
                  {isInProgress && (
                    <span className="inline-block rounded-md bg-[#F5C842] text-zinc-950 px-2 py-0.5 font-mono text-[10px] font-bold shadow-[0_0_8px_rgba(245,200,66,0.4)]">
                      In Progress 85%
                    </span>
                  )}
                </div>
              </div>

              {/* Connecting Line Arrow */}
              {index < PIPELINE_STEPS.length - 1 && (
                <div className="mx-1 h-[2px] w-4 flex-shrink-0 bg-gradient-to-r from-zinc-700 to-zinc-800" />
              )}
            </div>
          );
        })}
      </div>
    </section>
  );
}

// ── 4. Quick Actions Section ───────────────────────────────────────

function QuickActionsSection() {
  const navigate = useNavigate();
  const [openImport, setOpenImport] = useState(false);

  return (
    <section className="space-y-3">
      <h2 className="text-base font-semibold text-zinc-100 tracking-tight">
        Quick Actions
      </h2>

      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        {/* Button 1: Solid Vibrant Gold "New Project" */}
        <button
          type="button"
          onClick={() => void navigate({ to: "/production" })}
          className="flex h-12 items-center justify-center rounded-xl bg-[#F5C842] px-6 text-sm font-bold text-zinc-950 shadow-[0_0_20px_rgba(245,200,66,0.35)] transition-all duration-300 hover:bg-[#F9D76B] hover:shadow-[0_0_28px_rgba(245,200,66,0.5)] hover:scale-[1.02]"
        >
          ➕ New Project
        </button>

        {/* Button 2: Import Media */}
        <button
          type="button"
          onClick={() => setOpenImport(true)}
          className="flex h-12 items-center justify-center rounded-xl border border-zinc-800 bg-[#161619] px-6 text-sm font-medium text-zinc-200 transition-all duration-300 hover:border-zinc-700 hover:bg-[#1E1E22] hover:text-white"
        >
          📂 Import Media
        </button>

        {/* Button 3: Explore AI Styles */}
        <button
          type="button"
          onClick={() => void navigate({ to: "/settings" })}
          className="flex h-12 items-center justify-center rounded-xl border border-zinc-800 bg-[#161619] px-6 text-sm font-medium text-zinc-200 transition-all duration-300 hover:border-zinc-700 hover:bg-[#1E1E22] hover:text-white"
        >
          ✨ Explore AI Styles
        </button>

        {/* Button 4: Recent Activity */}
        <button
          type="button"
          onClick={() => void navigate({ to: "/assets" })}
          className="flex h-12 items-center justify-center rounded-xl border border-zinc-800 bg-[#161619] px-6 text-sm font-medium text-zinc-200 transition-all duration-300 hover:border-zinc-700 hover:bg-[#1E1E22] hover:text-white"
        >
          🕒 Recent Activity
        </button>
      </div>

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

// ── 5. System Status Strip (Compact Footer) ───────────────────────

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
    <div className="flex flex-wrap items-center gap-2 pt-2 text-xs font-mono text-zinc-500">
      <span className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 border text-[11px] ${
        ok ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-400" : "border-rose-500/30 bg-rose-500/10 text-rose-400"
      }`}>
        <span className={`h-1.5 w-1.5 rounded-full ${ok ? "bg-emerald-400 animate-pulse" : "bg-rose-400"}`} />
        {ok ? "Tauri Connected" : "Backend Disconnected"}
      </span>

      <span className="inline-flex items-center rounded-full border border-zinc-800 bg-zinc-900/60 px-3 py-1 text-[11px] text-zinc-400">
        v{version.data ?? "2.5.0"}
      </span>

      <span className="inline-flex items-center rounded-full border border-zinc-800 bg-zinc-900/60 px-3 py-1 text-[11px] text-zinc-400">
        {stepDefs.data?.length ?? 7} Steps Pipeline
      </span>

      <span className={`inline-flex items-center rounded-full px-3 py-1 border text-[11px] ${
        ffmpegOk ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-400" : "border-amber-500/30 bg-amber-500/10 text-amber-400"
      }`}>
        FFmpeg {ffmpegOk ? "Ready" : "System Check"}
      </span>
    </div>
  );
}
