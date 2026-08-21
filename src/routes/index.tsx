/**
 * splicr v1.0.1 · 首页 旗舰级电影调光室 Dashboard (全景多智能体态势与工程中枢)
 */

import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { BatchImportDialog } from "@components/dialogs/BatchImportDialog";
import { useProjectStore } from "@stores/project-store";
import { useSettingsStore } from "@stores/settings-store";
import { toast } from "sonner";
import { projectIpc } from "@ipc/commands";

export const Route = createFileRoute("/")({
  component: HomePage,
});

function HomePage() {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const locale = useSettingsStore((s) => s.locale);
  const setCurrentRecord = useProjectStore((s) => s.setCurrentRecord);
  const [showImport, setShowImport] = useState(false);

  // 真实加载历史工程
  const { data: recentPaths, isLoading: loadingRecents } = useQuery({
    queryKey: ["home-recent-projects"],
    queryFn: () => projectIpc.listRecent(),
  });

  const createProject = useMutation({
    mutationFn: projectIpc.createBlank,
    onSuccess: (rec) => {
      qc.setQueryData(["current-project"], rec);
      setCurrentRecord(rec.path, rec.project);
      void navigate({ to: "/production" });
      toast.success(locale === "en-US" ? "New Studio Project Created" : "三栏解说工作台已就绪");
    },
    onError: (e) => {
      toast.error("创建工程失败", { description: e instanceof Error ? e.message : String(e) });
    },
  });

  const handleOpenProject = async (p: string) => {
    try {
      const rec = await projectIpc.load(p);
      qc.setQueryData(["current-project"], rec);
      qc.setQueryData(["assets-current-project"], rec.project);
      setCurrentRecord(rec.path, rec.project);
      void navigate({ to: "/production" });
    } catch (e) {
      toast.error("加载项目失败", { description: e instanceof Error ? e.message : String(e) });
    }
  };

  const hasProjects = recentPaths && recentPaths.length > 0;

  return (
    <div className="mx-auto max-w-6xl space-y-7 px-8 py-8 select-none font-sans">
      {/* 1. 旗舰 Hero Header 态势大看板 */}
      <div className="relative overflow-hidden rounded-3xl border border-[var(--color-border)] bg-gradient-to-br from-zinc-950 via-[#0e0e11] to-black p-8 shadow-2xl">
        <div className="absolute -top-12 -right-12 h-72 w-96 bg-gradient-to-bl from-amber-500/20 via-yellow-500/10 to-transparent blur-3xl pointer-events-none" />
        <div className="relative z-10 flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
          <div className="space-y-2.5">
            <div className="inline-flex items-center gap-2 rounded-full border border-amber-500/30 bg-amber-500/10 px-3.5 py-1 text-[11px] font-bold text-[var(--color-gold)] shadow-[0_0_12px_rgba(245,200,66,0.15)]">
              <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse shadow-[0_0_8px_#34d399]" />
              <span>v1.0.1 · Rust Native 6-Agent 智能体协作中枢</span>
            </div>
            <h1 className="text-3xl md:text-4xl font-black tracking-tight text-white flex items-center gap-3">
              <span>splicr 叙影</span>
              <span className="bg-gradient-to-r from-[#F5C842] via-[#F9D76B] to-[#E8933A] bg-clip-text text-transparent">
                电影级短剧 AI 叙事工厂
              </span>
            </h1>
            <p className="text-xs md:text-sm text-zinc-400 font-normal max-w-2xl leading-relaxed">
              多模态切片 ➔ 6 大 Agent 自主编剧与 48kHz 配音 ➔ 5 轨毫秒级磁性对齐 ➔ 剪映草稿原生导出交付
            </p>
          </div>

          <div className="flex items-center gap-3 shrink-0">
            <button
              type="button"
              onClick={() => setShowImport(true)}
              className="flex items-center gap-2 rounded-xl border border-zinc-700/80 bg-zinc-900/90 px-4 py-2.5 text-xs font-bold text-zinc-200 shadow-md backdrop-blur-md transition-all hover:border-[var(--color-gold)] hover:text-[var(--color-gold)] hover:shadow-[0_0_12px_rgba(245,200,66,0.1)]"
            >
              <span>📁</span> 批量扫描素材
            </button>
            <button
              type="button"
              onClick={() => createProject.mutate()}
              className="flex items-center gap-2 rounded-xl bg-gradient-to-r from-[#F5C842] to-[#E8933A] px-5 py-2.5 text-xs font-black text-zinc-950 shadow-[0_0_20px_rgba(245,200,66,0.35)] transition-all hover:scale-105 hover:brightness-110 active:scale-95"
            >
              <span>⚡</span> 新建创作工程
            </button>
          </div>
        </div>
      </div>

      {/* 2. 6 大 Multi-Agent 专家团队协同中枢矩阵 */}
      <section className="rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)]/80 p-6 space-y-4 shadow-sm backdrop-blur-sm">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <span className="text-lg">🤖</span>
            <div>
              <h3 className="text-sm font-bold text-[var(--color-gold)]">6 大 Multi-Agent 专家团队协作矩阵</h3>
              <p className="text-xs text-[var(--color-text-secondary)]">Director / VisualCritic / Screenwriter / VoiceArtist / SoundEngineer / QualityReviewer</p>
            </div>
          </div>
          <button
            type="button"
            onClick={() => void navigate({ to: "/production" })}
            className="text-xs font-bold text-[var(--color-gold)] hover:underline flex items-center gap-1 transition-all hover:gap-1.5"
          >
            <span>进入三栏创作工作台</span>
            <span>➔</span>
          </button>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-6 gap-3">
          {[
            { id: 1, name: "总控导演", en: "Director", icon: "🎬", role: "全局任务规划与多智能体分发", tag: "Orchestrator" },
            { id: 2, name: "视觉分析", en: "VisualCritic", icon: "👁️", role: "多模态关键帧与情绪反转", tag: "Vision AI" },
            { id: 3, name: "金牌编剧", en: "Screenwriter", icon: "✍️", role: "0~3s Hook 与高能独白", tag: "Story LLM" },
            { id: 4, name: "声乐调音", en: "VoiceArtist", icon: "🎙️", role: "48kHz 情感配音与克隆", tag: "Neural TTS" },
            { id: 5, name: "混音剪辑", en: "SoundEngineer", icon: "🎛️", role: "5 轨毫秒级对齐与 BGM 闪避", tag: "5-Track Mix" },
            { id: 6, name: "质量验收", en: "QualityReviewer", icon: "🔍", role: "违禁词与剪映草稿质检", tag: "Quality QA" },
          ].map((s) => (
            <div
              key={s.id}
              onClick={() => void navigate({ to: "/production" })}
              className="group flex flex-col justify-between rounded-xl border border-[var(--color-border)] bg-[var(--color-bg)]/90 p-3.5 cursor-pointer transition-all hover:border-[var(--color-gold)]/80 hover:shadow-lg hover:scale-102"
            >
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-2xl transition-transform group-hover:scale-110">{s.icon}</span>
                  <span className="rounded bg-zinc-800/90 px-1.5 py-0.5 text-[8px] font-mono text-[var(--color-gold)]">
                    {s.tag}
                  </span>
                </div>
                <div className="text-xs font-bold text-[var(--color-text-primary)]">{s.name}</div>
                <div className="text-[9px] text-[var(--color-text-muted)] font-mono">{s.en}</div>
              </div>
              <div className="text-[10px] text-zinc-500 mt-2.5 line-clamp-2 leading-relaxed">
                {s.role}
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* 3. 本地创作工程胶片卡片网格 */}
      <section className="space-y-3.5">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <h2 className="text-sm font-bold text-[var(--color-text-primary)] tracking-tight">
              本地创作工程 (Narrative Projects)
            </h2>
            <span className="rounded-full bg-zinc-800 px-2 py-0.5 text-[10px] font-mono font-bold text-[var(--color-gold)]">
              {recentPaths?.length ?? 0}
            </span>
          </div>
          <button
            type="button"
            onClick={() => void navigate({ to: "/assets" })}
            className="text-xs text-[var(--color-text-secondary)] hover:text-[var(--color-gold)] flex items-center gap-1 transition-all hover:gap-1.5"
          >
            <span>查看项目资产库</span>
            <span>➔</span>
          </button>
        </div>

        {loadingRecents ? (
          <div className="flex h-36 items-center justify-center rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)] text-xs text-zinc-500 font-mono">
            <span>正在检索本地工程库...</span>
          </div>
        ) : hasProjects ? (
          <div className="grid grid-cols-1 gap-3.5 md:grid-cols-3">
            {recentPaths.slice(0, 6).map((p, idx) => {
              const name = p.split(/[/\\]/).pop()?.replace(/\.splicr(\.json)?$/, "") ?? p;
              return (
                <div
                  key={p}
                  onClick={() => handleOpenProject(p)}
                  className="group flex flex-col justify-between rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)]/90 p-4 transition-all hover:border-[var(--color-gold)] hover:shadow-xl cursor-pointer"
                >
                  <div className="space-y-2.5">
                    <div className="flex items-center justify-between">
                      <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-[var(--color-gold-muted)] text-xs font-bold text-[var(--color-gold)]">
                        #{idx + 1}
                      </span>
                      <span className="rounded-md border border-emerald-500/30 bg-emerald-500/10 px-2 py-0.5 font-mono text-[9px] text-emerald-400 font-semibold">
                        ● 就绪草稿
                      </span>
                    </div>
                    <h3 className="text-sm font-bold text-[var(--color-text-primary)] group-hover:text-[var(--color-gold)] truncate">
                      {name}
                    </h3>
                    <p className="font-mono text-[10px] text-zinc-500 truncate">{p}</p>
                  </div>
                  <div className="flex items-center justify-between pt-3.5 mt-3 border-t border-[var(--color-border)]/60 text-xs text-[var(--color-gold)] font-bold">
                    <span>进入剪辑工作台</span>
                    <span className="transition-transform group-hover:translate-x-1">➔</span>
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center rounded-2xl border border-dashed border-[var(--color-border)] bg-[var(--color-surface)]/50 p-10 text-center space-y-3">
            <span className="text-3xl">🎞️</span>
            <div className="space-y-1">
              <h4 className="text-sm font-bold text-[var(--color-text-primary)]">暂无历史解说工程</h4>
              <p className="text-xs text-[var(--color-text-secondary)]">
                点击上方「新建创作工程」快速启动第一个 AI 短剧解说项目
              </p>
            </div>
            <button
              type="button"
              onClick={() => createProject.mutate()}
              className="rounded-xl bg-[var(--color-gold-muted)] border border-[var(--color-gold)]/40 px-4 py-1.5 text-xs font-bold text-[var(--color-gold)] hover:bg-[var(--color-gold)] hover:text-zinc-950 transition-all"
            >
              ＋ 创建空白工程
            </button>
          </div>
        )}
      </section>

      {/* 4. 底栏系统加速状态条 */}
      <div className="flex items-center justify-between rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)]/60 px-4 py-2.5 text-xs text-[var(--color-text-secondary)]">
        <div className="flex items-center gap-4">
          <span className="flex items-center gap-1.5 font-semibold text-[var(--color-gold)]">
            <span>⚡</span> Apple Metal / NVENC 硬件加速就绪
          </span>
          <span className="text-[var(--color-border)]">|</span>
          <span>11 大大模型 (Qwen 3.8 / DeepSeek V4 / GPT-5.6) 在线</span>
          <span className="text-[var(--color-border)]">|</span>
          <span>GPT-SoVITS 人声克隆探针 (127.0.0.1:9880)</span>
        </div>
        <span className="font-mono text-[10px] text-[var(--color-text-muted)]">v1.0.1 · Tauri 2.0 + Rust</span>
      </div>

      <BatchImportDialog open={showImport} onClose={() => setShowImport(false)} />
    </div>
  );
}
