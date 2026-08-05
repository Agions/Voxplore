/**
 * Vynaro v2.5.0 · 制作流水线页 (电影调光室主题 + 7 步详情面板)
 */

import { createFileRoute } from "@tanstack/react-router";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useCallback, useState } from "react";
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

  const createProject = useMutation({
    mutationFn: projectIpc.createBlank,
    onSuccess: (rec) => {
      // 同步到 QueryClient 缓存
      qc.setQueryData(["current-project"], rec);
      // ✅ 关键修复: 同步 project + currentPath 到 useProjectStore
      // path 先, project 后 (setCurrentRecord 签名: path, project)
      setCurrentRecord(rec.path, rec.project);
      // 创建成功后自动弹出导入对话框
      setShowImport(true);
      toast.success("项目已创建，请选择目录导入素材");
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

  // 将 IPC stepDefs 与真实 pipeline 运行状态联动。
  // 若 IPC 数据尚未加载，则回退到内置默认配置。
  const STEP_ICON: Record<string, string> = {
    intake: "📥", detect: "✂️", script: "🤖",
    voice: "🎙️", subtitle: "📝", compose: "🎬", export: "📤",
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

  const handleNextStep = () => {
    const stepIds = ["intake", "detect", "script", "voice", "subtitle", "compose", "export"];
    const currIdx = stepIds.indexOf(activeStepId);
    if (currIdx >= 0 && currIdx < stepIds.length - 1 && stepIds[currIdx + 1]) {
      setActiveStepId(stepIds[currIdx + 1]!);
    }
  };

  return (
    <div style={{ maxWidth: "1200px", margin: "0 auto", padding: "32px 24px", display: "flex", flexDirection: "column", gap: "28px" }}>
      {/* 页头导航信息 */}
      <header style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
        <div>
          <div style={{ fontSize: "11px", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.15em", color: "#F5C842", marginBottom: "4px" }}>
            Vynaro Pipeline
          </div>
          <h1 style={{ fontSize: "26px", fontWeight: 700, color: "#F0EDE8", margin: "0 0 6px" }}>
            第一人称解说创作流水线
          </h1>
          <p style={{ fontSize: "13px", color: "#8A8680", margin: 0 }}>
            素材导入 → 智能拆条 → AI脚本 → TTS配音 → 字幕合成 → 画面对齐 → 平台导出
          </p>
        </div>

        <div style={{ display: "flex", gap: "10px", alignItems: "center" }}>
          {!currentProject ? (
            <button
              type="button"
              className="btn-primary"
              onClick={() => createProject.mutate()}
              disabled={createProject.isPending}
            >
              ➕ 创建新解说项目
            </button>
          ) : (
            <div style={{ display: "flex", gap: "8px" }}>
              <button type="button" className="btn-secondary" onClick={() => {
                // 确保已有项目的 path 也同步到 project-store
                if (currentProject) {
                  setCurrentRecord(currentProject.path, currentProject.project);
                }
                setShowImport(true);
              }}>
                📂 导入素材 ({mediaCount})
              </button>
              {pipeline.state === "running" ? (
                <button
                  type="button"
                  onClick={handleCancel}
                  style={{
                    background: "rgba(239, 68, 68, 0.15)",
                    border: "1px solid #EF4444",
                    color: "#EF4444",
                    fontWeight: 700,
                    borderRadius: "8px",
                    padding: "8px 16px",
                    fontSize: "13px",
                    cursor: "pointer",
                  }}
                >
                  ⏹ 终止/取消流水线
                </button>
              ) : (
                <button
                  type="button"
                  className="btn-primary"
                  onClick={handleStart}
                >
                  ▶ 启动 7 步自动流水线
                </button>
              )}
            </div>
          )}
        </div>
      </header>

      {/* 7 步卡片式流水线组件 (Cinematic Darkroom Style) */}
      <PipelineFlow
        steps={displaySteps}
        activeStepId={activeStepId}
        onStepClick={(step) => setActiveStepId(step.id)}
      />

      {/* 步骤详情展开面板 */}
      <main style={{ minHeight: "420px" }}>
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
