/**
 * Vynaro v1.0.0 · 首页 Dashboard (完美适配亮色/暗色多主题模式)
 *
 * 核心页面布局结构 (与 Image 1 UI 100% 对齐):
 * 1. 顶部 Welcome Banner: Vynaro 叙影 AI 视频叙事工作室 · 打造下一部爆款电影级解说作品
 * 2. Recent Video Projects 区域: 3 张带金色发光边框、进度条与 ▶ 播放按钮的项目卡片
 * 3. 7-Step AI Narrative Pipeline 区域: 视觉化 7 步横向流水线面板 (1-3 100%, 4 85% 进行中高亮, 5-7 待处理)
 * 4. Quick Actions 区域: 4 块核心快捷按钮 (实心金 "➕ 新建项目" + 3 个暗黑玻璃按钮)
 */

import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { BatchImportDialog } from "@components/dialogs/BatchImportDialog";
import { ThumbnailImage } from "@components/common/ThumbnailImage";
import { useProjectStore } from "@stores/project-store";
import { toast } from "sonner";
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
      <h1 className="text-3xl font-extrabold tracking-tight text-[var(--color-text-primary)]">
        Vynaro 叙影 AI 视频叙事工作室{" "}
        <span className="bg-gradient-to-r from-[#F5C842] via-[#F9D76B] to-[#E8933A] bg-clip-text text-transparent font-normal">
          打造下一部爆款电影级解说作品
        </span>
      </h1>
      <p className="text-xs text-[var(--color-text-secondary)] font-medium tracking-wide">
        支持 7 步全自动拆条、第一人称文案编排、TTS 人声克隆与剪映草稿工程导出
      </p>
    </div>
  );
}

// ── 2. Recent Video Projects ───────────────────────────────────────

function RecentProjectsSection() {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const setCurrentRecord = useProjectStore((s) => s.setCurrentRecord);

  const { data: recentPaths } = useQuery({
    queryKey: ["home-recent-projects"],
    queryFn: () => projectIpc.listRecent(),
  });

  const createProject = useMutation({
    mutationFn: projectIpc.createBlank,
    onSuccess: (rec) => {
      qc.setQueryData(["current-project"], rec);
      setCurrentRecord(rec.path, rec.project);
      void navigate({ to: "/production" });
      toast.success("新建解说工程已建立");
    },
    onError: (e) => {
      toast.error("创建工程失败", { description: e instanceof Error ? e.message : String(e) });
    },
  });

  const hasRecents = recentPaths && recentPaths.length > 0;

  return (
    <section className="space-y-3">
      {/* Header with See All */}
      <div className="flex items-center justify-between">
        <h2 className="text-base font-semibold text-[var(--color-text-primary)] tracking-tight">
          最近视频解说工程
        </h2>
        {hasRecents && (
          <button
            type="button"
            onClick={() => void navigate({ to: "/assets" })}
            className="text-xs font-medium text-[var(--color-text-secondary)] transition hover:text-[var(--color-gold)]"
          >
            查看资产库 →
          </button>
        )}
      </div>

      {!hasRecents ? (
        <div className="flex flex-col items-center justify-center rounded-2xl border border-dashed border-[var(--color-border)] bg-[var(--color-surface)] p-10 text-center">
          <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-[var(--color-gold-muted)] border border-[var(--color-gold)]/30 text-[var(--color-gold)] text-2xl mb-3">
            🎬
          </div>
          <h3 className="text-sm font-bold text-[var(--color-text-primary)]">暂无历史解说工程</h3>
          <p className="text-xs text-[var(--color-text-secondary)] mt-1 mb-4">
            点击下方按钮快速建立第一个 7 步 AI 短剧/影视解说工程
          </p>
          <button
            type="button"
            onClick={() => createProject.mutate()}
            disabled={createProject.isPending}
            className="btn-primary text-xs px-5 py-2.5 font-bold"
          >
            ➕ 新建解说工程
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
          {recentPaths.slice(0, 3).map((realPath) => {
            const displayTitle = realPath.split(/[/\\]/).pop() || realPath;

            return (
              <div
                key={realPath}
                onClick={() => void navigate({ to: "/production" })}
                className="group relative cursor-pointer overflow-hidden rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)] p-4 transition-all duration-300 hover:border-[var(--color-gold)] hover:bg-[var(--color-surface-elevated)] hover:shadow-[0_0_24px_var(--color-gold-glow)]"
              >
                {/* Thumbnail Container */}
                <div className="relative mb-3.5 h-28 w-full overflow-hidden rounded-xl bg-zinc-950/80 border border-[var(--color-border)]">
                  <div className="absolute inset-0 bg-gradient-to-t from-[var(--color-surface)] via-transparent to-transparent z-10 opacity-70" />
                  <ThumbnailImage source={realPath} kind="video" width={320} />
                </div>

                {/* Title & Metadata */}
                <div className="mb-3 space-y-0.5">
                  <h3 className="truncate text-sm font-semibold text-[var(--color-text-primary)] group-hover:text-[var(--color-gold)] transition-colors">
                    {displayTitle}
                  </h3>
                  <p className="text-[11px] text-[var(--color-text-muted)] font-mono">
                    工程文件 · 本地极速处理
                  </p>
                </div>

                {/* Action CTA */}
                <div className="flex items-center justify-between gap-3 border-t border-[var(--color-border)] pt-2.5">
                  <span className="text-[11px] font-semibold text-[var(--color-gold)]">
                    进入制作工作台 →
                  </span>
                  <button
                    type="button"
                    className="flex h-7 w-7 items-center justify-center rounded-full bg-[var(--color-gold)] text-zinc-950 font-bold shadow-[0_0_10px_var(--color-gold-glow)] transition-transform duration-200 group-hover:scale-110"
                  >
                    ▶
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}
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
  { num: 1, label: "素材导入", status: "completed", percent: 100, icon: "📥" },
  { num: 2, label: "智能拆条", status: "completed", percent: 100, icon: "🔍" },
  { num: 3, label: "镜头检测", status: "completed", percent: 100, icon: "✂️" },
  { num: 4, label: "文案编排", status: "in_progress", percent: 85, icon: "≡" },
  { num: 5, label: "片段精选", status: "pending", icon: "🎬" },
  { num: 6, label: "转场特效", status: "pending", icon: "🔀" },
  { num: 7, label: "草稿导出", status: "pending", icon: "📤" },
];

function PipelineSection() {
  const navigate = useNavigate();

  return (
    <section className="rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)] p-6 backdrop-blur-xl shadow-xl">
      <div className="mb-6 flex items-center justify-between">
        <h2 className="text-base font-semibold text-[var(--color-text-primary)] tracking-tight">
          7 步 AI 叙事工作流
        </h2>
        <span className="font-mono text-xs text-[var(--color-gold)] bg-[var(--color-gold-muted)] border border-[var(--color-gold)]/30 px-3 py-1 rounded-full font-medium">
          Step 4 / 7 进行中
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
                    ? "border border-[var(--color-gold)] bg-[var(--color-gold-muted)] shadow-[0_0_20px_var(--color-gold-glow)] scale-105"
                    : isCompleted
                      ? "border border-[var(--color-gold)]/40 bg-[var(--color-surface-elevated)] hover:border-[var(--color-gold)]"
                      : "border border-[var(--color-border)] bg-[var(--color-surface-elevated)]/40 opacity-60 hover:opacity-100"
                }`}
              >
                {/* Step Icon Badge */}
                <div
                  className={`mb-2 flex h-10 w-10 items-center justify-center rounded-xl font-bold text-base transition-all ${
                    isInProgress
                      ? "border border-[var(--color-gold)] bg-[var(--color-gold)] text-zinc-950 shadow-[0_0_12px_var(--color-gold-glow)]"
                      : isCompleted
                        ? "border border-[var(--color-gold)]/50 bg-[var(--color-gold-muted)] text-[var(--color-gold)]"
                        : "border border-[var(--color-border)] bg-[var(--color-surface)] text-[var(--color-text-muted)]"
                  }`}
                >
                  {isCompleted ? "✓" : step.icon}
                </div>

                {/* Step Label & Number */}
                <div className="space-y-1">
                  <span className="block text-xs font-semibold text-[var(--color-text-primary)]">
                    {step.num}. {step.label}
                  </span>

                  {/* Status Pill */}
                  {isCompleted && (
                    <span className="inline-block rounded-md bg-[var(--color-gold-muted)] border border-[var(--color-gold)]/30 px-2 py-0.5 font-mono text-[10px] text-[var(--color-gold)] font-semibold">
                      已完成 100%
                    </span>
                  )}
                  {isInProgress && (
                    <span className="inline-block rounded-md bg-[var(--color-gold)] text-zinc-950 px-2 py-0.5 font-mono text-[10px] font-bold shadow-[0_0_8px_var(--color-gold-glow)]">
                      进行中 85%
                    </span>
                  )}
                </div>
              </div>

              {/* Connecting Line Arrow */}
              {index < PIPELINE_STEPS.length - 1 && (
                <div className="mx-1 h-[2px] w-4 flex-shrink-0 bg-[var(--color-border)]" />
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
      <h2 className="text-base font-semibold text-[var(--color-text-primary)] tracking-tight">
        快捷操作
      </h2>

      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        {/* Button 1: Solid Vibrant Gold "➕ 新建项目" */}
        <button
          type="button"
          onClick={() => void navigate({ to: "/production" })}
          className="flex h-12 items-center justify-center rounded-xl bg-[var(--color-gold)] px-6 text-sm font-bold text-zinc-950 shadow-[0_0_20px_var(--color-gold-glow)] transition-all duration-300 hover:brightness-110 hover:scale-[1.02]"
        >
          ➕ 新建项目
        </button>

        {/* Button 2: Import Media */}
        <button
          type="button"
          onClick={() => setOpenImport(true)}
          className="flex h-12 items-center justify-center rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] px-6 text-sm font-medium text-[var(--color-text-primary)] transition-all duration-300 hover:border-[var(--color-gold)]/60 hover:bg-[var(--color-surface-elevated)]"
        >
          📂 导入素材
        </button>

        {/* Button 3: Explore AI Styles */}
        <button
          type="button"
          onClick={() => void navigate({ to: "/settings" })}
          className="flex h-12 items-center justify-center rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] px-6 text-sm font-medium text-[var(--color-text-primary)] transition-all duration-300 hover:border-[var(--color-gold)]/60 hover:bg-[var(--color-surface-elevated)]"
        >
          ✨ 探索 AI 风格
        </button>

        {/* Button 4: Recent Activity */}
        <button
          type="button"
          onClick={() => void navigate({ to: "/assets" })}
          className="flex h-12 items-center justify-center rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] px-6 text-sm font-medium text-[var(--color-text-primary)] transition-all duration-300 hover:border-[var(--color-gold)]/60 hover:bg-[var(--color-surface-elevated)]"
        >
          🕒 历史活动
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
    <div className="flex flex-wrap items-center gap-2 pt-2 text-xs font-mono text-[var(--color-text-muted)]">
      <span className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 border text-[11px] ${
        ok ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-500" : "border-rose-500/30 bg-rose-500/10 text-rose-500"
      }`}>
        <span className={`h-1.5 w-1.5 rounded-full ${ok ? "bg-emerald-500 animate-pulse" : "bg-rose-500"}`} />
        {ok ? "Tauri 已连接" : "后端未连接"}
      </span>

      <span className="inline-flex items-center rounded-full border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-1 text-[11px] text-[var(--color-text-secondary)]">
        v{version.data ?? "1.0.0"}
      </span>

      <span className="inline-flex items-center rounded-full border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-1 text-[11px] text-[var(--color-text-secondary)]">
        {stepDefs.data?.length ?? 7} 步解说工作流
      </span>

      <span className={`inline-flex items-center rounded-full px-3 py-1 border text-[11px] ${
        ffmpegOk ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-500" : "border-amber-500/30 bg-amber-500/10 text-amber-500"
      }`}>
        FFmpeg {ffmpegOk ? "已就绪" : "环境检测"}
      </span>
    </div>
  );
}
