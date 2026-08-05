/**
 * SceneFab v2.5.0 · 制作流水线页 (M3.2 接通后端 + M3 后续素材入口)
 *
 * 真实接入 pipeline_step_defs / pipeline_status / pipeline_start /
 *      pipeline_cancel / pipeline_reset + project_create_blank
 * 实时性:listen "pipeline:event" + 主动 refetch
 * 快捷键:⌘R / Ctrl+R 启动,⌘. 取消 (usePipelineHotkeys)
 *
 * 素材入口:
 * - 顶部 header 显示素材计数 (媒体/轨道/导出)
 * - "📂 导入素材" 按钮打开 BatchImportDialog (复用 assets UI)
 * - RunningPanel 顶部添加 "📂 导入更多素材" 二次入口
 * - 有项目但无素材时,在主控区给引导提示
 */

import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useCallback, useState } from "react";
import { toast } from "sonner";
import { StepFlow } from "@components/common/StepFlow";
import { BatchImportDialog } from "@components/dialogs/BatchImportDialog";
import { VideoPlanPreview } from "@components/production/VideoPlanPreview";
import {
  appIpc,
  pipelineIpc,
  projectIpc,
  type ProjectRecord,
} from "@ipc/commands";
import type { StepStatus } from "@ipc/types.gen";
import { usePipeline, usePipelineHotkeys } from "@hooks/usePipeline";

export const Route = createFileRoute("/production")({
  component: ProductionPage,
});

const STEP_ICONS = ["🎞", "✂", "✍", "🎙", "📤"];

function ProductionPage() {
  const qc = useQueryClient();
  const navigate = useNavigate();
  const { data: stepDefs } = useQuery({
    queryKey: ["pipeline-step-defs"],
    queryFn: pipelineIpc.stepDefs,
  });
  const sysInfo = useQuery({
    queryKey: ["prod-sys"],
    queryFn: appIpc.systemInfo,
  });

  // 真实接通后端的流水线 hook (含 listen + refetchInterval)
  const pipeline = usePipeline(stepDefs ?? []);

  const currentProject =
    (qc.getQueryData(["current-project"]) as ProjectRecord | undefined) ?? null;

  const createProject = useMutation({
    mutationFn: projectIpc.createBlank,
    onSuccess: (rec) => qc.setQueryData(["current-project"], rec),
  });

  // M3 后续:批量导入 dialog
  const [showImport, setShowImport] = useState(false);

  const handleStart = useCallback(() => {
    if (!currentProject) return;
    void pipeline.start(currentProject.project);
  }, [currentProject, pipeline]);

  const handleCancel = useCallback(() => {
    void pipeline.cancel();
  }, [pipeline]);

  const handleReset = useCallback(() => {
    void pipeline.reset();
  }, [pipeline]);

  // 全局快捷键
  usePipelineHotkeys(() => currentProject && handleStart(), handleCancel);

  // 后端 step_defs 是 label_zh 形式,StepFlow 需要 icon
  const stepsForView = pipeline.steps.slice(0, 5).map((s, idx) => ({
    id: s.id,
    label: s.label,
    icon: STEP_ICONS[idx] ?? "•",
    status: s.status as StepStatus,
  }));

  const percent = pipeline.percent;

  const mediaCount = currentProject?.project.media_files?.length ?? 0;
  const trackCount = currentProject?.project.timeline?.tracks?.length ?? 0;

  return (
    <div className="mx-auto max-w-6xl space-y-8 px-8 py-10">
      <header className="flex items-start justify-between">
        <div className="space-y-1">
          <div className="text-[10px] font-semibold uppercase tracking-[0.2em] text-violet-400">
            Production
          </div>
          <h1 className="text-3xl font-bold tracking-tight">制作流水线</h1>
          <p className="text-sm text-zinc-500">
            素材导入 → 场景拆分 → 脚本生成 → 配音字幕 → 导出发布
          </p>
          <div className="flex items-center gap-3 pt-2 text-[10px] text-zinc-500">
            <Kbd>⌘R</Kbd>
            <span>启动</span>
            <Kbd>⌘.</Kbd>
            <span>取消</span>
          </div>

          {/* 素材计数 + 快速导入入口 */}
          {currentProject && (
            <div className="flex flex-wrap items-center gap-2 pt-3">
              <button
                type="button"
                onClick={() => setShowImport(true)}
                className="inline-flex items-center gap-2 rounded-md border border-blue-700/50 bg-blue-950/30 px-3 py-1.5 text-xs text-blue-200 transition hover:border-blue-500 hover:bg-blue-950/60"
              >
                📂 导入素材
                <span className="rounded bg-blue-500/30 px-1.5 py-0.5 font-mono text-[10px] text-blue-100">
                  {mediaCount}
                </span>
              </button>
              <button
                type="button"
                onClick={() => void navigate({ to: "/assets" })}
                className="inline-flex items-center gap-2 rounded-md border border-zinc-700 bg-zinc-900 px-3 py-1.5 text-xs text-zinc-200 transition hover:border-zinc-500"
              >
                📦 管理素材 → /assets
              </button>
              <span className="text-[10px] text-zinc-500">
                轨道 {trackCount} · 脚本 {currentProject.project.scripts.length}
              </span>
            </div>
          )}
        </div>
        <PipelineStateBadge state={pipeline.state} />
      </header>

      <StepFlow steps={stepsForView} activeIndex={pipeline.activeIndex} />

      {/* 进度条 */}
      <ProgressBar percent={percent} state={pipeline.state} />

      {/* 主控区 */}
      <section className="rounded-2xl border border-zinc-800 bg-zinc-900/40 p-6">
        {!currentProject ? (
          <EmptyProjectState
            loading={createProject.isPending}
            onCreate={() => createProject.mutate()}
            ffmpegOk={sysInfo.data?.ffmpegAvailable ?? false}
          />
        ) : (
          <RunningPanel
            projectName={currentProject.project.name}
            mediaCount={mediaCount}
            running={pipeline.state === "running"}
            done={pipeline.state === "done"}
            failed={pipeline.state === "failed"}
            onStart={handleStart}
            onCancel={handleCancel}
            onReset={handleReset}
            onRefresh={() => pipeline.refetch()}
            onOpenImport={() => setShowImport(true)}
            onManageAssets={() => void navigate({ to: "/assets" })}
          />
        )}
      </section>

      {/* M4.5: 多视频导出策略预览 (scenefab-video · video_build_plans) */}
      {currentProject && mediaCount > 0 && (
        <VideoPlanPreview
          mediaPaths={currentProject.project.media_files.map((m) => m.path)}
        />
      )}

      {/* 系统准备度 */}
      <section className="grid grid-cols-1 gap-3 md:grid-cols-4">
        <CapabilityCard
          label="素材"
          ready={mediaCount > 0}
          value={mediaCount > 0 ? `${mediaCount} 项` : "空"}
          hint={mediaCount > 0 ? "已就绪,可启动流水线" : "请先导入素材"}
        />
        <CapabilityCard
          label="FFmpeg"
          ready={sysInfo.data?.ffmpegAvailable ?? false}
          value={sysInfo.data?.ffmpegVersion ?? null}
          hint="视频处理 / 字幕烧录需要"
        />
        <CapabilityCard
          label="LLM"
          ready
          value="11 个 Provider"
          hint="Qwen / Claude / DeepSeek 等"
        />
        <CapabilityCard
          label="TTS"
          ready
          value="3 个引擎"
          hint="Edge / OpenAI / GPT-SoVITS"
        />
      </section>

      <BatchImportDialog
        open={showImport}
        onClose={() => setShowImport(false)}
        onImported={(count) => {
          toast.success(`已为流水线项目添加 ${count} 个素材`);
          setShowImport(false);
        }}
      />
    </div>
  );
}

// ── 子组件 ────────────────────────────────────────────────────────

function PipelineStateBadge({
  state,
}: {
  state: "idle" | "running" | "done" | "failed";
}) {
  const map = {
    idle: { bg: "bg-zinc-800/60", tx: "text-zinc-400", label: "空闲" },
    running: {
      bg: "bg-blue-500/20 animate-pulse",
      tx: "text-blue-200",
      label: "运行中",
    },
    done: { bg: "bg-emerald-500/20", tx: "text-emerald-300", label: "完成" },
    failed: { bg: "bg-rose-500/20", tx: "text-rose-300", label: "失败" },
  };
  const m = map[state];
  return (
    <span
      className={`inline-flex items-center gap-2 rounded-full px-3 py-1 text-xs font-medium ${m.bg} ${m.tx}`}
    >
      <span className="h-1.5 w-1.5 rounded-full bg-current" />
      {m.label}
    </span>
  );
}

function ProgressBar({
  percent,
  state,
}: {
  percent: number;
  state: "idle" | "running" | "done" | "failed";
}) {
  const tone =
    state === "done"
      ? "bg-emerald-400"
      : state === "failed"
        ? "bg-rose-400"
        : "bg-gradient-to-r from-blue-400 to-violet-400";
  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between text-[11px] text-zinc-500">
        <span>整体进度</span>
        <span className="font-mono">{percent}%</span>
      </div>
      <div className="h-2 overflow-hidden rounded-full bg-zinc-900/80">
        <div
          className={`h-full transition-all duration-500 ${tone}`}
          style={{ width: `${percent}%` }}
        />
      </div>
    </div>
  );
}

function EmptyProjectState({
  loading,
  onCreate,
  ffmpegOk,
}: {
  loading: boolean;
  onCreate: () => void;
  ffmpegOk: boolean;
}) {
  return (
    <div className="flex flex-col items-center gap-6 py-12 text-center">
      <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-blue-500/20 to-violet-500/20 text-3xl">
        🎬
      </div>
      <div className="space-y-2">
        <div className="text-lg font-semibold text-zinc-100">
          开始一个新项目
        </div>
        <div className="mx-auto max-w-md text-sm text-zinc-500">
          项目将保存到本机 appData/projects。你可以在素材页继续添加视频。
        </div>
      </div>
      <button
        type="button"
        onClick={onCreate}
        disabled={loading}
        className="rounded-xl bg-gradient-to-r from-blue-500 to-violet-500 px-8 py-3 text-sm font-semibold text-white shadow-lg shadow-blue-500/30 transition hover:shadow-blue-500/50 disabled:opacity-50"
      >
        {loading ? "创建中..." : "新建空白项目"}
      </button>
      {!ffmpegOk && (
        <div className="rounded-lg border border-amber-700/40 bg-amber-950/30 px-4 py-2 text-xs text-amber-300">
          ⚠ 未检测到 ffmpeg:导出与字幕烧录步骤将被跳过
        </div>
      )}
    </div>
  );
}

function RunningPanel({
  projectName,
  mediaCount,
  running,
  done,
  failed,
  onStart,
  onCancel,
  onReset,
  onRefresh,
  onOpenImport,
  onManageAssets,
}: {
  projectName: string;
  mediaCount: number;
  running: boolean;
  done: boolean;
  failed: boolean;
  onStart: () => void;
  onCancel: () => void;
  onReset: () => void;
  onRefresh: () => void;
  onOpenImport: () => void;
  onManageAssets: () => void;
}) {
  const noMedia = mediaCount === 0;
  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between rounded-xl border border-zinc-800 bg-zinc-950/60 px-4 py-3">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-gradient-to-br from-blue-500 to-violet-500 text-sm font-bold text-white">
            P
          </div>
          <div className="space-y-0.5">
            <div className="text-sm font-medium text-zinc-100">
              {projectName}
            </div>
            <div className="text-[11px] text-zinc-500">
              {mediaCount} 个素材 · 已加载到流水线运行时
            </div>
          </div>
        </div>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={onOpenImport}
            className="rounded-md border border-blue-700/50 bg-blue-950/30 px-3 py-1.5 text-xs text-blue-200 transition hover:border-blue-500 hover:bg-blue-950/60"
          >
            📂 导入更多
          </button>
          <button
            type="button"
            onClick={onRefresh}
            className="rounded-md border border-zinc-800 bg-zinc-900 px-3 py-1.5 text-xs text-zinc-300 hover:border-zinc-700"
          >
            刷新状态
          </button>
        </div>
      </div>

      {noMedia && (
        <div className="rounded-xl border border-amber-700/40 bg-amber-950/20 px-5 py-4">
          <div className="flex items-start gap-3">
            <div className="mt-0.5 text-2xl">🎞</div>
            <div className="flex-1 space-y-2">
              <div className="text-sm font-medium text-amber-100">
                项目当前没有素材
              </div>
              <div className="text-xs text-amber-200/80">
                在启动流水线之前,请先导入 1
                个或多个视频文件。可以批量扫描整个目录。
              </div>
              <div className="flex flex-wrap gap-2 pt-1">
                <button
                  type="button"
                  onClick={onOpenImport}
                  className="rounded-md bg-gradient-to-r from-blue-500 to-violet-500 px-4 py-1.5 text-xs font-semibold text-white shadow shadow-blue-500/30"
                >
                  📂 导入素材
                </button>
                <button
                  type="button"
                  onClick={onManageAssets}
                  className="rounded-md border border-amber-700/50 bg-zinc-900/40 px-4 py-1.5 text-xs text-amber-200 transition hover:border-amber-500"
                >
                  📦 前往素材管理
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {failed && (
        <div className="rounded-lg border border-rose-800/60 bg-rose-950/30 px-4 py-3 text-sm text-rose-200">
          流水线失败:某一步返回错误。重置后可重新启动。
        </div>
      )}
      {done && (
        <div className="rounded-lg border border-emerald-700/60 bg-emerald-950/30 px-4 py-3 text-sm text-emerald-200">
          ✓ 全部完成。导出文件已写到 /tmp/scenefab-workdir。
        </div>
      )}

      <div className="flex flex-wrap gap-3">
        <button
          type="button"
          onClick={onStart}
          disabled={running || noMedia}
          title={noMedia ? "需要先导入素材" : undefined}
          className="rounded-xl bg-gradient-to-r from-blue-500 to-violet-500 px-6 py-2.5 text-sm font-semibold text-white shadow-lg shadow-blue-500/30 transition disabled:opacity-40 disabled:shadow-none"
        >
          {running ? "运行中..." : done ? "重新启动" : "启动流水线"}
          <span className="ml-2 inline-block rounded border border-white/30 px-1 font-mono text-[10px]">
            ⌘R
          </span>
        </button>
        <button
          type="button"
          onClick={onCancel}
          disabled={!running}
          className="rounded-xl border border-zinc-700 bg-zinc-900 px-6 py-2.5 text-sm text-zinc-200 transition hover:border-zinc-500 disabled:opacity-40"
        >
          取消
          <span className="ml-2 inline-block rounded border border-zinc-700 px-1 font-mono text-[10px] text-zinc-500">
            ⌘.
          </span>
        </button>
        <button
          type="button"
          onClick={onReset}
          disabled={running}
          className="rounded-xl border border-zinc-800 bg-zinc-900/40 px-6 py-2.5 text-sm text-zinc-400 transition hover:border-zinc-700 hover:text-zinc-200 disabled:opacity-40"
        >
          重置
        </button>
      </div>
    </div>
  );
}

function CapabilityCard({
  label,
  ready,
  value,
  hint,
}: {
  label: string;
  ready: boolean;
  value: string | null;
  hint: string;
}) {
  return (
    <div
      className={`rounded-2xl border p-5 ${
        ready
          ? "border-emerald-700/40 bg-emerald-950/20"
          : "border-amber-800/40 bg-amber-950/20"
      }`}
    >
      <div className="flex items-center justify-between">
        <div className="text-xs uppercase tracking-wider text-zinc-500">
          {label}
        </div>
        <div
          className={`text-[10px] ${
            ready ? "text-emerald-400" : "text-amber-400"
          }`}
        >
          {ready ? "● 就绪" : "○ 缺失"}
        </div>
      </div>
      <div className="mt-3 truncate font-mono text-sm text-zinc-200">
        {value ?? "—"}
      </div>
      <div className="mt-1 text-[11px] text-zinc-500">{hint}</div>
    </div>
  );
}

function Kbd({ children }: { children: React.ReactNode }) {
  return (
    <kbd className="inline-flex h-5 min-w-5 items-center justify-center rounded-md border border-zinc-700 bg-zinc-900 px-1.5 font-mono text-[10px] text-zinc-400">
      {children}
    </kbd>
  );
}
