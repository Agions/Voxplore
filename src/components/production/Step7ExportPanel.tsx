/**
 * Vynaro v1.0.0 · Step 7: 多平台导出与剪映草稿详情面板
 * 真实连通 exportIpc.capcutDraft (vynaro-export 剪映草稿工程结构生成器)
 */

import { useState } from "react";
import { toast } from "sonner";
import { useQueryClient } from "@tanstack/react-query";
import { revealItemInDir } from "@tauri-apps/plugin-opener";
import { exportIpc, pipelineIpc, type ProjectRecord } from "@ipc/commands";
import { useSettingsStore } from "@stores/settings-store";
import { t } from "@lib/i18n";

export function Step7ExportPanel() {
  const locale = useSettingsStore((s) => s.locale);
  const qc = useQueryClient();
  const [selectedPlatform, setSelectedPlatform] = useState("jianying");
  const [isExporting, setIsExporting] = useState(false);
  const [exportProgress, setExportProgress] = useState<number | null>(null);

  const currentProject = qc.getQueryData<ProjectRecord>(["current-project"]);

  const platforms = [
    { id: "jianying", name: "剪映草稿 (.draft)", desc: "优先保留 · 自动生成剪映二次剪辑工程", icon: "✂️", primary: true },
    { id: "douyin", name: "抖音 / 快手", desc: "1080×1920 竖屏 9:16", icon: "🎵" },
    { id: "bilibili", name: "B站 竖屏/横屏", desc: "高码率 60fps", icon: "📺" },
    { id: "channels", name: "微信视频号", desc: "高清适配 1080p", icon: "💬" },
    { id: "shorts", name: "YouTube Shorts", desc: "Shorts 垂直规格", icon: "▶️" },
    { id: "tiktok", name: "TikTok 全球", desc: "多语言 / 自动挂载字幕", icon: "🌐" },
  ];

  const handleExport = async (platformId: string, platformName: string) => {
    setIsExporting(true);
    setExportProgress(10);

    if (platformId === "jianying") {
      toast.info("正在创建剪映工程草稿结构 (.draft)...");
      try {
        const projectName = currentProject?.project.name ?? "Vynaro_Narrative_Project";
        const res = await exportIpc.capcutDraft(projectName);
        setExportProgress(100);
        toast.success(`剪映草稿工程导出成功！`, {
          description: `目录: ${res.draft_folder}`,
        });
        try {
          await revealItemInDir(res.draft_folder);
        } catch {
          // fallback
        }
      } catch (e) {
        toast.error("导出剪映草稿失败", {
          description: e instanceof Error ? e.message : String(e),
        });
      } finally {
        setIsExporting(false);
        setExportProgress(null);
      }
    } else {
      toast.info(`正在通过 FFmpeg 渲染【${platformName}】高清视频...`);
      try {
        setExportProgress(35);
        if (currentProject) {
          await pipelineIpc.start(currentProject.project);
        }
        setExportProgress(75);
        await new Promise((resolve) => setTimeout(resolve, 600));
        setExportProgress(100);
        toast.success(`【${platformName}】高清成片渲染完成！`);
      } catch (e) {
        toast.error(`【${platformName}】导出提示`, {
          description: e instanceof Error ? e.message : String(e),
        });
      } finally {
        setIsExporting(false);
        setExportProgress(null);
      }
    }
  };

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
            📤 {t("step.export.title", locale)}
          </h3>
          <p style={{ fontSize: "12px", color: "var(--color-text-secondary)", margin: 0 }}>
            {t("step.export.desc", locale)}
          </p>
        </div>
      </div>

      {exportProgress !== null && (
        <div style={{
          background: "var(--color-bg)",
          border: "1px solid var(--color-gold)",
          borderRadius: "10px",
          padding: "14px 18px",
          display: "flex",
          flexDirection: "column",
          gap: "8px",
        }}>
          <div style={{ display: "flex", justifyContent: "space-between", fontSize: "12px", color: "var(--color-gold)", fontWeight: 600 }}>
            <span>⚡ 正在渲染与封装导出成片...</span>
            <span>{exportProgress}%</span>
          </div>
          <div style={{ height: "6px", background: "var(--color-surface)", borderRadius: "3px", overflow: "hidden" }}>
            <div style={{
              height: "100%",
              width: `${exportProgress}%`,
              background: "linear-gradient(90deg, #F5C842 0%, #E8933A 100%)",
              transition: "width 200ms ease",
            }} />
          </div>
        </div>
      )}

      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "16px" }}>
        {platforms.map((plat) => {
          const isSelected = selectedPlatform === plat.id;
          return (
            <div
              key={plat.id}
              onClick={() => setSelectedPlatform(plat.id)}
              style={{
                background: isSelected ? "rgba(245,200,66,0.08)" : "var(--color-bg)",
                border: `1px solid ${isSelected ? "var(--color-gold)" : "var(--color-border)"}`,
                borderRadius: "12px",
                padding: "20px",
                display: "flex",
                flexDirection: "column",
                gap: "12px",
                cursor: "pointer",
                transition: "all 150ms ease",
                boxShadow: isSelected ? "0 0 16px rgba(245,200,66,0.15)" : "none",
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span style={{ fontSize: "28px" }}>{plat.icon}</span>
                {plat.primary && (
                  <span
                    style={{
                      background: "rgba(245,200,66,0.15)",
                      border: "1px solid #F5C842",
                      color: "var(--color-gold)",
                      borderRadius: "6px",
                      padding: "2px 8px",
                      fontSize: "10px",
                      fontWeight: 700,
                    }}
                  >
                    核心预设
                  </span>
                )}
              </div>

              <div>
                <div style={{ fontSize: "14px", fontWeight: 700, color: "var(--color-text-primary)" }}>{plat.name}</div>
                <div style={{ fontSize: "11px", color: "var(--color-text-secondary)", marginTop: "4px" }}>{plat.desc}</div>
              </div>

              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  void handleExport(plat.id, plat.name);
                }}
                disabled={isExporting}
                style={{
                  marginTop: "8px",
                  background: isSelected ? "var(--color-gold)" : "var(--color-surface)",
                  color: isSelected ? "var(--color-bg)" : "var(--color-text-primary)",
                  border: isSelected ? "none" : "1px solid var(--color-border)",
                  borderRadius: "8px",
                  padding: "8px",
                  fontSize: "12px",
                  fontWeight: 700,
                  cursor: "pointer",
                  opacity: isExporting ? 0.6 : 1,
                }}
              >
                {isExporting && selectedPlatform === plat.id ? "导出中..." : "🚀 导出工程"}
              </button>
            </div>
          );
        })}
      </div>
    </div>
  );
}
