/**
 * splicr v1.0.0 · 批量导入对话框 (M3 后续完整实装)
 *
 * 流程:
 * 1. "选择目录" → open({ directory: true }) 选一个目录
 * 2. 点击 "🔍 扫描" → useAssets.scan(dir, recursive) 拿 ScanResult
 * 3. 网格预览缩略图 + 多选框
 * 4. 点击 "📥 导入 N 项" → useAssets.importFromScan() → 关闭
 *
 * 注意:
 * - 列表里的"缩略图"用 ThumbnailImage 复用逻辑
 * - 卸载时应该关闭 dialog,避免 useAssets.thumbnail 仍执行
 */

import { useCallback, useMemo, useState } from "react";
import { open as openDialog } from "@tauri-apps/plugin-dialog";
import { toast } from "sonner";
import { useAssets } from "@hooks/useAssets";
import { ThumbnailImage } from "@components/common/ThumbnailImage";
import { basename, formatBytes } from "@lib/assets/probe";
import type { AssetEntry, AssetKind, ScanResult } from "@ipc/types.gen";

export interface BatchImportDialogProps {
  /** 是否打开 */
  open: boolean;
  /** 关闭回调 (导入完成后也会自动调用) */
  onClose: () => void;
  /** 导入成功回调 (参数: 实际导入的数量) */
  onImported?: (count: number) => void;
}

const KIND_LABEL: Record<AssetKind, string> = {
  video: "视频",
  audio: "音频",
  image: "图片",
  subtitle: "字幕",
  other: "其他",
};

const ALL_KINDS: AssetKind[] = ["video", "audio", "image", "subtitle", "other"];

/**
 * 批量导入对话框组件 — 复用:routes/assets.tsx · 后续可在 routes/production.tsx 顶部也接入
 */
export function BatchImportDialog({
  open,
  onClose,
  onImported,
}: BatchImportDialogProps) {
  const { scan, importFromScan, loading } = useAssets();

  const [dir, setDir] = useState<string | null>(null);
  const [recursive, setRecursive] = useState(true);
  const [scanResult, setScanResult] = useState<ScanResult | null>(null);
  const [scanError, setScanError] = useState<string | null>(null);
  const [scanning, setScanning] = useState(false);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [kindFilter, setKindFilter] = useState<AssetKind | "all">("all");
  const [searchPattern, setSearchPattern] = useState("");
  const [importError, setImportError] = useState<string | null>(null);
  const [projectName, setProjectName] = useState("");

  /** 过滤后的 entries (受 类型 + 搜索 双过滤) */
  const filteredEntries = useMemo<AssetEntry[]>(() => {
    if (!scanResult) return [];
    const q = searchPattern.trim().toLowerCase();
    return scanResult.entries.filter((e) => {
      if (kindFilter !== "all" && e.kind !== kindFilter) return false;
      if (q && !e.path.toLowerCase().includes(q)) return false;
      return true;
    });
  }, [scanResult, kindFilter, searchPattern]);

  /** 重置:关闭 dialog 时清状态 */
  const reset = useCallback(() => {
    setDir(null);
    setRecursive(true);
    setScanResult(null);
    setScanError(null);
    setSelected(new Set());
    setKindFilter("all");
    setSearchPattern("");
    setImportError(null);
    setProjectName("");
  }, []);

  const handleClose = useCallback(() => {
    reset();
    onClose();
  }, [reset, onClose]);

  /** 选择目录 */
  const handlePickDir = useCallback(async () => {
    try {
      const picked = await openDialog({ directory: true, multiple: false });
      if (!picked || Array.isArray(picked)) return;
      setDir(picked);
      setScanResult(null);
      setSelected(new Set());
      setScanError(null);
    } catch (e) {
      setScanError(e instanceof Error ? e.message : String(e));
    }
  }, []);

  /** 扫描目录 */
  const handleScan = useCallback(async () => {
    if (!dir) return;
    setScanning(true);
    setScanError(null);
    try {
      const result = await scan(dir, recursive);
      setScanResult(result);
      // 默认全选
      setSelected(new Set(result.entries.map((e) => e.path)));
    } catch (e) {
      setScanError(e instanceof Error ? e.message : String(e));
    } finally {
      setScanning(false);
    }
  }, [dir, recursive, scan]);

  const toggleSelected = useCallback((path: string) => {
    setSelected((cur) => {
      const next = new Set(cur);
      if (next.has(path)) next.delete(path);
      else next.add(path);
      return next;
    });
  }, []);

  const selectAllVisible = useCallback(() => {
    setSelected((cur) => {
      const next = new Set(cur);
      for (const e of filteredEntries) next.add(e.path);
      return next;
    });
  }, [filteredEntries]);

  const deselectAllVisible = useCallback(() => {
    setSelected((cur) => {
      const next = new Set(cur);
      for (const e of filteredEntries) next.delete(e.path);
      return next;
    });
  }, [filteredEntries]);

  /** 批量导入 — 构造一个虚拟 ScanResult (只含被勾选的) */
  const handleImport = useCallback(async () => {
    if (!scanResult) return;
    setImportError(null);
    const chosen = scanResult.entries.filter((e) => selected.has(e.path));
    if (chosen.length === 0) {
      toast.info("未选择任何素材");
      return;
    }
    try {
      const slice: ScanResult = {
        dir: scanResult.dir,
        total: chosen.length,
        entries: chosen,
        skipped: scanResult.skipped,
      };
      const added = await importFromScan(slice);
      toast.success(`已导入 ${added.length} 个素材`);
      onImported?.(added.length);
      handleClose();
    } catch (e) {
      setImportError(e instanceof Error ? e.message : String(e));
      toast.error("批量导入失败");
    }
  }, [scanResult, selected, importFromScan, onImported, handleClose]);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-md p-6 animate-fade-in"
      role="dialog"
      aria-modal="true"
      aria-label="批量导入素材"
      onClick={handleClose}
    >
      <div
        className="flex max-h-[88vh] w-full max-w-5xl flex-col rounded-3xl border border-[var(--color-gold)] bg-[var(--color-surface)] shadow-[0_0_36px_var(--color-gold-glow)] overflow-hidden transition-all duration-300"
        onClick={(e) => e.stopPropagation()}
      >
        {/* 1. Modal Header */}
        <header className="flex items-center justify-between border-b border-[var(--color-border)] bg-[var(--color-surface)] px-6 py-4">
          <div className="flex items-center space-x-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-[#F5C842] to-[#E8933A] text-zinc-950 font-black text-lg shadow-[0_0_12px_rgba(245,200,66,0.3)]">
              V
            </div>
            <div>
              <h2 className="text-base font-extrabold tracking-tight text-[var(--color-text-primary)]">
                BATCH ASSET SELECTOR <span className="text-xs font-normal text-[var(--color-gold)] ml-1 font-mono">· 批量素材选择器</span>
              </h2>
              <p className="text-[11px] text-[var(--color-text-secondary)]">
                极速扫描本地目录，自动提取视频与音频元数据
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-3">
            {/* Search Input */}
            <input
              type="search"
              value={searchPattern}
              onChange={(e) => setSearchPattern(e.target.value)}
              placeholder="🔎 文件名搜索..."
              className="w-56 rounded-xl border border-[var(--color-border)] bg-[var(--color-bg)] px-3 py-1.5 text-xs text-[var(--color-text-primary)] outline-none focus:border-[var(--color-gold)]"
            />

            <button
              type="button"
              onClick={handleClose}
              aria-label="关闭"
              className="flex h-8 w-8 items-center justify-center rounded-xl border border-[var(--color-border)] text-[var(--color-text-secondary)] hover:border-[var(--color-gold)] hover:text-[var(--color-gold)] transition"
            >
              ✕
            </button>
          </div>
        </header>

        {/* 2. Folder Selection Toolbar */}
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-[var(--color-border)] bg-[var(--color-surface-elevated)]/60 px-6 py-3">
          <div className="flex items-center space-x-3 flex-1 min-w-0">
            <button
              type="button"
              onClick={handlePickDir}
              className="flex items-center space-x-1.5 rounded-xl border border-[var(--color-gold)]/40 bg-[var(--color-gold-muted)] px-3.5 py-1.5 text-xs font-bold text-[var(--color-gold)] hover:border-[var(--color-gold)] shadow-sm transition"
            >
              📁 选择目录
            </button>
            <div className="min-w-0 flex-1 truncate font-mono text-xs text-[var(--color-text-secondary)] bg-[var(--color-bg)] px-3 py-1.5 rounded-xl border border-[var(--color-border)]">
              {dir ?? "尚未选择本地文件夹..."}
            </div>
          </div>

          <div className="flex items-center space-x-4">
            <label className="flex items-center gap-2 text-xs text-[var(--color-text-secondary)] cursor-pointer select-none">
              <input
                type="checkbox"
                checked={recursive}
                onChange={(e) => setRecursive(e.target.checked)}
                className="h-4 w-4 rounded accent-[#F5C842]"
              />
              <span>递归扫描子目录</span>
            </label>

            <button
              type="button"
              onClick={handleScan}
              disabled={!dir || scanning}
              className="flex items-center space-x-1 rounded-xl bg-gradient-to-r from-[#F5C842] to-[#E8933A] px-4 py-1.5 text-xs font-bold text-zinc-950 shadow-[0_2px_10px_rgba(245,200,66,0.3)] transition hover:brightness-110 disabled:opacity-40"
            >
              {scanning ? "扫描中..." : "🔍 扫描"}
            </button>
          </div>
        </div>

        {/* 2.5 Project Name Customization Bar */}
        <div className="flex items-center space-x-3 border-b border-[var(--color-border)] bg-[var(--color-surface)] px-6 py-2.5">
          <span className="text-xs font-bold text-[var(--color-gold)] flex items-center gap-1.5 shrink-0">
            <span>🎬</span> 解说工程名称:
          </span>
          <input
            type="text"
            value={projectName}
            onChange={(e) => setProjectName(e.target.value)}
            placeholder="自定义解说工程名称 (例：太阳神纪元 第01集)..."
            className="flex-1 rounded-xl border border-[var(--color-border)] bg-[var(--color-bg)] px-3.5 py-1.5 text-xs text-[var(--color-text-primary)] placeholder-[var(--color-text-muted)] outline-none focus:border-[var(--color-gold)] font-medium"
          />
        </div>

        {/* 3. Category Filter Tabs Bar */}
        {scanResult && scanResult.entries.length > 0 && (
          <div className="flex items-center justify-between border-b border-[var(--color-border)] bg-[var(--color-surface)] px-6 py-2.5">
            <div className="flex items-center space-x-2 overflow-x-auto">
              <select
                value={kindFilter}
                onChange={(e) =>
                  setKindFilter(e.target.value as AssetKind | "all")
                }
                className="rounded-lg border border-[var(--color-border)] bg-[var(--color-bg)] px-2 py-1 text-xs font-bold text-[var(--color-text-primary)] outline-none focus:border-[var(--color-gold)]"
              >
                <option value="all">全部类型</option>
                {ALL_KINDS.map((k) => (
                  <option key={k} value={k}>
                    {KIND_LABEL[k]}
                  </option>
                ))}
              </select>
              <button
                type="button"
                onClick={() => setKindFilter("all")}
                className={`rounded-lg px-3 py-1 text-xs font-bold transition ${
                  kindFilter === "all"
                    ? "bg-[var(--color-gold-muted)] border border-[var(--color-gold)]/40 text-[var(--color-gold)]"
                    : "text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]"
                }`}
              >
                ALL 全部 ({scanResult.entries.length})
              </button>
              {ALL_KINDS.map((k) => {
                const count = scanResult.entries.filter((e) => e.kind === k).length;
                if (count === 0) return null;
                return (
                  <button
                    key={k}
                    type="button"
                    onClick={() => setKindFilter(k)}
                    className={`rounded-lg px-3 py-1 text-xs font-bold transition ${
                      kindFilter === k
                        ? "bg-[var(--color-gold-muted)] border border-[var(--color-gold)]/40 text-[var(--color-gold)]"
                        : "text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]"
                    }`}
                  >
                    {KIND_LABEL[k].toUpperCase()} ({count})
                  </button>
                );
              })}
            </div>

            <div className="flex items-center space-x-2">
              <button
                type="button"
                onClick={selectAllVisible}
                className="text-[11px] text-[var(--color-text-secondary)] hover:text-[var(--color-gold)] font-medium"
              >
                当前页全选
              </button>
              <span className="text-[var(--color-border)]">|</span>
              <button
                type="button"
                onClick={deselectAllVisible}
                className="text-[11px] text-[var(--color-text-secondary)] hover:text-[var(--color-gold)] font-medium"
              >
                当前页反选
              </button>
              <span className="text-xs font-bold text-[var(--color-gold)] bg-[var(--color-gold-muted)] px-2.5 py-0.5 rounded-full border border-[var(--color-gold)]/30 ml-2">
                {selected.size} / {scanResult.total} 已选
                {scanResult.skipped > 0 ? ` · 跳过 ${scanResult.skipped}` : ""}
              </span>
            </div>
          </div>
        )}

        {/* 4. Asset Cards Main Grid */}
        <div className="flex-1 overflow-y-auto px-6 py-5 min-h-[280px]">
          {scanError && (
            <div className="mb-4 rounded-xl border border-rose-500/40 bg-rose-500/10 p-3 text-xs text-rose-400">
              扫描失败: {scanError}
            </div>
          )}
          {importError && (
            <div className="mb-4 rounded-xl border border-rose-500/40 bg-rose-500/10 p-3 text-xs text-rose-400">
              导入失败: {importError}
            </div>
          )}

          {!scanResult ? (
            <div className="flex flex-col items-center justify-center py-16 text-center space-y-3">
              <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-[var(--color-gold-muted)] border border-[var(--color-gold)]/30 text-[var(--color-gold)] text-3xl">
                📂
              </div>
              <div className="space-y-1">
                <h3 className="text-sm font-bold text-[var(--color-text-primary)]">选择一个目录开始扫描</h3>
                <p className="text-xs text-[var(--color-text-secondary)]">
                  点击上方「选择扫描目录」以获取本地视频、音频与字幕素材
                </p>
              </div>
            </div>
          ) : filteredEntries.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16 text-center space-y-2">
              <div className="text-3xl opacity-50">🔍</div>
              <div className="text-sm font-bold text-[var(--color-text-primary)]">未匹配到素材文件</div>
              <div className="text-xs text-[var(--color-text-secondary)]">
                请调整搜索关键词或切换类型过滤
              </div>
            </div>
          ) : (
            <div className="grid grid-cols-2 gap-4 md:grid-cols-3 lg:grid-cols-4">
              {filteredEntries.map((e) => {
                const isSelected = selected.has(e.path);
                return (
                  <button
                    type="button"
                    key={e.path}
                    onClick={() => toggleSelected(e.path)}
                    aria-pressed={isSelected}
                    className={`group relative flex flex-col justify-between cursor-pointer rounded-2xl border p-3 text-left transition-all duration-300 ${
                      isSelected
                        ? "border-[var(--color-gold)] bg-[var(--color-gold-muted)] shadow-[0_0_16px_var(--color-gold-glow)] scale-[1.02]"
                        : "border-[var(--color-border)] bg-[var(--color-bg)] hover:border-[var(--color-gold)]/40 hover:bg-[var(--color-surface-elevated)]"
                    }`}
                  >
                    {/* Checkmark Badge */}
                    <div className="absolute top-4 right-4 z-20">
                      <div
                        className={`flex h-5 w-5 items-center justify-center rounded-full text-xs font-black transition ${
                          isSelected
                            ? "bg-[var(--color-gold)] text-zinc-950 shadow-md"
                            : "border border-[var(--color-border)] bg-[var(--color-surface)] text-transparent"
                        }`}
                      >
                        ✓
                      </div>
                    </div>

                    {/* Thumbnail */}
                    <div className="relative mb-2.5 h-28 w-full overflow-hidden rounded-xl bg-zinc-950 border border-[var(--color-border)]">
                      <ThumbnailImage source={e.path} kind={e.kind} width={240} />
                      <span className="absolute bottom-1.5 left-1.5 rounded-md bg-zinc-950/80 px-2 py-0.5 text-[9px] font-mono font-bold text-[var(--color-gold)] border border-[var(--color-gold)]/30">
                        {KIND_LABEL[e.kind].toUpperCase()}
                      </span>
                    </div>

                    {/* File Details */}
                    <div className="space-y-1">
                      <div
                        className="truncate text-xs font-semibold text-[var(--color-text-primary)] group-hover:text-[var(--color-gold)] transition-colors"
                        title={e.path}
                      >
                        {basename(e.path)}
                      </div>
                      <div className="flex items-center justify-between text-[10px] font-mono text-[var(--color-text-muted)]">
                        <span>{formatBytes(e.sizeBytes)}</span>
                        <span className="uppercase">{e.mime?.split("/")[1] || e.kind}</span>
                      </div>
                    </div>
                  </button>
                );
              })}
            </div>
          )}
        </div>

        {/* 5. Modal Footer / Action Bar */}
        <footer className="flex items-center justify-between border-t border-[var(--color-border)] bg-[var(--color-surface)] px-6 py-4">
          {/* Dashed Dropzone */}
          <div
            onClick={handlePickDir}
            className="flex items-center space-x-2 rounded-xl border border-dashed border-[var(--color-gold)]/40 bg-[var(--color-gold-muted)]/50 px-4 py-2 text-xs font-medium text-[var(--color-gold)] cursor-pointer hover:border-[var(--color-gold)] transition"
          >
            <span>📥</span>
            <span>拖拽文件至此处 或 浏览选择...</span>
          </div>

          <div className="flex items-center space-x-3">
            <button
              type="button"
              onClick={handleClose}
              className="rounded-xl border border-[var(--color-border)] bg-[var(--color-surface-elevated)] px-4 py-2 text-xs font-bold text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] transition"
            >
              取消
            </button>
            <button
              type="button"
              onClick={handleImport}
              disabled={loading || selected.size === 0}
              className="flex items-center space-x-1.5 rounded-xl bg-gradient-to-r from-[#F5C842] to-[#E8933A] px-6 py-2 text-xs font-black text-zinc-950 shadow-[0_0_16px_rgba(245,200,66,0.3)] transition hover:brightness-110 disabled:opacity-40"
            >
              {loading ? "导入中..." : `📥 导入 ${selected.size} 项`}
            </button>
          </div>
        </footer>
      </div>
    </div>
  );
}
