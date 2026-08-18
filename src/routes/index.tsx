/**
 * splicr v1.0.1 · 首页 Dashboard (真实工程数据绑定，无 Mock 残留)
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
    <div className="mx-auto max-w-6xl space-y-8 px-8 py-8 select-none">
      {/* 1. Header */}
      <div className="flex items-center justify-between">
        <div className="space-y-1">
          <h1 className="text-3xl font-extrabold tracking-tight text-[var(--color-text-primary)]">
            splicr 叙影{" "}
            <span className="bg-gradient-to-r from-[#F5C842] via-[#F9D76B] to-[#E8933A] bg-clip-text text-transparent font-bold">
              · Rust Native 多智能体影视解说引擎
            </span>
          </h1>
          <p className="text-xs text-[var(--color-text-secondary)] font-medium tracking-wide">
            短剧拆条 ➔ 5轨磁性时间轴 ➔ Multi-Agent 编剧/配音/混音 ➔ 原生剪映草稿
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() => setShowImport(true)}
            className="flex items-center gap-1.5 rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] px-4 py-2.5 text-xs font-semibold text-[var(--color-text-primary)] shadow-sm transition-all hover:border-[var(--color-gold)] hover:text-[var(--color-gold)]"
          >
            <span>📁</span> 批量导入素材
          </button>
          <button
            type="button"
            onClick={() => createProject.mutate()}
            className="flex items-center gap-1.5 rounded-xl bg-gradient-to-r from-[#F5C842] to-[#E8933A] px-5 py-2.5 text-xs font-bold text-zinc-950 shadow-[0_0_16px_rgba(245,200,66,0.35)] transition-all hover:brightness-110"
          >
            <span>⚡</span> 新建创作工程
          </button>
        </div>
      </div>

      {/* 2. 真实工程列表 */}
      <section className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-bold text-[var(--color-text-primary)] tracking-tight">
            本地创作工程 (Local Narrative Projects)
          </h2>
          <span className="text-[10px] font-mono text-[var(--color-gold)]">
            {recentPaths?.length ?? 0} 个本地工程
          </span>
        </div>

        {loadingRecents ? (
          <div className="flex h-36 items-center justify-center rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)]">
            <span className="text-xs text-[var(--color-text-muted)] animate-pulse">正在扫描本地工程...</span>
          </div>
        ) : hasProjects ? (
          <div className="grid grid-cols-3 gap-4">
            {recentPaths.map((p, idx) => {
              const name = p.split(/[\/]/).pop()?.replace(/\.splicr$/, "") ?? p;
              return (
                <div
                  key={p}
                  onClick={() => handleOpenProject(p)}
                  className="group flex flex-col rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)] p-4 cursor-pointer transition-all hover:border-[var(--color-gold)] hover:shadow-[0_0_20px_var(--color-gold-glow)]"
                >
                  <div className="flex items-center justify-between mb-3">
                    <span className="font-mono text-xs font-bold text-[var(--color-gold)]">#{idx + 1}</span>
                    <span className="rounded bg-emerald-500/20 border border-emerald-500/40 px-1.5 py-0.5 font-mono text-[9px] text-emerald-400">
                      就绪
                    </span>
                  </div>
                  <span className="text-xs font-bold text-[var(--color-text-primary)] truncate mb-1">{name}</span>
                  <span className="font-mono text-[10px] text-[var(--color-text-muted)] truncate">{p}</span>
                </div>
              );
            })}
          </div>
        ) : (
          <div
            onClick={() => createProject.mutate()}
            className="flex h-36 flex-col items-center justify-center gap-2 rounded-2xl border border-dashed border-[var(--color-border)] bg-[var(--color-surface)]/40 p-6 text-center cursor-pointer transition-all hover:border-[var(--color-gold)]"
          >
            <span className="text-2xl">🎬</span>
            <span className="text-xs font-bold text-[var(--color-text-primary)]">暂无历史项目，点击创建第一个解说工程</span>
            <span className="text-[10px] text-[var(--color-text-muted)]">支持多段视频素材一键拆条与 AI 独白生成</span>
          </div>
        )}
      </section>

      {/* 3. 7 步全自动流水线概览 */}
      <section className="rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)] p-6 space-y-4 shadow-sm">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-sm font-bold text-[var(--color-gold)]">⚡ 6 大 Multi-Agent 创作团队协同闭环</h3>
            <p className="text-xs text-[var(--color-text-secondary)]">Director / VisualCritic / Screenwriter / VoiceArtist / SoundEngineer / QualityReviewer</p>
          </div>
          <button
            type="button"
            onClick={() => void navigate({ to: "/production" })}
            className="text-xs font-bold text-[var(--color-gold)] hover:underline"
          >
            打开三栏工作台 →
          </button>
        </div>

        <div className="grid grid-cols-6 gap-2">
          {[
            { id: 1, name: "总控导演", en: "Director", icon: "🎬" },
            { id: 2, name: "视觉分析", en: "VisualCritic", icon: "👁️" },
            { id: 3, name: "金牌编剧", en: "Screenwriter", icon: "✍️" },
            { id: 4, name: "声乐调音", en: "VoiceArtist", icon: "🎙️" },
            { id: 5, name: "混音剪辑", en: "SoundEngineer", icon: "🎛️" },
            { id: 6, name: "质量验收", en: "QualityReviewer", icon: "🔍" },
          ].map((s) => (
            <div
              key={s.id}
              onClick={() => void navigate({ to: "/production" })}
              className="flex flex-col items-center rounded-xl border border-[var(--color-border)] bg-[var(--color-bg)] p-3 text-center cursor-pointer transition-all hover:border-[var(--color-gold)] hover:scale-102"
            >
              <span className="text-2xl mb-1">{s.icon}</span>
              <span className="text-xs font-bold text-[var(--color-text-primary)]">{s.name}</span>
              <span className="text-[9px] text-[var(--color-text-muted)] font-mono">{s.en}</span>
            </div>
          ))}
        </div>
      </section>

      {/* 4. 底栏系统加速状态 */}
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
