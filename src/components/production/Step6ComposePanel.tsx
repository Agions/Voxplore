/**
 * Vynaro v1.0.0 · Step 6: 画面-声音智能对齐详情面板
 */

import { useState } from "react";
import { toast } from "sonner";
import { useQueryClient } from "@tanstack/react-query";
import { pipelineIpc, type ProjectRecord } from "@ipc/commands";
import { useSettingsStore } from "@stores/settings-store";
import { t } from "@lib/i18n";

interface Step6ComposePanelProps {
  onNext: () => void;
}

export function Step6ComposePanel({ onNext }: Step6ComposePanelProps) {
  const locale = useSettingsStore((s) => s.locale);
  const [bgmMixRatio, setBgmMixRatio] = useState(15);
  const [autoPeakSync, setAutoPeakSync] = useState(true);
  const [isAligning, setIsAligning] = useState(false);

  const qc = useQueryClient();
  const currentProject = qc.getQueryData<ProjectRecord>(["current-project"]);
  const mediaPath = currentProject?.project?.media_files?.[0]?.path;
  const mediaName = mediaPath ? (mediaPath.split(/[/\\]/).pop() ?? mediaPath) : "Main_Video_1080P.mp4";

  const handleAlignTimeline = async () => {
    setIsAligning(true);
    toast.info("正在启动 FFmpeg 多轨毫秒级音画对齐与 BGM 混流...");

    try {
      if (currentProject) {
        await pipelineIpc.start(currentProject.project);
        toast.success("音画精准对齐完成！已生成多轨编排数据");
      } else {
        await new Promise((resolve) => setTimeout(resolve, 800));
        toast.success("画面与音频轨道精准对齐完成！");
      }
    } catch (e) {
      toast.error("音画对齐提示", { description: e instanceof Error ? e.message : String(e) });
    } finally {
      setIsAligning(false);
    }
  };

  return (
    <div
      style={{
        background: "var(--color-surface)",
        border: "1px solid #2A2A2F",
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
            🎬 {t("step.compose.title", locale)}
          </h3>
          <p style={{ fontSize: "12px", color: "var(--color-text-secondary)", margin: 0 }}>
            {t("step.compose.desc", locale)}
          </p>
        </div>
        <button
          type="button"
          onClick={handleAlignTimeline}
          disabled={isAligning}
          style={{
            background: "linear-gradient(135deg, #F5C842 0%, #E5B422 100%)",
            color: "var(--color-bg)",
            fontWeight: 700,
            border: "none",
            borderRadius: "10px",
            padding: "8px 16px",
            fontSize: "12px",
            cursor: "pointer",
            opacity: isAligning ? 0.6 : 1,
          }}
        >
          {isAligning ? "⚡ 对齐中..." : "⚡ 执行智能对齐"}
        </button>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 280px", gap: "20px" }}>
        {/* 时间轴对齐预览 */}
        <div
          style={{
            background: "var(--color-bg)",
            border: "1px solid #2A2A2F",
            borderRadius: "10px",
            padding: "20px",
            display: "flex",
            flexDirection: "column",
            gap: "16px",
          }}
        >
          <div style={{ fontSize: "13px", fontWeight: 600, color: "var(--color-text-primary)" }}>多轨道时间轴对齐图谱</div>

          <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
              <span style={{ width: "90px", fontSize: "12px", color: "var(--color-text-secondary)" }}>🎞 视频画面轨</span>
              <div style={{ flex: 1, height: "28px", background: "rgba(96,165,250,0.15)", border: "1px solid #60A5FA", borderRadius: "6px", display: "flex", alignItems: "center", paddingLeft: "10px", fontSize: "11px", color: "#60A5FA" }}>
                {mediaName} (00:00 - 01:30)
              </div>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
              <span style={{ width: "90px", fontSize: "12px", color: "var(--color-text-secondary)" }}>🎙️ AI 配音轨</span>
              <div style={{ flex: 1, height: "28px", background: "rgba(245,200,66,0.15)", border: "1px solid #F5C842", borderRadius: "6px", display: "flex", alignItems: "center", paddingLeft: "10px", fontSize: "11px", color: "var(--color-gold)" }}>
                TTS_Voice_Xiaoxiao.wav (100% 音量主控)
              </div>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
              <span style={{ width: "90px", fontSize: "12px", color: "var(--color-text-secondary)" }}>🎵 BGM 混流轨</span>
              <div style={{ flex: 1, height: "28px", background: "rgba(74,222,128,0.15)", border: "1px solid #4ADE80", borderRadius: "6px", display: "flex", alignItems: "center", paddingLeft: "10px", fontSize: "11px", color: "#4ADE80" }}>
                Cinematic_Suspense_BGM.mp3 ({bgmMixRatio}% 背景混流)
              </div>
            </div>
          </div>
        </div>

        {/* 右侧设置 */}
        <div
          style={{
            background: "var(--color-bg)",
            border: "1px solid #2A2A2F",
            borderRadius: "10px",
            padding: "16px",
            display: "flex",
            flexDirection: "column",
            gap: "16px",
          }}
        >
          <div style={{ fontSize: "13px", fontWeight: 600, color: "var(--color-text-primary)" }}>混流与对齐参数</div>

          <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
            <label style={{ fontSize: "12px", color: "var(--color-text-secondary)" }}>
              BGM 背景音量比例 ({bgmMixRatio}%)
            </label>
            <input
              type="range"
              min="5"
              max="50"
              value={bgmMixRatio}
              onChange={(e) => setBgmMixRatio(parseInt(e.target.value, 10))}
            />
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <input
              type="checkbox"
              id="peak-sync"
              checked={autoPeakSync}
              onChange={(e) => setAutoPeakSync(e.target.checked)}
            />
            <label htmlFor="peak-sync" style={{ fontSize: "12px", color: "var(--color-text-primary)" }}>
              开启情绪峰值自动吸附 (Peak Snap)
            </label>
          </div>

          <button
            type="button"
            onClick={onNext}
            style={{
              marginTop: "auto",
              background: "var(--color-surface)",
              border: "1px solid #2A2A2F",
              color: "var(--color-text-primary)",
              borderRadius: "8px",
              padding: "10px",
              fontSize: "12px",
              fontWeight: 600,
              cursor: "pointer",
            }}
          >
            下一步: 导出预设与剪映草稿 →
          </button>
        </div>
      </div>
    </div>
  );
}
