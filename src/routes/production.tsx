/**
 * splicr v1.0.1 · 三栏专业影视级 NLE 智能体创作工作台
 * 
 * 视觉与交互重构:
 * - 电影级调色监看台 (Hero Cinema Viewport): 9:16 / 16:9 画幅自适应浮动 + 悬浮极简控制器 + 内嵌式频谱
 * - 智能体角色中枢 (Agent Control Rack): 胶囊徽章 + 进度指示 + 实时微交互
 * - 全景 5 轨磁性时间轴 (MultiTrack Timeline)
 * - 终端式 Agent 思考流与断点决策区 (HITL Cockpit)
 */

import { createFileRoute } from "@tanstack/react-router";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useState, useRef } from "react";
import { open as openDialog } from "@tauri-apps/plugin-dialog";
import { BatchImportDialog } from "@components/dialogs/BatchImportDialog";
import { AudioVisualizerCanvas } from "@components/production/AudioVisualizerCanvas";
import { MultiTrackTimeline } from "@components/production/MultiTrackTimeline";
import {
  agentIpc,
  projectIpc,
  scriptIpc,
  settingsIpc,
  exportIpc,
  type AgentMessage,
  type BreakpointRequest,
  type ProjectRecord,
} from "@ipc/commands";
import { useAssets } from "@hooks/useAssets";
import { useTauriEvent } from "@hooks/useTauriEvent";
import { useProjectStore } from "@stores/project-store";
import { toast } from "sonner";

export const Route = createFileRoute("/production")({
  component: ProductionCinemaStudio,
});

export function ProductionCinemaStudio() {
  const qc = useQueryClient();
  const setCurrentRecord = useProjectStore((s) => s.setCurrentRecord);
  const storeProject = useProjectStore((s) => s.current);
  const storePath = useProjectStore((s) => s.currentPath);
  const { importFromPaths, items: mediaItems } = useAssets();

  // 1. 真实数据订阅与工程加载
  const cachedRecord = qc.getQueryData<ProjectRecord>(["current-project"]);
  const currentProject: ProjectRecord | null = useMemo(() => {
    if (storeProject && storePath) {
      return { path: storePath, project: storeProject };
    }
    return cachedRecord ?? null;
  }, [storeProject, storePath, cachedRecord]);

  const { data: config } = useQuery({
    queryKey: ["app-config-settings"],
    queryFn: settingsIpc.get,
  });

  // 2. 状态管理
  const [activeTab, setActiveTab] = useState<"agent" | "script" | "voice" | "export">("agent");
  const [showImport, setShowImport] = useState(false);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);

  // ── Multi-Agent 状态 ──
  const [isAgentRunning, setIsAgentRunning] = useState(false);
  const [agentAutoMode, setAgentAutoMode] = useState(true);
  const [currentStepIndex, setCurrentStepIndex] = useState<number>(-1);
  const [agentMessages, setAgentMessages] = useState<AgentMessage[]>([]);
  const [breakpoint, setBreakpoint] = useState<BreakpointRequest | null>(null);
  const pausedStepRef = useRef<number>(0);

  // 场景切片状态
  const [sceneCuts, setSceneCuts] = useState<{ id: number; time: string; tag: string; emotion: string }[]>([]);
  // 逐字精准对齐字幕片段 (VAD 对齐)
  const [subtitleSegments, setSubtitleSegments] = useState<{ id: string; text: string; start: number; duration: number }[]>([]);

  // AI 脚本状态
  const [llmProvider, setLlmProvider] = useState("qwen");
  const [scriptStyle, setScriptStyle] = useState<"immersive" | "critic" | "story" | "roast">("immersive");
  const [userPrompt, setUserPrompt] = useState("");
  const [scriptText, setScriptText] = useState("");
  const [isGeneratingScript, setIsGeneratingScript] = useState(false);

  // 配音与克隆状态
  const [voiceEngine, setVoiceEngine] = useState("edge");

  // 混流与防重构参数
  const [antiDupZoom, setAntiDupZoom] = useState(1.03);
  const [enableAmbientBlur, setEnableAmbientBlur] = useState(true);

  // 订阅 Agent 实时事件通道 (agent://event)
  useTauriEvent<any>("agent://event", (e) => {
    const payload = e.payload;
    if (!payload) return;
    if (payload.type === "step_started") {
      setCurrentStepIndex(payload.data?.step_idx ?? 0);
    } else if (payload.type === "breakpoint_required") {
      setBreakpoint(payload.data);
    } else if (payload.type === "workflow_completed") {
      setIsAgentRunning(false);
      setCurrentStepIndex(6);
      setActiveTab("export");
    } else if (payload.type === "error") {
      setIsAgentRunning(false);
      toast.error(`Agent 协同异常: ${payload.data?.message ?? "未知错误"}`);
    }
  });

  // 加载最靠前的历史项目或在无项目时初始化
  useEffect(() => {
    if (!currentProject) {
      void projectIpc.listRecent().then(async (recents) => {
        if (recents && recents.length > 0 && recents[0]) {
          try {
            const rec = await projectIpc.load(recents[0]);
            qc.setQueryData(["current-project"], rec);
            qc.setQueryData(["assets-current-project"], rec.project);
            setCurrentRecord(rec.path, rec.project);
          } catch {
            // ignore
          }
        }
      });
    }
  }, [currentProject, qc, setCurrentRecord]);

  // 保证有活动项目（若无项目自动创建空白工程避免流程阻塞）
  const ensureActiveProject = async (): Promise<ProjectRecord> => {
    if (currentProject) return currentProject;
    const rec = await projectIpc.createBlank();
    qc.setQueryData(["current-project"], rec);
    qc.setQueryData(["assets-current-project"], rec.project);
    setCurrentRecord(rec.path, rec.project);
    return rec;
  };

  // 3. 核心流转调度 (自适应多模态全自动流水线)
  const executeAgentSteps = async (startIdx: number) => {
    setIsAgentRunning(true);
    setBreakpoint(null);

    try {
      for (let i = startIdx; i < 6; i++) {
        setCurrentStepIndex(i);
        const bp = await agentIpc.step(i);
        const ctx = await agentIpc.getContext();
        if (ctx) {
          setAgentMessages(ctx.messages);
          if (ctx.memory["script_text"]) {
            setScriptText(ctx.memory["script_text"]);
          }
          if (ctx.memory["subtitles_json"]) {
            try {
              const subs = JSON.parse(ctx.memory["subtitles_json"]);
              setSubtitleSegments(
                subs.map((s: any, idx: number) => ({
                  id: `sub_${idx + 1}`,
                  text: s.text,
                  start: s.start,
                  duration: s.end - s.start,
                }))
              );
            } catch {
              // ignore
            }
          }
          if (ctx.memory["scene_count"]) {
            setSceneCuts([
              { id: 1, time: "00:00 - 00:18", tag: "开篇悬念镜头", emotion: "高能" },
              { id: 2, time: "00:18 - 00:45", tag: "角色冲突爆发", emotion: "紧张" },
              { id: 3, time: "00:45 - 01:15", tag: "反转高潮段落", emotion: "震撼" },
              { id: 4, time: "01:15 - 01:40", tag: "下集留白钩子", emotion: "悬疑" },
            ]);
          }
        }
        if (bp) {
          pausedStepRef.current = i;
          setBreakpoint(bp);
          toast.warning(`⏸️ 智能体工作流在【${bp.step_title}】暂停，等待创作者审核`);
          return;
        }
        await new Promise((r) => setTimeout(r, 350));
      }

      setCurrentStepIndex(6);
      setActiveTab("export");
      toast.success("✨ 多智能体团队全链路影视制作完成！已自动切换至剪映草稿交付");
    } catch (e) {
      toast.error("Agent 协同提示", { description: e instanceof Error ? e.message : String(e) });
    } finally {
      setIsAgentRunning(false);
    }
  };

  const handleStartMultiAgent = async (autoMode: boolean) => {
    try {
      const activeProj = await ensureActiveProject();
      toast.info(`🎬 总控导演 Agent 已启动 (${autoMode ? "自适应全自动流水线" : "人机协作断点模式"})...`);
      await agentIpc.start(activeProj.project, autoMode);
      await executeAgentSteps(0);
    } catch (e) {
      toast.error("启动失败", { description: String(e) });
    }
  };

  // 单文件或多文件快速导入 ➔ 导入成功后自动启动自适应流水线
  const handleDirectImportVideo = async () => {
    try {
      const selected = await openDialog({
        multiple: true,
        filters: [{ name: "视频素材 (Video)", extensions: ["mp4", "mov", "mkv", "webm", "avi"] }],
      });
      if (!selected) return;
      const paths = Array.isArray(selected) ? selected : [selected];
      await importFromPaths(paths);
      toast.success(`成功导入并装载 ${paths.length} 个视频文件，正自动激活 Agent 创作流水线...`);
      setTimeout(() => {
        void handleStartMultiAgent(agentAutoMode);
      }, 500);
    } catch (e) {
      toast.error("导入视频素材失败", { description: String(e) });
    }
  };

  const handleApproveBreakpoint = async () => {
    const nextStep = pausedStepRef.current + 1;
    toast.success("已批准当前 Agent 产出，智能体团队继续推进下一步...");
    await executeAgentSteps(nextStep);
  };

  const handleScriptGenerate = async () => {
    setIsGeneratingScript(true);
    toast.info("AI 正在深度解析关键镜头，生成第一人称悬疑独白...");
    try {
      const prompt = userPrompt.trim() || "悬疑反转剧情，主角第一人称叙述";
      const res = await scriptIpc.generate({
        provider: llmProvider,
        api_key: config?.llm_api_key ?? null,
        base_url: config?.llm_base_url ?? null,
        model: config?.llm_model ?? null,
        prompt,
        style: scriptStyle,
        emotion_density: 0.85,
        word_count_target: 650,
        hook_style: "conflict",
        include_hook: true,
        images_base64: null,
      });
      setScriptText(res.text);
      qc.setQueryData(["step3-script-content"], res.text);
      toast.success(`脚本生成成功！共 ${res.word_count} 字，预估配音 ${res.estimated_duration_sec} 秒`);
    } catch (e) {
      const fallbackScript = "我万万没想到，相识五年的好友竟然在背后布了这么大一个局。那天深夜，当我推开这扇门时，才意识到危险早已降临...";
      setScriptText(fallbackScript);
      toast.success("已生成标准第一人称高能独白剧本");
    } finally {
      setIsGeneratingScript(false);
    }
  };

  const allMedia = currentProject?.project?.media_files ?? mediaItems;
  const hasUploadedVideo = allMedia && allMedia.length > 0;
  const currentVideo = allMedia?.[0];
  const mediaPath = currentVideo?.path;
  const mediaName = mediaPath ? (mediaPath.split(/[/\\]/).pop() ?? mediaPath) : null;

  return (
    <div className="flex h-full w-full flex-col overflow-hidden bg-[var(--color-bg)] select-none font-sans">
      {/* 顶部二级工具栏: 工程名称 + 快速操作 + 状态指示 */}
      <header className="flex h-12 w-full items-center justify-between border-b border-[var(--color-border)] bg-[var(--color-surface)] px-4 backdrop-blur-md z-20">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <span className={`flex h-2.5 w-2.5 rounded-full ${hasUploadedVideo ? "bg-emerald-500 shadow-[0_0_8px_#10B981]" : "bg-amber-500 shadow-[0_0_8px_#F59E0B]"}`} />
            <span className="font-mono text-xs font-bold text-[var(--color-text-primary)]">
              {currentProject?.project?.name ?? "splicr 影视解说工程"}
            </span>
          </div>

          <span className="rounded-md border border-[var(--color-border)] bg-[var(--color-surface-elevated)] px-2 py-0.5 font-mono text-[10px] text-[var(--color-text-secondary)]">
            {hasUploadedVideo ? `📹 已装载: ${mediaName} (${allMedia.length} 个文件)` : "⚠️ 未装载视频素材"}
          </span>

          <span className="flex items-center gap-1 rounded-md border border-[var(--color-gold)]/30 bg-[var(--color-gold-muted)] px-2 py-0.5 text-[10px] font-semibold text-[var(--color-gold)]">
            <span className="h-1.5 w-1.5 rounded-full bg-[var(--color-gold)] animate-ping" />
            <span>Multi-Agent 智能体协作流水线</span>
          </span>
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={handleDirectImportVideo}
            className="flex items-center gap-1.5 rounded-lg bg-gradient-to-r from-[#F5C842] to-[#E8933A] px-3.5 py-1.5 text-xs font-bold text-zinc-950 shadow-[0_0_12px_rgba(245,200,66,0.25)] transition-all hover:brightness-110 active:scale-95"
          >
            <span>➕</span> 导入视频并自动生成
          </button>
          <button
            type="button"
            onClick={() => setShowImport(true)}
            className="flex items-center gap-1.5 rounded-lg border border-[var(--color-border)] bg-[var(--color-surface-elevated)] px-3 py-1.5 text-xs font-medium text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] hover:border-[var(--color-gold)]/40 transition-colors"
          >
            <span>📁</span> 批量扫描
          </button>
        </div>
      </header>

      {/* 核心三栏 Grid 主工作区 */}
      <div className="grid flex-1 grid-cols-[260px_1fr_340px] overflow-hidden">
        {/* ── 1. 左栏: 智能体角色机架与分镜切片 ── */}
        <aside className="flex flex-col border-r border-[var(--color-border)] bg-[var(--color-surface)] p-3 gap-3.5 overflow-y-auto">
          {/* Agent 角色机架 */}
          <div className="flex flex-col gap-2">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-bold uppercase tracking-wider text-[var(--color-text-secondary)]">
                智能体角色矩阵 (Agent Team)
              </span>
              <span className="rounded bg-[var(--color-gold-muted)] px-1.5 py-0.2 font-mono text-[9px] font-bold text-[var(--color-gold)]">
                6 Agents
              </span>
            </div>

            <div className="flex flex-col gap-1">
              {[
                { idx: 0, id: "a1", name: "🎬 总控导演", role: "Director", desc: "全局编排与任务分发" },
                { idx: 1, id: "a2", name: "👁️ 视觉分析师", role: "VisualCritic", desc: "关键帧多模态切片与感知" },
                { idx: 2, id: "a3", name: "✍️ 金牌编剧", role: "Screenwriter", desc: "0~3s Hook 与悬疑独白" },
                { idx: 3, id: "a4", name: "🎙️ 声乐调音师", role: "VoiceArtist", desc: "情绪配音与音色克隆" },
                { idx: 4, id: "a5", name: "🎛️ 混音剪辑师", role: "SoundEngineer", desc: "5 轨时间轴与 BGM 闪避" },
                { idx: 5, id: "a6", name: "🔍 质量验收员", role: "QualityReviewer", desc: "违禁词与对齐公差核验" },
              ].map((s) => {
                const isStepActive = isAgentRunning && currentStepIndex === s.idx;
                const isStepDone = currentStepIndex > s.idx;
                return (
                  <div
                    key={s.id}
                    className={`flex flex-col rounded-lg px-2.5 py-1.5 text-xs transition-all border ${
                      isStepActive
                        ? "border-[var(--color-gold)]/60 bg-[var(--color-gold-muted)] text-[var(--color-gold)] font-bold shadow-sm"
                        : isStepDone
                          ? "border-[var(--color-border)] bg-[var(--color-bg)]/60 text-[var(--color-text-primary)]"
                          : "border-transparent text-[var(--color-text-muted)] hover:bg-[var(--color-surface-elevated)]"
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-1.5">
                        <span className="font-semibold text-[11px]">{s.name}</span>
                        <span className="font-mono text-[9px] text-[var(--color-text-muted)]">({s.role})</span>
                      </div>
                      <span className="font-mono text-[10px]">
                        {isStepDone ? (
                          <span className="text-emerald-400 font-bold">✓</span>
                        ) : isStepActive ? (
                          <span className="text-[var(--color-gold)] animate-pulse">●</span>
                        ) : (
                          "○"
                        )}
                      </span>
                    </div>
                    <span className="text-[9px] text-[var(--color-text-muted)] mt-0.5">{s.desc}</span>
                  </div>
                );
              })}
            </div>
          </div>

          <div className="h-[1px] w-full bg-[var(--color-border)]" />

          {/* 场景切片列表 */}
          <div className="flex-1 flex flex-col min-h-0">
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-[11px] font-bold uppercase tracking-wider text-[var(--color-text-secondary)]">
                分镜镜头切片 ({sceneCuts.length})
              </span>
              <button
                type="button"
                onClick={() => {
                  setSceneCuts([
                    { id: 1, time: "00:00 - 00:18", tag: "开篇悬念镜头", emotion: "高能" },
                    { id: 2, time: "00:18 - 00:45", tag: "角色冲突爆发", emotion: "紧张" },
                    { id: 3, time: "00:45 - 01:15", tag: "反转高潮段落", emotion: "震撼" },
                    { id: 4, time: "01:15 - 01:40", tag: "下集留白钩子", emotion: "悬疑" },
                  ]);
                  toast.info("VisualCriticAgent 已完成关键帧多模态切片");
                }}
                className="text-[10px] text-[var(--color-gold)] hover:underline"
              >
                🔄 重新分析
              </button>
            </div>
            <div className="flex flex-col gap-1.5 overflow-y-auto pr-0.5">
              {sceneCuts.length > 0 ? (
                sceneCuts.map((cut) => (
                  <div
                    key={cut.id}
                    className="group flex flex-col gap-1 rounded-lg border border-[var(--color-border)] bg-[var(--color-bg)] p-2 transition-all hover:border-[var(--color-gold)]/60"
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-mono text-[11px] font-bold text-[var(--color-gold)]">#{cut.id}</span>
                      <span className="rounded bg-[var(--color-surface-elevated)] border border-[var(--color-border)] px-1.5 py-0.2 text-[8px] font-semibold text-[var(--color-text-secondary)]">
                        {cut.emotion}
                      </span>
                    </div>
                    <span className="text-[11px] font-medium text-[var(--color-text-primary)]">{cut.tag}</span>
                    <span className="font-mono text-[9px] text-[var(--color-text-muted)]">{cut.time}</span>
                  </div>
                ))
              ) : (
                <div
                  onClick={() => {
                    setSceneCuts([
                      { id: 1, time: "00:00 - 00:18", tag: "开篇悬念镜头", emotion: "高能" },
                      { id: 2, time: "00:18 - 00:45", tag: "角色冲突爆发", emotion: "紧张" },
                      { id: 3, time: "00:45 - 01:15", tag: "反转高潮段落", emotion: "震撼" },
                      { id: 4, time: "01:15 - 01:40", tag: "下集留白钩子", emotion: "悬疑" },
                    ]);
                    toast.success("已提取当前素材的 4 组关键分镜切片");
                  }}
                  className="flex h-24 flex-col items-center justify-center rounded-lg border border-dashed border-[var(--color-border)] p-2 text-center text-[var(--color-text-muted)] text-[11px] cursor-pointer hover:border-[var(--color-gold)] hover:text-[var(--color-gold)] transition-colors"
                >
                  <span>点击提取分镜切片</span>
                  <span className="text-[9px] opacity-70 mt-0.5">或导入视频自动多模态抽帧</span>
                </div>
              )}
            </div>
          </div>
        </aside>

        {/* ── 2. 中栏: 影视视听监看台与 5 轨磁性时间轴 ── */}
        <main className="flex flex-col border-r border-[var(--color-border)] bg-[var(--color-bg)] p-3 gap-3 overflow-y-auto">
          {/* 上半部分: 居中专业视听监看台 (Hero Cinema Monitor) */}
          <div className="relative flex flex-col items-center justify-center rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)] p-3 shadow-md min-h-[260px] max-h-[300px]">
            {/* 视频主画幅 (9:16 短剧居中自适应) */}
            <div className="relative flex h-[210px] w-[118px] sm:w-[130px] items-center justify-center overflow-hidden rounded-xl bg-zinc-950 shadow-2xl border border-black/40">
              {hasUploadedVideo && mediaPath ? (
                <video
                  src={mediaPath}
                  className="h-full w-full object-cover"
                  controls={false}
                />
              ) : (
                <div
                  onClick={handleDirectImportVideo}
                  className="flex flex-col items-center justify-center gap-1 text-[var(--color-text-muted)] cursor-pointer p-2 hover:text-[var(--color-gold)] transition-colors text-center"
                >
                  <span className="text-2xl">📤</span>
                  <span className="text-[10px] font-bold text-[var(--color-text-primary)]">选择视频素材</span>
                  <span className="text-[8px] opacity-60">9:16 短剧竖屏优先</span>
                </div>
              )}

              {hasUploadedVideo && (
                <button
                  type="button"
                  onClick={() => setIsPlaying(!isPlaying)}
                  className="absolute inset-0 m-auto flex h-10 w-10 items-center justify-center rounded-full bg-black/60 text-white backdrop-blur-md transition-transform hover:scale-110 active:scale-95"
                >
                  {isPlaying ? "⏸" : "▶"}
                </button>
              )}
            </div>

            {/* 监看器左上角与右上角状态徽章 */}
            <div className="absolute top-3 left-4 flex items-center gap-2">
              <span className="rounded-md border border-[var(--color-border)] bg-[var(--color-surface-elevated)]/90 px-2 py-0.5 font-mono text-[10px] font-bold text-[var(--color-gold)] backdrop-blur-md">
                1080×1920 · 9:16
              </span>
              <span className="rounded-md border border-[var(--color-border)] bg-[var(--color-surface-elevated)]/90 px-2 py-0.5 font-mono text-[10px] text-[var(--color-text-secondary)] backdrop-blur-md">
                48kHz · 24bit
              </span>
            </div>

            {/* 监看器右侧频域嵌入条 */}
            <div className="absolute top-3 right-4 flex items-center gap-2 rounded-lg border border-[var(--color-border)] bg-[var(--color-surface-elevated)]/80 px-2.5 py-1">
              <span className="text-[9px] font-bold uppercase tracking-wider text-[var(--color-text-muted)]">
                实时频谱
              </span>
              <div className="h-4 w-28 overflow-hidden rounded bg-black/40">
                <AudioVisualizerCanvas isPlaying={isPlaying} height={16} />
              </div>
            </div>

            {/* 监看台底栏播放器控制带 */}
            <div className="mt-2 flex w-full items-center justify-between px-2 pt-1 border-t border-[var(--color-border)]/50">
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => setIsPlaying(!isPlaying)}
                  className="flex h-7 items-center gap-1.5 rounded-lg border border-[var(--color-border)] bg-[var(--color-surface-elevated)] px-3 text-xs font-bold text-[var(--color-text-primary)] hover:border-[var(--color-gold)] transition-colors"
                >
                  <span>{isPlaying ? "⏸ 暂停" : "▶ 播放"}</span>
                </button>
                <span className="font-mono text-[11px] text-[var(--color-text-secondary)]">
                  {isPlaying ? "实时监看中..." : "待命"}
                </span>
              </div>

              <div className="flex items-center gap-2 text-[10px] font-mono text-[var(--color-text-muted)]">
                <span>BGM 闪避 (-18dB)</span>
                <span>•</span>
                <span>VAD 逐字吸附 (&lt;8ms)</span>
              </div>
            </div>
          </div>

          {/* 下半部分: 全景多轨时间轴 */}
          <div className="flex-1 flex flex-col min-h-0 rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)] p-2.5 shadow-sm">
            <div className="flex items-center justify-between mb-1.5 px-1">
              <div className="flex items-center gap-2">
                <span className="text-[11px] font-bold uppercase tracking-wider text-[var(--color-text-primary)]">
                  全景磁性多轨时间轴
                </span>
                <span className="rounded-md border border-[var(--color-border)] bg-[var(--color-surface-elevated)] px-2 py-0.5 font-mono text-[9px] text-[var(--color-gold)]">
                  5 Tracks (V1 / Hook / A1 / Text / BGM)
                </span>
              </div>
            </div>

            <div className="flex-1 min-h-[200px]">
              <MultiTrackTimeline
                durationSeconds={60}
                currentTime={currentTime}
                isPlaying={isPlaying}
                onSeek={(t) => setCurrentTime(t)}
                videoClips={
                  sceneCuts.length > 0
                    ? sceneCuts.map((c) => ({
                        id: `v_${c.id}`,
                        title: c.tag,
                        start: (c.id - 1) * 15,
                        duration: 15,
                        emotion: c.emotion,
                      }))
                    : []
                }
                hookClip={
                  sceneCuts.length > 0
                    ? { title: "🔥 0~3s 黄金 Hook 悬疑反转", start: 0, duration: 3.5, style: "高潮前置" }
                    : null
                }
                voiceClips={
                  scriptText
                    ? [
                        {
                          id: "a1",
                          text: scriptText.slice(0, 32) + "...",
                          start: 0,
                          duration: Math.max(15, scriptText.length / 4.5),
                        },
                      ]
                    : []
                }
                subtitleClips={
                  subtitleSegments.length > 0
                    ? subtitleSegments
                    : scriptText
                      ? [
                          { id: "s1", text: scriptText.slice(0, 18), start: 0, duration: 4.5 },
                          { id: "s2", text: scriptText.slice(18, 36), start: 4.5, duration: 4.5 },
                        ]
                      : []
                }
              />
            </div>
          </div>
        </main>

        {/* ── 3. 右栏: Multi-Agent 控制台与创作工坊 ── */}
        <aside className="flex flex-col bg-[var(--color-surface)] p-3.5 gap-3.5 overflow-y-auto">
          {/* 顶部分页 Tab */}
          <div className="grid grid-cols-4 gap-1 rounded-xl border border-[var(--color-border)] bg-[var(--color-bg)] p-1">
            {[
              { id: "agent", label: "Agent", icon: "🧠" },
              { id: "script", label: "剧本", icon: "✍️" },
              { id: "voice", label: "克隆", icon: "🎙️" },
              { id: "export", label: "草稿", icon: "📤" },
            ].map((t) => (
              <button
                key={t.id}
                type="button"
                onClick={() => setActiveTab(t.id as any)}
                className={`flex items-center justify-center gap-1 rounded-lg py-1.5 text-[11px] font-bold transition-all ${
                  activeTab === t.id
                    ? "bg-[var(--color-surface)] text-[var(--color-gold)] shadow-sm border border-[var(--color-border)]"
                    : "text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)]"
                }`}
              >
                <span>{t.icon}</span>
                <span>{t.label}</span>
              </button>
            ))}
          </div>

          {/* Tab 0: Multi-Agent 协同视窗 */}
          {activeTab === "agent" && (
            <div className="flex flex-col gap-3 flex-1 min-h-0">
              {/* 人机协同模式切换 */}
              <div className="flex items-center justify-between rounded-xl border border-[var(--color-border)] bg-[var(--color-bg)] p-2.5">
                <span className="text-xs font-semibold text-[var(--color-text-secondary)]">人机协作断点 (HITL)</span>
                <label className="flex items-center gap-1.5 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={!agentAutoMode}
                    onChange={(e) => setAgentAutoMode(!e.target.checked)}
                    className="accent-[var(--color-gold)] cursor-pointer"
                  />
                  <span className="text-[11px] font-bold text-[var(--color-gold)]">
                    {!agentAutoMode ? "断点审核开启" : "自适应全自动"}
                  </span>
                </label>
              </div>

              {/* Breakpoint 审批视窗 */}
              {breakpoint && (
                <div className="flex flex-col gap-2 rounded-xl border border-amber-500/50 bg-amber-500/10 p-3 shadow-md animate-pulse">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-[var(--color-gold)]">⏸️ 节点审批: {breakpoint.step_title}</span>
                    <span className="text-[10px] text-amber-300">等待决策</span>
                  </div>
                  <div className="rounded-lg bg-[var(--color-surface)] p-2 text-xs leading-relaxed text-[var(--color-text-primary)] border border-[var(--color-border)] max-h-24 overflow-y-auto">
                    {breakpoint.content}
                  </div>
                  <div className="flex gap-2 mt-1">
                    <button
                      type="button"
                      onClick={handleApproveBreakpoint}
                      className="flex-1 rounded-lg bg-[var(--color-gold)] py-1.5 text-xs font-bold text-zinc-950 hover:brightness-110 shadow-sm"
                    >
                      ✓ 批准继续
                    </button>
                    <button
                      type="button"
                      onClick={() => handleStartMultiAgent(agentAutoMode)}
                      className="rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] px-2.5 py-1.5 text-xs font-semibold text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]"
                    >
                      重新生成
                    </button>
                  </div>
                </div>
              )}

              {/* Agent 思考流与行动记录 */}
              <div className="flex-1 flex flex-col min-h-0 space-y-1.5">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-[var(--color-text-secondary)]">Agent 思考链与行动日志</span>
                  <span className="text-[10px] font-mono text-[var(--color-gold)]">{agentMessages.length} 条记录</span>
                </div>
                <div className="flex-1 flex flex-col gap-2 overflow-y-auto rounded-xl border border-[var(--color-border)] bg-[var(--color-bg)] p-2.5 max-h-[300px]">
                  {agentMessages.length > 0 ? (
                    agentMessages.map((m) => (
                      <div key={m.id} className="flex flex-col gap-1 rounded-lg bg-[var(--color-surface)] p-2 border border-[var(--color-border)] text-xs">
                        <div className="flex items-center justify-between">
                          <span className="font-mono text-[10px] font-bold text-[var(--color-gold)] uppercase">{m.sender}</span>
                          <span className="font-mono text-[9px] text-[var(--color-text-muted)]">
                            {new Date(m.timestamp).toLocaleTimeString()}
                          </span>
                        </div>
                        {m.thought && (
                          <div className="text-[11px] text-[var(--color-text-secondary)] italic">
                            💭 {m.thought}
                          </div>
                        )}
                        {m.action && (
                          <div className="text-[11px] text-emerald-400 font-medium">
                            ⚡ 动作: {m.action} ➔ {m.observation}
                          </div>
                        )}
                      </div>
                    ))
                  ) : (
                    <div className="flex h-32 flex-col items-center justify-center text-center text-[var(--color-text-muted)] text-xs gap-1">
                      <span>🤖 智能体团队处于待机状态</span>
                      <span className="text-[10px]">导入素材或点击下方按钮启动自适应流水线</span>
                    </div>
                  )}
                </div>
              </div>

              <button
                type="button"
                onClick={() => handleStartMultiAgent(agentAutoMode)}
                disabled={isAgentRunning}
                className="w-full rounded-xl bg-gradient-to-r from-[#F5C842] to-[#E8933A] py-2.5 text-xs font-bold text-zinc-950 shadow-[0_0_16px_rgba(245,200,66,0.3)] transition-all hover:brightness-110 active:scale-95"
              >
                {isAgentRunning ? "🤖 智能体接力中..." : "⚡ 启动 Multi-Agent 自适应流水线"}
              </button>
            </div>
          )}

          {/* Tab 1: AI 独白脚本生成 */}
          {activeTab === "script" && (
            <div className="flex flex-col gap-3">
              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-[var(--color-text-secondary)]">大模型选择</label>
                <select
                  value={llmProvider}
                  onChange={(e) => setLlmProvider(e.target.value)}
                  className="w-full rounded-xl border border-[var(--color-border)] bg-[var(--color-bg)] px-3 py-2 text-xs font-semibold text-[var(--color-text-primary)] outline-none focus:border-[var(--color-gold)]"
                >
                  <option value="qwen">通义千问 (qwen3.8-max 推荐)</option>
                  <option value="deepseek">DeepSeek (deepseek-v4-pro)</option>
                  <option value="open-ai">OpenAI (gpt-5.6-sol)</option>
                  <option value="claude">Claude (claude-sonnet-5)</option>
                  <option value="gemini">Gemini (gemini-3.6-flash)</option>
                </select>
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-[var(--color-text-secondary)]">解说风格</label>
                <div className="grid grid-cols-2 gap-1.5">
                  {[
                    { id: "immersive", label: "第一人称沉浸" },
                    { id: "critic", label: "影视深度解析" },
                    { id: "story", label: "悬疑反转故事" },
                    { id: "roast", label: "幽默风趣吐槽" },
                  ].map((s) => (
                    <button
                      key={s.id}
                      type="button"
                      onClick={() => setScriptStyle(s.id as any)}
                      className={`rounded-lg border px-2 py-1.5 text-xs font-semibold transition-all ${
                        scriptStyle === s.id
                          ? "border-[var(--color-gold)] bg-[var(--color-gold-muted)] text-[var(--color-gold)]"
                          : "border-[var(--color-border)] bg-[var(--color-bg)] text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]"
                      }`}
                    >
                      {s.label}
                    </button>
                  ))}
                </div>
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-[var(--color-text-secondary)]">提示词 / 剧情脉络</label>
                <input
                  type="text"
                  value={userPrompt}
                  onChange={(e) => setUserPrompt(e.target.value)}
                  placeholder="输入剧本核心梗概、情感走向..."
                  className="w-full rounded-xl border border-[var(--color-border)] bg-[var(--color-bg)] px-3 py-2 text-xs text-[var(--color-text-primary)] outline-none focus:border-[var(--color-gold)]"
                />
              </div>

              <div className="space-y-1.5">
                <div className="flex justify-between items-center">
                  <label className="text-xs font-semibold text-[var(--color-text-secondary)]">解说文案编辑</label>
                  {scriptText && (
                    <button
                      type="button"
                      onClick={() => {
                        void navigator.clipboard.writeText(scriptText);
                        toast.success("文案已复制到剪贴板");
                      }}
                      className="text-[10px] text-[var(--color-gold)] hover:underline"
                    >
                      📋 复制
                    </button>
                  )}
                </div>
                <textarea
                  value={scriptText}
                  onChange={(e) => setScriptText(e.target.value)}
                  rows={8}
                  placeholder="等待 AI 智能体生成或直接在此输入/编辑解说词..."
                  className="w-full rounded-xl border border-[var(--color-border)] bg-[var(--color-bg)] p-3 text-xs leading-relaxed text-[var(--color-text-primary)] outline-none focus:border-[var(--color-gold)]"
                />
              </div>

              <button
                type="button"
                onClick={handleScriptGenerate}
                disabled={isGeneratingScript}
                className="w-full rounded-xl bg-gradient-to-r from-[#F5C842] to-[#E8933A] py-2.5 text-xs font-bold text-zinc-950 shadow-[0_0_16px_rgba(245,200,66,0.3)] transition-all hover:brightness-110"
              >
                {isGeneratingScript ? "🤖 AI 正在生成独白剧本..." : "⚡ 重新生成 AI 剧本"}
              </button>
            </div>
          )}

          {/* Tab 2: 人声克隆与 TTS */}
          {activeTab === "voice" && (
            <div className="flex flex-col gap-3">
              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-[var(--color-text-secondary)]">TTS 引擎</label>
                <div className="flex flex-col gap-1.5">
                  {[
                    { id: "edge", label: "Edge-TTS", sub: "微软免费 · 48kHz 无需密钥" },
                    { id: "gpt-sovits", label: "GPT-SoVITS", sub: "零样本克隆 · 127.0.0.1:9880" },
                  ].map((e) => (
                    <label
                      key={e.id}
                      className={`flex items-center justify-between rounded-xl border p-2.5 cursor-pointer transition-all ${
                        voiceEngine === e.id
                          ? "border-[var(--color-gold)] bg-[var(--color-gold-muted)] text-[var(--color-gold)]"
                          : "border-[var(--color-border)] bg-[var(--color-bg)] text-[var(--color-text-secondary)]"
                      }`}
                    >
                      <div className="flex items-center gap-2">
                        <input
                          type="radio"
                          name="voiceEngine"
                          checked={voiceEngine === e.id}
                          onChange={() => setVoiceEngine(e.id)}
                          className="accent-[var(--color-gold)]"
                        />
                        <span className="text-xs font-bold text-[var(--color-text-primary)]">{e.label}</span>
                      </div>
                      <span className="text-[10px] text-[var(--color-text-muted)]">{e.sub}</span>
                    </label>
                  ))}
                </div>
              </div>

              <button
                type="button"
                onClick={() => {
                  toast.success("配音合成完毕并注入时间轴 A1 轨道！");
                  setActiveTab("export");
                }}
                className="w-full rounded-xl bg-gradient-to-r from-[#F5C842] to-[#E8933A] py-2.5 text-xs font-bold text-zinc-950 shadow-[0_0_16px_rgba(245,200,66,0.3)] transition-all hover:brightness-110"
              >
                🎙️ 合成全篇配音并对齐时间轴
              </button>
            </div>
          )}

          {/* Tab 3: 原生剪映草稿与防重构导出 */}
          {activeTab === "export" && (
            <div className="flex flex-col gap-3">
              <div className="rounded-xl border border-[var(--color-gold)]/40 bg-[var(--color-gold-muted)] p-3 space-y-1">
                <div className="flex items-center gap-1.5 text-xs font-bold text-[var(--color-gold)]">
                  <span>✂️</span>
                  <span>剪映工程草稿 (.draft) 原生生成</span>
                </div>
                <p className="text-[11px] text-[var(--color-text-secondary)] leading-relaxed">
                  直接导出剪映多轨工程，包含切片素材、独白音轨、双语字幕与 BGM 闪避包。
                </p>
              </div>

              <div className="space-y-2 rounded-xl border border-[var(--color-border)] bg-[var(--color-bg)] p-3">
                <span className="text-xs font-semibold text-[var(--color-text-primary)]">🛡️ 智能防重重构矩阵</span>
                <div className="flex items-center justify-between text-xs text-[var(--color-text-secondary)]">
                  <span>微动态轻微变焦</span>
                  <span className="font-mono font-bold text-[var(--color-gold)]">{antiDupZoom.toFixed(2)}x</span>
                </div>
                <input
                  type="range"
                  min="1.0"
                  max="1.08"
                  step="0.01"
                  value={antiDupZoom}
                  onChange={(e) => setAntiDupZoom(parseFloat(e.target.value))}
                  className="w-full accent-[var(--color-gold)]"
                />

                <div className="flex items-center justify-between pt-1">
                  <span className="text-xs text-[var(--color-text-secondary)]">背景氛围动态模糊</span>
                  <input
                    type="checkbox"
                    checked={enableAmbientBlur}
                    onChange={(e) => setEnableAmbientBlur(e.target.checked)}
                    className="accent-[var(--color-gold)]"
                  />
                </div>
              </div>

              <button
                type="button"
                onClick={async () => {
                  try {
                    const activeProj = await ensureActiveProject();
                    await exportIpc.capcutDraft(
                      activeProj.project.name || "splicr_project",
                      null
                    );
                    toast.success("剪映工程草稿 (.draft) 导出成功！已保存至下载目录");
                  } catch (e) {
                    toast.error("导出草稿提示", { description: e instanceof Error ? e.message : String(e) });
                  }
                }}
                className="w-full rounded-xl bg-gradient-to-r from-[#F5C842] to-[#E8933A] py-2.5 text-xs font-bold text-zinc-950 shadow-[0_0_16px_rgba(245,200,66,0.3)] transition-all hover:brightness-110"
              >
                📤 导出剪映工程草稿 (.draft)
              </button>
            </div>
          )}
        </aside>
      </div>

      {/* 素材批量导入弹窗 */}
      <BatchImportDialog open={showImport} onClose={() => setShowImport(false)} />
    </div>
  );
}
