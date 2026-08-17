/**
 * splicr v1.0.0 · 7 步卡片式全自动解说工作流 (根据用户设计原图 100% 对齐重构)
 *
 * 对应设计图 7 步垂直高保真卡片:
 * 1. 素材导入 (Media) -> 包含视频预览帧与绿色 ✓ 完成角标
 * 2. 智能拆条 (Scene Detection) -> 包含蓝色 ⚡ Processing 动态脉冲
 * 3. 脚本生成 (Script Gen) -> 包含机器人 🤖 Generating
 * 4. TTS配音 (Voice) -> 包含金色动态音频波形 🎚️
 * 5. 字幕合成 (Subtitles) -> 屏幕字幕图标
 * 6. 画面对齐 (Sync) -> 轴向对齐图标
 * 7. 导出 (Export) -> 包含多平台社交图标
 */

import type { StepStatus } from "@ipc/types.gen";

export interface PipelineStep {
  id: string;
  index: number;
  label: string;
  labelEn: string;
  icon: string;
  status: StepStatus;
  statusText?: string;
  thumbnail?: string;
}

interface PipelineCardProps {
  step: PipelineStep;
  isActive: boolean;
  onClick: () => void;
}

export function PipelineCard({ step, isActive, onClick }: PipelineCardProps) {
  const isDone = step.status === "done";
  const isProcessing = step.status === "active";

  return (
    <div
      onClick={onClick}
      className={`group relative flex flex-col justify-between items-center flex-1 min-w-[152px] h-[340px] cursor-pointer rounded-2xl border p-4 transition-all duration-300 select-none ${
        isActive
          ? "border-[var(--color-gold)] bg-[var(--color-surface)] shadow-[0_0_24px_var(--color-gold-glow)] scale-[1.02]"
          : isDone
            ? "border-[var(--color-gold)]/40 bg-[var(--color-surface)] hover:border-[var(--color-gold)]/80"
            : "border-[var(--color-border)] bg-[var(--color-surface)]/60 hover:border-[var(--color-border)]/80"
      }`}
    >
      {/* 1. 顶部 Header (序号 + 完成绿勾) */}
      <div className="flex w-full items-center justify-between">
        <span
          className={`font-mono text-xs font-bold ${
            isActive ? "text-[var(--color-gold)]" : "text-[var(--color-text-muted)]"
          }`}
        >
          {step.index}
        </span>
        {isDone && (
          <span className="flex h-5 w-5 items-center justify-center rounded-full bg-emerald-500 text-zinc-950 font-black text-xs shadow-md">
            ✓
          </span>
        )}
      </div>

      {/* 2. 中央大图标与标题 */}
      <div className="flex flex-col items-center space-y-2 text-center my-1">
        <div
          className={`flex h-14 w-14 items-center justify-center rounded-2xl border transition-transform duration-200 group-hover:scale-110 ${
            isActive || isDone
              ? "border-[var(--color-gold)]/30 bg-[var(--color-gold-muted)] text-[var(--color-gold)] shadow-md"
              : "border-[var(--color-border)] bg-[var(--color-surface-elevated)] text-[var(--color-text-secondary)]"
          }`}
        >
          <span className="text-2xl">{step.icon}</span>
        </div>

        <div className="space-y-0.5">
          <h3 className="text-sm font-extrabold tracking-tight text-[var(--color-text-primary)]">
            {step.label}
          </h3>
          <p className="text-[11px] font-medium text-[var(--color-text-muted)] tracking-wide">
            {step.labelEn}
          </p>
        </div>
      </div>

      {/* 3. 卡片内部动态内容插槽 (对应设计原图) */}
      <div className="flex h-20 w-full items-center justify-center overflow-hidden rounded-xl border border-[var(--color-border)] bg-[var(--color-surface-elevated)]/60 p-2 my-1">
        {step.index === 1 && (
          <div className="relative flex h-full w-full items-center justify-center overflow-hidden rounded-lg bg-zinc-950 border border-zinc-800">
            <img
              src="https://images.unsplash.com/photo-1536440136628-849c177e76a1?w=300&q=80"
              alt="Video Preview"
              className="h-full w-full object-cover opacity-80"
            />
            <div className="absolute flex h-6 w-6 items-center justify-center rounded-full bg-[var(--color-gold)] text-zinc-950 text-xs font-bold shadow-md">
              ▶
            </div>
          </div>
        )}

        {step.index === 2 && (
          <div className="flex flex-col items-center space-y-1 text-center">
            <div className="flex h-8 w-8 items-center justify-center rounded-full bg-blue-500/20 text-blue-400 animate-pulse text-lg">
              ⚡
            </div>
            <span className="text-[10px] font-mono text-blue-400 font-semibold">
              {isProcessing ? "Processing..." : "Ready"}
            </span>
          </div>
        )}

        {step.index === 3 && (
          <div className="flex flex-col items-center space-y-1 text-center">
            <div className="text-xl">🤖</div>
            <span className="rounded-full bg-zinc-800 px-2 py-0.5 text-[9px] font-mono text-zinc-300">
              Generating
            </span>
          </div>
        )}

        {step.index === 4 && (
          <div className="flex items-center space-x-1">
            <div className="h-6 w-1 rounded bg-[var(--color-gold)] animate-pulse" />
            <div className="h-10 w-1 rounded bg-[var(--color-gold)] animate-pulse delay-75" />
            <div className="h-4 w-1 rounded bg-[var(--color-gold)] animate-pulse delay-150" />
            <div className="h-8 w-1 rounded bg-[var(--color-gold)] animate-pulse delay-200" />
            <div className="h-5 w-1 rounded bg-[var(--color-gold)]" />
          </div>
        )}

        {step.index === 5 && (
          <div className="flex flex-col items-center space-y-1">
            <div className="text-lg">📝</div>
            <span className="text-[9px] font-mono text-[var(--color-text-muted)]">
              VAD Auto Align
            </span>
          </div>
        )}

        {step.index === 6 && (
          <div className="flex items-center space-x-2 text-lg text-[var(--color-gold)]">
            <span>🎬</span>
            <span>🔀</span>
            <span>🎵</span>
          </div>
        )}

        {step.index === 7 && (
          <div className="grid grid-cols-2 gap-1 text-center text-xs">
            <span className="rounded bg-zinc-800/80 p-1">🎵</span>
            <span className="rounded bg-zinc-800/80 p-1">📹</span>
            <span className="rounded bg-zinc-800/80 p-1">🔴</span>
            <span className="rounded bg-zinc-800/80 p-1">✂️</span>
          </div>
        )}
      </div>

      {/* 4. 底部金色 Pill 按钮 */}
      <button
        type="button"
        className="w-full rounded-xl bg-gradient-to-r from-[#F5C842] to-[#E8933A] py-2 text-xs font-black text-zinc-950 shadow-[0_2px_10px_rgba(245,200,66,0.3)] transition-all duration-200 hover:brightness-110 hover:shadow-[0_4px_16px_rgba(245,200,66,0.5)]"
      >
        {step.label}
      </button>
    </div>
  );
}

// ── 7 步卡片横向排列容器 ──────────────────────────────────────────

export function PipelineFlow({
  steps,
  activeStepId,
  onStepClick,
}: {
  steps: PipelineStep[];
  activeStepId: string | null;
  onStepClick: (step: PipelineStep) => void;
}) {
  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 md:grid-cols-4 lg:grid-cols-7 w-full py-2">
      {steps.map((step) => (
        <PipelineCard
          key={step.id}
          step={step}
          isActive={step.id === activeStepId}
          onClick={() => onStepClick(step)}
        />
      ))}
    </div>
  );
}

export const DEFAULT_PIPELINE_STEPS: PipelineStep[] = [
  { id: "intake",   index: 1, label: "素材导入", labelEn: "Media",           icon: "📁", status: "done" },
  { id: "detect",   index: 2, label: "智能拆条", labelEn: "Scene Detection", icon: "🎞️", status: "active" },
  { id: "script",   index: 3, label: "脚本生成", labelEn: "Script Gen",      icon: "📝", status: "pending" },
  { id: "voice",    index: 4, label: "TTS配音",  labelEn: "Voice",           icon: "🎙️", status: "pending" },
  { id: "subtitle", index: 5, label: "字幕合成", labelEn: "Subtitles",       icon: "📝", status: "pending" },
  { id: "compose",  index: 6, label: "画面对齐", labelEn: "Sync",            icon: "🔀", status: "pending" },
  { id: "export",   index: 7, label: "导出",     labelEn: "Export",          icon: "📤", status: "pending" },
];
