/**
 * Monoloop v1.0.0 · Step 4: TTS 配音与人声克隆详情面板
 * 修复:
 * - requestAnimationFrame 驱动实时波形动画
 * - Tauri 文件选择器真实选取参考音频 (人声克隆)
 * - GPT-SoVITS 正确传递 ref_audio_path / prompt_text
 * - 克隆模式未上传时禁用试听
 */

import { useEffect, useRef, useState, useCallback } from "react";
import { toast } from "sonner";
import { convertFileSrc } from "@tauri-apps/api/core";
import { open as openFileDialog } from "@tauri-apps/plugin-dialog";
import { voiceIpc } from "@ipc/commands";
import { useSettingsStore } from "@stores/settings-store";
import { t } from "@lib/i18n";
import { AudioWaveformVisualizer } from "./AudioWaveformVisualizer";

interface Step4VoicePanelProps {
  onNext: () => void;
}

export function Step4VoicePanel({ onNext }: Step4VoicePanelProps) {
  const locale = useSettingsStore((s) => s.locale);
  const [selectedVoice, setSelectedVoice] = useState("zh-CN-XiaoxiaoNeural");
  const [engine, setEngine] = useState<"edge" | "open-ai" | "gpt-sovits">("edge");
  const [speed, setSpeed] = useState(1.0);
  const [pitch, setPitch] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [previewText, setPreviewText] = useState("欢迎使用 Monoloop 叙影 AI 智能解说，体验第一人称沉浸式配音效果。");
  const audioRef = useRef<HTMLAudioElement | null>(null);

  // 克隆音色
  const [refAudioPath, setRefAudioPath] = useState<string | null>(null);
  const [refAudioName, setRefAudioName] = useState<string | null>(null);
  const [clonePromptText, setClonePromptText] = useState("");

  // GPT-SoVITS 本地服务健康探针
  const [sovitsHealth, setSovitsHealth] = useState<"checking" | "online" | "offline">("checking");

  const checkSovitsHealth = useCallback(async () => {
    setSovitsHealth("checking");
    try {
      const res = await fetch("http://127.0.0.1:9880/", { method: "HEAD" }).catch(() => null);
      if (res && (res.ok || res.status === 404 || res.status === 405 || res.status === 200)) {
        setSovitsHealth("online");
      } else {
        setSovitsHealth("offline");
      }
    } catch {
      setSovitsHealth("offline");
    }
  }, []);

  useEffect(() => {
    if (selectedVoice === "clone_voice" || engine === "gpt-sovits") {
      void checkSovitsHealth();
    }
  }, [selectedVoice, engine, checkSovitsHealth]);

  const voiceList = [
    { id: "zh-CN-XiaoxiaoNeural", name: "晓晓", sub: "灵动女声", icon: "👩", clone: false },
    { id: "zh-CN-YunxiNeural", name: "云希", sub: "沉稳男声", icon: "👨‍💼", clone: false },
    { id: "zh-CN-YunjianNeural", name: "云健", sub: "激情叙事", icon: "🎙️", clone: false },
    { id: "zh-CN-XiaoyiNeural", name: "晓伊", sub: "温婉女述", icon: "👩‍💼", clone: false },
    { id: "clone_voice", name: "克隆音色", sub: "GPT-SoVITS", icon: "🧬", clone: true },
  ];

  const isCloneMode = selectedVoice === "clone_voice";
  const canPreview = !isGenerating && (!isCloneMode || !!refAudioPath);

  const handlePickRefAudio = async (e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      const selected = await openFileDialog({
        title: "选择参考音频 (3~10 秒清晰人声)",
        filters: [{ name: "音频", extensions: ["wav", "mp3", "flac", "ogg"] }],
        multiple: false,
      });
      if (selected && typeof selected === "string") {
        setRefAudioPath(selected);
        const fileName = selected.split(/[/\\]/).pop() ?? selected;
        setRefAudioName(fileName);
        setEngine("gpt-sovits");
        setSelectedVoice("clone_voice");
        toast.success(`参考音频已加载: ${fileName}`);
      }
    } catch (err) {
      toast.error("选择文件失败", { description: err instanceof Error ? err.message : String(err) });
    }
  };

  const handlePreviewVoice = async (voiceId?: string) => {
    const targetVoice = voiceId ?? selectedVoice;
    const isClone = targetVoice === "clone_voice";

    if (isClone && !refAudioPath) {
      toast.error("请先上传参考音频", { description: "点击「↑ 上传音频」选择 3~10 秒清晰人声文件" });
      return;
    }
    if (!previewText.trim()) { toast.error("请输入试听文本"); return; }

    if (audioRef.current) { audioRef.current.pause(); audioRef.current = null; }
    setIsPlaying(false);

    const ratePercent = Math.round((speed - 1.0) * 100);
    const actualEngine = isClone ? "gpt-sovits" : engine;
    const actualVoice = isClone ? null : targetVoice;

    setIsGenerating(true);
    toast.info(`正在合成 TTS 试听 (${actualEngine})...`);

    try {
      const result = await voiceIpc.preview({
        text: previewText,
        provider: actualEngine,
        voice: actualVoice,
        rate_percent: ratePercent,
        api_key: null,
        base_url: null,
        model: null,
        ref_audio_path: isClone ? refAudioPath : null,
        prompt_text: isClone && clonePromptText.trim() ? clonePromptText.trim() : null,
      });

      const src = convertFileSrc(result.file_path);
      setAudioUrl(src);
      const audio = new Audio(src);
      audioRef.current = audio;
      audio.onended = () => setIsPlaying(false);
      audio.onerror = () => { setIsPlaying(false); toast.error("音频播放失败，请检查系统音频输出"); };
      await audio.play();
      setIsPlaying(true);
      toast.success(`试听播放中 (${result.format.toUpperCase()}, ${(result.bytes_written / 1024).toFixed(1)} KB)`);
    } catch (e) {
      toast.error("TTS 试听合成失败", { description: e instanceof Error ? e.message : String(e) });
    } finally {
      setIsGenerating(false);
    }
  };

  const togglePlay = () => {
    if (isGenerating) return;
    if (!audioRef.current) { void handlePreviewVoice(); return; }
    if (isPlaying) { audioRef.current.pause(); setIsPlaying(false); }
    else { void audioRef.current.play().then(() => setIsPlaying(true)); }
  };

  return (
    <div style={{ background: "var(--color-surface)", border: "1px solid var(--color-border)", borderRadius: "14px", padding: "24px", display: "flex", flexDirection: "column", gap: "20px" }}>
      {/* 标题 */}
      <div>
        <h3 style={{ fontSize: "18px", fontWeight: 700, color: "var(--color-gold)", margin: "0 0 4px" }}>
          🎙️ {t("step.voice.title", locale)}
        </h3>
        <p style={{ fontSize: "12px", color: "var(--color-text-secondary)", margin: 0 }}>
          {t("step.voice.desc", locale)}
        </p>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 280px", gap: "20px" }}>
        {/* 左侧 */}
        <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>

          {/* 音色卡片 */}
          <div>
            <div style={{ fontSize: "13px", fontWeight: 600, color: "var(--color-text-primary)", marginBottom: "12px" }}>
              {t("voice.voice_select", locale)}
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: "10px" }}>
              {voiceList.map((voice) => {
                const isSelected = selectedVoice === voice.id;
                return (
                  <div
                    key={voice.id}
                    onClick={() => { setSelectedVoice(voice.id); if (!voice.clone) void handlePreviewVoice(voice.id); }}
                    style={{
                      background: isSelected ? "rgba(245,200,66,0.08)" : "var(--color-bg)",
                      border: `1px solid ${isSelected ? "var(--color-gold)" : "var(--color-border)"}`,
                      borderRadius: "12px", padding: "16px 10px",
                      display: "flex", flexDirection: "column", alignItems: "center", gap: "8px",
                      cursor: "pointer", transition: "all 150ms ease",
                      boxShadow: isSelected ? "0 0 16px rgba(245,200,66,0.2)" : "none",
                    }}
                  >
                    <div style={{
                      width: 44, height: 44, borderRadius: "50%",
                      background: voice.clone ? "rgba(245,200,66,0.15)" : "var(--color-surface)",
                      border: `1px solid ${isSelected ? "var(--color-gold)" : "var(--color-border)"}`,
                      display: "flex", alignItems: "center", justifyContent: "center",
                      fontSize: "22px", position: "relative",
                    }}>
                      {voice.icon}
                      {voice.clone && refAudioPath && (
                        <div style={{ position: "absolute", bottom: -2, right: -2, width: 14, height: 14, borderRadius: "50%", background: "#22c55e", border: "2px solid var(--color-bg)", fontSize: "8px", display: "flex", alignItems: "center", justifyContent: "center", color: "white" }}>✓</div>
                      )}
                    </div>
                    <div style={{ textAlign: "center" }}>
                      <div style={{ fontSize: "12px", fontWeight: 600, color: isSelected ? "var(--color-gold)" : "var(--color-text-primary)" }}>{voice.name}</div>
                      <div style={{ fontSize: "10px", color: "var(--color-text-muted)" }}>
                        {voice.clone && refAudioName ? (refAudioName.length > 7 ? refAudioName.slice(0,6)+"…" : refAudioName) : voice.sub}
                      </div>
                    </div>
                    {voice.clone ? (
                      <button type="button" onClick={handlePickRefAudio} style={{ fontSize: "10px", background: refAudioPath ? "rgba(34,197,94,0.15)" : "rgba(245,200,66,0.15)", color: refAudioPath ? "#22c55e" : "var(--color-gold)", border: `1px solid ${refAudioPath ? "rgba(34,197,94,0.4)" : "rgba(245,200,66,0.3)"}`, borderRadius: "6px", padding: "3px 8px", cursor: "pointer", whiteSpace: "nowrap" }}>
                        {refAudioPath ? "✓ 已选择" : "↑ 上传音频"}
                      </button>
                    ) : (
                      <button type="button" onClick={(e) => { e.stopPropagation(); void handlePreviewVoice(voice.id); }} disabled={isGenerating} style={{ fontSize: "10px", background: "var(--color-surface)", color: "var(--color-gold)", border: "1px solid rgba(245,200,66,0.3)", borderRadius: "6px", padding: "3px 8px", cursor: isGenerating ? "not-allowed" : "pointer", opacity: isGenerating ? 0.5 : 1 }}>
                        ▶ 试听
                      </button>
                    )}
                  </div>
                );
              })}
            </div>
          </div>

          {/* 克隆配置面板 */}
          {isCloneMode && (
            <div style={{ background: "rgba(245,200,66,0.05)", border: "1px solid rgba(245,200,66,0.2)", borderRadius: "10px", padding: "14px 16px", display: "flex", flexDirection: "column", gap: "10px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <div style={{ fontSize: "12px", fontWeight: 600, color: "var(--color-gold)" }}>🧬 GPT-SoVITS 克隆配置</div>
                <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                  <span style={{
                    fontSize: "10px",
                    fontWeight: 600,
                    padding: "2px 8px",
                    borderRadius: "10px",
                    background: sovitsHealth === "online" ? "rgba(34,197,94,0.15)" : sovitsHealth === "checking" ? "rgba(245,200,66,0.15)" : "rgba(239,68,68,0.15)",
                    color: sovitsHealth === "online" ? "#22c55e" : sovitsHealth === "checking" ? "var(--color-gold)" : "#ef4444",
                    border: `1px solid ${sovitsHealth === "online" ? "rgba(34,197,94,0.3)" : sovitsHealth === "checking" ? "rgba(245,200,66,0.3)" : "rgba(239,68,68,0.3)"}`,
                  }}>
                    {sovitsHealth === "online" ? "🟢 服务在线 (127.0.0.1:9880)" : sovitsHealth === "checking" ? "⏳ 检测中..." : "🔴 服务未启动"}
                  </span>
                  <button
                    type="button"
                    onClick={() => void checkSovitsHealth()}
                    style={{ fontSize: "10px", background: "var(--color-surface)", border: "1px solid var(--color-border)", color: "var(--color-text-secondary)", borderRadius: "6px", padding: "2px 6px", cursor: "pointer" }}
                  >
                    🔄 重新检测
                  </button>
                </div>
              </div>
              {refAudioPath ? (
                <div style={{ fontSize: "11px", color: "var(--color-text-muted)", display: "flex", alignItems: "center", gap: "6px" }}>
                  <span>参考音频:</span>
                  <span style={{ color: "var(--color-text-primary)" }}>{refAudioName}</span>
                  <button type="button" onClick={() => { setRefAudioPath(null); setRefAudioName(null); }} style={{ fontSize: "10px", color: "#ef4444", background: "none", border: "none", cursor: "pointer", padding: 0 }}>✕ 移除</button>
                </div>
              ) : (
                <div style={{ fontSize: "11px", color: "#f59e0b" }}>⚠️ 请上传 3~10 秒清晰人声参考音频以启用克隆</div>
              )}
              <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
                <label style={{ fontSize: "11px", color: "var(--color-text-secondary)" }}>参考音频文本 (可选，提升精准度)</label>
                <input type="text" value={clonePromptText} onChange={(e) => setClonePromptText(e.target.value)} placeholder="参考音频中说话的具体文字..." style={{ background: "var(--color-bg)", border: "1px solid var(--color-border)", borderRadius: "6px", padding: "6px 10px", fontSize: "12px", color: "var(--color-text-primary)", outline: "none" }} />
              </div>
            </div>
          )}

          {/* 试听文本 */}
          <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
            <label style={{ fontSize: "12px", color: "var(--color-text-secondary)" }}>试听文本</label>
            <input type="text" value={previewText} onChange={(e) => setPreviewText(e.target.value)} placeholder="输入需要测试配音效果的句段..." style={{ background: "var(--color-bg)", border: "1px solid var(--color-border)", borderRadius: "8px", padding: "8px 12px", fontSize: "13px", color: "var(--color-text-primary)", outline: "none" }} />
          </div>

          {/* 实时波形播放器 */}
          <div style={{ background: "var(--color-bg)", border: "1px solid var(--color-border)", borderRadius: "12px", padding: "16px 20px", display: "flex", flexDirection: "column", gap: "12px" }}>
            <div style={{ fontSize: "13px", fontWeight: 600, color: "var(--color-text-primary)", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span>实时波形预览 (Web Audio Spectrum)</span>
              <span style={{ fontSize: "11px", color: isPlaying ? "var(--color-gold)" : "var(--color-text-muted)" }}>
                {isGenerating ? "⏳ 合成中..." : isPlaying ? "▶ 播放中" : audioUrl ? "⏹ 已就绪" : "等待试听"}
              </span>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: "16px" }}>
              <button type="button" onClick={togglePlay} disabled={isGenerating || (isCloneMode && !refAudioPath)} title={isCloneMode && !refAudioPath ? "请先上传参考音频" : undefined} style={{ width: 48, height: 48, borderRadius: "50%", flexShrink: 0, background: canPreview ? "linear-gradient(135deg, #F5C842 0%, #E8933A 100%)" : "var(--color-surface)", border: canPreview ? "none" : "1px solid var(--color-border)", color: canPreview ? "#1A1A1F" : "var(--color-text-muted)", fontSize: "18px", display: "flex", alignItems: "center", justifyContent: "center", cursor: canPreview ? "pointer" : "not-allowed", transition: "all 200ms ease", boxShadow: canPreview && isPlaying ? "0 0 24px rgba(245,200,66,0.45)" : "none" }}>
                {isGenerating ? "⏳" : isPlaying ? "⏸" : "▶"}
              </button>
              <div style={{ flex: 1 }}>
                <AudioWaveformVisualizer audioRef={audioRef} isPlaying={isPlaying} height={54} barCount={52} />
              </div>
            </div>
          </div>
        </div>

        {/* 右侧控制 */}
        <div style={{ background: "var(--color-bg)", border: "1px solid var(--color-border)", borderRadius: "12px", padding: "20px", display: "flex", flexDirection: "column", gap: "16px" }}>
          <div>
            <label style={{ fontSize: "12px", color: "var(--color-text-secondary)", display: "block", marginBottom: "8px", fontWeight: 600 }}>TTS 引擎</label>
            <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
              {[
                { id: "edge", label: "Edge-TTS", sub: "微软免费 · 无需密钥" },
                { id: "open-ai", label: "OpenAI-TTS", sub: "gpt-4o-mini-tts · 需 API Key" },
                { id: "gpt-sovits", label: "GPT-SoVITS", sub: "人声克隆 · 本地推理" },
              ].map((item) => (
                <label key={item.id} style={{ fontSize: "12px", color: "var(--color-text-primary)", display: "flex", alignItems: "flex-start", gap: "8px", cursor: "pointer", padding: "8px 10px", borderRadius: "8px", background: engine === item.id ? "rgba(245,200,66,0.06)" : "transparent", border: engine === item.id ? "1px solid rgba(245,200,66,0.2)" : "1px solid transparent", transition: "all 150ms ease" }}>
                  <input type="radio" name="engine" checked={engine === item.id} onChange={() => setEngine(item.id as "edge" | "open-ai" | "gpt-sovits")} style={{ accentColor: "var(--color-gold)", marginTop: "2px" }} />
                  <div>
                    <div style={{ fontWeight: 600 }}>{item.label}</div>
                    <div style={{ fontSize: "10px", color: "var(--color-text-muted)" }}>{item.sub}</div>
                  </div>
                </label>
              ))}
            </div>
          </div>

          <div>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "6px" }}>
              <span style={{ fontSize: "12px", color: "var(--color-text-secondary)" }}>语速</span>
              <span style={{ fontSize: "12px", color: "var(--color-gold)", fontWeight: 600 }}>{speed.toFixed(1)}x</span>
            </div>
            <input type="range" min="0.5" max="2.0" step="0.1" value={speed} onChange={(e) => setSpeed(parseFloat(e.target.value))} style={{ width: "100%", accentColor: "var(--color-gold)" }} />
          </div>

          <div>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "6px" }}>
              <span style={{ fontSize: "12px", color: "var(--color-text-secondary)" }}>音调</span>
              <span style={{ fontSize: "12px", color: "var(--color-gold)", fontWeight: 600 }}>{pitch > 0 ? `+${pitch}` : pitch}</span>
            </div>
            <input type="range" min="-12" max="12" value={pitch} onChange={(e) => setPitch(parseInt(e.target.value))} style={{ width: "100%", accentColor: "var(--color-gold)" }} />
          </div>

          <div style={{ marginTop: "auto", padding: "10px", borderRadius: "8px", background: "var(--color-surface)", border: "1px solid var(--color-border)", fontSize: "11px", color: "var(--color-text-muted)" }}>
            <div style={{ fontWeight: 600, color: "var(--color-text-secondary)", marginBottom: "4px" }}>当前配置</div>
            <div>引擎: <span style={{ color: "var(--color-text-primary)" }}>{engine}</span></div>
            <div>音色: <span style={{ color: "var(--color-text-primary)" }}>{isCloneMode ? (refAudioPath ? `克隆 · ${refAudioName}` : "克隆 (待上传)") : selectedVoice}</span></div>
            {audioUrl && <div style={{ color: "#22c55e", marginTop: "4px" }}>✓ 已有试听缓存</div>}
          </div>
        </div>
      </div>

      {/* 底部操作条 */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", borderTop: "1px solid var(--color-border)", paddingTop: "16px" }}>
        <button type="button" className="btn-primary" onClick={() => void handlePreviewVoice()} disabled={!canPreview} title={isCloneMode && !refAudioPath ? "请先上传参考音频" : undefined} style={{ padding: "12px 32px", fontSize: "15px", opacity: canPreview ? 1 : 0.5, cursor: canPreview ? "pointer" : "not-allowed" }}>
          {isGenerating ? "⏳ 合成中..." : "🎙️ 合成全部配音"}
        </button>
        <button type="button" className="btn-primary" onClick={onNext}>进入 Step 5: 字幕合成 →</button>
      </div>
    </div>
  );
}
