/**
 * Vynaro v2.5.0 · 7步工作流卡片式流水线
 *
 * 电影调光室主题：深色底 + 暖金高亮
 * 每个 Step 是一个独立卡片，点击展开详情面板
 */

import type { StepStatus } from "@ipc/types.gen";
import React from "react";

// ── 工作流步骤定义 ──────────────────────────────
export interface PipelineStep {
  id: string;
  index: number;       // 1-7
  label: string;       // 中文名
  labelEn: string;     // 英文副标题
  icon: string;        // emoji 图标
  status: StepStatus;
  statusText?: string; // 自定义状态文字（如"8段 / 已分析"）
}

interface PipelineCardProps {
  step: PipelineStep;
  isActive: boolean;
  onClick: () => void;
}

// ── 状态配置 ───────────────────────────────────
const STATUS_CONFIG: Record<
  StepStatus,
  { color: string; bg: string; border: string; shadow: string; label: string; dot: string }
> = {
  pending: {
    color:  "var(--color-text-muted)",
    bg:     "transparent",
    border: "var(--color-border)",
    shadow: "none",
    label:  "待开始",
    dot:    "var(--color-text-muted)",
  },
  active: {
    color:  "#60A5FA",
    bg:     "rgba(96,165,250,0.08)",
    border: "rgba(96,165,250,0.4)",
    shadow: "0 0 16px rgba(96,165,250,0.15)",
    label:  "处理中",
    dot:    "#60A5FA",
  },
  done: {
    color:  "#4ADE80",
    bg:     "rgba(74,222,128,0.06)",
    border: "rgba(74,222,128,0.35)",
    shadow: "none",
    label:  "已完成",
    dot:    "#4ADE80",
  },
  error: {
    color:  "#F87171",
    bg:     "rgba(248,113,113,0.08)",
    border: "rgba(248,113,113,0.4)",
    shadow: "0 0 16px rgba(248,113,113,0.12)",
    label:  "出错",
    dot:    "#F87171",
  },
};

// ── 单张流水线卡片 ─────────────────────────────
function PipelineCard({ step, isActive, onClick }: PipelineCardProps) {
  const cfg = STATUS_CONFIG[step.status];
  const [hovered, setHovered] = React.useState(false);

  const borderColor = isActive
    ? "var(--color-gold)"
    : hovered
    ? "rgba(245,200,66,0.3)"
    : cfg.border;

  const boxShadow = isActive
    ? "0 0 24px rgba(245,200,66,0.20), 0 0 1px rgba(0,0,0,0.8)"
    : hovered
    ? "0 4px 16px rgba(0,0,0,0.4)"
    : cfg.shadow;

  return (
    <button
      type="button"
      id={`pipeline-card-step-${step.index}`}
      onClick={onClick}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        gap: "12px",
        padding: "18px 14px 14px",
        minWidth: "156px",
        background: isActive
          ? "rgba(245,200,66,0.04)"
          : hovered
          ? "var(--color-surface-elevated)"
          : "var(--color-surface)",
        border: `1px solid ${borderColor}`,
        borderRadius: "14px",
        cursor: "pointer",
        transition: "all 200ms cubic-bezier(0.4,0,0.2,1)",
        boxShadow,
        transform: hovered && !isActive ? "translateY(-2px)" : "none",
        position: "relative",
        textAlign: "center",
        flexShrink: 0,
      }}
      aria-pressed={isActive}
      aria-label={`步骤 ${step.index}: ${step.label}`}
    >
      {/* 步骤编号 */}
      <span
        style={{
          position: "absolute",
          top: "10px",
          left: "12px",
          fontSize: "11px",
          fontWeight: 600,
          color: isActive ? "var(--color-gold)" : "var(--color-text-muted)",
          letterSpacing: "0.04em",
        }}
      >
        {step.index}
      </span>

      {/* 状态点 */}
      <span
        style={{
          position: "absolute",
          top: "12px",
          right: "12px",
          width: "7px",
          height: "7px",
          borderRadius: "50%",
          background: cfg.dot,
          boxShadow: step.status === "active"
            ? `0 0 6px ${cfg.dot}`
            : step.status === "done"
            ? `0 0 4px ${cfg.dot}`
            : "none",
        }}
      />

      {/* 主图标 */}
      <div
        style={{
          width: 48,
          height: 48,
          borderRadius: "12px",
          background: isActive ? "rgba(245,200,66,0.10)" : "var(--color-bg)",
          border: `1px solid ${isActive ? "rgba(245,200,66,0.25)" : "var(--color-border)"}`,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          fontSize: "22px",
          transition: "all 200ms ease",
        }}
      >
        {step.icon}
      </div>

      {/* 文字区 */}
      <div style={{ lineHeight: 1.3 }}>
        <div
          style={{
            fontSize: "14px",
            fontWeight: 600,
            color: isActive ? "var(--color-gold)" : "var(--color-text-primary)",
            marginBottom: "3px",
          }}
        >
          {step.label}
        </div>
        <div
          style={{
            fontSize: "11px",
            color: "var(--color-text-muted)",
            letterSpacing: "0.04em",
          }}
        >
          {step.labelEn}
        </div>
      </div>

      {/* 状态文字 */}
      <div
        style={{
          fontSize: "11px",
          fontWeight: 500,
          color: cfg.color,
          background: cfg.bg,
          border: `1px solid ${cfg.border}`,
          borderRadius: "999px",
          padding: "3px 10px",
          width: "100%",
          textAlign: "center",
        }}
      >
        {step.status === "active" && "⚡ "}
        {step.status === "done" && "✓ "}
        {step.status === "error" && "✕ "}
        {step.statusText ?? cfg.label}
      </div>

      {/* 活跃时背景光晕 */}
      {step.status === "active" && (
        <div
          style={{
            position: "absolute",
            inset: 0,
            borderRadius: "14px",
            background: "rgba(96,165,250,0.03)",
            animation: "pulse 2s ease-in-out infinite",
          }}
        />
      )}
    </button>
  );
}

// ── 连接箭头 ───────────────────────────────────
function Arrow({ lit }: { lit: boolean }) {
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        padding: "0 2px",
        flexShrink: 0,
      }}
      aria-hidden="true"
    >
      <svg width="20" height="12" viewBox="0 0 20 12" fill="none">
        <path
          d="M0 6 H14 M10 2 L18 6 L10 10"
          stroke={lit ? "#4ADE80" : "var(--color-border)"}
          strokeWidth="1.5"
          strokeLinecap="round"
          strokeLinejoin="round"
          style={{ transition: "stroke 400ms ease" }}
        />
      </svg>
    </div>
  );
}

// ── 主流水线组件 ───────────────────────────────
export interface PipelineFlowProps {
  steps: PipelineStep[];
  activeStepId: string | null;
  onStepClick: (step: PipelineStep) => void;
}

export function PipelineFlow({ steps, activeStepId, onStepClick }: PipelineFlowProps) {
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: "4px",
        padding: "0 4px",
        overflowX: "auto",
        scrollbarWidth: "none",
      }}
      role="list"
      aria-label="影视解说工作流步骤"
    >
      {steps.map((step, idx) => {
        const isLast = idx === steps.length - 1;
        const prevDone = idx > 0 && steps[idx - 1]?.status === "done";
        return (
          <React.Fragment key={step.id}>
            <div role="listitem">
              <PipelineCard
                step={step}
                isActive={step.id === activeStepId}
                onClick={() => onStepClick(step)}
              />
            </div>
            {!isLast && <Arrow lit={prevDone || step.status === "done"} />}
          </React.Fragment>
        );
      })}
    </div>
  );
}

// ── 默认 7 步工作流配置 ────────────────────────
export const DEFAULT_PIPELINE_STEPS: PipelineStep[] = [
  { id: "intake",   index: 1, label: "素材导入", labelEn: "Media Import",    icon: "📥", status: "pending" },
  { id: "detect",   index: 2, label: "智能拆条", labelEn: "Scene Detection", icon: "✂️", status: "pending" },
  { id: "script",   index: 3, label: "脚本生成", labelEn: "Script Gen",      icon: "🤖", status: "pending" },
  { id: "voice",    index: 4, label: "TTS配音",  labelEn: "Voice Synth",     icon: "🎙️", status: "pending" },
  { id: "subtitle", index: 5, label: "字幕合成", labelEn: "Subtitles",       icon: "📝", status: "pending" },
  { id: "compose",  index: 6, label: "画面对齐", labelEn: "Compose & Sync",  icon: "🎬", status: "pending" },
  { id: "export",   index: 7, label: "导出发布", labelEn: "Export",          icon: "📤", status: "pending" },
];

// ── 向后兼容 StepFlow 导出 ──────────────────────
export interface StepFlowStep {
  id: string;
  label: string;
  icon: string;
  status: StepStatus;
}

export interface StepFlowProps {
  steps: StepFlowStep[];
  activeIndex?: number;
  onStepClick?: (stepId: string) => void;
}

export function StepFlow({ steps, activeIndex = -1, onStepClick }: StepFlowProps) {
  const convertedSteps: PipelineStep[] = steps.map((s, idx) => ({
    id: s.id,
    index: idx + 1,
    label: s.label,
    labelEn: `Step ${idx + 1}`,
    icon: s.icon,
    status: s.status,
  }));

  const activeStepId = activeIndex >= 0 && activeIndex < steps.length ? (steps[activeIndex]?.id ?? null) : null;

  return (
    <PipelineFlow
      steps={convertedSteps}
      activeStepId={activeStepId}
      onStepClick={(step) => onStepClick?.(step.id)}
    />
  );
}

