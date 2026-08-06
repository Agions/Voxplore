/**
 * Vynaro v2.5.0 · 批量导入对话框 (M3 后续完整实装)
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
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-6"
      role="dialog"
      aria-modal="true"
      aria-label="批量导入素材"
      onClick={handleClose}
    >
      <div
        className="flex max-h-[90vh] w-full max-w-5xl flex-col rounded-2xl border border-zinc-800 bg-zinc-950 shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <header className="flex items-center justify-between border-b border-zinc-800 px-5 py-4">
          <div className="space-y-0.5">
            <h2 className="text-base font-semibold text-zinc-100">
              📂 批量导入素材
            </h2>
            <p className="text-xs text-zinc-500">
              选择目录 → 扫描 → 多选 → 一键导入到当前项目
            </p>
          </div>
          <button
            type="button"
            onClick={handleClose}
            aria-label="关闭"
            className="rounded-md px-2 py-1 text-zinc-400 hover:bg-zinc-800 hover:text-zinc-200"
          >
            ✕
          </button>
        </header>

        {/* Toolbar */}
        <div className="flex flex-wrap items-center gap-3 border-b border-zinc-800 bg-zinc-900/30 px-5 py-3">
          <button
            type="button"
            onClick={handlePickDir}
            className="rounded-md border border-zinc-700 bg-zinc-900 px-3 py-1.5 text-xs text-zinc-200 hover:border-zinc-500"
          >
            📁 选择目录
          </button>
          <div className="min-w-0 flex-1 truncate font-mono text-[11px] text-zinc-400">
            {dir ?? "尚未选择目录"}
          </div>
          <label className="flex items-center gap-2 text-xs text-zinc-400">
            <input
              type="checkbox"
              checked={recursive}
              onChange={(e) => setRecursive(e.target.checked)}
              className="h-3.5 w-3.5"
            />
            递归子目录
          </label>
          <button
            type="button"
            onClick={handleScan}
            disabled={!dir || scanning}
            className="rounded-md bg-gradient-to-r from-blue-500 to-violet-500 px-4 py-1.5 text-xs font-semibold text-white shadow shadow-blue-500/30 transition disabled:opacity-40"
          >
            {scanning ? "扫描中..." : "🔍 扫描"}
          </button>
        </div>

        {/* Filters */}
        {scanResult && scanResult.entries.length > 0 && (
          <div className="flex flex-wrap items-center gap-2 border-b border-zinc-800 bg-zinc-900/20 px-5 py-3">
            <select
              value={kindFilter}
              onChange={(e) =>
                setKindFilter(e.target.value as AssetKind | "all")
              }
              className="py-1.5 text-xs font-semibold"
            >
              <option value="all">全部类型</option>
              {ALL_KINDS.map((k) => (
                <option key={k} value={k}>
                  {KIND_LABEL[k]}
                </option>
              ))}
            </select>
            <input
              type="search"
              value={searchPattern}
              onChange={(e) => setSearchPattern(e.target.value)}
              placeholder="🔎 文件名搜索 (substring)"
              className="min-w-[200px] flex-1 rounded-md border border-zinc-700 bg-zinc-900 px-3 py-1 text-xs text-zinc-200 outline-none focus:border-blue-500"
            />
            <button
              type="button"
              onClick={selectAllVisible}
              className="rounded border border-zinc-700 px-2 py-1 text-[11px] text-zinc-300 hover:border-zinc-500"
            >
              当前页全选
            </button>
            <button
              type="button"
              onClick={deselectAllVisible}
              className="rounded border border-zinc-700 px-2 py-1 text-[11px] text-zinc-300 hover:border-zinc-500"
            >
              当前页反选
            </button>
            <div className="font-mono text-[11px] text-zinc-500">
              {selected.size} / {scanResult.total} 已选
              {scanResult.skipped > 0 ? ` · 跳过 ${scanResult.skipped}` : ""}
            </div>
          </div>
        )}

        {/* Body */}
        <div className="flex-1 overflow-y-auto px-5 py-4">
          {scanError && (
            <div className="mb-4 rounded-lg border border-rose-800/60 bg-rose-950/30 px-3 py-2 text-xs text-rose-200">
              扫描失败: {scanError}
            </div>
          )}
          {importError && (
            <div className="mb-4 rounded-lg border border-rose-800/60 bg-rose-950/30 px-3 py-2 text-xs text-rose-200">
              导入失败: {importError}
            </div>
          )}

          {!scanResult ? (
            <div className="flex flex-col items-center justify-center gap-2 py-20 text-center">
              <div className="text-3xl opacity-50">📂</div>
              <div className="text-sm text-zinc-400">选择一个目录开始扫描</div>
              <div className="text-xs text-zinc-500">
                支持视频 / 音频 / 图片 / 字幕 等常见格式
              </div>
            </div>
          ) : filteredEntries.length === 0 ? (
            <div className="flex flex-col items-center justify-center gap-2 py-20 text-center">
              <div className="text-3xl opacity-50">🔍</div>
              <div className="text-sm text-zinc-400">没有匹配的素材</div>
              <div className="text-xs text-zinc-500">
                尝试清空搜索词或切换类型过滤
              </div>
            </div>
          ) : (
            <div className="grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-4">
              {filteredEntries.map((e) => {
                const isSelected = selected.has(e.path);
                return (
                  <button
                    type="button"
                    key={e.path}
                    onClick={() => toggleSelected(e.path)}
                    aria-pressed={isSelected}
                    className={`group flex flex-col gap-2 rounded-xl border p-2 text-left transition ${
                      isSelected
                        ? "border-blue-500 bg-blue-950/30"
                        : "border-zinc-800 bg-zinc-900/40 hover:border-zinc-600"
                    }`}
                  >
                    <ThumbnailImage source={e.path} kind={e.kind} width={240} />
                    <div className="flex items-start justify-between gap-2 px-1">
                      <div className="min-w-0 flex-1 space-y-0.5">
                        <div
                          className="truncate font-mono text-[11px] text-zinc-200"
                          title={e.path}
                        >
                          {basename(e.path)}
                        </div>
                        <div className="flex items-center gap-2 text-[10px] text-zinc-500">
                          <span>{KIND_LABEL[e.kind]}</span>
                          <span>·</span>
                          <span>{formatBytes(e.sizeBytes)}</span>
                          <span>·</span>
                          <span className="truncate">{e.mime}</span>
                        </div>
                      </div>
                      <div
                        className={`mt-0.5 flex h-4 w-4 flex-shrink-0 items-center justify-center rounded border ${
                          isSelected
                            ? "border-blue-400 bg-blue-500 text-white"
                            : "border-zinc-600 bg-zinc-900"
                        }`}
                        aria-hidden="true"
                      >
                        {isSelected ? "✓" : ""}
                      </div>
                    </div>
                  </button>
                );
              })}
            </div>
          )}
        </div>

        {/* Footer */}
        <footer className="flex items-center justify-between border-t border-zinc-800 px-5 py-3">
          <div className="text-[11px] text-zinc-500">
            {scanResult
              ? `共 ${scanResult.total} 项 · 已选 ${selected.size}`
              : "未扫描"}
          </div>
          <div className="flex gap-2">
            <button
              type="button"
              onClick={handleClose}
              className="rounded-md border border-zinc-700 bg-zinc-900 px-4 py-1.5 text-xs text-zinc-200 hover:border-zinc-500"
            >
              取消
            </button>
            <button
              type="button"
              onClick={handleImport}
              disabled={loading || selected.size === 0}
              className="rounded-md bg-gradient-to-r from-blue-500 to-violet-500 px-5 py-1.5 text-xs font-semibold text-white shadow shadow-blue-500/30 transition disabled:opacity-40"
            >
              {loading ? "导入中..." : `📥 导入 ${selected.size} 项`}
            </button>
          </div>
        </footer>
      </div>
    </div>
  );
}
