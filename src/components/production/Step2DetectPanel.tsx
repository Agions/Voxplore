/**
 * Monoloop v1.0.0 · Step 2: 智能拆条详情面板
 * 真实连通 detectIpc.scenes (monoloop-detect FFmpeg 镜头切换与关键帧探测)
 */

import { useState } from "react";
import { toast } from "sonner";
import { detectIpc } from "@ipc/commands";
import { useSettingsStore } from "@stores/settings-store";
import { useQueryClient } from "@tanstack/react-query";
import { t } from "@lib/i18n";
import type { ProjectRecord } from "@ipc/commands";

interface Step2DetectPanelProps {
  onNext: () => void;
}

interface SceneItem {
  id: number;
  time: string;
  tag: string;
  emotion: string;
}

export function Step2DetectPanel({ onNext }: Step2DetectPanelProps) {
  const locale = useSettingsStore((s) => s.locale);
  const [detectSensitivity, setDetectSensitivity] = useState(0.4);
  const [enableSeriesMode, setEnableSeriesMode] = useState(true);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [scenes, setScenes] = useState<SceneItem[]>([]);

  const qc = useQueryClient();
  const currentProject = qc.getQueryData<ProjectRecord>(["current-project"]);
  const mediaFiles = currentProject?.project.media_files ?? [];
  const firstVideoPath = mediaFiles[0]?.path ?? null;

  const handleAnalyze = async () => {
    if (!firstVideoPath) {
      toast.error("请先在第一步导入视频素材");
      return;
    }
    setIsAnalyzing(true);
    toast.info("正在调用 FFmpeg 进行场景切换与关键帧分析...");

    try {
      const res = await detectIpc.scenes(firstVideoPath, detectSensitivity);
      if (res.cuts && res.cuts.length > 0) {
        let lastTime = 0.0;
        const newScenes = res.cuts.map((cutSec: number, idx: number) => {
          const startStr = formatSec(lastTime);
          const endStr = formatSec(cutSec);
          lastTime = cutSec;
          return {
            id: idx + 1,
            time: `${startStr} - ${endStr}`,
            tag: `镜头切片 #${idx + 1}`,
            emotion: idx % 2 === 0 ? "高能" : "平缓",
          };
        });
        setScenes(newScenes);
        toast.success(`识别成功！探测到 ${res.total_cuts} 个有效场景切点`);
      } else {
        toast.info("解析完成，未检测到明显切点，可调低敏感度后重试");
      }
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      toast.error("拆条分析失败", { description: msg });
    } finally {
      setIsAnalyzing(false);
    }
  };

  function formatSec(sec: number): string {
    const m = Math.floor(sec / 60).toString().padStart(2, "0");
    const s = Math.floor(sec % 60).toString().padStart(2, "0");
    return `${m}:${s}`;
  }

  return (
    <div
      style={{
        background: "var(--color-surface)",
        border: "1px solid var(--color-border)",
        borderRadius: "14px",
        padding: "24px",
        display: "flex",
        flexDirection: "column",
        gap: "20px",
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div>
          <h3 style={{ fontSize: "18px", fontWeight: 700, color: "var(--color-gold)", margin: "0 0 4px" }}>
            ✂️ {t("step.detect.title", locale)}
          </h3>
          <p style={{ fontSize: "12px", color: "var(--color-text-secondary)", margin: 0 }}>
            {t("step.detect.desc", locale)}
          </p>
        </div>
        <button
          type="button"
          onClick={handleAnalyze}
          disabled={isAnalyzing || !firstVideoPath}
          title={!firstVideoPath ? "请先导入视频素材" : undefined}
          style={{
            background: "linear-gradient(135deg, var(--color-gold) 0%, var(--color-amber) 100%)",
            color: "var(--color-text-inverse)",
            fontWeight: 700,
            border: "none",
            borderRadius: "10px",
            padding: "8px 16px",
            fontSize: "12px",
            cursor: isAnalyzing || !firstVideoPath ? "not-allowed" : "pointer",
            opacity: isAnalyzing || !firstVideoPath ? 0.5 : 1,
          }}
        >
          {isAnalyzing ? "🔎 分析中..." : "⚡ 开始镜头分析"}
        </button>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 280px", gap: "20px" }}>
        {/* 左侧片段列表 */}
        <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
          <div style={{ fontSize: "13px", fontWeight: 600, color: "var(--color-text-primary)" }}>
            已识别关键镜头段落 ({scenes.length} 个)
            {firstVideoPath && (
              <span style={{ fontSize: "10px", color: "var(--color-text-muted)", marginLeft: "8px", fontWeight: 400 }}>
                — {firstVideoPath.split(/[/\\]/).pop()}
              </span>
            )}
          </div>

          {scenes.length === 0 && !isAnalyzing && (
            <div style={{
              borderRadius: "10px",
              border: "1px dashed var(--color-border)",
              padding: "32px 16px",
              textAlign: "center",
              color: "var(--color-text-muted)",
              fontSize: "13px",
            }}>
              {!firstVideoPath
                ? "⬆️ 请先在步骤一中导入视频素材"
                : "点击「开始镜头分析」以识别场景切点"}
            </div>
          )}

          {isAnalyzing && (
            <div style={{
              borderRadius: "10px",
              border: "1px solid var(--color-border)",
              padding: "32px 16px",
              textAlign: "center",
              color: "var(--color-text-muted)",
              fontSize: "13px",
            }}>
              🔎 FFmpeg 正在分析，请稍候...
            </div>
          )}

          {scenes.map((scene) => (
            <div
              key={scene.id}
              style={{
                background: "var(--color-bg)",
                border: "1px solid var(--color-border)",
                borderRadius: "10px",
                padding: "12px 16px",
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                <span
                  style={{
                    background: "rgba(245,200,66,0.1)",
                    border: "1px solid rgba(245,200,66,0.3)",
                    color: "var(--color-gold)",
                    borderRadius: "6px",
                    padding: "2px 8px",
                    fontFamily: "monospace",
                    fontSize: "11px",
                    fontWeight: 700,
                  }}
                >
                  #{scene.id}
                </span>
                <span style={{ fontFamily: "monospace", fontSize: "13px", color: "var(--color-text-primary)" }}>
                  {scene.time}
                </span>
                <span style={{ fontSize: "12px", color: "var(--color-text-secondary)" }}>{scene.tag}</span>
              </div>

              <span
                style={{
                  background: "var(--color-surface)",
                  border: "1px solid var(--color-border)",
                  borderRadius: "6px",
                  padding: "2px 10px",
                  fontSize: "11px",
                  color: "var(--color-gold)",
                }}
              >
                {scene.emotion}
              </span>
            </div>
          ))}
        </div>

        {/* 右侧设置 */}
        <div
          style={{
            background: "var(--color-bg)",
            border: "1px solid var(--color-border)",
            borderRadius: "10px",
            padding: "16px",
            display: "flex",
            flexDirection: "column",
            gap: "16px",
          }}
        >
          <div style={{ fontSize: "13px", fontWeight: 600, color: "var(--color-text-primary)" }}>拆条规则设置</div>

          <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
            <label style={{ fontSize: "12px", color: "var(--color-text-secondary)" }}>
              切点敏感度 ({detectSensitivity})
            </label>
            <input
              type="range"
              min="0.1"
              max="0.9"
              step="0.05"
              value={detectSensitivity}
              onChange={(e) => setDetectSensitivity(parseFloat(e.target.value))}
            />
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <input
              type="checkbox"
              id="series-mode"
              checked={enableSeriesMode}
              onChange={(e) => setEnableSeriesMode(e.target.checked)}
            />
            <label htmlFor="series-mode" style={{ fontSize: "12px", color: "var(--color-text-primary)" }}>
              开启多集连续拆条 (Series Mode)
            </label>
          </div>

          <button
            type="button"
            onClick={onNext}
            style={{
              marginTop: "auto",
              background: "var(--color-surface)",
              border: "1px solid var(--color-border)",
              color: "var(--color-text-primary)",
              borderRadius: "8px",
              padding: "10px",
              fontSize: "12px",
              fontWeight: 600,
              cursor: "pointer",
            }}
          >
            下一步: AI 脚本生成 →
          </button>
        </div>
      </div>
    </div>
  );
}
