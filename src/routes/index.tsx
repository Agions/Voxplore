/**
 * Vynaro v1.0.0 · 首页 Dashboard (完美适配亮色/暗色双模式与中英文双语)
 */

import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { BatchImportDialog } from "@components/dialogs/BatchImportDialog";
import { ThumbnailImage } from "@components/common/ThumbnailImage";
import { useProjectStore } from "@stores/project-store";
import { useSettingsStore } from "@stores/settings-store";
import { t } from "@lib/i18n";
import { toast } from "sonner";
import {
  appIpc,
  pipelineIpc,
  projectIpc,
} from "@ipc/commands";

export const Route = createFileRoute("/")({
  component: HomePage,
});

function HomePage() {
  return (
    <div className="mx-auto max-w-6xl space-y-8 px-8 py-8">
      {/* 1. 顶部 Header */}
      <WelcomeHeader />

      {/* 2. 最近视频项目卡片 */}
      <RecentProjectsSection />

      {/* 3. 7 步 AI 叙事流水线 */}
      <PipelineSection />

      {/* 4. 快捷操作栏 */}
      <QuickActionsSection />

      {/* 5. 底栏系统探针状态 */}
      <SystemStatusStrip />
    </div>
  );
}

// ── 1. Welcome Header ──────────────────────────────────────────────

function WelcomeHeader() {
  const locale = useSettingsStore((s) => s.locale);
  return (
    <div className="space-y-1">
      <h1 className="text-3xl font-extrabold tracking-tight text-[var(--color-text-primary)]">
        {t("home.welcome_title", locale)}{" "}
        <span className="bg-gradient-to-r from-[#F5C842] via-[#F9D76B] to-[#E8933A] bg-clip-text text-transparent font-normal">
          · 电影级 AI 短剧与影视解说
        </span>
      </h1>
      <p className="text-xs text-[var(--color-text-secondary)] font-medium tracking-wide">
        {t("home.welcome_subtitle", locale)}
      </p>
    </div>
  );
}

// ── 2. Recent Video Projects ───────────────────────────────────────

function RecentProjectsSection() {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const locale = useSettingsStore((s) => s.locale);
  const setCurrentRecord = useProjectStore((s) => s.setCurrentRecord);

  const { data: recentPaths } = useQuery({
    queryKey: ["home-recent-projects"],
    queryFn: () => projectIpc.listRecent(),
  });

  const createProject = useMutation({
    mutationFn: projectIpc.createBlank,
    onSuccess: (rec) => {
      qc.setQueryData(["current-project"], rec);
      setCurrentRecord(rec.path, rec.project);
      void navigate({ to: "/production" });
      toast.success(locale === "en-US" ? "New Narrative Project Created" : "新建解说工程已建立");
    },
    onError: (e) => {
      toast.error("创建工程失败", { description: e instanceof Error ? e.message : String(e) });
    },
  });

  const hasRecents = recentPaths && recentPaths.length > 0;

  return (
    <section className="space-y-3">
      {/* Header with See All */}
      <div className="flex items-center justify-between">
        <h2 className="text-base font-semibold text-[var(--color-text-primary)] tracking-tight">
          {t("home.recent_title", locale)}
        </h2>
        {hasRecents && (
          <button
            type="button"
            onClick={() => void navigate({ to: "/assets" })}
            className="text-xs font-medium text-[var(--color-text-secondary)] transition hover:text-[var(--color-gold)]"
          >
            {t("home.see_all", locale)}
          </button>
        )}
      </div>

      {!hasRecents ? (
        <div className="flex flex-col items-center justify-center rounded-2xl border border-dashed border-[var(--color-border)] bg-[var(--color-surface)] p-10 text-center">
          <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-[var(--color-gold-muted)] border border-[var(--color-gold)]/30 text-[var(--color-gold)] text-2xl mb-3">
            🎬
          </div>
          <h3 className="text-sm font-bold text-[var(--color-text-primary)]">
            {t("home.no_project", locale)}
          </h3>
          <p className="text-xs text-[var(--color-text-secondary)] mt-1 mb-4">
            {t("home.no_project_sub", locale)}
          </p>
          <button
            type="button"
            onClick={() => createProject.mutate()}
            disabled={createProject.isPending}
            className="btn-primary text-xs px-5 py-2.5 font-bold"
          >
            {t("home.create_project", locale)}
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
          {recentPaths.slice(0, 3).map((realPath) => {
            const displayTitle = realPath.split(/[/\\]/).pop() || realPath;

            const handleOpenProject = async (e?: React.MouseEvent) => {
              if (e) {
                e.preventDefault();
                e.stopPropagation();
              }
              try {
                const rec = await projectIpc.load(realPath);
                setCurrentRecord(rec.path, rec.project);
                qc.setQueryData(["current-project"], rec);
                qc.setQueryData(["assets-current-project"], rec.project);
                toast.success(locale === "en-US" ? `Opened project ${rec.project.name}` : `已打开解说工程 ${rec.project.name}`);
                void navigate({ to: "/production" });
              } catch (err) {
                toast.error("加载项目失败", { description: err instanceof Error ? err.message : String(err) });
              }
            };

            return (
              <div
                key={realPath}
                onClick={handleOpenProject}
                className="group relative cursor-pointer overflow-hidden rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)] p-4 transition-all duration-300 hover:border-[var(--color-gold)] hover:bg-[var(--color-surface-elevated)] hover:shadow-[0_0_24px_var(--color-gold-glow)]"
              >
                {/* Thumbnail Container */}
                <div className="relative mb-3.5 h-28 w-full overflow-hidden rounded-xl bg-zinc-950/80 border border-[var(--color-border)]">
                  <div className="absolute inset-0 bg-gradient-to-t from-[var(--color-surface)] via-transparent to-transparent z-10 opacity-70" />
                  <ThumbnailImage source={realPath} kind="video" width={320} />
                </div>

                {/* Title & Metadata */}
                <div className="mb-3 space-y-0.5">
                  <h3 className="truncate text-sm font-semibold text-[var(--color-text-primary)] group-hover:text-[var(--color-gold)] transition-colors">
                    {displayTitle}
                  </h3>
                  <p className="text-[11px] text-[var(--color-text-muted)] font-mono">
                    {t("home.project_file_tag", locale)}
                  </p>
                </div>

                {/* Action CTA */}
                <div className="flex items-center justify-between gap-3 border-t border-[var(--color-border)] pt-2.5">
                  <span className="text-[11px] font-semibold text-[var(--color-gold)]">
                    {t("action.enter", locale)}
                  </span>
                  <button
                    type="button"
                    onClick={handleOpenProject}
                    className="flex h-7 w-7 items-center justify-center rounded-full bg-[var(--color-gold)] text-zinc-950 font-bold shadow-[0_0_10px_var(--color-gold-glow)] transition-transform duration-200 group-hover:scale-110"
                  >
                    ▶
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
}

// ── 3. 7-Step AI Narrative Pipeline Card ───────────────────────────

function PipelineSection() {
  const navigate = useNavigate();
  const locale = useSettingsStore((s) => s.locale);

  const steps = [
    {
      num: 1,
      nameZh: "素材导入",
      nameEn: "Media Intake",
      descZh: "格式校验与分析",
      descEn: "Format & resolution",
      icon: "📥",
    },
    {
      num: 2,
      nameZh: "智能拆条",
      nameEn: "Scene Cut",
      descZh: "FFmpeg 镜头检测",
      descEn: "Scene transitions",
      icon: "🔍",
    },
    {
      num: 3,
      nameZh: "文案脚本",
      nameEn: "AI Script",
      descZh: "第一人称视角",
      descEn: "1st-person monologue",
      icon: "📝",
    },
    {
      num: 4,
      nameZh: "TTS 配音",
      nameEn: "TTS Voice",
      descZh: "零样本人声克隆",
      descEn: "Voice cloning & synth",
      icon: "🎙️",
    },
    {
      num: 5,
      nameZh: "字幕特效",
      nameEn: "Subtitles",
      descZh: "VAD 时间轴花字",
      descEn: "VAD timeline & FX",
      icon: "💬",
    },
    {
      num: 6,
      nameZh: "音画对齐",
      nameEn: "Sync Align",
      descZh: "多轨混音与高潮",
      descEn: "Multi-track timeline",
      icon: "🔀",
    },
    {
      num: 7,
      nameZh: "草稿导出",
      nameEn: "Draft Export",
      descZh: "剪映工程多平台",
      descEn: "CapCut draft export",
      icon: "📤",
    },
  ];

  return (
    <section className="rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)] p-6 backdrop-blur-xl shadow-xl space-y-5">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-[var(--color-border)] pb-4">
        <div>
          <h2 className="text-base font-bold text-[var(--color-text-primary)] tracking-tight">
            {t("home.pipeline_title", locale)}
          </h2>
          <p className="text-xs text-[var(--color-text-secondary)] mt-0.5">
            {locale === "en-US" ? "End-to-end 7-step automated narrative video production" : "全流程 7 步一键贯通解说视频自动化生产"}
          </p>
        </div>
        <span className="self-start sm:self-auto font-mono text-xs text-[var(--color-gold)] bg-[var(--color-gold-muted)] border border-[var(--color-gold)]/30 px-3 py-1 rounded-full font-medium">
          7 Steps Workflow
        </span>
      </div>

      {/* Grid of cards with ample padding and non-truncated multi-line text */}
      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-3">
        {steps.map((step) => {
          const title = locale === "en-US" ? step.nameEn : step.nameZh;
          const desc = locale === "en-US" ? step.descEn : step.descZh;

          return (
            <div
              key={step.num}
              onClick={() => void navigate({ to: "/production" })}
              className="group relative flex flex-col justify-between cursor-pointer rounded-2xl border border-[var(--color-border)] bg-[var(--color-bg)] p-3.5 text-left transition-all duration-300 hover:border-[var(--color-gold)] hover:bg-[var(--color-surface-elevated)] hover:shadow-[0_0_20px_var(--color-gold-glow)] hover:-translate-y-0.5 min-h-[105px]"
            >
              <div className="flex items-center justify-between mb-2">
                <span className="font-mono text-[10px] font-bold text-[var(--color-gold)] bg-[var(--color-gold-muted)] px-2 py-0.5 rounded-md border border-[var(--color-gold)]/30">
                  0{step.num}
                </span>
                <div className="flex h-7 w-7 items-center justify-center rounded-xl bg-[var(--color-gold-muted)] border border-[var(--color-gold)]/20 text-[var(--color-gold)] text-sm group-hover:scale-110 transition-transform">
                  {step.icon}
                </div>
              </div>

              <div className="space-y-0.5">
                <h3 className="text-xs font-bold text-[var(--color-text-primary)] group-hover:text-[var(--color-gold)] transition-colors leading-snug">
                  {title}
                </h3>
                <p className="text-[10px] text-[var(--color-text-muted)] leading-tight">
                  {desc}
                </p>
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}

// ── 4. Quick Actions Section ───────────────────────────────────────

function QuickActionsSection() {
  const navigate = useNavigate();
  const locale = useSettingsStore((s) => s.locale);
  const [openImport, setOpenImport] = useState(false);

  return (
    <section className="space-y-3">
      <h2 className="text-base font-semibold text-[var(--color-text-primary)] tracking-tight">
        {t("home.quick_actions", locale)}
      </h2>

      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        {/* Button 1: Solid Vibrant Gold "➕ 新建工程" */}
        <button
          type="button"
          onClick={() => void navigate({ to: "/production" })}
          className="flex h-12 items-center justify-center rounded-xl bg-[var(--color-gold)] px-6 text-xs font-bold text-zinc-950 shadow-[0_0_20px_var(--color-gold-glow)] transition-all duration-300 hover:brightness-110 hover:scale-[1.02]"
        >
          ➕ {t("home.action_new", locale)}
        </button>

        {/* Button 2: Import Media */}
        <button
          type="button"
          onClick={() => setOpenImport(true)}
          className="flex h-12 items-center justify-center rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] px-6 text-xs font-semibold text-[var(--color-text-primary)] transition-all duration-300 hover:border-[var(--color-gold)]/60 hover:bg-[var(--color-surface-elevated)]"
        >
          📂 {t("home.action_scan", locale)}
        </button>

        {/* Button 3: Engine Settings */}
        <button
          type="button"
          onClick={() => void navigate({ to: "/settings" })}
          className="flex h-12 items-center justify-center rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] px-6 text-xs font-semibold text-[var(--color-text-primary)] transition-all duration-300 hover:border-[var(--color-gold)]/60 hover:bg-[var(--color-surface-elevated)]"
        >
          ⚙️ {t("home.action_settings", locale)}
        </button>

        {/* Button 4: Help Center */}
        <button
          type="button"
          onClick={() => void navigate({ to: "/help" })}
          className="flex h-12 items-center justify-center rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] px-6 text-xs font-semibold text-[var(--color-text-primary)] transition-all duration-300 hover:border-[var(--color-gold)]/60 hover:bg-[var(--color-surface-elevated)]"
        >
          📘 {t("home.action_help", locale)}
        </button>
      </div>

      <BatchImportDialog
        open={openImport}
        onClose={() => setOpenImport(false)}
        onImported={() => {
          setOpenImport(false);
        }}
      />
    </section>
  );
}

// ── 5. System Status Strip (Compact Footer) ───────────────────────

function SystemStatusStrip() {
  const locale = useSettingsStore((s) => s.locale);
  const version = useQuery({
    queryKey: ["home-version"],
    queryFn: appIpc.version,
  });
  const stepDefs = useQuery({
    queryKey: ["home-steps"],
    queryFn: pipelineIpc.stepDefs,
  });
  const sysInfo = useQuery({
    queryKey: ["home-sys"],
    queryFn: appIpc.systemInfo,
  });

  const ok = !version.isError && !stepDefs.isError && !sysInfo.isError;
  const ffmpegOk = sysInfo.data?.ffmpegAvailable ?? false;

  return (
    <div className="flex flex-wrap items-center gap-2 pt-2 text-xs font-mono text-[var(--color-text-muted)]">
      <span className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 border text-[11px] ${
        ok ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-500" : "border-rose-500/30 bg-rose-500/10 text-rose-500"
      }`}>
        <span className={`h-1.5 w-1.5 rounded-full ${ok ? "bg-emerald-500 animate-pulse" : "bg-rose-500"}`} />
        {ok ? (locale === "en-US" ? "Tauri Connected" : "Tauri 已连接") : "Disconnected"}
      </span>

      <span className="inline-flex items-center rounded-full border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-1 text-[11px] text-[var(--color-text-secondary)]">
        v{version.data ?? "1.0.0"}
      </span>

      <span className="inline-flex items-center rounded-full border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-1 text-[11px] text-[var(--color-text-secondary)]">
        {stepDefs.data?.length ?? 7} {locale === "en-US" ? "Pipeline Steps" : "步解说工作流"}
      </span>

      <span className={`inline-flex items-center rounded-full px-3 py-1 border text-[11px] ${
        ffmpegOk ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-500" : "border-amber-500/30 bg-amber-500/10 text-amber-500"
      }`}>
        FFmpeg {ffmpegOk ? (locale === "en-US" ? "Ready" : "已就绪") : "Probe"}
      </span>
    </div>
  );
}
