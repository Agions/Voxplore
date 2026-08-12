/**
 * Vynaro v1.0.0 · Step 5: 字幕合成详情面板
 * 真实连通 subtitleIpc.generate (vynaro-subtitle VAD 语音断句与 ASS/SRT 渲染)
 */

import { useState } from "react";
import { toast } from "sonner";
import { subtitleIpc } from "@ipc/commands";
import { useSettingsStore } from "@stores/settings-store";
import { useQueryClient } from "@tanstack/react-query";
import { t } from "@lib/i18n";
import type { SubtitleItem } from "@ipc/types.gen";

interface Step5SubtitlePanelProps {
  onNext: () => void;
}

export function Step5SubtitlePanel({ onNext }: Step5SubtitlePanelProps) {
  const locale = useSettingsStore((s) => s.locale);
  const qc = useQueryClient();
  const [subFormat, setSubFormat] = useState("SRT");
  const [enableDynamic, setEnableDynamic] = useState(true);
  const [enableBilingual, setEnableBilingual] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);

  // 从 Step3 共享的脚本内容（存在 QueryClient 缓存中）
  const scriptText = qc.getQueryData<string>(["step3-script-content"]) ?? "";

  const [subtitles, setSubtitles] = useState<Array<{
    id: string; time: string; text: string; emotion: string;
  }>>([]);

  const handleGenerate = async () => {
    if (!scriptText.trim()) {
      toast.error("请先在步骤三中生成脚本内容");
      return;
    }
    setIsGenerating(true);
    toast.info("正在调用 VAD 算法对齐字幕时间轴...");

    try {
      const res = await subtitleIpc.generate({
        script_text: scriptText,
        format: subFormat.toLowerCase(),
      });

      if (res.items && res.items.length > 0) {
        const mapped = res.items.map((it: SubtitleItem, idx: number) => ({
          id: `sub-${idx + 1}`,
          time: `${formatSrtTime(it.start_seconds)} --> ${formatSrtTime(it.end_seconds)}`,
          text: it.text,
          emotion: idx % 2 === 0 ? "核心叙事" : "情绪高潮",
        }));
        setSubtitles(mapped);
        toast.success(`字幕对齐与 ${subFormat} 格式渲染完成！共 ${res.item_count} 条`);
      } else {
        toast.info("未生成字幕条目，请检查脚本内容后重试");
      }
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      toast.error("字幕生成失败", { description: msg });
    } finally {
      setIsGenerating(false);
    }
  };

  function formatSrtTime(sec: number): string {
    const ms = Math.floor((sec % 1) * 1000).toString().padStart(3, "0");
    const s = Math.floor(sec % 60).toString().padStart(2, "0");
    const m = Math.floor(sec / 60).toString().padStart(2, "0");
    return `00:${m}:${s},${ms}`;
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
            📝 {t("step.subtitle.title", locale)}
          </h3>
          <p style={{ fontSize: "12px", color: "var(--color-text-secondary)", margin: 0 }}>
            {t("step.subtitle.desc", locale)}
          </p>
        </div>
        <button
          type="button"
          onClick={handleGenerate}
          disabled={isGenerating}
          style={{
            background: "linear-gradient(135deg, #F5C842 0%, #E5B422 100%)",
            color: "var(--color-bg)",
            fontWeight: 700,
            border: "none",
            borderRadius: "10px",
            padding: "8px 16px",
            fontSize: "12px",
            cursor: "pointer",
            opacity: isGenerating ? 0.6 : 1,
          }}
        >
          {isGenerating ? "⏱ 生成中..." : "⚡ 识别并生成字幕"}
        </button>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 280px", gap: "20px" }}>
        {/* 左侧字幕时间轴预览 */}
        <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
          <div style={{ fontSize: "13px", fontWeight: 600, color: "var(--color-text-primary)" }}>
            字幕时间轴预览 ({subtitles.length} 条)
          </div>

          {subtitles.length === 0 && !isGenerating && (
            <div style={{
              borderRadius: "10px",
              border: "1px dashed var(--color-border)",
              padding: "32px 16px",
              textAlign: "center",
              color: "var(--color-text-muted)",
              fontSize: "13px",
            }}>
              {!scriptText.trim()
                ? "⬆️ 请先在步骤三中生成脚本，再识别字幕"
                : "点击「识别并生成字幕」以对齐时间轴"}
            </div>
          )}

          {isGenerating && (
            <div style={{
              borderRadius: "10px",
              border: "1px solid var(--color-border)",
              padding: "32px 16px",
              textAlign: "center",
              color: "var(--color-text-muted)",
              fontSize: "13px",
            }}>
              ⏱ VAD 正在分析语音断句，请稍候...
            </div>
          )}

          {subtitles.map((sub) => (
            <div
              key={sub.id}
              style={{
                background: "var(--color-bg)",
                border: "1px solid var(--color-border)",
                borderRadius: "10px",
                padding: "12px 16px",
                display: "flex",
                flexDirection: "column",
                gap: "6px",
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span style={{ fontFamily: "monospace", fontSize: "11px", color: "var(--color-gold)" }}>
                  ⏱ {sub.time}
                </span>
                <span
                  style={{
                    background: "var(--color-surface)",
                    border: "1px solid var(--color-border)",
                    borderRadius: "4px",
                    padding: "1px 6px",
                    fontSize: "10px",
                    color: "var(--color-text-secondary)",
                  }}
                >
                  {sub.emotion}
                </span>
              </div>
              <div style={{ fontSize: "13px", color: "var(--color-text-primary)", lineHeight: 1.5 }}>
                {sub.text}
              </div>
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
          <div style={{ fontSize: "13px", fontWeight: 600, color: "var(--color-text-primary)" }}>字幕导出格式</div>

          <div style={{ display: "flex", gap: "8px" }}>
            {["SRT", "VTT", "ASS"].map((fmt) => (
              <button
                key={fmt}
                type="button"
                onClick={() => setSubFormat(fmt)}
                style={{
                  flex: 1,
                  background: subFormat === fmt ? "rgba(245,200,66,0.1)" : "var(--color-surface)",
                  border: `1px solid ${subFormat === fmt ? "var(--color-gold)" : "var(--color-border)"}`,
                  color: subFormat === fmt ? "var(--color-gold)" : "var(--color-text-secondary)",
                  borderRadius: "6px",
                  padding: "6px",
                  fontSize: "12px",
                  fontWeight: 600,
                  cursor: "pointer",
                }}
              >
                {fmt}
              </button>
            ))}
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <input
                type="checkbox"
                id="dynamic-highlight"
                checked={enableDynamic}
                onChange={(e) => setEnableDynamic(e.target.checked)}
              />
              <label htmlFor="dynamic-highlight" style={{ fontSize: "12px", color: "var(--color-text-primary)" }}>
                启用卡拉 OK 逐字高亮
              </label>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <input
                type="checkbox"
                id="bilingual-mode"
                checked={enableBilingual}
                onChange={(e) => setEnableBilingual(e.target.checked)}
              />
              <label htmlFor="bilingual-mode" style={{ fontSize: "12px", color: "var(--color-text-primary)" }}>
                生成中英双语对照字幕
              </label>
            </div>
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
            下一步: 画面与音频对齐 →
          </button>
        </div>
      </div>
    </div>
  );
}
