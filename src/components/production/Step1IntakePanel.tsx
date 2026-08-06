/**
 * Vynaro v2.5.0 · Step 1: 素材导入详情面板
 */

import { useState } from "react";

interface Step1IntakePanelProps {
  mediaCount: number;
  onImportClick: () => void;
  onNext: () => void;
}

export function Step1IntakePanel({ mediaCount, onImportClick, onNext }: Step1IntakePanelProps) {
  const [selectedFormat, setSelectedFormat] = useState("all");

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
            📥 Step 1: 本地素材导入与预处理
          </h3>
          <p style={{ fontSize: "12px", color: "var(--color-text-secondary)", margin: 0 }}>
            选择或拖入本地影视/短剧片段，自动进行音视频分离、格式检测与首帧缩略图提取。
          </p>
        </div>
        <div style={{ display: "flex", gap: "10px" }}>
          <button
            type="button"
            className="btn-primary"
            onClick={onImportClick}
            style={{ display: "flex", alignItems: "center", gap: "6px" }}
          >
            <span>📂</span> 导入本地素材 ({mediaCount})
          </button>
        </div>
      </div>

      {/* 拖拽/状态区域 */}
      <div
        onClick={onImportClick}
        style={{
          border: "2px dashed rgba(245, 200, 66, 0.3)",
          borderRadius: "12px",
          padding: "40px",
          textAlign: "center",
          background: "rgba(245, 200, 66, 0.02)",
          cursor: "pointer",
          transition: "all 200ms ease",
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.borderColor = "var(--color-gold)";
          e.currentTarget.style.background = "rgba(245, 200, 66, 0.05)";
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.borderColor = "rgba(245, 200, 66, 0.3)";
          e.currentTarget.style.background = "rgba(245, 200, 66, 0.02)";
        }}
      >
        <div style={{ fontSize: "40px", marginBottom: "12px" }}>🎬</div>
        <div style={{ fontSize: "16px", fontWeight: 600, color: "var(--color-text-primary)", marginBottom: "6px" }}>
          点击或拖拽视频/音频文件到此处
        </div>
        <div style={{ fontSize: "12px", color: "var(--color-text-secondary)" }}>
          支持 MP4, MOV, AVI, WEBM, MP3, WAV 格式 · 本地安全处理无上传风险
        </div>
      </div>

      {/* 预处理设置与下一步 */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          borderTop: "1px solid #2A2A2F",
          paddingTop: "16px",
        }}
      >
        <div style={{ display: "flex", gap: "16px", alignItems: "center" }}>
          <span style={{ fontSize: "13px", color: "var(--color-text-secondary)" }}>解析格式:</span>
          <select
            value={selectedFormat}
            onChange={(e) => setSelectedFormat(e.target.value)}
            style={{
              background: "var(--color-bg)",
              border: "1px solid #2A2A2F",
              color: "var(--color-text-primary)",
              padding: "6px 12px",
              borderRadius: "8px",
              fontSize: "13px",
            }}
          >
            <option value="all">自动识别全部格式</option>
            <option value="mp4">仅 MP4 容器</option>
            <option value="mov">仅 MOV 容器</option>
          </select>
        </div>
        <button type="button" className="btn-primary" onClick={onNext}>
          进入 Step 2: 智能拆条 →
        </button>
      </div>
    </div>
  );
}
