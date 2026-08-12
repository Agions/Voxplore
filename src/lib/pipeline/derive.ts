/**
 * Vynaro v1.0.0 · 流水线状态派生 (纯函数,可单测)
 *
 * 设计:
 * - 不依赖 React / IPC / Store
 * - 由 usePipeline.ts 调用,也由测试单独验证
 * - 输入是后端 PipelineStatus + 前端 stepDefs,输出是 UI 直接消费的视图
 */

import type { PipelineState, PipelineStatus, StepStatus } from "@ipc/types.gen";

export interface PipelineStepView {
  id: string;
  label: string;
  status: StepStatus;
}

/** 简化的 step 定义 (usePipeline 入参只需要 id + label_zh) */
export interface StepDefLike {
  id: string;
  label_zh: string;
}

/**
 * 把 stepDefs 与后端 status 合并成 UI 用的 PipelineStepView 数组
 * - 后端缺数据 → 视为 "pending"
 * - 后端返回的 stepStatuses 数组比 defs 长 → 多余项截断
 * - 后端返回的数组比 defs 短 → 缺的视为 "pending"
 */
export function deriveSteps(
  stepDefs: StepDefLike[],
  status: PipelineStatus | null | undefined,
): PipelineStepView[] {
  return stepDefs.map((def, idx) => ({
    id: def.id,
    label: def.label_zh,
    status: (status?.stepStatuses?.[idx] ?? "pending") as StepStatus,
  }));
}

/** 找到第一个 status === "active" 的 step index (无 → -1) */
export function findActiveIndex(steps: PipelineStepView[]): number {
  return steps.findIndex((s) => s.status === "active");
}

/**
 * 计算整体进度百分比 (done 步骤数 / 总步骤数)
 * - totalSteps <= 0 时除数取 1,避免 NaN
 * - 返回 0-100 整数
 */
export function computePercent(
  status: PipelineStatus | null | undefined,
  totalSteps: number,
): number {
  const doneCount = (status?.stepStatuses ?? []).filter(
    (s) => s === "done",
  ).length;
  return Math.round((doneCount / Math.max(totalSteps, 1)) * 100);
}

/** PipelineState → 用户友好的中文标签 */
const PIPELINE_STATE_LABEL: Record<PipelineState, string> = {
  idle: "空闲",
  running: "运行中",
  done: "已完成",
  failed: "失败",
};

export function pipelineStateLabel(state: PipelineState): string {
  return PIPELINE_STATE_LABEL[state];
}

/** StepStatus → 中文标签 */
const STEP_STATUS_LABEL: Record<StepStatus, string> = {
  pending: "待执行",
  active: "执行中",
  done: "已完成",
  error: "失败",
};

export function stepStatusLabel(status: StepStatus): string {
  return STEP_STATUS_LABEL[status];
}
