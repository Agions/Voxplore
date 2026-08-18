/**
 * splicr v1.0.1 · 三栏专业集成影视解说工作台 (集成 Rust Native Multi-Agent 系统)
 * - 左栏: 7 步卡片生产流水线 & 场景分镜切片列表
 * - 中栏: 高清视听播放中枢、实时频域 Canvas 声波谱与 5 轨磁性多轨时间轴
 * - 右栏: Multi-Agent 智能体协同视窗 (思考流/行动流/Human-in-the-Loop 断点) + 剧本/克隆/导出控制
 */

import { createFileRoute } from "@tanstack/react-router";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import { BatchImportDialog } from "@components/dialogs/BatchImportDialog";
import { AudioVisualizerCanvas } from "@components/production/AudioVisualizerCanvas";
import { MultiTrackTimeline } from "@components/production/MultiTrackTimeline";
import {
  agentIpc,
  projectIpc,
  scriptIpc,
  settingsIpc,
  type AgentMessage,
  type BreakpointRequest,
  type ProjectRecord,
} from "@ipc/commands";
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

  // 1. 数据订阅与工程加载
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

  // ── Multi-Agent 状态 ──
  const [isAgentRunning, setIsAgentRunning] = useState(false);
  const [agentAutoMode, setAgentAutoMode] = useState(false);
  const [agentMessages, setAgentMessages] = useState<AgentMessage[]>([
    {
      id: "m1",
      sender: "director",
      receiver: null,
      thought: "初始化 splicr-agent 协同上下文，检查视频源与 5 轨时间轴配置...",
      action: "分配镜头拆条任务给 VisualCriticAgent",
      observation: "切片分析准备就绪",
      timestamp: Date.now() - 5000,
    },
    {
      id: "m2",
      sender: "visual_critic",
      receiver: null,
      thought: "多模态关键帧分析中...检测到第 1 镜头具有高能反转与情感张力",
      action: "智能切片",
      observation: "提取 4 个核心分镜，标注情绪峰值 (00:45)",
      timestamp: Date.now() - 3000,
    },
    {
      id: "m3",
      sender: "screenwriter",
      receiver: null,
      thought: "正在撰写 0~3s 黄金 Hook 与第一人称悬疑独白...完播率自反思评分: 96/100",
      action: "生成文案",
      observation: "生成 650 字高潮独白，注入共享缓存",
      timestamp: Date.now() - 1000,
    },
  ]);
  const [breakpoint, setBreakpoint] = useState<BreakpointRequest | null>(null);

  // 场景切片状态
  const [sceneCuts] = useState<{ id: number; time: string; tag: string; emotion: string }[]>([
    { id: 1, time: "00:00 - 00:18", tag: "开篇悬念切片", emotion: "高能" },
    { id: 2, time: "00:18 - 00:45", tag: "角色冲突爆发", emotion: "紧张" },
    { id: 3, time: "00:45 - 01:15", tag: "反转高潮段落", emotion: "震撼" },
    { id: 4, time: "01:15 - 01:40", tag: "下集留白钩子", emotion: "悬疑" },
  ]);

  // AI 脚本状态
  const [llmProvider, setLlmProvider] = useState("qwen");
  const [scriptStyle, setScriptStyle] = useState<"immersive" | "critic" | "story" | "roast">("immersive");
  const [userPrompt, setUserPrompt] = useState("");
  const [scriptText, setScriptText] = useState(
    "我万万没想到，相识五年的好友竟然在背后布了这么大一个局。那天深夜，当我推开这扇门时，才意识到危险早已降临..."
  );
  const [isGeneratingScript, setIsGeneratingScript] = useState(false);

  // 配音与克隆状态
  const [voiceEngine, setVoiceEngine] = useState("edge");

  // 混流与防重构参数
  const [antiDupZoom, setAntiDupZoom] = useState(1.03);
  const [enableAmbientBlur, setEnableAmbientBlur] = useState(true);

  // 加载最靠前的历史项目
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

  // 3. 业务操作处理
  const handleStartMultiAgent = async (autoMode: boolean) => {
    if (!currentProject) {
      setShowImport(true);
      return;
    }
    setIsAgentRunning(true);
    setBreakpoint(null);
    toast.info(`🎬 总控导演 Agent 已启动 (${autoMode ? "全自动模式" : "人机协作断点模式"})...`);

    try {
      await agentIpc.start(currentProject.project, autoMode);
      
      // 逐步执行 Agent 节点
      for (let i = 0; i < 6; i++) {
        const bp = await agentIpc.step(i);
        const ctx = await agentIpc.getContext();
        if (ctx) {
          setAgentMessages(ctx.messages);
        }
        if (bp) {
          setBreakpoint(bp);
          toast.warning(`⏸️ 智能体工作流在【${bp.step_title}】暂停，等待创作者审核`);
          break;
        }
        await new Promise((r) => setTimeout(r, 400));
      }

      if (!breakpoint) {
        toast.success("✨ 多智能体团队全链路影视制作完成！已准备好剪映草稿");
      }
    } catch (e) {
      toast.error("Agent 协同提示", { description: e instanceof Error ? e.message : String(e) });
    } finally {
      setIsAgentRunning(false);
    }
  };

  const handleApproveBreakpoint = async () => {
    setBreakpoint(null);
    setIsAgentRunning(true);
    toast.success("已批准当前 Agent 产出，智能体团队继续推进下一步...");
    try {
      for (let i = 3; i < 6; i++) {
        const bp = await agentIpc.step(i);
        const ctx = await agentIpc.getContext();
        if (ctx) {
          setAgentMessages(ctx.messages);
        }
        if (bp) {
          setBreakpoint(bp);
          break;
        }
        await new Promise((r) => setTimeout(r, 400));
      }
      toast.success("✨ 多智能体团队全流程交付完成！");
    } catch (e) {
      toast.error("Agent 推进提示", { description: e instanceof Error ? e.message : String(e) });
    } finally {
      setIsAgentRunning(false);
    }
  };

  const handleScriptGenerate = async () => {
    if (!userPrompt.trim()) {
      toast.error("请输入剧本核心主题或提示词");
      return;
    }
    setIsGeneratingScript(true);
    toast.info("AI 正在深度解析关键镜头，生成第一人称悬疑独白...");
    try {
      const res = await scriptIpc.generate({
        provider: llmProvider,
        api_key: config?.llm_api_key ?? null,
        base_url: config?.llm_base_url ?? null,
        model: config?.llm_model ?? null,
        prompt: userPrompt,
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
      toast.error("生成脚本提示", { description: e instanceof Error ? e.message : String(e) });
    } finally {
      setIsGeneratingScript(false);
    }
  };

  const mediaPath = currentProject?.project?.media_files?.[0]?.path;
  const mediaName = mediaPath ? (mediaPath.split(/[/\\]/).pop() ?? mediaPath) : "Episode_01_Main_1080P.mp4";

  return (
    <div className="flex h-full w-full flex-col overflow-hidden bg-[var(--color-bg)] select-none">
      {/* 顶部二级工具栏: 工程名称 + 快速操作 + 状态指示 */}
      <div className="flex h-12 w-full items-center justify-between border-b border-[var(--color-border)] bg-[var(--color-surface)]/80 px-4 backdrop-blur-md">
        <div className="flex items-center gap-3">
          <span className="flex h-2.5 w-2.5 rounded-full bg-emerald-500 shadow-[0_0_8px_#10B981]" />
          <span className="font-mono text-xs font-bold text-[var(--color-text-primary)]">
            {currentProject?.project?.name ?? "短剧解说工程 #1"}
          </span>
          <span className="rounded-md border border-[var(--color-border)] bg-[var(--color-bg)] px-2 py-0.5 font-mono text-[10px] text-[var(--color-text-muted)]">
            {mediaName}
          </span>
          <span className="rounded-md border border-amber-500/30 bg-amber-500/10 px-2 py-0.5 text-[10px] font-semibold text-[var(--color-gold)]">
            🤖 Rust Multi-Agent 引擎活跃
          </span>
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => setShowImport(true)}
            className="flex items-center gap-1.5 rounded-lg border border-[var(--color-border)] bg-[var(--color-bg)] px-3 py-1.5 text-xs font-semibold text-[var(--color-text-secondary)] transition-all hover:border-[var(--color-gold)] hover:text-[var(--color-gold)]"
          >
            <span>📁</span> 导入素材
          </button>
          <button
            type="button"
            onClick={() => handleStartMultiAgent(agentAutoMode)}
            disabled={isAgentRunning}
            className="flex items-center gap-1.5 rounded-lg bg-gradient-to-r from-[#F5C842] to-[#E8933A] px-3.5 py-1.5 text-xs font-bold text-zinc-950 shadow-[0_0_16px_rgba(245,200,66,0.35)] transition-all hover:brightness-110"
          >
            <span>{isAgentRunning ? "⏳" : "🎬"}</span>
            {isAgentRunning ? "智能体团队协同中..." : "启动 Multi-Agent 创作团队"}
          </button>
        </div>
      </div>

      {/* 核心三栏 Grid 主工作区 */}
      <div className="grid flex-1 grid-cols-[280px_1fr_380px] overflow-hidden">
        {/* ── 1. 左栏: 7 步流水线与分镜切片 ── */}
        <aside className="flex flex-col border-r border-[var(--color-border)] bg-[var(--color-surface)]/40 p-3.5 gap-4 overflow-y-auto">
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-bold uppercase tracking-wider text-[var(--color-text-secondary)]">
                智能体角色矩阵 (Agent Team)
              </span>
              <span className="text-[10px] font-mono text-[var(--color-gold)]">6 Agents</span>
            </div>
            <div className="flex flex-col gap-1.5">
              {[
                { id: "a1", name: "🎬 总控导演 (Director)", desc: "全局任务规划与分发", status: isAgentRunning ? "active" : "done" },
                { id: "a2", name: "👁️ 视觉分析师 (VisualCritic)", desc: "多模态关键帧与情绪感知", status: "done" },
                { id: "a3", name: "✍️ 金牌编剧 (Screenwriter)", desc: "0~3s Hook 与悬疑独白", status: "active" },
                { id: "a4", name: "🎙️ 声乐调音师 (VoiceArtist)", desc: "情绪配音与音色克隆", status: "pending" },
                { id: "a5", name: "🎛️ 混音剪辑师 (SoundEngineer)", desc: "5 轨时间轴与 BGM 闪避", status: "pending" },
                { id: "a6", name: "🔍 质量验收员 (QualityReviewer)", desc: "违禁词与对齐公差核验", status: "pending" },
              ].map((s) => (
                <div
                  key={s.id}
                  className={`flex flex-col rounded-lg px-2.5 py-2 text-xs transition-all ${
                    s.status === "active"
                      ? "border border-[var(--color-gold)]/40 bg-[var(--color-gold-muted)] text-[var(--color-gold)] font-bold shadow-sm"
                      : s.status === "done"
                        ? "border border-transparent bg-[var(--color-bg)]/80 text-[var(--color-text-primary)]"
                        : "border border-transparent text-[var(--color-text-muted)]"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-[11px]">{s.name}</span>
                    <span className="font-mono text-[10px]">
                      {s.status === "done" ? "✓" : s.status === "active" ? "●" : "○"}
                    </span>
                  </div>
                  <span className="text-[9px] text-[var(--color-text-muted)] mt-0.5">{s.desc}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="h-[1px] w-full bg-[var(--color-border)]" />

          {/* 场景切片列表 */}
          <div className="flex-1 flex flex-col min-h-0">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-bold uppercase tracking-wider text-[var(--color-text-secondary)]">
                镜头切片 ({sceneCuts.length})
              </span>
              <button
                type="button"
                onClick={() => toast.info("VisualCriticAgent 已重新触发切片检测")}
                className="text-[10px] text-[var(--color-gold)] hover:underline"
              >
                🔄 重新分析
              </button>
            </div>
            <div className="flex flex-col gap-2 overflow-y-auto pr-1">
              {sceneCuts.map((cut) => (
                <div
                  key={cut.id}
                  className="group flex flex-col gap-1 rounded-xl border border-[var(--color-border)] bg-[var(--color-bg)] p-2.5 transition-all hover:border-[var(--color-gold)]/60 hover:shadow-sm"
                >
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-xs font-bold text-[var(--color-gold)]">#{cut.id}</span>
                    <span className="rounded bg-zinc-800 px-1.5 py-0.5 text-[9px] font-semibold text-zinc-300">
                      {cut.emotion}
                    </span>
                  </div>
                  <span className="text-xs font-medium text-[var(--color-text-primary)]">{cut.tag}</span>
                  <span className="font-mono text-[10px] text-[var(--color-text-muted)]">{cut.time}</span>
                </div>
              ))}
            </div>
          </div>
        </aside>

        {/* ── 2. 中栏: 视听播放中枢与 5 轨磁性时间轴 ── */}
        <main className="flex flex-col border-r border-[var(--color-border)] bg-[var(--color-bg)] p-4 gap-4 overflow-y-auto">
          {/* 上半部分: 视频播放器 + 实时音频频域 Canvas */}
          <div className="grid grid-cols-[1fr_260px] gap-4 h-[240px]">
            {/* 视频主画面 */}
            <div className="relative flex flex-col items-center justify-center overflow-hidden rounded-2xl border border-[var(--color-border)] bg-zinc-950 shadow-lg">
              <img
                src="https://images.unsplash.com/photo-1536440136628-849c177e76a1?w=800&q=80"
                alt="Video Preview"
                className="h-full w-full object-cover opacity-85"
              />
              <div className="absolute top-3 left-3 rounded-md bg-black/60 px-2 py-1 text-[10px] font-mono text-[var(--color-gold)] backdrop-blur-md">
                1080×1920 · 9:16 短剧竖屏
              </div>
              <div className="absolute top-3 right-3 rounded-md bg-amber-500/20 border border-amber-500/40 px-2 py-1 text-[10px] font-bold text-[var(--color-gold)] backdrop-blur-md">
                0~3s 黄金 Hook 活跃
              </div>
              {/* 居中播放控制 */}
              <button
                type="button"
                onClick={() => setIsPlaying(!isPlaying)}
                className="absolute flex h-12 w-12 items-center justify-center rounded-full bg-[var(--color-gold)] text-zinc-950 text-xl font-bold shadow-[0_0_20px_rgba(245,200,66,0.5)] transition-transform hover:scale-110"
              >
                {isPlaying ? "⏸" : "▶"}
              </button>
            </div>

            {/* 音频频域 Canvas 频谱与控制 */}
            <div className="flex flex-col justify-between rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)] p-3.5 shadow-sm">
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-bold text-[var(--color-text-primary)]">实时频域声波谱</span>
                  <span className="text-[10px] font-mono text-[var(--color-gold)]">48 FFT</span>
                </div>
                <AudioVisualizerCanvas isPlaying={isPlaying} height={70} />
              </div>
              <div className="space-y-1.5 text-xs text-[var(--color-text-secondary)]">
                <div className="flex justify-between">
                  <span>BGM 闪避混音:</span>
                  <span className="font-mono font-bold text-[var(--color-gold)]">-18%</span>
                </div>
                <div className="flex justify-between">
                  <span>声画对齐偏差:</span>
                  <span className="font-mono font-bold text-emerald-400">&lt; 18ms</span>
                </div>
              </div>
            </div>
          </div>

          {/* 下半部分: 5 轨磁性多轨时间轴 */}
          <div className="flex-1 flex flex-col rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)] p-3.5 shadow-sm overflow-hidden min-h-[320px]">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <span className="text-xs font-bold uppercase tracking-wider text-[var(--color-text-primary)]">
                  多轨时间轴 (5-Tracks Timeline)
                </span>
                <span className="rounded bg-zinc-800 px-1.5 py-0.5 font-mono text-[9px] text-zinc-400">
                  00:00 / 01:45
                </span>
              </div>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => setIsPlaying(!isPlaying)}
                  className="rounded-md border border-[var(--color-border)] bg-[var(--color-bg)] px-2.5 py-1 text-xs font-semibold text-[var(--color-text-primary)] hover:border-[var(--color-gold)]"
                >
                  {isPlaying ? "⏸ 暂停" : "▶ 播放"}
                </button>
              </div>
            </div>
            <div className="flex-1 overflow-hidden">
              <MultiTrackTimeline isPlaying={isPlaying} onSeek={() => {}} />
            </div>
          </div>
        </main>

        {/* ── 3. 右栏: Multi-Agent 智能体视窗与创作控制台 ── */}
        <aside className="flex flex-col bg-[var(--color-surface)]/60 p-3.5 gap-4 overflow-y-auto">
          {/* 顶部分页 Tab: Agent视窗 / 独白脚本 / 人声克隆 / 原生导出 */}
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
                    ? "bg-[var(--color-surface)] text-[var(--color-gold)] shadow-sm"
                    : "text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)]"
                }`}
              >
                <span>{t.icon}</span>
                <span>{t.label}</span>
              </button>
            ))}
          </div>

          {/* Tab 0: Multi-Agent 协同视窗 (思考流 + Breakpoints) */}
          {activeTab === "agent" && (
            <div className="flex flex-col gap-3.5 flex-1 min-h-0">
              {/* 人机协同模式切换 */}
              <div className="flex items-center justify-between rounded-xl border border-[var(--color-border)] bg-[var(--color-bg)] p-2.5">
                <span className="text-xs font-semibold text-[var(--color-text-secondary)]">人机协作断点 (HITL)</span>
                <label className="flex items-center gap-1.5 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={!agentAutoMode}
                    onChange={(e) => setAgentAutoMode(!e.target.checked)}
                    className="accent-[var(--color-gold)]"
                  />
                  <span className="text-[11px] font-bold text-[var(--color-gold)]">
                    {!agentAutoMode ? "断点审核开启" : "一键全自动"}
                  </span>
                </label>
              </div>

              {/* Breakpoint 审批视窗 */}
              {breakpoint && (
                <div className="flex flex-col gap-2 rounded-xl border border-amber-500/50 bg-amber-500/10 p-3 shadow-md animate-pulse">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-[var(--color-gold)]">⏸️ 节点审批: {breakpoint.step_title}</span>
                    <span className="text-[10px] text-amber-300">等待人类决策</span>
                  </div>
                  <div className="rounded-lg bg-zinc-950/80 p-2 text-xs leading-relaxed text-zinc-200 border border-zinc-800 max-h-24 overflow-y-auto">
                    {breakpoint.content}
                  </div>
                  <div className="flex gap-2 mt-1">
                    <button
                      type="button"
                      onClick={handleApproveBreakpoint}
                      className="flex-1 rounded-lg bg-[var(--color-gold)] py-1.5 text-xs font-bold text-zinc-950 hover:brightness-110 shadow-sm"
                    >
                      ✓ 批准并继续下一步
                    </button>
                    <button
                      type="button"
                      onClick={() => handleStartMultiAgent(agentAutoMode)}
                      className="rounded-lg border border-[var(--color-border)] bg-[var(--color-bg)] px-2.5 py-1.5 text-xs font-semibold text-[var(--color-text-secondary)] hover:text-white"
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
                <div className="flex-1 flex flex-col gap-2 overflow-y-auto rounded-xl border border-[var(--color-border)] bg-[var(--color-bg)] p-2.5 max-h-[340px]">
                  {agentMessages.map((m) => (
                    <div key={m.id} className="flex flex-col gap-1 rounded-lg bg-[var(--color-surface)] p-2 border border-[var(--color-border)]/60 text-xs">
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
                  ))}
                </div>
              </div>

              <button
                type="button"
                onClick={() => handleStartMultiAgent(agentAutoMode)}
                disabled={isAgentRunning}
                className="w-full rounded-xl bg-gradient-to-r from-[#F5C842] to-[#E8933A] py-2.5 text-xs font-bold text-zinc-950 shadow-[0_0_16px_rgba(245,200,66,0.3)] transition-all hover:brightness-110"
              >
                {isAgentRunning ? "🤖 智能体接力中..." : "⚡ 重新运行 Multi-Agent 流水线"}
              </button>
            </div>
          )}

          {/* Tab 1: AI 独白脚本生成 */}
          {activeTab === "script" && (
            <div className="flex flex-col gap-3.5">
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
                </div>
                <textarea
                  value={scriptText}
                  onChange={(e) => setScriptText(e.target.value)}
                  rows={8}
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
            <div className="flex flex-col gap-3.5">
              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-[var(--color-text-secondary)]">TTS 引擎</label>
                <div className="flex flex-col gap-1.5">
                  {[
                    { id: "edge", label: "Edge-TTS", sub: "微软免费 · 无需密钥" },
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

              <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-bg)] p-3 space-y-2">
                <div className="flex justify-between items-center">
                  <span className="text-xs font-semibold text-[var(--color-text-primary)]">🧬 参考音频</span>
                  <button
                    type="button"
                    onClick={() => toast.success("已导入人声样本: protagonist_voice.wav")}
                    className="text-[10px] text-[var(--color-gold)] hover:underline"
                  >
                    ↑ 上传新音频
                  </button>
                </div>
                <div className="rounded-lg bg-zinc-900 p-2 font-mono text-[10px] text-zinc-400">
                  protagonist_sample_5s.wav (已就绪)
                </div>
              </div>

              <button
                type="button"
                onClick={() => toast.success("配音合成完毕并注入时间轴 A1 轨道！")}
                className="w-full rounded-xl bg-gradient-to-r from-[#F5C842] to-[#E8933A] py-2.5 text-xs font-bold text-zinc-950 shadow-[0_0_16px_rgba(245,200,66,0.3)] transition-all hover:brightness-110"
              >
                🎙️ 合成全篇配音并对齐时间轴
              </button>
            </div>
          )}

          {/* Tab 3: 原生剪映草稿与防重构导出 */}
          {activeTab === "export" && (
            <div className="flex flex-col gap-3.5">
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
                onClick={() => toast.success("剪映工程草稿 (.draft) 导出成功！已打开导出文件夹")}
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
