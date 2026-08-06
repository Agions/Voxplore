/**
 * Vynaro v1.0.0 · 制作流水线页 (与用户设计原图 100% 对齐)
 */

import { createFileRoute } from "@tanstack/react-router";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useCallback, useEffect, useState } from "react";
import { PipelineFlow, DEFAULT_PIPELINE_STEPS, type PipelineStep } from "@components/common/StepFlow";
import { BatchImportDialog } from "@components/dialogs/BatchImportDialog";
import { Step1IntakePanel } from "@components/production/Step1IntakePanel";
import { Step2DetectPanel } from "@components/production/Step2DetectPanel";
import { Step3ScriptPanel } from "@components/production/Step3ScriptPanel";
import { Step4VoicePanel } from "@components/production/Step4VoicePanel";
import { Step5SubtitlePanel } from "@components/production/Step5SubtitlePanel";
import { Step6ComposePanel } from "@components/production/Step6ComposePanel";
import { Step7ExportPanel } from "@components/production/Step7ExportPanel";
import {
  pipelineIpc,
  projectIpc,
  type ProjectRecord,
} from "@ipc/commands";
import type { StepStatus } from "@ipc/types.gen";
import { usePipeline, usePipelineHotkeys } from "@hooks/usePipeline";
import { useProjectStore } from "@stores/project-store";
import { toast } from "sonner";

export const Route = createFileRoute("/production")({
  component: ProductionPage,
});

function ProductionPage() {
  const qc = useQueryClient();
  const setCurrentRecord = useProjectStore((s) => s.setCurrentRecord);

  const { data: stepDefs } = useQuery({
    queryKey: ["pipeline-step-defs"],
    queryFn: pipelineIpc.stepDefs,
  });

  const pipeline = usePipeline(stepDefs ?? []);
  const [activeStepId, setActiveStepId] = useState<string>("intake");
  const [showImport, setShowImport] = useState(false);

  const currentProject =
    (qc.getQueryData(["current-project"]) as ProjectRecord | undefined) ?? null;

  // 自动恢复最近的项目，防止页面刷新或直接切路由导致项目视频丢失
  useEffect(() => {
    if (!currentProject) {
      void projectIpc.listRecent().then(async (recents) => {
        if (recents && recents.length > 0 && recents[0]) {
          try {
            const rec = await projectIpc.load(recents[0]);
            qc.setQueryData(["current-project"], rec);
            qc.setQueryData(["assets-current-project"], rec.project);
            setCurrentRecord(rec.path, rec.project);
          } catch {
            // ignore load error
          }
        }
      });
    }
  }, [currentProject, qc, setCurrentRecord]);

  const createProject = useMutation({
    mutationFn: projectIpc.createBlank,
    onSuccess: (rec) => {
      qc.setQueryData(["current-project"], rec);
      setCurrentRecord(rec.path, rec.project);
      setShowImport(true);
      toast.success("解说工程已建立，请在弹窗中选取视频素材文件夹");
    },
    onError: (e) => {
      toast.error("创建项目失败", { description: e instanceof Error ? e.message : String(e) });
    },
  });

  const handleStart = useCallback(() => {
    if (!currentProject) return;
    void pipeline.start(currentProject.project);
  }, [currentProject, pipeline]);

  const handleCancel = useCallback(() => {
    void pipeline.cancel();
  }, [pipeline]);

  usePipelineHotkeys(() => currentProject && handleStart(), handleCancel);

  const STEP_ICON: Record<string, string> = {
    intake: "📁", detect: "🎞️", script: "📝",
    voice: "🎙️", subtitle: "📝", compose: "🔀", export: "📤",
  };
  const baseSteps: PipelineStep[] = stepDefs && stepDefs.length > 0
    ? stepDefs.map((s, idx) => ({
        id: s.id,
        index: idx + 1,
        label: s.label_zh,
        labelEn: s.id,
        icon: STEP_ICON[s.id] ?? "📦",
        status: "pending" as const,
      }))
    : DEFAULT_PIPELINE_STEPS;

  const displaySteps: PipelineStep[] = baseSteps.map((step, idx) => {
    const backendStep = pipeline.steps[idx];
    const status = backendStep ? (backendStep.status as StepStatus) : step.status;
    return { ...step, status };
  });

  const mediaCount = currentProject?.project.media_files?.length ?? 0;

  const handleStepClick = (targetStep: PipelineStep) => {
    const stepIds = ["intake", "detect", "script", "voice", "subtitle", "compose", "export"];
    const targetIdx = stepIds.indexOf(targetStep.id);
    if (targetIdx <= 0) {
      setActiveStepId(targetStep.id);
      return;
    }

    // Guard 1: Step 2+ requires media file in Step 1
    if (mediaCount === 0) {
      toast.warning("请先在步骤 1 导入视频素材，再进行后续操作", {
        description: "点击「📂 导入素材」添加至少一个视频或音频文件",
      });
      return;
    }

    // Guard 2: Sequential step enforcement - check uncompleted prior step
    const priorSteps = displaySteps.slice(0, targetIdx);
    const uncompletedStep = priorSteps.find(
      (s) => s.status !== "done" && s.status !== "active"
    );

    if (uncompletedStep) {
      toast.warning(`请先完成步骤 ${uncompletedStep.index} (${uncompletedStep.label})，才能解锁此步骤`, {
        description: "7 步 AI 叙事流水线需按顺序逐步完成",
      });
      return;
    }

    setActiveStepId(targetStep.id);
  };

  const handleNextStep = () => {
    const stepIds = ["intake", "detect", "script", "voice", "subtitle", "compose", "export"];
    const currIdx = stepIds.indexOf(activeStepId);
    if (currIdx >= 0 && currIdx < stepIds.length - 1 && stepIds[currIdx + 1]) {
      const nextStepId = stepIds[currIdx + 1]!;
      const targetStep = displaySteps.find((s) => s.id === nextStepId);
      if (targetStep) {
        handleStepClick(targetStep);
      }
    }
  };

  return (
    <div className="mx-auto max-w-7xl px-8 py-6 space-y-6 flex flex-col min-h-screen">
      {/* 1. 页头 */}
      <header className="flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <h1 className="text-xl font-bold tracking-tight text-[var(--color-text-primary)]">
            7 步 AI 解说工作流水线
          </h1>
          <span className="text-xs text-[var(--color-text-muted)] bg-[var(--color-surface-elevated)] border border-[var(--color-border)] px-2.5 py-0.5 rounded-full font-mono">
            {currentProject ? currentProject.project.name || "当前解说工程" : "未打开工程"}
          </span>
        </div>

        <div className="flex items-center space-x-3">
          {!currentProject ? (
            <button
              type="button"
              onClick={() => createProject.mutate()}
              disabled={createProject.isPending}
              className="flex items-center space-x-1.5 rounded-xl bg-gradient-to-r from-[#F5C842] to-[#E8933A] px-4 py-2 text-xs font-bold text-zinc-950 shadow-[0_2px_10px_rgba(245,200,66,0.3)] transition hover:brightness-110"
            >
              <span>+</span>
              <span>新建解说工程</span>
            </button>
          ) : (
            <div className="flex items-center space-x-2">
              <button
                type="button"
                className="btn-secondary text-xs"
                onClick={() => {
                  if (currentProject) {
                    setCurrentRecord(currentProject.path, currentProject.project);
                  }
                  setShowImport(true);
                }}
              >
                📂 导入素材 ({mediaCount})
              </button>
              {pipeline.state === "running" ? (
                <button
                  type="button"
                  onClick={handleCancel}
                  className="rounded-xl border border-rose-500/50 bg-rose-500/10 px-4 py-2 text-xs font-bold text-rose-500 transition hover:bg-rose-500/20"
                >
                  ⏹ 终止/取消
                </button>
              ) : (
                <button
                  type="button"
                  className="flex items-center space-x-1.5 rounded-xl bg-gradient-to-r from-[#F5C842] to-[#E8933A] px-4 py-2 text-xs font-bold text-zinc-950 shadow-[0_2px_10px_rgba(245,200,66,0.3)] transition hover:brightness-110"
                  onClick={handleStart}
                >
                  <span>▶</span>
                  <span>启动 7 步全自动流水线</span>
                </button>
              )}
            </div>
          )}
        </div>
      </header>

      {/* 2. 7 步卡片式流水线组件 */}
      <PipelineFlow
        steps={displaySteps}
        activeStepId={activeStepId}
        onStepClick={handleStepClick}
      />

      {/* 3. 步骤详情展开面板 */}
      <main className="flex-1 min-h-[360px] rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)] p-6 shadow-xl">
        {activeStepId === "intake" && (
          <Step1IntakePanel
            mediaCount={mediaCount}
            onImportClick={() => {
              if (currentProject) {
                setCurrentRecord(currentProject.path, currentProject.project);
              }
              setShowImport(true);
            }}
            onNext={handleNextStep}
          />
        )}

        {activeStepId === "detect" && (
          <Step2DetectPanel onNext={handleNextStep} />
        )}

        {activeStepId === "script" && (
          <Step3ScriptPanel onNext={handleNextStep} />
        )}

        {activeStepId === "voice" && (
          <Step4VoicePanel onNext={handleNextStep} />
        )}

        {activeStepId === "subtitle" && (
          <Step5SubtitlePanel onNext={handleNextStep} />
        )}

        {activeStepId === "compose" && (
          <Step6ComposePanel onNext={handleNextStep} />
        )}

        {activeStepId === "export" && (
          <Step7ExportPanel />
        )}
      </main>

      {/* 4. 底部长条进度条 + Log 输出面板 (对齐设计原图底部) */}
      <footer className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2">
        {/* 左侧金光长进度条 */}
        <div className="flex flex-col justify-center space-y-2 rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)] p-4">
          <div className="flex items-center justify-between text-xs font-mono text-[var(--color-text-secondary)]">
            <span>流水线处理进度</span>
            <span className="font-bold text-[var(--color-gold)]">
              {pipeline.state === "running" ? `${pipeline.percent}%` : "100% 已就绪"}
            </span>
          </div>
          <div className="h-3.5 w-full overflow-hidden rounded-full bg-zinc-900 border border-[var(--color-border)] p-0.5">
            <div
              className="h-full rounded-full bg-gradient-to-r from-[#F5C842] via-[#F9D76B] to-[#E8933A] shadow-[0_0_12px_rgba(245,200,66,0.5)] transition-all duration-500"
              style={{ width: `${pipeline.state === "running" ? pipeline.percent : 70}%` }}
            />
          </div>
        </div>

        {/* 右侧 Log 日志终端面板 */}
        <div className="flex flex-col space-y-2 rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)] p-4">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-[var(--color-text-primary)]">Log 运行控制台</span>
            <select className="py-0.5 px-2 text-[10px] bg-zinc-900 rounded border border-zinc-800 text-zinc-400">
              <option>All Logs</option>
              <option>Errors Only</option>
            </select>
          </div>
          <div className="h-12 w-full overflow-y-auto rounded-xl bg-zinc-950/80 p-2 font-mono text-[11px] text-zinc-400 border border-zinc-800/80">
            <p className="text-emerald-400">[SYSTEM] Pipeline initialized. Ready to process video intake...</p>
            <p className="text-zinc-500">[INFO] Waiting for user action or next step trigger.</p>
          </div>
        </div>
      </footer>

      {/* 批量导入弹窗 */}
      {showImport && (
        <BatchImportDialog
          open={showImport}
          onClose={() => setShowImport(false)}
        />
      )}
    </div>
  );
}
