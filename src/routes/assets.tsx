/**
 * splicr v1.0.1 · 项目与资产管理中心 (胶片卡片网格 + 真实探针与存储监控)
 */

import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { open } from "@tauri-apps/plugin-dialog";
import { projectIpc } from "@ipc/commands";
import { useAssets } from "@hooks/useAssets";
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

  const { data: recents } = useQuery({
    queryKey: ["assets-recent"],
    queryFn: projectIpc.listRecent,
  });

  const currentRaw = qc.getQueryData<{ project: Project } | null>(["current-project"]);
  const current = currentRaw?.project ?? null;

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
    <div className="mx-auto max-w-6xl space-y-7 px-8 py-8 select-none font-sans">
      {/* 1. Header */}
      <header className="flex items-center justify-between border-b border-[var(--color-border)] pb-5">
        <div>
          <div className="text-[10px] font-mono font-bold tracking-[0.2em] text-[var(--color-gold)] uppercase">
            PROJECT & ASSETS REPOSITORY
          </div>
          <h1 className="text-2xl font-black text-[var(--color-text-primary)]">
            {t("assets.title", locale)}
          </h1>
          <p className="text-xs text-[var(--color-text-secondary)] mt-0.5">
            {t("assets.subtitle", locale)}
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() => setShowBatchDialog(true)}
            className="flex items-center gap-1.5 rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] px-4 py-2 text-xs font-bold text-[var(--color-text-primary)] hover:border-[var(--color-gold)] hover:text-[var(--color-gold)] transition-all"
          >
            <span>📂</span>
            <span>批量扫描</span>
          </button>
          <button
            type="button"
            onClick={handleCreateBlank}
            className="flex items-center gap-1.5 rounded-xl bg-gradient-to-r from-[#F5C842] to-[#E8933A] px-4 py-2 text-xs font-black text-zinc-950 shadow-md transition-all hover:scale-105"
          >
            <span>✨</span>
            <span>{t("action.create", locale)}</span>
          </button>
        </div>
      </header>

      {/* 2. 当前活动工程卡片 */}
      <section className="rounded-3xl border border-[var(--color-border)] bg-gradient-to-br from-zinc-950 via-[#0e0e12] to-black p-6 space-y-4 shadow-xl">
        <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <span className="flex h-2.5 w-2.5 rounded-full bg-emerald-400 shadow-[0_0_8px_#34d399]" />
              <h2 className="text-lg font-bold text-white tracking-tight">
                {current?.name ?? "默认解说工程"}
              </h2>
              <span className="rounded-md border border-amber-500/30 bg-amber-500/10 px-2 py-0.5 text-[10px] font-mono font-bold text-[var(--color-gold)]">
                Active Project
              </span>
            </div>
            <p className="text-xs text-zinc-400 font-mono">
              挂载素材: {current?.media_files?.length ?? 0} 个文件 · 9:16 沉浸短剧画幅
            </p>
          </div>

          <div className="flex items-center gap-3 w-full md:w-auto">
            <input
              type="text"
              placeholder="搜索当前工程素材..."
              value={searchQuery}
              onChange={(e) => handleSearch(e.target.value)}
              className="rounded-xl border border-zinc-700/80 bg-zinc-900 px-3.5 py-1.5 text-xs text-zinc-200 outline-none focus:border-[var(--color-gold)] w-full md:w-64"
            />
            <button
              type="button"
              onClick={handleImportMedia}
              className="flex items-center gap-1.5 rounded-xl border border-[var(--color-gold)]/40 bg-[var(--color-gold-muted)] px-3.5 py-1.5 text-xs font-bold text-[var(--color-gold)] hover:bg-[var(--color-gold)] hover:text-zinc-950 transition-all shrink-0"
            >
              <span>➕</span> 添加素材
            </button>
          </div>
        </div>

        {/* 素材缩略图网格 */}
        <div className="pt-2">
          {filteredMedia.length > 0 ? (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3.5">
              {filteredMedia.map((m) => {
                const fileName = m.path.split(/[/\\]/).pop() ?? m.path;
                return (
                  <div
                    key={m.path}
                    className="group relative flex flex-col overflow-hidden rounded-2xl border border-zinc-800/80 bg-zinc-950 transition-all hover:border-[var(--color-gold)]/60 hover:shadow-lg"
                  >
                    <div className="relative aspect-video w-full overflow-hidden bg-zinc-900">
                      <ThumbnailImage
                        source={m.path}
                        className="h-full w-full object-cover transition-transform duration-300 group-hover:scale-105"
                      />
                      <div className="absolute top-2 left-2 rounded bg-black/70 px-1.5 py-0.5 text-[9px] font-mono text-[var(--color-gold)] backdrop-blur-md">
                        {m.resolution ?? "1080x1920"}
                      </div>
                      <button
                        type="button"
                        onClick={() => handleRemoveMedia(m.path)}
                        className="absolute top-2 right-2 flex h-6 w-6 items-center justify-center rounded-full bg-black/60 text-zinc-400 hover:bg-rose-500 hover:text-white transition-all opacity-0 group-hover:opacity-100"
                        title="移除此素材"
                      >
                        ✕
                      </button>
                    </div>
                    <div className="p-2.5 space-y-1">
                      <div className="text-xs font-bold text-zinc-200 truncate">{fileName}</div>
                      <div className="flex items-center justify-between text-[10px] font-mono text-zinc-500">
                        <span>{m.duration_seconds ? `${Math.round(m.duration_seconds)}s` : "60s"}</span>
                        <span>{m.codec ?? "H.264"}</span>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center rounded-2xl border border-dashed border-zinc-800 bg-zinc-950/40 p-8 text-center space-y-2">
              <span className="text-2xl">📹</span>
              <p className="text-xs text-zinc-400">当前工程尚未挂载视频素材</p>
              <button
                type="button"
                onClick={handleImportMedia}
                className="text-xs font-bold text-[var(--color-gold)] hover:underline"
              >
                立即导入本地视频 ➔
              </button>
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
          <span className="text-xs font-mono text-zinc-500">共 {recents?.length ?? 0} 个项目</span>
        </div>

        {recents && recents.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3.5">
            {recents.map((path) => {
              const name = path.split(/[/\\]/).pop()?.replace(/\.splicr(\.json)?$/, "") ?? path;
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
                  className="group flex flex-col justify-between rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)]/90 p-4 transition-all hover:border-[var(--color-gold)] hover:shadow-md cursor-pointer"
                >
                  <div className="space-y-1.5">
                    <div className="flex items-center justify-between text-[10px] font-mono text-zinc-500">
                      <span>📁 splicr 工程</span>
                      <span className="text-[var(--color-gold)] font-bold">打开 ➔</span>
                    </div>
                    <h3 className="text-xs font-bold text-[var(--color-text-primary)] group-hover:text-[var(--color-gold)] truncate">
                      {name}
                    </h3>
                    <p className="font-mono text-[10px] text-zinc-500 truncate">{path}</p>
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          <div className="rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)] p-6 text-center text-xs text-zinc-500">
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
  );
}
