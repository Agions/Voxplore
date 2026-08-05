/**
 * SceneFab v2.5.0 · 5 步流水线可视化组件
 *
 * 视觉化:每个步骤是一个图标卡 + 当前态指示
 * 不堆砌文字,只通过颜色 / 动画传递状态。
 */

import type { StepStatus } from "@ipc/types.gen";

export interface StepFlowStep {
  id: string;
  label: string;
  icon: string;
  status: StepStatus;
}

interface StepFlowProps {
  steps: StepFlowStep[];
  /** 当前执行步索引 (-1 表示都未开始) */
  activeIndex: number;
}

const STATUS_STYLES: Record<
  StepStatus,
  {
    badge: string;
    border: string;
    glow: string;
    ring: string;
    icon: string;
    label: string;
  }
> = {
  pending: {
    badge: "bg-zinc-800/60 text-zinc-500",
    border: "border-zinc-800",
    glow: "",
    ring: "ring-zinc-800/40",
    icon: "○",
    label: "待执行",
  },
  active: {
    badge: "bg-blue-500/20 text-blue-300",
    border: "border-blue-500/60",
    glow: "shadow-lg shadow-blue-500/30",
    ring: "ring-blue-500/40",
    icon: "▶",
    label: "执行中",
  },
  done: {
    badge: "bg-emerald-500/20 text-emerald-300",
    border: "border-emerald-500/50",
    glow: "",
    ring: "ring-emerald-500/30",
    icon: "✓",
    label: "已完成",
  },
  error: {
    badge: "bg-rose-500/20 text-rose-300",
    border: "border-rose-500/60",
    glow: "shadow-lg shadow-rose-500/30",
    ring: "ring-rose-500/40",
    icon: "✕",
    label: "失败",
  },
};

export function StepFlow({ steps, activeIndex }: StepFlowProps) {
  return (
    <ol className="flex w-full items-stretch gap-3">
      {steps.map((step, idx) => {
        const s = STATUS_STYLES[step.status];
        const isLast = idx === steps.length - 1;
        const next = !isLast ? steps[idx + 1] : undefined;
        const connecting =
          !isLast &&
          (step.status === "done" ||
            (activeIndex >= 0 &&
              idx < activeIndex &&
              next !== undefined &&
              next.status !== "pending"));
        return (
          <li key={step.id} className="relative flex flex-1 items-center">
            <div
              className={`flex w-full flex-col items-center gap-2 rounded-2xl border bg-zinc-900/50 p-4 text-center transition-all ${s.border} ${s.glow}`}
            >
              <div
                className={`relative flex h-12 w-12 items-center justify-center rounded-full bg-zinc-950 ring-2 ${s.ring}`}
              >
                <span className="text-xl">{step.icon}</span>
                <span
                  className={`absolute -bottom-1 -right-1 flex h-5 w-5 items-center justify-center rounded-full text-[10px] font-bold ${s.badge}`}
                >
                  {s.icon}
                </span>
              </div>
              <div className="space-y-0.5">
                <div className="text-sm font-medium text-zinc-100">
                  {step.label}
                </div>
                <div className="text-[10px] uppercase tracking-wider text-zinc-500">
                  {s.label}
                </div>
              </div>
              {step.status === "active" && (
                <div className="absolute inset-0 -z-10 animate-pulse rounded-2xl bg-blue-500/5" />
              )}
            </div>
            {!isLast && (
              <div className="absolute left-full top-1/2 z-10 -translate-y-1/2 px-1">
                <div
                  className={`h-0.5 w-3 transition-colors ${
                    connecting ? "bg-emerald-500" : "bg-zinc-800"
                  }`}
                />
              </div>
            )}
          </li>
        );
      })}
    </ol>
  );
}
