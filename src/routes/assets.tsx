/**
 * splicr v1.0.1 · 项目与资产管理中心 (深浅双模电影调色台设计系统重构 + 真实工程与媒体资产统一)
 */

import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import { open } from "@tauri-apps/plugin-dialog";
import { projectIpc } from "@ipc/commands";
import { useAssets } from "@hooks/useAssets";
import { useProjectStore } from "@stores/project-store";
import { useSettingsStore } from "@stores/settings-store";
import { t } from "@lib/i18n";
import { BatchImportDialog } from "@components/dialogs/BatchImportDialog";
import { ThumbnailImage } from "@components/common/ThumbnailImage";
import { toast } from "sonner";
import type { MediaFile, Project, ProjectRecord } from "@ipc/types.gen";

export const Route = createFileRoute("/assets")({
  component: AssetsPage,
});

function AssetsPage() {
  const qc = useQueryClient();
  const navigate = useNavigate();
  const locale = useSettingsStore((s) => s.locale);
  const setCurrentRecord = useProjectStore((s) => s.setCurrentRecord);
  const storeProject = useProjectStore((s) => s.current);

  const { data: recents } = useQuery({
    queryKey: ["assets-recent"],
    queryFn: projectIpc.listRecent,
  });

  // 获取当前活动项目
  const cachedRaw = qc.getQueryData<ProjectRecord | null>(["current-project"]);
  const current: Project | null = useMemo(() => {
    return storeProject ?? cachedRaw?.project ?? null;
  }, [storeProject, cachedRaw]);

  // 如果 store 为空，自动尝试从最近历史项目恢复或初始化
  useEffect(() => {
    if (!current && recents && recents.length > 0 && recents[0]) {
      void projectIpc.load(recents[0]).then((rec) => {
        setCurrentRecord(rec.path, rec.project);
        qc.setQueryData(["current-project"], rec);
        qc.setQueryData(["assets-current-project"], rec.project);
      });
    }
  }, [current, recents, setCurrentRecord, qc]);

  const {
    importFromPaths,
    remove: removeAssets,
    search,
  } = useAssets();

  const [importError, setImportError] = useState<string | null>(null);
  const [showBatchDialog, setShowBatchDialog] = useState(false);
  const [matchingPaths, setMatchingPaths] = useState<string[] | null>(null);
  const [searchQuery, setSearchQuery] = useState("");

  const handleImportMedia = async () => {
    setImportError(null);
    try {
      const selected = await open({
        multiple: true,
        filters: [
          {
            name: "视频素材 (Video)",
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
    setSearchQuery(pattern);
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
    try {
      const rec = await projectIpc.createBlank();
      setCurrentRecord(rec.path, rec.project);
      qc.setQueryData(["assets-current-project"], rec.project);
      qc.setQueryData(["current-project"], rec);
      void qc.invalidateQueries({ queryKey: ["assets-recent"] });
      toast.success(`已创建空白解说工程: ${rec.project.name}`);
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
    <div className="h-full w-full overflow-y-auto bg-[var(--color-bg)] p-6 md:p-8 select-none font-sans">
      <div className="mx-auto max-w-6xl space-y-6">
        {/* 1. Header 顶栏 */}
        <header className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-[var(--color-border)] pb-5">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <span className="h-2 w-2 rounded-full bg-[var(--color-gold)] shadow-[0_0_8px_var(--color-gold)]" />
              <span className="text-[11px] font-mono font-bold tracking-wider text-[var(--color-gold)] uppercase">
                Project & Media Assets Repository
              </span>
            </div>
            <h1 className="text-2xl font-black tracking-tight text-[var(--color-text-primary)]">
              {t("assets.title", locale)}
            </h1>
            <p className="text-xs text-[var(--color-text-secondary)]">
              管理多模态解说工程、高清媒体素材、AI 脚本与渲染导出库
            </p>
          </div>

          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={() => setShowBatchDialog(true)}
              className="flex items-center gap-1.5 rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] px-4 py-2 text-xs font-bold text-[var(--color-text-primary)] hover:border-[var(--color-gold)]/50 hover:text-[var(--color-gold)] transition-all"
            >
              <span>📂</span>
              <span>批量扫描</span>
            </button>
            <button
              type="button"
              onClick={handleCreateBlank}
              className="flex items-center gap-2 rounded-xl bg-gradient-to-r from-[#F5C842] to-[#E8933A] px-5 py-2 text-xs font-black text-zinc-950 shadow-[0_0_16px_rgba(245,200,66,0.25)] transition-all hover:brightness-110 active:scale-95"
            >
              <span>✨</span>
              <span>{t("action.create", locale)}</span>
            </button>
          </div>
        </header>

        {/* 2. 当前活动工程卡片 */}
        <section className="rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)] p-5 sm:p-6 shadow-sm space-y-4">
          <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 border-b border-[var(--color-border)] pb-4">
            <div className="space-y-1">
              <div className="flex items-center gap-2.5">
                <span className="flex h-2.5 w-2.5 rounded-full bg-emerald-400 shadow-[0_0_8px_#34d399]" />
                <h2 className="text-lg font-bold text-[var(--color-text-primary)] tracking-tight">
                  {current?.name ?? "默认解说工程"}
                </h2>
                <span className="rounded-full border border-amber-500/40 bg-amber-500/10 px-2.5 py-0.5 text-[9px] font-mono font-bold text-[var(--color-gold)]">
                  ACTIVE
                </span>
              </div>
              <div className="flex items-center gap-3 text-xs text-[var(--color-text-secondary)] font-mono">
                <span>📹 挂载素材: {current?.media_files?.length ?? 0} 个文件</span>
                <span>•</span>
                <span>📐 9:16 短剧竖屏画幅</span>
              </div>
            </div>

            <div className="flex items-center gap-3 w-full md:w-auto">
              <div className="relative flex-1 md:w-64">
                <input
                  type="text"
                  placeholder="搜索工程内素材名称..."
                  value={searchQuery}
                  onChange={(e) => handleSearch(e.target.value)}
                  className="w-full text-xs pr-8"
                />
                {searchQuery && (
                  <button
                    type="button"
                    onClick={() => handleSearch("")}
                    className="absolute right-2.5 top-1/2 -translate-y-1/2 text-xs text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)]"
                  >
                    ✕
                  </button>
                )}
              </div>

              <button
                type="button"
                onClick={handleImportMedia}
                className="flex items-center gap-1.5 rounded-xl border border-[var(--color-gold)]/40 bg-[var(--color-gold-muted)] px-4 py-2 text-xs font-bold text-[var(--color-gold)] hover:bg-[var(--color-gold)] hover:text-zinc-950 transition-all shrink-0 active:scale-95 shadow-sm"
              >
                <span>➕</span> 添加素材
              </button>
            </div>
          </div>

          {/* 素材缩略图网格 */}
          <div>
            {filteredMedia.length > 0 ? (
              <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4">
                {filteredMedia.map((m) => {
                  const fileName = m.path.split(/[/\\]/).pop() ?? m.path;
                  return (
                    <div
                      key={m.path}
                      className="group relative flex flex-col overflow-hidden rounded-xl border border-[var(--color-border)] bg-[var(--color-surface-elevated)]/60 transition-all duration-200 hover:border-[var(--color-gold)]/60 hover:shadow-md"
                    >
                      <div className="relative aspect-video w-full overflow-hidden bg-zinc-950">
                        <ThumbnailImage
                          source={m.path}
                          className="h-full w-full object-cover transition-transform duration-300 group-hover:scale-105"
                        />
                        <div className="absolute top-2 left-2 rounded-md bg-black/70 px-1.5 py-0.5 text-[9px] font-mono text-[var(--color-gold)] backdrop-blur-md">
                          {m.resolution ?? "1080×1920"}
                        </div>
                        <button
                          type="button"
                          onClick={() => handleRemoveMedia(m.path)}
                          className="absolute top-2 right-2 flex h-6 w-6 items-center justify-center rounded-full bg-black/70 text-zinc-300 hover:bg-rose-500 hover:text-white transition-all opacity-0 group-hover:opacity-100"
                          title="移除此素材"
                        >
                          ✕
                        </button>
                      </div>

                      <div className="p-3 space-y-1">
                        <div className="text-xs font-bold text-[var(--color-text-primary)] truncate" title={fileName}>
                          {fileName}
                        </div>
                        <div className="flex items-center justify-between text-[10px] font-mono text-[var(--color-text-muted)]">
                          <span>{m.duration_seconds ? `${Math.round(m.duration_seconds)}s` : "60s"}</span>
                          <span>{m.codec ?? "H.264"}</span>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : (
              <div
                onClick={handleImportMedia}
                className="flex flex-col items-center justify-center rounded-2xl border border-dashed border-[var(--color-border)] bg-[var(--color-surface-elevated)]/30 p-10 text-center space-y-2 cursor-pointer hover:border-[var(--color-gold)] hover:bg-[var(--color-surface-elevated)]/60 transition-all"
              >
                <span className="text-3xl">📹</span>
                <p className="text-xs font-bold text-[var(--color-text-primary)]">当前工程尚未挂载视频素材</p>
                <p className="text-[10px] text-[var(--color-text-secondary)]">点击选择或拖拽本地 MP4, MOV, MKV, WebM 视频</p>
                <span className="text-xs font-bold text-[var(--color-gold)] pt-1">立即导入本地视频 ➔</span>
              </div>
            )}
          </div>
        </section>

        {/* 3. 历史项目索引库 */}
        <section className="space-y-3.5">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-bold text-[var(--color-text-primary)]">
              历史项目归档 (Recent Projects)
            </h2>
            <span className="text-xs font-mono text-[var(--color-text-muted)]">
              共 {recents?.length ?? 0} 个历史工程
            </span>
          </div>

          {recents && recents.length > 0 ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3.5">
              {recents.map((path) => {
                const name = path.split(/[/\\]/).pop()?.replace(/\\.splicr(\\.json)?$/, "") ?? path;
                return (
                  <div
                    key={path}
                    onClick={() => {
                      void projectIpc.load(path).then((rec) => {
                        setCurrentRecord(rec.path, rec.project);
                        qc.setQueryData(["assets-current-project"], rec.project);
                        qc.setQueryData(["current-project"], rec);
                        void navigate({ to: "/production" });
                      });
                    }}
                    className="group flex flex-col justify-between rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)] p-4 transition-all hover:border-[var(--color-gold)]/60 hover:shadow-md cursor-pointer"
                  >
                    <div className="space-y-2">
                      <div className="flex items-center justify-between text-[10px] font-mono text-[var(--color-text-muted)]">
                        <span className="flex items-center gap-1">📁 <span>splicr 工程</span></span>
                        <span className="text-[var(--color-gold)] font-bold group-hover:translate-x-0.5 transition-transform">进入制作 ➔</span>
                      </div>
                      <h3 className="text-xs font-bold text-[var(--color-text-primary)] group-hover:text-[var(--color-gold)] truncate">
                        {name}
                      </h3>
                      <p className="font-mono text-[9px] text-[var(--color-text-muted)] truncate opacity-75">{path}</p>
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <div className="rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)] p-6 text-center text-xs text-[var(--color-text-muted)]">
              暂无历史归档项目
            </div>
          )}
        </section>

        {importError && (
          <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-3 text-xs text-rose-400">
            {importError}
          </div>
        )}

        <BatchImportDialog open={showBatchDialog} onClose={() => setShowBatchDialog(false)} />
      </div>
    </div>
  );
}
