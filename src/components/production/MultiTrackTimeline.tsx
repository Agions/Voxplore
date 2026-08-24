/**
 * splicr v1.0.1 · 全景多轨生产时间轴组件 (MultiTrackTimeline)
 * 
 * 深度适配 Dark/Light 调色台设计系统:
 * - 5 轨全景磁性轨道 (V1 视频切片、HK 黄金高光、A1 第一人称独白配音、SUB 逐字花字字幕、BGM 动态闪避伴奏)
 * - 沉浸式刻度标尺与发光指针 (Playhead Scrubber)
 * - 优雅空状态骨架
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
  isPlaying: _isPlaying = false,
  onSeek,
  videoClips = [],
  hookClip = null,
  voiceClips = [],
  subtitleClips = [],
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
    const ratio = Math.max(0, Math.min(1, clickX / rect.width));
    onSeek(ratio * durationSeconds);
  };

  const playheadPercent = Math.min(100, (currentTime / (durationSeconds || 1)) * 100);

  const isEmpty = videoClips.length === 0 && voiceClips.length === 0 && !hookClip;

  return (
    <div className="flex h-full w-full flex-col select-none font-sans">
      {/* 1. 顶部控制栏: 缩放、BGM 闪避控制、时间码 */}
      <div className="flex items-center justify-between border-b border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-1.5 text-xs">
        <div className="flex items-center gap-3 font-mono">
          <div className="flex items-center gap-1">
            <span className="text-[10px] text-[var(--color-text-muted)] font-semibold">POS</span>
            <span className="font-bold text-[var(--color-gold)]">{formatTime(currentTime)}</span>
          </div>
          <span className="text-[var(--color-border)]">/</span>
          <div className="flex items-center gap-1">
            <span className="text-[10px] text-[var(--color-text-muted)]">DUR</span>
            <span className="text-[var(--color-text-secondary)]">{formatTime(durationSeconds)}</span>
          </div>
        </div>

        <div className="flex items-center gap-4">
          <label className="flex items-center gap-1.5 text-[11px] cursor-pointer text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] transition-colors">
            <input
              type="checkbox"
              checked={autoDucking}
              onChange={(e) => onDuckingChange?.(e.target.checked)}
              className="rounded accent-[var(--color-gold)] text-xs cursor-pointer"
            />
            <span>BGM 闪避 (-{bgmMixRatio}%)</span>
          </label>

          <div className="flex items-center gap-1 text-[11px] text-[var(--color-text-secondary)] font-mono">
            <button
              type="button"
              onClick={() => setZoomLevel((z) => Math.max(0.5, z - 0.25))}
              className="h-5 w-5 rounded border border-[var(--color-border)] bg-[var(--color-surface-elevated)] hover:bg-[var(--color-border)] flex items-center justify-center font-bold text-[var(--color-text-primary)] transition-colors"
            >
              -
            </button>
            <span className="w-8 text-center">{Math.round(zoomLevel * 100)}%</span>
            <button
              type="button"
              onClick={() => setZoomLevel((z) => Math.min(2.5, z + 0.25))}
              className="h-5 w-5 rounded border border-[var(--color-border)] bg-[var(--color-surface-elevated)] hover:bg-[var(--color-border)] flex items-center justify-center font-bold text-[var(--color-text-primary)] transition-colors"
            >
              +
            </button>
          </div>
        </div>
      </div>

      {/* 2. 主轨道网格区 */}
      <div className="relative flex-1 flex flex-col overflow-hidden bg-[var(--color-bg)] p-2 gap-1.5">
        {/* 时间标尺刻度 */}
        <div className="h-4 w-full flex justify-between px-2 font-mono text-[9px] text-[var(--color-text-muted)] border-b border-[var(--color-border)]/60">
          <span>00:00.0</span>
          <span>00:15.0</span>
          <span>00:30.0</span>
          <span>00:45.0</span>
          <span>{formatTime(durationSeconds)}</span>
        </div>

        {/* 轨道层容器 */}
        <div
          ref={containerRef}
          onClick={handleTimelineClick}
          className="relative flex-1 flex flex-col gap-1.5 cursor-crosshair overflow-y-auto"
        >
          {/* Playhead 播放指针 */}
          <div
            className="absolute top-0 bottom-0 z-20 w-[2px] bg-gradient-to-b from-[var(--color-gold)] via-amber-400 to-amber-600 shadow-[0_0_8px_var(--color-gold)] pointer-events-none transition-all duration-75"
            style={{ left: `${playheadPercent}%` }}
          >
            <div className="h-2 w-2 -translate-x-[3px] rotate-45 bg-[var(--color-gold)] shadow-[0_0_6px_var(--color-gold)]" />
          </div>

          {isEmpty ? (
            <div className="flex h-full flex-col items-center justify-center text-center text-[var(--color-text-muted)] text-xs gap-1.5 my-auto">
              <span className="text-2xl">⏱️</span>
              <span className="font-bold text-[var(--color-text-secondary)]">多轨时间轴待命</span>
              <span className="text-[10px]">导入素材或启动 Multi-Agent 智能体将实时排布 5 轨视听流</span>
            </div>
          ) : (
            <>
              {/* Track 1: 视频分镜切片 (V1) */}
              <div className="flex items-center gap-2 h-8 rounded-lg bg-[var(--color-surface)] border border-[var(--color-border)] px-2">
                <span className="w-14 font-mono text-[10px] font-bold text-sky-400 shrink-0">V1 视频</span>
                <div className="relative flex-1 h-5 flex gap-1">
                  {videoClips.map((c) => (
                    <div
                      key={c.id}
                      className="h-full rounded bg-sky-950/70 dark:bg-sky-950/70 light:bg-sky-100 border border-sky-500/40 px-2 flex items-center justify-between text-[10px] text-sky-300 font-medium truncate"
                      style={{ width: `${(c.duration / durationSeconds) * 100}%` }}
                    >
                      <span className="truncate">{c.title}</span>
                      {c.emotion && (
                        <span className="rounded bg-sky-900/60 px-1 py-0.2 text-[8px] text-sky-200 shrink-0">
                          {c.emotion}
                        </span>
                      )}
                    </div>
                  ))}
                </div>
              </div>

              {/* Track 2: 0~3s 黄金 Hook 轨 (HK) */}
              {hookClip && (
                <div className="flex items-center gap-2 h-8 rounded-lg bg-[var(--color-surface)] border border-amber-500/40 px-2">
                  <span className="w-14 font-mono text-[10px] font-bold text-[var(--color-gold)] shrink-0">HK 高光</span>
                  <div className="relative flex-1 h-5">
                    <div
                      className="h-full rounded bg-gradient-to-r from-amber-500/30 to-yellow-500/15 border border-amber-400/60 px-2 flex items-center gap-1 text-[9px] font-bold text-[var(--color-gold)] animate-pulse"
                      style={{ width: `${(hookClip.duration / durationSeconds) * 100}%` }}
                    >
                      <span>🔥</span>
                      <span className="truncate">{hookClip.title}</span>
                    </div>
                  </div>
                </div>
              )}

              {/* Track 3: 第一人称独白配音轨 (A1) */}
              <div className="flex items-center gap-2 h-8 rounded-lg bg-[var(--color-surface)] border border-[var(--color-border)] px-2">
                <span className="w-14 font-mono text-[10px] font-bold text-emerald-400 shrink-0">A1 配音</span>
                <div className="relative flex-1 h-5 flex gap-1">
                  {voiceClips.map((c) => (
                    <div
                      key={c.id}
                      className="h-full rounded bg-emerald-950/70 border border-emerald-500/40 px-2 flex items-center text-[10px] text-emerald-300 truncate"
                      style={{ width: `${(c.duration / durationSeconds) * 100}%` }}
                    >
                      <span className="truncate">🎙️ {c.text}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Track 4: 逐字高亮字幕轨 (SUB) */}
              <div className="flex items-center gap-2 h-7 rounded-lg bg-[var(--color-surface)] border border-[var(--color-border)] px-2">
                <span className="w-14 font-mono text-[9px] font-bold text-purple-400 shrink-0">SUB 字幕</span>
                <div className="relative flex-1 h-4 flex gap-1">
                  {subtitleClips.map((c) => (
                    <div
                      key={c.id}
                      className="h-full rounded bg-purple-950/60 border border-purple-500/30 px-1.5 flex items-center text-[9px] text-purple-300 truncate"
                      style={{ width: `${(c.duration / durationSeconds) * 100}%` }}
                    >
                      <span className="truncate">{c.text}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Track 5: BGM 闪避动态轨 (BGM) */}
              <div className="flex items-center gap-2 h-7 rounded-lg bg-[var(--color-surface)] border border-[var(--color-border)] px-2">
                <span className="w-14 font-mono text-[9px] font-bold text-pink-400 shrink-0">BGM 伴奏</span>
                <div className="relative flex-1 h-4 rounded bg-pink-950/40 border border-pink-500/30 px-2 flex items-center justify-between text-[9px] text-pink-300">
                  <span>🎵 悬疑激昂电影原声 (Movie Suspense Arc)</span>
                  <span className="font-mono text-[8px] text-pink-400">Ducking Active</span>
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
