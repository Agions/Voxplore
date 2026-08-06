/**
 * Vynaro v1.0.0 · Step 3: AI 第一人称脚本生成详情面板
 * 真实连通 vynaro-script (Qwen 3.7 / DeepSeek / GPT-4o 等 11 个 LLM 引擎)
 */

import { useState } from "react";
import { toast } from "sonner";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "@tanstack/react-router";
import { scriptIpc, settingsIpc } from "@ipc/commands";
import { useSettingsStore } from "@stores/settings-store";
import { t } from "@lib/i18n";

interface Step3ScriptPanelProps {
  onNext: () => void;
}

export function Step3ScriptPanel({ onNext }: Step3ScriptPanelProps) {
  const locale = useSettingsStore((s) => s.locale);
  const qc = useQueryClient();
  const [provider, setProvider] = useState("qwen");
  const [styleTab, setStyleTab] = useState<"immersive" | "critic" | "story" | "roast">("immersive");
  const [emotionDensity, setEmotionDensity] = useState(80);
  const [wordCount, setWordCount] = useState(800);
  const [userPrompt, setUserPrompt] = useState("");
  const [isGenerating, setIsGenerating] = useState(false);
  const [scriptContent, setScriptContent] = useState("");

  const { data: config } = useQuery({
    queryKey: ["app-config-settings"],
    queryFn: settingsIpc.get,
  });

  const hasApiKey = Boolean(config?.llm_api_key && config.llm_api_key.trim().length > 0);
  const isLocalProvider = provider === "local";

  const handleRegenerate = async () => {
    if (!isLocalProvider && !hasApiKey) {
      toast.error("未检测到 API Key，请先配置 Key 沉浸式生成脚本", {
        description: "点击上方「前往设置页配置 Key」进行填写",
      });
      return;
    }
    if (!userPrompt.trim()) {
      toast.error("请输入提示词");
      return;
    }

    setIsGenerating(true);
    toast.info("正在使用 LLM 生成第一人称独白脚本...");

    try {
      const res = await scriptIpc.generate({
        provider,
        api_key: config?.llm_api_key ?? null,
        base_url: config?.llm_base_url ?? null,
        model: config?.llm_model ?? null,
        prompt: userPrompt,
        style: styleTab,
        emotion_density: emotionDensity / 100,
        word_count_target: wordCount,
      });

      setScriptContent(res.text);
      // 将脚本内容写入共享缓存，Step5 字幕面板可读取
      qc.setQueryData(["step3-script-content"], res.text);
      toast.success(`脚本生成成功！共 ${res.word_count} 字，预估配音时长 ${res.estimated_duration_sec} 秒`);
    } catch (e) {
      toast.error("生成失败", {
        description: e instanceof Error ? e.message : String(e),
      });
    } finally {
      setIsGenerating(false);
    }
  };

  const handleCopy = () => {
    navigator.clipboard.writeText(scriptContent);
    toast.success("已复制脚本文本到剪贴板");
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
            🤖 {t("step.script.title", locale)}
          </h3>
          <p style={{ fontSize: "12px", color: "var(--color-text-secondary)", margin: 0 }}>
            {t("step.script.desc", locale)}
          </p>
        </div>
      </div>

      {!isLocalProvider && !hasApiKey && (
        <div style={{
          background: "rgba(245,200,66,0.06)",
          border: "1px solid rgba(245,200,66,0.3)",
          borderRadius: "10px",
          padding: "12px 16px",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
        }}>
          <div style={{ fontSize: "12px", color: "var(--color-gold)", display: "flex", alignItems: "center", gap: "8px" }}>
            <span>⚠️</span>
            <span>未检测到 API Key，无法调用线上 LLM 生成脚本。请先配置 API Key 或切换为本地模型模式。</span>
          </div>
          <Link
            to="/settings"
            style={{
              fontSize: "11px",
              fontWeight: 600,
              color: "var(--color-bg)",
              background: "var(--color-gold)",
              borderRadius: "6px",
              padding: "5px 12px",
              textDecoration: "none",
              whiteSpace: "nowrap",
            }}
          >
            ⚙️ 前往设置页配置 Key →
          </Link>
        </div>
      )}

      {/* 提示词输入区 */}
      <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
        <label style={{ fontSize: "12px", color: "var(--color-text-secondary)" }}>{t("script.prompt_label", locale)}</label>
        <input
          type="text"
          value={userPrompt}
          onChange={(e) => setUserPrompt(e.target.value)}
          placeholder="输入剧本核心梗概、情感走向或主角特点..."
          style={{
            background: "var(--color-bg)",
            border: "1px solid #2A2A2F",
            borderRadius: "8px",
            padding: "10px 14px",
            fontSize: "14px",
            color: "var(--color-text-primary)",
            outline: "none",
          }}
        />
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 340px", gap: "20px" }}>
        {/* 左侧脚本编辑器 */}
        <div
          style={{
            background: "var(--color-bg)",
            border: "1px solid #2A2A2F",
            borderRadius: "12px",
            padding: "20px",
            display: "flex",
            flexDirection: "column",
            gap: "16px",
            position: "relative",
          }}
        >
          <div style={{ fontSize: "12px", color: "var(--color-text-secondary)", fontWeight: 600 }}>脚本编排预览</div>

          <textarea
            value={scriptContent}
            onChange={(e) => setScriptContent(e.target.value)}
            rows={12}
            placeholder="点击「重新生成脚本」让 AI 生成解说文案，或在此直接输入/编辑脚本内容..."
            style={{
              width: "100%",
              background: "transparent",
              border: "none",
              color: "var(--color-text-primary)",
              fontSize: "14px",
              lineHeight: 1.8,
              resize: "none",
              outline: "none",
            }}
          />
        </div>

        {/* 右侧参数面板 */}
        <div
          style={{
            background: "var(--color-bg)",
            border: "1px solid #2A2A2F",
            borderRadius: "12px",
            padding: "20px",
            display: "flex",
            flexDirection: "column",
            gap: "20px",
          }}
        >
          {/* LLM Provider */}
          <div>
            <label style={{ fontSize: "12px", color: "var(--color-text-secondary)", display: "block", marginBottom: "8px" }}>
              LLM Provider
            </label>
            <select
              value={provider}
              onChange={(e) => setProvider(e.target.value)}
              style={{
                width: "100%",
                background: "var(--color-surface)",
                border: "1px solid #2A2A2F",
                color: "var(--color-text-primary)",
                padding: "8px 12px",
                borderRadius: "8px",
                fontSize: "14px",
              }}
            >
              <option value="qwen">通义千问 (qwen3.8-max 推荐)</option>
              <option value="open-ai">OpenAI (gpt-5.6-sol 旗舰款)</option>
              <option value="claude">Claude (claude-sonnet-5)</option>
              <option value="deepseek">DeepSeek (deepseek-v4-pro)</option>
              <option value="gemini">Gemini (gemini-3.6-flash)</option>
            </select>
          </div>

          {/* 风格 Tabs */}
          <div>
            <label style={{ fontSize: "12px", color: "var(--color-text-secondary)", display: "block", marginBottom: "8px" }}>
              解说风格
            </label>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "6px" }}>
              {[
                { id: "immersive", label: "第一人称沉浸" },
                { id: "critic", label: "影评解析" },
                { id: "story", label: "故事化叙述" },
                { id: "roast", label: "轻松吐槽" },
              ].map((tab) => (
                <button
                  key={tab.id}
                  type="button"
                  onClick={() => setStyleTab(tab.id as any)}
                  style={{
                    padding: "8px",
                    borderRadius: "6px",
                    fontSize: "12px",
                    border: styleTab === tab.id ? "1px solid #F5C842" : "1px solid #2A2A2F",
                    background: styleTab === tab.id ? "rgba(245,200,66,0.1)" : "var(--color-surface)",
                    color: styleTab === tab.id ? "var(--color-gold)" : "var(--color-text-secondary)",
                    cursor: "pointer",
                    transition: "all 150ms ease",
                  }}
                >
                  {tab.label}
                </button>
              ))}
            </div>
          </div>

          {/* 情绪密度 Slider */}
          <div>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "6px" }}>
              <span style={{ fontSize: "12px", color: "var(--color-text-secondary)" }}>情绪密度</span>
              <span style={{ fontSize: "12px", color: "var(--color-gold)", fontWeight: 600 }}>{emotionDensity}%</span>
            </div>
            <input
              type="range"
              min="10"
              max="100"
              value={emotionDensity}
              onChange={(e) => setEmotionDensity(parseInt(e.target.value))}
              style={{ width: "100%", accentColor: "var(--color-gold)" }}
            />
          </div>

          {/* 字数控制 Input */}
          <div>
            <label style={{ fontSize: "12px", color: "var(--color-text-secondary)", display: "block", marginBottom: "6px" }}>
              目标字数控制
            </label>
            <input
              type="number"
              value={wordCount}
              onChange={(e) => setWordCount(parseInt(e.target.value))}
              style={{
                width: "100%",
                background: "var(--color-surface)",
                border: "1px solid #2A2A2F",
                color: "var(--color-text-primary)",
                padding: "8px 12px",
                borderRadius: "8px",
                fontSize: "14px",
              }}
            />
          </div>
        </div>
      </div>

      {/* 底部按钮条 */}
      <div
        style={{
          display: "flex",
          justifyContent: "flex-end",
          gap: "12px",
          borderTop: "1px solid #2A2A2F",
          paddingTop: "16px",
        }}
      >
        <button
          type="button"
          className="btn-primary"
          onClick={handleRegenerate}
          disabled={isGenerating}
          style={{ display: "flex", alignItems: "center", gap: "6px" }}
        >
          <span>🔄</span> {isGenerating ? "生成中..." : "重新生成脚本"}
        </button>
        <button type="button" className="btn-secondary" onClick={handleCopy}>
          📋 复制文本
        </button>
        <button type="button" className="btn-primary" onClick={onNext}>
          进入 Step 4: TTS 配音 →
        </button>
      </div>
    </div>
  );
}
