/**
 * Monoloop v1.0.0 · 项目管理页 — 电影调光室主题（深黑 + 暖金）
 *
 * 1. 顶部: 项目统计看板 (项目数/媒体文件/脚本/轨道)
 * 2. 当前项目: 素材清单 + 缩略图 + 实时搜索 + 单文件/批量目录导入
 * 3. 历史项目: 胶片卡片网格 (支持打开/删除)
 * 4. 视觉对齐: 完整对齐 design_report.md 电影调光室风格
 */

import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { open } from "@tauri-apps/plugin-dialog";
import { projectIpc } from "@ipc/commands";
import { useAssets } from "@hooks/useAssets";
import { useProject } from "@hooks/useProject";
import { useProjectStore } from "@stores/project-store";
import { useSettingsStore } from "@stores/settings-store";
import { t } from "@lib/i18n";
import { BatchImportDialog } from "@components/dialogs/BatchImportDialog";
import { ThumbnailImage } from "@components/common/ThumbnailImage";
import { toast } from "sonner";
import type { MediaFile, Project } from "@ipc/types.gen";

export const Route = createFileRoute("/assets")({
  component: AssetsPage,
});

function AssetsPage() {
  const qc = useQueryClient();
  const navigate = useNavigate();
  const locale = useSettingsStore((s) => s.locale);

  const { data: recents, isLoading } = useQuery({
    queryKey: ["assets-recent"],
    queryFn: projectIpc.listRecent,
  });

  // 读取当前已打开的项目（由 production 页面写入 QueryClient 缓存）
  const currentRaw = qc.getQueryData<{ project: Project } | null>(["current-project"]);
  const current = currentRaw?.project ?? null;


  const {
    importFromPaths,
    remove: removeAssets,
    search,
    loading: assetsLoading,
  } = useAssets();

  const { hasProject } = useProject();

  const [importError, setImportError] = useState<string | null>(null);
  const [showBatchDialog, setShowBatchDialog] = useState(false);
  const [matchingPaths, setMatchingPaths] = useState<string[] | null>(null);

  const handleImportMedia = async () => {
    setImportError(null);
    try {
      const selected = await open({
        multiple: true,
        filters: [
          {
            name: "视频文件",
            extensions: ["mp4", "mov", "avi", "mkv", "webm"],
          },
        ],
      });
      if (!selected) return;
      const paths = Array.isArray(selected) ? selected : [selected];
      await importFromPaths(paths);
      toast.success(`成功导入 ${paths.length} 个视频文件`);
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      setImportError(msg);
      toast.error("导入素材失败", { description: msg });
    }
  };

  const handleRemoveMedia = async (id: string) => {
    setImportError(null);
    try {
      await removeAssets([id]);
      toast.success("已移除素材");
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      setImportError(msg);
      toast.error("移除素材失败", { description: msg });
    }
  };

  const handleSearch = async (pattern: string) => {
    if (!pattern.trim() || !current) {
      setMatchingPaths(null);
      return;
    }
    try {
      const all = current.media_files.map((m) => m.path);
      const filtered = await search(all, pattern.trim());
      setMatchingPaths(filtered);
    } catch {
      setMatchingPaths(null);
    }
  };

  const setCurrentRecord = useProjectStore((s) => s.setCurrentRecord);

  const handleCreateBlank = async () => {
    try {
      const rec = await projectIpc.createBlank();
      setCurrentRecord(rec.path, rec.project);
      qc.setQueryData(["assets-current-project"], rec.project);
      qc.setQueryData(["current-project"], rec);
      void qc.invalidateQueries({ queryKey: ["assets-recent"] });
      toast.success(`已创建空白项目 ${rec.project.name}`);
      void navigate({ to: "/production" });
    } catch (e) {
      toast.error("创建空白项目失败", { description: String(e) });
    }
  };

  const filteredMedia = useMemo<MediaFile[]>(() => {
    if (!matchingPaths) return current?.media_files ?? [];
    const set = new Set(matchingPaths);
    return (current?.media_files ?? []).filter((m) => set.has(m.path));
  }, [current?.media_files, matchingPaths]);

  return (
    <div className="mx-auto max-w-6xl space-y-8 px-6 py-8">
      {/* 页头 */}
      <header className="flex items-start justify-between border-b border-[var(--color-border)] pb-6">
        <div className="space-y-1">
          <div className="text-[11px] font-bold uppercase tracking-[0.2em] text-[var(--color-gold)]">
            PROJECT MANAGEMENT
          </div>
          <h1 className="text-3xl font-bold tracking-tight text-[var(--color-text-primary)]">
            {t("assets.title", locale)}
          </h1>
          <p className="text-xs text-[var(--color-text-secondary)]">
            {t("assets.subtitle", locale)}
          </p>
        </div>

        {recents && recents.length > 0 && (
          <button
            type="button"
            onClick={handleCreateBlank}
            className="flex items-center gap-2 rounded-xl bg-gradient-to-r from-amber-400 to-yellow-500 px-5 py-2.5 text-xs font-bold text-zinc-950 shadow-lg shadow-amber-500/20 transition hover:shadow-amber-500/40 hover:brightness-105"
          >
            <span>✨</span>
            <span>{t("action.create", locale)}</span>
          </button>
        )}
      </header>

      {/* 当前项目信息卡 / 状态 */}
      <CurrentProjectCard
        project={current ?? null}
        onImportMedia={handleImportMedia}
        onRemoveMedia={handleRemoveMedia}
        onOpenBatchDialog={() => setShowBatchDialog(true)}
        onSearch={handleSearch}
        filteredMedia={filteredMedia}
        searching={assetsLoading}
        importing={assetsLoading}
        importError={importError}
        hasProject={hasProject}
        onCreateBlank={handleCreateBlank}
      />

      {/* 最近项目 */}
      <section className="space-y-4">
        <div className="flex items-center justify-between border-b border-[var(--color-border)]/60 pb-3">
          <div>
            <h2 className="text-base font-bold text-[var(--color-text-primary)]">
              {t("assets.recent", locale)}
            </h2>
            <p className="text-[11px] text-[var(--color-text-secondary)]">
              {t("assets.recent_subtitle", locale)}
            </p>
          </div>
        </div>

        {isLoading ? (
          <SkeletonGrid />
        ) : recents && recents.length > 0 ? (
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
            {recents.map((p: string, idx: number) => (
              <RecentCard key={p} path={p} index={idx + 1} />
            ))}
          </div>
        ) : (
          <EmptyState />
        )}
      </section>

      <BatchImportDialog
        open={showBatchDialog}
        onClose={() => setShowBatchDialog(false)}
        onImported={() => {
          setMatchingPaths(null);
        }}
      />
    </div>
  );
}

// ── 当前项目信息卡 ─────────────────────────────────────────────────

function CurrentProjectCard({
  project,
  onImportMedia,
  onRemoveMedia,
  onOpenBatchDialog,
  onSearch,
  filteredMedia,
  importing,
  importError,
  hasProject,
  onCreateBlank,
}: {
  project: Project | null;
  onImportMedia: () => Promise<void> | void;
  onRemoveMedia: (id: string) => Promise<void> | void;
  onOpenBatchDialog: () => void;
  onSearch: (pattern: string) => void;
  filteredMedia: MediaFile[];
  searching?: boolean;
  importing: boolean;
  importError: string | null;
  hasProject: boolean;
  onCreateBlank: () => void;
}) {
  const locale = useSettingsStore((s) => s.locale);

  if (!project) {
    return (
      <section className="relative overflow-hidden rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)] p-6 shadow-xl">
        <div className="flex flex-col md:flex-row items-center justify-between gap-6">
          <div className="space-y-2">
            <div className="inline-flex items-center gap-2 rounded-full border border-amber-500/30 bg-amber-500/10 px-3 py-1 text-[11px] font-semibold text-[var(--color-gold)]">
              <span>🎬</span>
              <span>电影调光室影院解说引擎</span>
            </div>
            <h2 className="text-xl font-bold text-[var(--color-text-primary)]">
              {t("assets.no_project", locale)}
            </h2>
            <p className="text-xs text-[var(--color-text-secondary)] max-w-md">
              选择下方的历史项目工程或新建空白项目，开启 AI 第一人称解说、智能拆条与 TTS 配音合成。
            </p>
          </div>
          <button
            type="button"
            onClick={onCreateBlank}
            className="flex shrink-0 items-center gap-2 rounded-xl bg-gradient-to-r from-amber-400 to-yellow-500 px-6 py-3 text-xs font-bold text-zinc-950 shadow-lg shadow-amber-500/20 transition hover:shadow-amber-500/40 hover:brightness-105"
          >
            <span>✨</span>
            <span>{t("assets.create_now", locale)}</span>
          </button>
        </div>
      </section>
    );
  }

  return (
    <section className="rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)] p-6 shadow-xl space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-[var(--color-border)] pb-5">
        <div className="flex items-center gap-4">
          <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br from-amber-400 to-yellow-500 text-lg font-bold text-zinc-950 shadow-md shadow-amber-500/20">
            🎬
          </div>
          <div className="space-y-1">
            <div className="text-lg font-bold text-[var(--color-text-primary)]">
              {project.name}
            </div>
            <div className="font-mono text-[11px] text-[var(--color-text-secondary)]">
              ID: {project.id}
            </div>
          </div>
        </div>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={onOpenBatchDialog}
            disabled={!hasProject}
            className="flex items-center gap-1.5 rounded-xl border border-amber-500/30 bg-amber-500/10 px-4 py-2 text-xs font-medium text-[var(--color-gold)] transition hover:border-amber-500/60 hover:bg-amber-500/20 disabled:opacity-50"
          >
            <span>📂</span>
            <span>{t("assets.batch_import", locale)}</span>
          </button>
          <button
            type="button"
            onClick={onImportMedia}
            disabled={importing || !hasProject}
            className="flex items-center gap-1.5 rounded-xl border border-[var(--color-border)] bg-[var(--color-bg)] px-4 py-2 text-xs font-medium text-[var(--color-text-primary)] transition hover:border-[var(--color-border)] disabled:opacity-50"
          >
            <span>🎞</span>
            <span>{t("action.import", locale)}</span>
          </button>
        </div>
      </div>

      {importError && (
        <div className="rounded-xl border border-rose-800/60 bg-rose-950/30 px-4 py-3 text-xs text-rose-200">
          导入失败: {importError}
        </div>
      )}

      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <Stat label="媒体素材" value={project.media_files.length} tone="amber" />
        <Stat label="脚本段落" value={project.scripts.length} tone="gold" />
        <Stat
          label="时间轴轨道"
          value={project.timeline?.tracks?.length ?? 0}
          tone="dark"
        />
        <Stat
          label="导出记录"
          value={project.exports?.length ?? 0}
          tone="emerald"
        />
      </div>

      {/* 媒体清单:搜索 + 缩略图网格 */}
      {project.media_files.length > 0 && (
        <div className="space-y-4 border-t border-[var(--color-border)] pt-5">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div className="text-xs font-bold text-[var(--color-text-primary)]">
              媒体文件清单 ({filteredMedia.length}/{project.media_files.length})
            </div>
            <div className="relative min-w-[260px] max-w-md">
              <input
                type="search"
                onChange={(e) => onSearch(e.target.value)}
                placeholder="🔍 搜索媒体文件名称..."
                className="w-full rounded-xl border border-[var(--color-border)] bg-[var(--color-bg)] px-3.5 py-2 text-xs text-[var(--color-text-primary)] placeholder-[var(--color-text-muted)] outline-none focus:border-[var(--color-gold)]"
              />
            </div>
          </div>

          {filteredMedia.length === 0 ? (
            <div className="rounded-xl border border-dashed border-[var(--color-border)] bg-[var(--color-bg)] px-4 py-8 text-center text-xs text-[var(--color-text-secondary)]">
              没有匹配的素材
            </div>
          ) : (
            <div className="grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-4">
              {filteredMedia.map((m) => (
                <MediaCard
                  key={m.path}
                  media={m}
                  onRemove={() => onRemoveMedia(m.path)}
                  disabled={importing || !hasProject}
                />
              ))}
            </div>
          )}
        </div>
      )}
    </section>
  );
}

// ── 统计卡片 ──────────────────────────────────────────────────────

function Stat({
  label,
  value,
  tone,
}: {
  label: string;
  value: number;
  tone: "amber" | "gold" | "dark" | "emerald";
}) {
  const map: Record<string, string> = {
    amber: "from-amber-500/10 to-amber-500/0 border-amber-500/30 text-amber-400",
    gold: "from-yellow-500/10 to-yellow-500/0 border-yellow-500/30 text-yellow-400",
    dark: "from-zinc-800/40 to-zinc-800/0 border-[var(--color-border)] text-zinc-300",
    emerald: "from-emerald-500/10 to-emerald-500/0 border-emerald-500/30 text-emerald-400",
  };
  return (
    <div className={`rounded-xl border bg-gradient-to-br p-4 ${map[tone]}`}>
      <div className="text-[10px] font-bold uppercase tracking-wider text-[var(--color-text-secondary)]">
        {label}
      </div>
      <div className="mt-1 text-2xl font-bold">{value}</div>
    </div>
  );
}

// ── 媒体卡 (缩略图 + 删除按钮) ───────────────────────────────────

function MediaCard({
  media,
  onRemove,
  disabled,
}: {
  media: MediaFile;
  onRemove: () => void;
  disabled: boolean;
}) {
  const basename = media.path.split(/[/\\]/).pop() ?? media.path;
  return (
    <div className="group flex flex-col gap-2 rounded-xl border border-[var(--color-border)] bg-[var(--color-bg)] p-2 transition hover:border-[var(--color-gold)]/50">
      <ThumbnailImage source={media.path} kind="video" width={240} />
      <div className="flex items-start justify-between gap-2 px-1 pb-1">
        <div className="min-w-0 flex-1 space-y-0.5">
          <div
            className="truncate font-mono text-[11px] font-medium text-[var(--color-text-primary)]"
            title={media.path}
          >
            {basename}
          </div>
          <div className="text-[10px] text-[var(--color-text-secondary)]">
            {(media.file_size_bytes / (1024 * 1024)).toFixed(1)} MB
          </div>
        </div>
        <button
          type="button"
          onClick={onRemove}
          disabled={disabled}
          title="移除此素材"
          className="rounded-lg border border-red-500/20 bg-red-500/10 p-1 text-xs text-red-400 opacity-70 transition hover:opacity-100 disabled:opacity-30"
        >
          🗑
        </button>
      </div>
    </div>
  );
}

// ── 最近项目卡 ─────────────────────────────────────────────────────

function RecentCard({ path, index }: { path: string; index: number }) {
  const qc = useQueryClient();
  const navigate = useNavigate();
  const locale = useSettingsStore((s) => s.locale);

  const { data: projectRec } = useQuery({
    queryKey: ["assets-project-card", path],
    queryFn: () => projectIpc.load(path),
    staleTime: 5000,
  });

  const fileName = path.split("/").pop() ?? path;
  const dir = path.substring(0, path.length - fileName.length);
  const displayTitle = projectRec?.project?.name || fileName.replace(/\.(scenefab|monoloop)\.json$/, "");
  const firstVideo = projectRec?.project?.media_files?.find(
    (m) => m.path.match(/\.(mp4|mov|avi|mkv|webm)$/i)
  )?.path || projectRec?.project?.media_files?.[0]?.path;

  const setCurrentRecord = useProjectStore((s) => s.setCurrentRecord);

  const handleLoad = async () => {
    try {
      const rec = projectRec ?? (await projectIpc.load(path));
      setCurrentRecord(rec.path, rec.project);
      qc.setQueryData(["assets-current-project"], rec.project);
      qc.setQueryData(["current-project"], rec);
      toast.success(locale === "en-US" ? `Opened project ${rec.project.name}` : `已打开解说工程 ${rec.project.name}`);
      void navigate({ to: "/production" });
    } catch (e) {
      toast.error("加载项目失败", { description: String(e) });
    }
  };

  const handleDelete = async (e: React.MouseEvent) => {
    e.stopPropagation();
    if (!confirm(t("assets.delete_confirm", locale))) return;
    try {
      await projectIpc.remove(path);
      toast.success(locale === "en-US" ? "Project deleted successfully" : "已成功删除解说工程");

      const currentStorePath = useProjectStore.getState().currentPath;
      if (currentStorePath === path) {
        useProjectStore.getState().clear();
        qc.setQueryData(["assets-current-project"], null);
        qc.setQueryData(["current-project"], null);
      }

      void qc.invalidateQueries({ queryKey: ["assets-recent"] });
      void qc.invalidateQueries({ queryKey: ["home-recent-projects"] });
    } catch (err) {
      toast.error("删除项目失败", { description: String(err) });
    }
  };

  return (
    <div
      onClick={handleLoad}
      className="group relative flex cursor-pointer flex-col justify-between gap-3.5 rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)] p-4 text-left transition-all duration-300 hover:border-[var(--color-gold)]/60 hover:bg-[var(--color-surface-elevated)] hover:shadow-lg hover:shadow-amber-500/5"
    >
      <div className="flex w-full items-center justify-between">
        <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-[var(--color-bg)] border border-[var(--color-border)] text-xs font-mono font-bold text-[var(--color-gold)] group-hover:border-[var(--color-gold)]/40 group-hover:bg-[var(--color-gold-muted)]">
          0{index}
        </div>
        <button
          type="button"
          onClick={handleDelete}
          title="删除此项目"
          className="rounded-lg border border-red-500/20 bg-red-500/10 px-2.5 py-1 text-xs text-red-400 opacity-70 transition hover:border-red-500/50 hover:bg-red-500/20 hover:opacity-100"
        >
          🗑 {t("action.delete", locale)}
        </button>
      </div>

      {/* Video 1st Frame Cover Preview */}
      <div className="relative h-32 w-full overflow-hidden rounded-xl bg-zinc-950/80 border border-[var(--color-border)]">
        <div className="absolute inset-0 bg-gradient-to-t from-[var(--color-surface)] via-transparent to-transparent z-10 opacity-70" />
        {firstVideo ? (
          <ThumbnailImage source={firstVideo} kind="video" width={320} />
        ) : (
          <div className="flex h-full w-full items-center justify-center text-3xl opacity-40">
            🎬
          </div>
        )}
      </div>

      <div className="w-full space-y-1">
        <div className="truncate text-sm font-bold text-[var(--color-text-primary)] group-hover:text-[var(--color-gold)] transition">
          {displayTitle}
        </div>
        <div className="truncate font-mono text-[10px] text-[var(--color-text-secondary)] flex items-center justify-between">
          <span>{projectRec?.project?.media_files?.length ?? 0} 个素材</span>
          <span>{dir || path}</span>
        </div>
      </div>
    </div>
  );
}

// ── 空态 ──────────────────────────────────────────────────────────

function EmptyState() {
  const locale = useSettingsStore((s) => s.locale);
  return (
    <div className="flex flex-col items-center gap-3 rounded-2xl border border-dashed border-[var(--color-border)] bg-[var(--color-surface)]/40 px-6 py-10 text-center">
      <div className="overflow-hidden rounded-2xl border border-[var(--color-border)]">
        <img
          src="/empty-state.jpg"
          alt="电影调光室空状态"
          className="h-40 w-72 object-cover"
        />
      </div>
      <div className="text-base font-bold text-[var(--color-text-primary)]">
        {t("assets.no_project", locale)}
      </div>
    </div>
  );
}

// ── 骨架 ──────────────────────────────────────────────────────────

function SkeletonGrid() {
  return (
    <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
      {[1, 2, 3].map((i) => (
        <div
          key={i}
          className="h-32 animate-pulse rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)]"
        />
      ))}
    </div>
  );
}
