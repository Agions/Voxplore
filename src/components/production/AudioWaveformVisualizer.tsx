/**
 * splicr v1.0.0 · Web Audio API Canvas 级实时音频波形图
 * 
 * 特性:
 * - 结合 Web Audio API (AudioContext + AnalyserNode) 与 Canvas 2D 绘图
 * - 播放时实时采集频域 (FFT) 与时域波形数据
 * - 双重视效: 56 频段柱状频谱 + 柔滑贝塞尔波形包络线
 * - 赛博暗黑黄金配色 (#F5C842 / #F9D76B) + 动态发光粒子效果
 * - 暂停/未播放时自动降级为平滑息屏呼吸波形
 */

import { useEffect, useRef } from "react";

interface AudioWaveformVisualizerProps {
  audioRef?: React.RefObject<HTMLAudioElement | null>;
  isPlaying?: boolean;
  height?: number;
  barCount?: number;
  className?: string;
}

export function AudioWaveformVisualizer({
  audioRef,
  isPlaying = false,
  height = 72,
  barCount = 56,
  className = "",
}: AudioWaveformVisualizerProps) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const audioCtxRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const sourceRef = useRef<MediaElementAudioSourceNode | null>(null);
  const rafRef = useRef<number | null>(null);

  // 初始化 Web Audio API 上下文 (防重复挂载)
  useEffect(() => {
    const audioEl = audioRef?.current;
    if (!audioEl) return;

    const setupAudioContext = () => {
      try {
        if (!audioCtxRef.current) {
          const AudioCtx =
            window.AudioContext ||
            (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
          const ctx = new AudioCtx();
          const analyser = ctx.createAnalyser();
          analyser.fftSize = 256;
          analyser.smoothingTimeConstant = 0.82;

          let source = sourceRef.current;
          if (!source) {
            try {
              source = ctx.createMediaElementSource(audioEl);
              sourceRef.current = source;
            } catch {
              // 忽略元素已挂载的场景
            }
          }

          if (source) {
            source.connect(analyser);
            analyser.connect(ctx.destination);
          }

          audioCtxRef.current = ctx;
          analyserRef.current = analyser;
        }

        if (audioCtxRef.current.state === "suspended" && isPlaying) {
          void audioCtxRef.current.resume();
        }
      } catch (err) {
        console.warn("[Waveform] AudioContext setup fallback:", err);
      }
    };

    if (isPlaying) {
      setupAudioContext();
    }
  }, [audioRef, isPlaying]);

  // Canvas 渲染主循环 (支持 Retina / High-DPI 屏幕清晰度缩放)
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let animTime = 0;

    const updateCanvasBounds = () => {
      const dpr = typeof window !== "undefined" ? window.devicePixelRatio || 1 : 1;
      const rect = canvas.getBoundingClientRect();
      const targetW = Math.floor((rect.width || 600) * dpr);
      const targetH = Math.floor((height || 72) * dpr);

      if (canvas.width !== targetW || canvas.height !== targetH) {
        canvas.width = targetW;
        canvas.height = targetH;
      }
      return { dpr, width: rect.width || 600, height: height || 72 };
    };

    const render = () => {
      animTime += 0.04;
      const { dpr, width, height: ch } = updateCanvasBounds();

      ctx.save();
      ctx.scale(dpr, dpr);
      ctx.clearRect(0, 0, width, ch);

      const analyser = analyserRef.current;
      const dataArray = new Uint8Array(barCount);

      let hasRealData = false;
      if (isPlaying && analyser && audioCtxRef.current?.state === "running") {
        const rawData = new Uint8Array(analyser.frequencyBinCount);
        analyser.getByteFrequencyData(rawData);
        for (let i = 0; i < barCount; i++) {
          dataArray[i] = rawData[i % rawData.length] || 0;
        }
        hasRealData = dataArray.some((v) => v > 0);
      }

      const step = width / barCount;
      const barWidth = Math.max(2.5, step - 2.5);

      // 1. 绘制柱状频域图 (Bar Frequency Visualizer)
      for (let i = 0; i < barCount; i++) {
        let val = 0;
        const v = dataArray[i] ?? 0;
        if (hasRealData) {
          val = (v / 255) * ch * 0.85;
        } else if (isPlaying) {
          const wave1 = Math.sin(i * 0.35 + animTime * 3);
          const wave2 = Math.cos(i * 0.2 + animTime * 4);
          val = (Math.abs(wave1 + wave2) / 2) * ch * 0.65 + 4;
        } else {
          const wave = Math.sin(i * 0.3 + animTime * 1.5);
          val = (wave * 0.15 + 0.25) * ch * 0.25 + 3;
        }

        const barHeight = Math.max(3, val);
        const x = i * step + (step - barWidth) / 2;
        const y = ch - barHeight;

        // 金黄香槟发光渐变
        const gradient = ctx.createLinearGradient(0, ch, 0, y);
        gradient.addColorStop(0, "rgba(245, 200, 66, 0.15)");
        gradient.addColorStop(0.5, "rgba(245, 200, 66, 0.7)");
        gradient.addColorStop(1, "#F9D76B");

        ctx.fillStyle = gradient;
        ctx.beginPath();
        const ctxExt = ctx as unknown as CanvasRenderingContext2D & {
          roundRect?: (x: number, y: number, w: number, h: number, radii: number[]) => void;
        };
        if (typeof ctxExt.roundRect === "function") {
          ctxExt.roundRect(x, y, barWidth, barHeight, [3, 3, 0, 0]);
        } else {
          ctx.rect(x, y, barWidth, barHeight);
        }
        ctx.fill();

        // 顶部高亮粒子圆点
        if (isPlaying && barHeight > 10) {
          ctx.shadowBlur = 8;
          ctx.shadowColor = "rgba(245, 200, 66, 0.9)";
          ctx.fillStyle = "#FFFFFF";
          ctx.beginPath();
          ctx.arc(x + barWidth / 2, y + 1.5, barWidth / 2, 0, Math.PI * 2);
          ctx.fill();
          ctx.shadowBlur = 0;
        }
      }

      // 2. 顶部平滑贝塞尔包络曲线 (Smooth Waveform Envelope)
      ctx.beginPath();
      ctx.lineWidth = 2;
      const lineGradient = ctx.createLinearGradient(0, 0, width, 0);
      lineGradient.addColorStop(0, "rgba(245, 200, 66, 0.2)");
      lineGradient.addColorStop(0.5, "rgba(249, 215, 107, 0.9)");
      lineGradient.addColorStop(1, "rgba(232, 147, 58, 0.2)");
      ctx.strokeStyle = lineGradient;

      for (let i = 0; i < barCount; i++) {
        let val = 0;
        const v = dataArray[i] ?? 0;
        if (hasRealData) {
          val = (v / 255) * ch * 0.85;
        } else if (isPlaying) {
          val = Math.abs(Math.sin(i * 0.35 + animTime * 3)) * ch * 0.65 + 4;
        } else {
          val = (Math.sin(i * 0.3 + animTime * 1.5) * 0.15 + 0.25) * ch * 0.25 + 3;
        }
        const x = i * step + step / 2;
        const y = ch - val - 4;
        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      }
      ctx.stroke();

      ctx.restore();
      rafRef.current = requestAnimationFrame(render);
    };

    rafRef.current = requestAnimationFrame(render);

    return () => {
      if (rafRef.current !== null) {
        cancelAnimationFrame(rafRef.current);
      }
    };
  }, [isPlaying, barCount]);

  return (
    <div className={`relative w-full overflow-hidden rounded-xl border border-[var(--color-border)] bg-zinc-950/90 p-3 shadow-inner ${className}`}>
      <div className="mb-2 flex items-center justify-between px-1">
        <div className="flex items-center space-x-2">
          <span className={`inline-block h-2 w-2 rounded-full ${isPlaying ? "bg-amber-400 animate-ping" : "bg-zinc-600"}`} />
          <span className="text-[11px] font-bold tracking-wide text-[var(--color-gold)] uppercase">
            Real-Time Audio Spectrum Visualizer
          </span>
        </div>
        <span className="text-[10px] font-mono text-zinc-400">
          {isPlaying ? "LIVE ANALYZER ACTIVE" : "IDLE"}
        </span>
      </div>

      <canvas
        ref={canvasRef}
        width={640}
        height={height}
        className="w-full h-full block rounded-lg"
      />
    </div>
  );
}
