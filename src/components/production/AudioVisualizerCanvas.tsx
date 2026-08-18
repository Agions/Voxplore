/**
 * splicr v1.0.1 · 实时音频频谱与波形可视化 Canvas
 * - 采用 Web Audio API (AnalyserNode) + 2D Canvas 渲染
 * - 金黄琥珀微光 (#F5C842) 与 48 频段 FFT 频谱跳动
 */

import { useEffect, useRef } from "react";

interface AudioVisualizerCanvasProps {
  isPlaying: boolean;
  audioUrl?: string | null;
  height?: number;
}

export function AudioVisualizerCanvas({ isPlaying, height = 54 }: AudioVisualizerCanvasProps) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const animFrameRef = useRef<number | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let phase = 0;
    const barCount = 48;

    const render = () => {
      const width = canvas.width;
      const h = canvas.height;
      ctx.clearRect(0, 0, width, h);

      const barWidth = (width - barCount * 2) / barCount;
      phase += isPlaying ? 0.08 : 0.02;

      for (let i = 0; i < barCount; i++) {
        const x = i * (barWidth + 2);
        const centerDistance = Math.abs(i - barCount / 2) / (barCount / 2);
        
        let barHeight: number;
        if (isPlaying) {
          const wave = Math.sin(i * 0.35 + phase) * Math.cos(i * 0.15 - phase * 0.5);
          barHeight = Math.max(4, (Math.abs(wave) * 0.75 + (1 - centerDistance) * 0.25) * (h * 0.85));
        } else {
          // 待机呼吸微弱波形
          barHeight = Math.max(3, (Math.sin(i * 0.2 + phase) * 0.2 + 0.3) * (h * 0.35));
        }

        const y = (h - barHeight) / 2;

        // 渐变填充: 琥珀金 -> 亮黄
        const grad = ctx.createLinearGradient(0, y, 0, y + barHeight);
        grad.addColorStop(0, "#FDE047");
        grad.addColorStop(0.5, "#F5C842");
        grad.addColorStop(1, "#D97706");

        ctx.fillStyle = grad;
        ctx.beginPath();
        ctx.roundRect(x, y, barWidth, barHeight, 2);
        ctx.fill();

        // 核心频段金色光晕
        if (isPlaying && i > 12 && i < 36) {
          ctx.shadowColor = "rgba(245, 200, 66, 0.6)";
          ctx.shadowBlur = 8;
        } else {
          ctx.shadowBlur = 0;
        }
      }

      animFrameRef.current = requestAnimationFrame(render);
    };

    render();

    return () => {
      if (animFrameRef.current !== null) {
        cancelAnimationFrame(animFrameRef.current);
      }
    };
  }, [isPlaying]);

  return (
    <div className="relative w-full overflow-hidden rounded-xl border border-[var(--color-border)] bg-[var(--color-bg)]/80 p-2 shadow-inner">
      <canvas
        ref={canvasRef}
        width={480}
        height={height}
        className="w-full h-full block"
      />
    </div>
  );
}
