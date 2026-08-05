/**
 * SceneFab v2.5.0 · 项目管理页 (M3 后续: 完整接入 assets 5 个 actions)
 *
 * 顶部:项目统计 + 当前项目信息卡
 * 中段:最近项目网格 (使用 projectIpc.listRecent)
 * 下段:当前项目的素材列表 (缩略图网格 + 搜索 + 批量导入)
 *      - 🎞 单文件导入 (tauri-plugin-dialog + useAssets.importFromPaths)
 *      - 📂 批量目录扫描导入 (BatchImportDialog + useAssets.scan + importFromScan)
 *      - 顶部搜索框 (substring 过滤当前 media_files)
 *      - 缩略图 (ThumbnailImage + useAssets.thumbnail)
 */

import { createFileRoute } from "@tanstack/react-router";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { open } from "@tauri-apps/plugin-dialog";
import { projectIpc } from "@ipc/commands";
import { useAssets } from "@hooks/useAssets";
import { useProject } from "@hooks/useProject";
import { BatchImportDialog } from "@components/dialogs/BatchImportDialog";
import { ThumbnailImage } from "@components/common/ThumbnailImage";
import type { MediaFile, Project } from "@ipc/types.gen";

export const Route = createFileRoute("/assets")({
  component: AssetsPage,
});

function AssetsPage() {
  const qc = useQueryClient();
  const { data: recents, isLoading } = useQuery({
    queryKey: ["assets-recent"],
    queryFn: projectIpc.listRecent,
  });
  const { data: currentRaw } = useQuery<Project | null>({
    queryKey: ["assets-current-project"],
    queryFn: async () => null,
    enabled: false,
  });
  const current = currentRaw;

  // M4 真实接通:素材导入/删除由 useAssets 接管
  const {
    importFromPaths,
    remove: removeAssets,
    search,
    loading: assetsLoading,
  } = useAssets();
  // useProject 让 hook 自动跟随 current / currentPath 变化
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
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      setImportError(msg);
    }
  };

  const handleRemoveMedia = async (id: string) => {
    setImportError(null);
    try {
      await removeAssets([id]);
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      setImportError(msg);
    }
  };

  /**
   * 搜索:实时 substring 过滤
   * - searchPattern 为空时不过滤,显示全部
   * - 非空时通过后端 search 命令过滤
   */
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

  const handleCreateBlank = async () => {
    const rec = await projectIpc.createBlank();
    qc.setQueryData(["assets-current-project"], rec.project);
    void qc.invalidateQueries({ queryKey: ["assets-recent"] });
  };

  /** 视图层过滤后的 media_files (None 表示不过滤) */
  const filteredMedia = useMemo<MediaFile[]>(() => {
    if (!matchingPaths) return current?.media_files ?? [];
    const set = new Set(matchingPaths);
    return (current?.media_files ?? []).filter((m) => set.has(m.path));
  }, [current?.media_files, matchingPaths]);

  return (
    <div className="mx-auto max-w-6xl space-y-10 px-8 py-10">
      <header className="flex items-start justify-between">
        <div className="space-y-1">
          <div className="text-[10px] font-semibold uppercase tracking-[0.2em] text-violet-400">
            Project Management
          </div>
          <h1 className="text-3xl font-bold tracking-tight">项目管理</h1>
          <p className="text-sm text-zinc-500">管理项目、媒体、脚本与导出</p>
        </div>
        <button
          type="button"
          onClick={handleCreateBlank}
          className="rounded-xl bg-gradient-to-r from-blue-500 to-violet-500 px-5 py-2.5 text-sm font-semibold text-white shadow-lg shadow-blue-500/30 transition hover:shadow-blue-500/50"
        >
          新建空白项目
        </button>
      </header>

      {/* 当前项目 */}
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
      />

      {/* 最近项目 */}
      <section>
        <SectionHeader
          kicker="历史"
          title="最近的项目"
          subtitle="最多保留 20 条"
        />
        {isLoading ? (
          <SkeletonGrid />
        ) : recents && recents.length > 0 ? (
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2 lg:grid-cols-3">
            {recents.map((p, idx) => (
              <RecentCard key={p} path={p} index={idx + 1} />
            ))}
          </div>
        ) : (
          <EmptyState onCreate={handleCreateBlank} />
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
  searching,
  importing,
  importError,
  hasProject,
}: {
  project: Project | null;
  onImportMedia: () => Promise<void> | void;
  onRemoveMedia: (id: string) => Promise<void> | void;
  onOpenBatchDialog: () => void;
  onSearch: (pattern: string) => void;
  filteredMedia: MediaFile[];
  searching: boolean;
  importing: boolean;
  importError: string | null;
  hasProject: boolean;
}) {
  if (!project) {
    return (
      <section className="flex items-center justify-between rounded-2xl border border-dashed border-zinc-800 bg-zinc-900/30 px-6 py-5">
        <div className="space-y-0.5">
          <div className="text-sm font-medium text-zinc-300">
            尚未打开任何项目
          </div>
          <div className="text-xs text-zinc-500">
            选择现有项目或新建空白项目开始
          </div>
        </div>
      </section>
    );
  }

  return (
    <section className="rounded-2xl border border-zinc-800 bg-zinc-900/40 p-6">
      <div className="mb-5 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-gradient-to-br from-blue-500 to-violet-500 text-sm font-bold text-white">
            P
          </div>
          <div className="space-y-0.5">
            <div className="text-base font-semibold text-zinc-100">
              {project.name}
            </div>
            <div className="font-mono text-[10px] text-zinc-500">
              id: {project.id.slice(0, 8)}
            </div>
          </div>
        </div>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={onOpenBatchDialog}
            disabled={!hasProject}
            title={!hasProject ? "请先打开或新建项目" : undefined}
            className="rounded-lg border border-blue-700/50 bg-blue-950/30 px-4 py-2 text-xs text-blue-200 transition hover:border-blue-500 hover:bg-blue-950/60 disabled:opacity-50"
          >
            📂 批量扫描导入
          </button>
          <button
            type="button"
            onClick={onImportMedia}
            disabled={importing || !hasProject}
            title={!hasProject ? "请先打开或新建项目" : undefined}
            className="rounded-lg border border-zinc-700 bg-zinc-900 px-4 py-2 text-xs text-zinc-200 transition hover:border-zinc-500 disabled:opacity-50"
          >
            🎞 导入媒体
          </button>
        </div>
      </div>

      {importError && (
        <div className="mb-4 rounded-lg border border-rose-800/60 bg-rose-950/30 px-3 py-2 text-xs text-rose-200">
          导入失败: {importError}
        </div>
      )}

      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <Stat label="媒体素材" value={project.media_files.length} tone="blue" />
        <Stat label="脚本段" value={project.scripts.length} tone="violet" />
        <Stat
          label="轨道"
          value={project.timeline?.tracks?.length ?? 0}
          tone="cyan"
        />
        <Stat
          label="导出记录"
          value={project.exports?.length ?? 0}
          tone="emerald"
        />
      </div>

      {/* 媒体清单:搜索 + 缩略图网格 */}
      {project.media_files.length > 0 && (
        <div className="mt-6 space-y-3">
          <div className="flex items-center justify-between gap-3">
            <div className="text-[10px] uppercase tracking-wider text-zinc-500">
              媒体清单 ({filteredMedia.length}/{project.media_files.length})
            </div>
            <div className="relative min-w-[260px] flex-1 max-w-md">
              <input
                type="search"
                value={searching ? "🔎 搜索中..." : ""}
                readOnly
                placeholder=""
                className="absolute inset-0 cursor-text rounded-md border border-transparent bg-transparent text-xs text-zinc-200 outline-none"
                tabIndex={-1}
              />
              <input
                type="search"
                onChange={(e) => onSearch(e.target.value)}
                placeholder="🔎 搜索文件路径 (substring)"
                className="w-full rounded-md border border-zinc-700 bg-zinc-950/40 px-3 py-1.5 text-xs text-zinc-200 outline-none focus:border-blue-500"
              />
            </div>
          </div>

          {filteredMedia.length === 0 ? (
            <div className="rounded-lg border border-dashed border-zinc-800 bg-zinc-950/40 px-4 py-6 text-center text-xs text-zinc-500">
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

// ── 媒体卡 (缩略图 + 元数据 + 删除按钮) ───────────────────────────

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
    <div className="flex flex-col gap-2 rounded-xl border border-zinc-800 bg-zinc-900/40 p-2 transition hover:border-zinc-600">
      <ThumbnailImage source={media.path} kind="video" width={240} />
      <div className="flex items-start justify-between gap-2 px-1 pb-1">
        <div className="min-w-0 flex-1 space-y-0.5">
          <div
            className="truncate font-mono text-[11px] text-zinc-200"
            title={media.path}
          >
            {basename}
          </div>
          <div className="flex flex-wrap items-center gap-1.5 text-[10px] text-zinc-500">
            <span>{Math.round(media.duration_seconds)}s</span>
            {media.resolution && (
              <>
                <span>·</span>
                <span>{media.resolution}</span>
              </>
            )}
            {media.codec && (
              <>
                <span>·</span>
                <span className="uppercase">{media.codec}</span>
              </>
            )}
          </div>
        </div>
        <button
          type="button"
          onClick={onRemove}
          disabled={disabled}
          title="从项目移除"
          aria-label={`删除 ${basename}`}
          className="rounded px-1.5 py-0.5 text-rose-400 transition hover:bg-rose-950/40 hover:text-rose-200 disabled:opacity-40"
        >
          ✕
        </button>
      </div>
    </div>
  );
}

function Stat({
  label,
  value,
  tone,
}: {
  label: string;
  value: number;
  tone: "blue" | "violet" | "cyan" | "emerald";
}) {
  const map: Record<string, string> = {
    blue: "from-blue-500/15 to-blue-500/0 border-blue-500/30",
    violet: "from-violet-500/15 to-violet-500/0 border-violet-500/30",
    cyan: "from-cyan-500/15 to-cyan-500/0 border-cyan-500/30",
    emerald: "from-emerald-500/15 to-emerald-500/0 border-emerald-500/30",
  };
  return (
    <div className={`rounded-xl border bg-gradient-to-br p-4 ${map[tone]}`}>
      <div className="text-[10px] uppercase tracking-wider text-zinc-500">
        {label}
      </div>
      <div className="mt-1 text-2xl font-bold text-zinc-100">{value}</div>
    </div>
  );
}

// ── 最近项目卡 ─────────────────────────────────────────────────────

function RecentCard({ path, index }: { path: string; index: number }) {
  const fileName = path.split("/").pop() ?? path;
  const dir = path.substring(0, path.length - fileName.length);
  return (
    <button
      type="button"
      className="group flex flex-col items-start gap-3 rounded-2xl border border-zinc-800 bg-zinc-900/40 p-5 text-left transition hover:border-blue-500/50 hover:bg-zinc-900"
    >
      <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br from-zinc-700 to-zinc-900 text-base font-bold text-zinc-300 group-hover:from-blue-500 group-hover:to-violet-500 group-hover:text-white">
        {index}
      </div>
      <div className="w-full space-y-0.5">
        <div className="truncate text-sm font-medium text-zinc-100">
          {fileName.replace(/\.scenefab\.json$/, "")}
        </div>
        <div className="truncate font-mono text-[10px] text-zinc-500">
          {dir}
        </div>
      </div>
    </button>
  );
}

// ── 空态 ──────────────────────────────────────────────────────────

function EmptyState({ onCreate }: { onCreate: () => void }) {
  return (
    <div className="flex flex-col items-center gap-4 rounded-2xl border border-dashed border-zinc-800 bg-zinc-900/30 px-6 py-12 text-center">
      <div className="text-3xl">📁</div>
      <div className="text-sm font-medium text-zinc-200">还没有项目</div>
      <div className="text-xs text-zinc-500">点击下方按钮创建一个空白项目</div>
      <button
        type="button"
        onClick={onCreate}
        className="mt-2 rounded-lg bg-gradient-to-r from-blue-500 to-violet-500 px-5 py-2 text-xs font-semibold text-white shadow shadow-blue-500/30"
      >
        立即创建
      </button>
    </div>
  );
}

// ── 骨架 ──────────────────────────────────────────────────────────

function SkeletonGrid() {
  return (
    <div className="grid grid-cols-1 gap-3 md:grid-cols-2 lg:grid-cols-3">
      {[1, 2, 3].map((i) => (
        <div
          key={i}
          className="h-32 animate-pulse rounded-2xl border border-zinc-800 bg-zinc-900/40"
        />
      ))}
    </div>
  );
}

// ── Section header ────────────────────────────────────────────────

function SectionHeader({
  kicker,
  title,
  subtitle,
}: {
  kicker: string;
  title: string;
  subtitle: string;
}) {
  return (
    <div className="mb-4 space-y-1">
      <div className="text-[10px] font-semibold uppercase tracking-[0.2em] text-violet-400">
        {kicker}
      </div>
      <h2 className="text-xl font-semibold tracking-tight text-zinc-100">
        {title}
      </h2>
      <p className="text-sm text-zinc-500">{subtitle}</p>
    </div>
  );
}
