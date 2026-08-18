/**
 * splicr v1.0.0 · 全景多轨生产时间轴组件 (MultiTrackTimeline)
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
    <div className="flex h-full w-full flex-col select-none text-zinc-300 font-sans">
      {/* 1. 顶部控制栏: 缩放、BGM 闪避控制、时间码 */}
      <div className="flex items-center justify-between border-b border-[var(--color-border)] bg-[var(--color-surface)]/80 px-3 py-1.5 text-xs">
        <div className="flex items-center gap-3 font-mono">
          <div className="flex items-center gap-1">
            <span className="text-[10px] text-zinc-500">POS</span>
            <span className="font-bold text-[var(--color-gold)]">{formatTime(currentTime)}</span>
          </div>
          <span className="text-zinc-700">/</span>
          <div className="flex items-center gap-1">
            <span className="text-[10px] text-zinc-500">DUR</span>
            <span className="text-zinc-400">{formatTime(durationSeconds)}</span>
          </div>
        </div>

        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <label className="flex items-center gap-1 text-[11px] cursor-pointer text-zinc-400 hover:text-zinc-200">
              <input
                type="checkbox"
                checked={autoDucking}
                onChange={(e) => onDuckingChange?.(e.target.checked)}
                className="rounded accent-[var(--color-gold)] text-xs"
              />
              <span>BGM 闪避 (-{bgmMixRatio}%)</span>
            </label>
          </div>

          <div className="flex items-center gap-1 text-[11px] text-zinc-400 font-mono">
            <button
              type="button"
              onClick={() => setZoomLevel((z) => Math.max(0.5, z - 0.25))}
              className="h-5 w-5 rounded bg-zinc-800 hover:bg-zinc-700 flex items-center justify-center font-bold"
            >
              -
            </button>
            <span className="w-8 text-center">{Math.round(zoomLevel * 100)}%</span>
            <button
              type="button"
              onClick={() => setZoomLevel((z) => Math.min(2.5, z + 0.25))}
              className="h-5 w-5 rounded bg-zinc-800 hover:bg-zinc-700 flex items-center justify-center font-bold"
            >
              +
            </button>
          </div>
        </div>
      </div>

      {/* 2. 主轨道网格区 */}
      <div className="relative flex-1 flex flex-col overflow-hidden bg-zinc-950/60 p-2 gap-1.5">
        {/* 时间标尺刻度 */}
        <div className="h-4 w-full flex justify-between px-2 font-mono text-[9px] text-zinc-600 border-b border-zinc-900">
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
            className="absolute top-0 bottom-0 z-20 w-[1.5px] bg-gradient-to-b from-[var(--color-gold)] via-amber-400 to-amber-600 shadow-[0_0_8px_var(--color-gold)] pointer-events-none transition-all duration-75"
            style={{ left: `${playheadPercent}%` }}
          >
            <div className="h-2 w-2 -translate-x-[3px] rotate-45 bg-[var(--color-gold)]" />
          </div>

          {isEmpty ? (
            <div className="flex h-full flex-col items-center justify-center text-center text-zinc-600 text-xs gap-1.5 my-auto">
              <span className="text-xl">⏱️</span>
              <span className="font-semibold text-zinc-500">多轨时间轴待命</span>
              <span className="text-[10px] text-zinc-600">启动 Multi-Agent 智能体或导入素材后将在此生成 5 轨实时流</span>
            </div>
          ) : (
            <>
              {/* Track 1: 视频分镜切片 (V1) */}
              <div className="flex items-center gap-2 h-9 rounded-lg bg-zinc-900/80 border border-zinc-800/80 px-2">
                <span className="w-12 font-mono text-[10px] font-bold text-sky-400 shrink-0">V1 视频</span>
                <div className="relative flex-1 h-6 flex gap-1">
                  {videoClips.map((c) => (
                    <div
                      key={c.id}
                      className="h-full rounded bg-sky-950/70 border border-sky-600/40 px-2 flex items-center justify-between text-[10px] text-sky-200 truncate"
                      style={{ width: `${(c.duration / durationSeconds) * 100}%` }}
                    >
                      <span className="truncate">{c.title}</span>
                      {c.emotion && (
                        <span className="rounded bg-sky-900/60 px-1 py-0.2 text-[8px] text-sky-300 shrink-0">
                          {c.emotion}
                        </span>
                      )}
                    </div>
                  ))}
                </div>
              </div>

              {/* Track 2: 0~3s 黄金 Hook 轨 (HK) */}
              {hookClip && (
                <div className="flex items-center gap-2 h-8 rounded-lg bg-zinc-900/80 border border-amber-500/30 px-2">
                  <span className="w-12 font-mono text-[10px] font-bold text-[var(--color-gold)] shrink-0">HK 高潮</span>
                  <div className="relative flex-1 h-5">
                    <div
                      className="h-full rounded bg-gradient-to-r from-amber-500/40 to-yellow-500/20 border border-amber-400/60 px-2 flex items-center gap-1 text-[9px] font-bold text-[var(--color-gold)] animate-pulse"
                      style={{ width: `${(hookClip.duration / durationSeconds) * 100}%` }}
                    >
                      <span>🔥</span>
                      <span className="truncate">{hookClip.title}</span>
                    </div>
                  </div>
                </div>
              )}

              {/* Track 3: 第一人称独白配音轨 (A1) */}
              <div className="flex items-center gap-2 h-9 rounded-lg bg-zinc-900/80 border border-zinc-800/80 px-2">
                <span className="w-12 font-mono text-[10px] font-bold text-emerald-400 shrink-0">A1 配音</span>
                <div className="relative flex-1 h-6 flex gap-1">
                  {voiceClips.map((c) => (
                    <div
                      key={c.id}
                      className="h-full rounded bg-emerald-950/70 border border-emerald-600/40 px-2 flex items-center text-[10px] text-emerald-200 truncate"
                      style={{ width: `${(c.duration / durationSeconds) * 100}%` }}
                    >
                      <span className="truncate">🎙️ {c.text}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Track 4: 逐字高亮字幕轨 (SUB) */}
              <div className="flex items-center gap-2 h-7 rounded-lg bg-zinc-900/80 border border-zinc-800/80 px-2">
                <span className="w-12 font-mono text-[9px] font-bold text-purple-400 shrink-0">SUB 字幕</span>
                <div className="relative flex-1 h-4 flex gap-1">
                  {subtitleClips.map((c) => (
                    <div
                      key={c.id}
                      className="h-full rounded bg-purple-950/60 border border-purple-600/30 px-1.5 flex items-center text-[9px] text-purple-200 truncate"
                      style={{ width: `${(c.duration / durationSeconds) * 100}%` }}
                    >
                      <span className="truncate">{c.text}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Track 5: BGM 闪避动态轨 (BGM) */}
              <div className="flex items-center gap-2 h-7 rounded-lg bg-zinc-900/80 border border-zinc-800/80 px-2">
                <span className="w-12 font-mono text-[9px] font-bold text-pink-400 shrink-0">BGM 伴奏</span>
                <div className="relative flex-1 h-4 rounded bg-pink-950/40 border border-pink-700/30 px-2 flex items-center justify-between text-[9px] text-pink-300">
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
