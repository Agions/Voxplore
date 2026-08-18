/**
 * splicr v1.0.1 · 首页 Dashboard (直通三栏专业解说工作台)
 */

import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useMutation, useQueryClient } from "@tanstack/react-query";
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

  return (
    <div className="mx-auto max-w-6xl space-y-8 px-8 py-8 select-none">
      {/* 1. Header */}
      <div className="flex items-center justify-between">
        <div className="space-y-1">
          <h1 className="text-3xl font-extrabold tracking-tight text-[var(--color-text-primary)]">
            splicr 叙影{" "}
            <span className="bg-gradient-to-r from-[#F5C842] via-[#F9D76B] to-[#E8933A] bg-clip-text text-transparent font-bold">
              · 三栏专业影视解说工作台
            </span>
          </h1>
          <p className="text-xs text-[var(--color-text-secondary)] font-medium tracking-wide">
            短剧拆条 ➔ 5轨磁性时间轴 ➔ AI独白与人声克隆 ➔ 原生剪映草稿导出
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
            <span>⚡</span> 进入解说工作台
          </button>
        </div>
      </div>

      {/* 2. 最近短剧项目卡片 */}
      <section className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-bold text-[var(--color-text-primary)] tracking-tight">
            最近创作工程 (Recent Drama Projects)
          </h2>
          <span className="text-[10px] font-mono text-[var(--color-gold)]">4 个活跃草稿</span>
        </div>

        <div className="grid grid-cols-4 gap-4">
          {[
            { id: "p1", name: "1. 逆袭复仇短剧 · 第1集", tag: "高能反转", time: "10分钟前", status: "Active" },
            { id: "p2", name: "2. 都市商战谍影 · 第4集", tag: "悬疑独白", time: "2小时前", status: "Rendered" },
            { id: "p3", name: "3. 破晓迷案解说 · 电影版", tag: "硬核解析", time: "昨天", status: "Draft" },
            { id: "p4", name: "4. 豪门风云录 · 预告片", tag: "Hook剪辑", time: "3天前", status: "Active" },
          ].map((item) => (
            <div
              key={item.id}
              onClick={() => void navigate({ to: "/production" })}
              className="group flex flex-col rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)] p-3 cursor-pointer transition-all hover:border-[var(--color-gold)] hover:shadow-[0_0_20px_var(--color-gold-glow)]"
            >
              <div className="relative h-28 w-full overflow-hidden rounded-xl bg-zinc-950 border border-zinc-800 mb-2">
                <img
                  src={`https://images.unsplash.com/photo-1536440136628-849c177e76a1?w=400&q=80`}
                  alt="cover"
                  className="h-full w-full object-cover opacity-80 transition-transform duration-300 group-hover:scale-105"
                />
                <span className="absolute top-2 left-2 rounded bg-black/60 px-1.5 py-0.5 font-mono text-[9px] text-[var(--color-gold)] backdrop-blur-md">
                  {item.tag}
                </span>
                <span className="absolute bottom-2 right-2 rounded bg-emerald-500/20 border border-emerald-500/40 px-1.5 py-0.5 font-mono text-[9px] text-emerald-400">
                  {item.status}
                </span>
              </div>
              <span className="text-xs font-bold text-[var(--color-text-primary)] truncate">{item.name}</span>
              <span className="text-[10px] text-[var(--color-text-muted)] mt-1">{item.time}</span>
            </div>
          ))}
        </div>
      </section>

      {/* 3. 7 步全自动流水线概览 */}
      <section className="rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)] p-6 space-y-4 shadow-sm">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-sm font-bold text-[var(--color-gold)]">⚡ 7 步全自动化解说工厂 (7-Step Auto Pipeline)</h3>
            <p className="text-xs text-[var(--color-text-secondary)]">无需人工繁琐拼接，单屏集成流水线全链路掌控</p>
          </div>
          <button
            type="button"
            onClick={() => void navigate({ to: "/production" })}
            className="text-xs font-bold text-[var(--color-gold)] hover:underline"
          >
            打开三栏工作台 →
          </button>
        </div>

        <div className="grid grid-cols-7 gap-2">
          {[
            { id: 1, name: "素材解析", en: "Media Intake", icon: "📥" },
            { id: 2, name: "智能拆条", en: "Scene Detect", icon: "✂️" },
            { id: 3, name: "独白剧本", en: "Script Gen", icon: "🤖" },
            { id: 4, name: "配音克隆", en: "Voice Clone", icon: "🎙️" },
            { id: 5, name: "VAD字幕", en: "Subtitles", icon: "📝" },
            { id: 6, name: "音画混流", en: "MultiTrack", icon: "🎬" },
            { id: 7, name: "剪映草稿", en: "Export Draft", icon: "📤" },
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
