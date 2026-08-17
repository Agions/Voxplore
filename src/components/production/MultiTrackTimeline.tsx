/**
 * Vynaro v1.0.0 · 全景多轨生产时间轴组件 (MultiTrackTimeline)
 * 
 * 特性:
 * - 5 轨全景编排 (视频切片轨、黄金前3秒高光轨、第一人称配音轨、花字字幕轨、动态闪避 BGM 轨)
 * - 毫秒级时间标尺与可拖拽播放指针 (Playhead Scrubber)
 * - 情绪峰值卡点指示 (Emotional Arc Beat Indicator)
 */

import { useState, useRef } from "react";

interface MultiTrackTimelineProps {
  durationSeconds?: number;
  currentTime?: number;
  isPlaying?: boolean;
  onSeek?: (time: number) => void;
  videoClips?: { id: string; title: string; start: number; duration: number; emotion?: string }[];
  hookClip?: { title: string; start: number; duration: number; style: string } | null;
  voiceClips?: { id: string; text: string; start: number; duration: number }[];
  subtitleClips?: { id: string; text: string; start: number; duration: number }[];
  bgmMixRatio?: number;
  autoDucking?: boolean;
  onDuckingChange?: (enabled: boolean) => void;
}

export function MultiTrackTimeline({
  durationSeconds = 60,
  currentTime = 0,
  isPlaying = false,
  onSeek,
  videoClips = [
    { id: "v1", title: "Shot 01 · 身份反转", start: 0, duration: 4.5, emotion: "激烈冲突" },
    { id: "v2", title: "Shot 02 · 悬念对峙", start: 4.5, duration: 8.0, emotion: "紧张悬疑" },
    { id: "v3", title: "Shot 03 · 战神归来", start: 12.5, duration: 15.0, emotion: "情绪高潮" },
  ],
  hookClip = { title: "🔥 黄金前3秒高潮前置", start: 0, duration: 3.5, style: "战神反转" },
  voiceClips = [
    { id: "a1", text: "如果不是亲眼所见，谁敢相信眼前这个平平无奇的外卖员...", start: 0, duration: 3.8 },
    { id: "a2", text: "三年隐忍，今日豪门家主亲自下跪相迎！", start: 4.5, duration: 7.2 },
  ],
  subtitleClips = [
    { id: "s1", text: "如果不是亲眼所见", start: 0, duration: 1.8 },
    { id: "s2", text: "谁敢相信眼前这个平平无奇的外卖员", start: 1.8, duration: 2.0 },
    { id: "s3", text: "三年隐忍，今日豪门家主亲自下跪相迎！", start: 4.5, duration: 7.2 },
  ],
  bgmMixRatio = 18,
  autoDucking = true,
  onDuckingChange,
}: MultiTrackTimelineProps) {
  const [zoomLevel, setZoomLevel] = useState(1);
  const containerRef = useRef<HTMLDivElement | null>(null);

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    const ms = Math.floor((seconds % 1) * 10);
    return `${String(mins).padStart(2, "0")}:${String(secs).padStart(2, "0")}.${ms}`;
  };

  const handleTimelineClick = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!containerRef.current || !onSeek) return;
    const rect = containerRef.current.getBoundingClientRect();
    const clickX = e.clientX - rect.left;
    const totalWidth = rect.width;
    const targetTime = Math.max(0, Math.min(durationSeconds, (clickX / totalWidth) * durationSeconds));
    onSeek(targetTime);
  };

  return (
    <div className="flex flex-col gap-3 rounded-xl border border-[var(--color-border)] bg-zinc-950 p-4 shadow-2xl">
      {/* 顶部控制栏 */}
      <div className="flex items-center justify-between border-b border-[var(--color-border)] pb-3">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <span className="text-sm">🎞</span>
            <span className="text-xs font-bold uppercase tracking-wider text-[var(--color-gold)]">
              Multi-Track Production Timeline
            </span>
          </div>
          <span className="rounded-full bg-amber-500/10 px-2.5 py-0.5 font-mono text-[11px] font-bold text-[var(--color-gold)] border border-amber-500/30">
            {formatTime(currentTime)} / {formatTime(durationSeconds)}
          </span>
          {isPlaying && (
            <span className="flex items-center gap-1 text-[11px] text-emerald-400 font-medium animate-pulse">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
              PLAYING
            </span>
          )}
        </div>

        <div className="flex items-center gap-4">
          <label className="flex items-center gap-2 cursor-pointer text-xs text-[var(--color-text-secondary)]">
            <input
              type="checkbox"
              checked={autoDucking}
              onChange={(e) => onDuckingChange?.(e.target.checked)}
              className="accent-[var(--color-gold)]"
            />
            <span>动态 BGM 智能闪避 (Audio Ducking -60%)</span>
          </label>

          <div className="flex items-center gap-1 rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] p-1 text-xs">
            <button
              type="button"
              onClick={() => setZoomLevel((z) => Math.max(0.6, z - 0.2))}
              className="px-2 py-0.5 rounded hover:bg-zinc-800 text-[var(--color-text-primary)]"
              title="缩小时间轴"
            >
              -
            </button>
            <span className="px-1 text-[11px] text-[var(--color-text-secondary)]">{Math.round(zoomLevel * 100)}%</span>
            <button
              type="button"
              onClick={() => setZoomLevel((z) => Math.min(2.5, z + 0.2))}
              className="px-2 py-0.5 rounded hover:bg-zinc-800 text-[var(--color-text-primary)]"
              title="放大时间轴"
            >
              +
            </button>
          </div>
        </div>
      </div>

      {/* 时间轴主渲染容器 */}
      <div
        ref={containerRef}
        onClick={handleTimelineClick}
        className="relative flex flex-col gap-2 overflow-x-auto select-none cursor-crosshair pb-2 pt-1"
        style={{ minHeight: "220px" }}
      >
        {/* 时间刻度标尺 */}
        <div className="relative h-5 w-full border-b border-[var(--color-border)]/60 text-[9px] font-mono text-[var(--color-text-muted)] flex justify-between px-1">
          {Array.from({ length: 9 }).map((_, i) => {
            const sec = (durationSeconds / 8) * i;
            return (
              <div key={i} className="flex flex-col items-center">
                <span>{formatTime(sec)}</span>
                <span className="h-1.5 w-[1px] bg-[var(--color-border)] mt-0.5" />
              </div>
            );
          })}
        </div>

        {/* 播放指针指示线 */}
        <div
          className="absolute top-0 bottom-0 z-30 w-[2px] bg-amber-400 pointer-events-none shadow-[0_0_8px_rgba(245,200,66,0.8)]"
          style={{ left: `${(currentTime / durationSeconds) * 100}%` }}
        >
          <div className="absolute -top-1 -left-1.5 h-3 w-3 rounded-full bg-amber-400 border border-zinc-950 shadow" />
        </div>

        {/* Track 1: 🎬 视频切片轨 */}
        <div className="flex items-center gap-2">
          <div className="flex w-24 shrink-0 items-center justify-between px-1 text-[11px] font-medium text-[var(--color-text-secondary)]">
            <span className="truncate">🎬 视频画面</span>
            <span className="text-[9px] opacity-60">V1</span>
          </div>
          <div className="relative h-10 flex-1 rounded-lg border border-blue-500/30 bg-blue-950/20 overflow-hidden flex items-center">
            {videoClips.map((clip) => {
              const leftPercent = (clip.start / durationSeconds) * 100;
              const widthPercent = (clip.duration / durationSeconds) * 100;
              return (
                <div
                  key={clip.id}
                  style={{ left: `${leftPercent}%`, width: `${widthPercent}%` }}
                  className="absolute top-1 bottom-1 rounded-md border border-blue-400/50 bg-blue-500/20 px-2 flex items-center justify-between text-[10px] text-blue-200 overflow-hidden shadow"
                >
                  <span className="font-bold truncate">{clip.title}</span>
                  {clip.emotion && (
                    <span className="rounded bg-blue-500/30 px-1 py-0.2 text-[8px] text-blue-100 font-normal">
                      {clip.emotion}
                    </span>
                  )}
                </div>
              );
            })}
          </div>
        </div>

        {/* Track 2: ✨ 黄金前 3 秒高潮轨 */}
        {hookClip && (
          <div className="flex items-center gap-2">
            <div className="flex w-24 shrink-0 items-center justify-between px-1 text-[11px] font-medium text-[var(--color-gold)]">
              <span className="truncate">✨ 爆款钩子</span>
              <span className="text-[9px] opacity-60">HOOK</span>
            </div>
            <div className="relative h-8 flex-1 rounded-lg border border-amber-500/40 bg-amber-950/20 overflow-hidden flex items-center">
              <div
                style={{
                  left: `${(hookClip.start / durationSeconds) * 100}%`,
                  width: `${(hookClip.duration / durationSeconds) * 100}%`,
                }}
                className="absolute top-1 bottom-1 rounded-md border border-amber-400 bg-gradient-to-r from-amber-500/40 to-yellow-500/30 px-2 flex items-center justify-between text-[10px] text-amber-200 shadow-[0_0_12px_rgba(245,200,66,0.3)] animate-pulse"
              >
                <span className="font-bold truncate">{hookClip.title}</span>
                <span className="rounded bg-amber-400/30 px-1 text-[8px] text-amber-100">{hookClip.style}</span>
              </div>
            </div>
          </div>
        )}

        {/* Track 3: 🎙️ 第一人称配音轨 */}
        <div className="flex items-center gap-2">
          <div className="flex w-24 shrink-0 items-center justify-between px-1 text-[11px] font-medium text-amber-300">
            <span className="truncate">🎙️ 独白配音</span>
            <span className="text-[9px] opacity-60">A1</span>
          </div>
          <div className="relative h-9 flex-1 rounded-lg border border-amber-400/30 bg-amber-950/15 overflow-hidden flex items-center">
            {voiceClips.map((clip) => {
              const leftPercent = (clip.start / durationSeconds) * 100;
              const widthPercent = (clip.duration / durationSeconds) * 100;
              return (
                <div
                  key={clip.id}
                  style={{ left: `${leftPercent}%`, width: `${widthPercent}%` }}
                  className="absolute top-1 bottom-1 rounded-md border border-amber-400/60 bg-amber-500/25 px-2 flex items-center gap-2 text-[10px] text-amber-100 overflow-hidden shadow"
                >
                  <span className="text-[10px]">🗣</span>
                  <span className="truncate font-mono">{clip.text}</span>
                </div>
              );
            })}
          </div>
        </div>

        {/* Track 4: 💬 花字字幕轨 */}
        <div className="flex items-center gap-2">
          <div className="flex w-24 shrink-0 items-center justify-between px-1 text-[11px] font-medium text-emerald-300">
            <span className="truncate">💬 花字字幕</span>
            <span className="text-[9px] opacity-60">SUB</span>
          </div>
          <div className="relative h-7 flex-1 rounded-lg border border-emerald-500/30 bg-emerald-950/15 overflow-hidden flex items-center">
            {subtitleClips.map((clip) => {
              const leftPercent = (clip.start / durationSeconds) * 100;
              const widthPercent = (clip.duration / durationSeconds) * 100;
              return (
                <div
                  key={clip.id}
                  style={{ left: `${leftPercent}%`, width: `${widthPercent}%` }}
                  className="absolute top-0.5 bottom-0.5 rounded border border-emerald-400/50 bg-emerald-500/20 px-1.5 flex items-center text-[9px] text-emerald-100 overflow-hidden"
                >
                  <span className="truncate">{clip.text}</span>
                </div>
              );
            })}
          </div>
        </div>

        {/* Track 5: 🎵 动态闪避背景音乐轨 */}
        <div className="flex items-center gap-2">
          <div className="flex w-24 shrink-0 items-center justify-between px-1 text-[11px] font-medium text-purple-300">
            <span className="truncate">🎵 BGM 混流</span>
            <span className="text-[9px] opacity-60">BGM</span>
          </div>
          <div className="relative h-8 flex-1 rounded-lg border border-purple-500/30 bg-purple-950/20 overflow-hidden flex items-center">
            <div className="absolute inset-0 bg-[repeating-linear-gradient(90deg,rgba(168,85,247,0.1)_0px,rgba(168,85,247,0.1)_4px,transparent_4px,transparent_8px)]" />
            <div className="relative z-10 flex items-center justify-between w-full px-3 text-[10px] text-purple-200">
              <span className="font-mono">Cinematic_Suspense_BGM.mp3 ({bgmMixRatio}% 音量)</span>
              {autoDucking && (
                <span className="rounded bg-purple-500/30 px-1.5 py-0.5 text-[8px] text-purple-100 font-bold border border-purple-400/30">
                  ⚡ Ducking Active (-60%)
                </span>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
