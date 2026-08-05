/**
 * Vynaro v2.5.0 · 应用更新对话框 (M4 · 完整实装)
 *
 * 设计:
 * - 调用 useUpdate hook (state + check / download / install / reset)
 * - 5 阶段状态机驱动的展示: idle / checking / available / downloading / ready
 * - 错误内联展示,不弹 toast (对话框本身是 modal)
 *
 * 用法:
 *   <UpdateDialog open={showUpdate} onClose={() => setShowUpdate(false)} />
 *
 * M4 范围:
 * - 不实装二进制替换 (需重启)
 * - "安装"动作 = 打开下载目录 + 提示用户手动替换
 */

import { useEffect } from "react";
import { useUpdate } from "@hooks/useUpdate";
import { formatBytes } from "@lib/format/bytes";
import type {
  UpdateInfo,
  UpdatePhase,
  UpdateProgress,
  UpdateState,
} from "@ipc/types.gen";

export interface UpdateDialogProps {
  /** 是否显示 */
  open: boolean;
  /** 关闭回调 (卸载前清状态) */
  onClose: () => void;
  /** 当前版本号 (注入 useUpdate) */
  currentVersion?: string;
}

const PHASE_TITLE: Record<UpdatePhase, string> = {
  idle: "检查更新",
  checking: "正在检查...",
  available: "发现新版本",
  downloading: "下载中...",
  ready: "下载完成",
};

const PHASE_ICON: Record<UpdatePhase, string> = {
  idle: "↻",
  checking: "⏳",
  available: "⬇",
  downloading: "⏳",
  ready: "✓",
};

const PHASE_TONE: Record<UpdatePhase, string> = {
  idle: "from-zinc-700 to-zinc-600",
  checking: "from-zinc-600 to-zinc-500",
  available: "from-blue-500 to-violet-500",
  downloading: "from-blue-500 to-cyan-500",
  ready: "from-emerald-500 to-teal-500",
};

/**
 * 应用更新对话框 — 单一入口承载 5 阶段状态机
 */
export function UpdateDialog({
  open,
  onClose,
  currentVersion,
}: UpdateDialogProps) {
  const update = useUpdate({ currentVersion });

  // ESC 关闭
  useEffect(() => {
    if (!open) return undefined;
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;

  const phase = update.state.phase;
  const available = update.state.available;
  const progress = update.state.progress;
  const error = update.state.error;
  const downloadedPath = update.state.downloadedPath;
  const busy = update.busy;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-6 backdrop-blur-sm"
      role="dialog"
      aria-modal="true"
      aria-label="应用更新"
      onClick={onClose}
    >
      <div
        className="flex w-full max-w-lg flex-col overflow-hidden rounded-2xl border border-zinc-800 bg-zinc-950 shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <Header
          phase={phase}
          currentVersion={currentVersion}
          onClose={onClose}
        />

        <div className="space-y-4 p-6">
          <PhaseBlock phase={phase} available={available} />

          {/* 进度条 (downloading 时) */}
          {phase === "downloading" && progress && (
            <ProgressBar progress={progress} />
          )}

          {/* release notes (available/ready 时) */}
          {(phase === "available" || phase === "ready") && available?.notes && (
            <NotesBlock notes={available.notes} />
          )}

          {/* 错误信息 */}
          {error && <ErrorBlock message={error} />}

          {/* 调试信息:已下载路径 (ready 时) */}
          {phase === "ready" && downloadedPath && (
            <div className="rounded-md border border-emerald-500/20 bg-emerald-500/5 px-3 py-2 text-[11px] text-emerald-300">
              ✓ 安装包已下载到:{" "}
              <span className="font-mono">{downloadedPath}</span>
            </div>
          )}
        </div>

        <Footer
          phase={phase}
          busy={busy}
          onCheck={() => void update.check()}
          onDownload={() => void update.download()}
          onInstall={() => void update.install()}
          onReset={() => void update.reset()}
          onClose={onClose}
        />
      </div>
    </div>
  );
}

// ── sub-components ──────────────────────────────────────────────────

function Header({
  phase,
  currentVersion,
  onClose,
}: {
  phase: UpdatePhase;
  currentVersion?: string;
  onClose: () => void;
}) {
  return (
    <header className="flex items-center justify-between border-b border-zinc-800/60 px-6 py-4">
      <div className="space-y-0.5">
        <h2 className="text-base font-semibold text-zinc-100">
          {PHASE_TITLE[phase]}
        </h2>
        <p className="text-[11px] text-zinc-500">
          Vynaro 应用更新器 · 当前版本 v{currentVersion ?? "—"}
        </p>
      </div>
      <button
        type="button"
        onClick={onClose}
        aria-label="关闭"
        className="rounded-md p-1 text-zinc-500 transition hover:bg-zinc-900 hover:text-zinc-100"
      >
        ✕
      </button>
    </header>
  );
}

function PhaseBlock({
  phase,
  available,
}: {
  phase: UpdatePhase;
  available: UpdateInfo | null;
}) {
  if (phase === "idle") {
    return (
      <div className="flex items-start gap-3 rounded-xl border border-zinc-800 bg-zinc-900/50 p-4">
        <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-zinc-700 to-zinc-600 text-lg">
          ↻
        </div>
        <div className="space-y-1">
          <div className="text-sm font-medium text-zinc-200">
            点击「检查更新」开始
          </div>
          <div className="text-[11px] leading-relaxed text-zinc-500">
            从 GitHub Releases 拉取最新版本号与下载链接,本地比对后给出提示
          </div>
        </div>
      </div>
    );
  }

  if (phase === "available" && available) {
    return (
      <div className="flex items-start gap-3 rounded-xl border border-blue-500/30 bg-blue-500/5 p-4">
        <div
          className={`flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-xl bg-gradient-to-br text-lg ${PHASE_TONE.available}`}
        >
          ⬇
        </div>
        <div className="space-y-1">
          <div className="text-sm font-medium text-zinc-100">
            v{available.version} 已发布
          </div>
          <div className="text-[11px] leading-relaxed text-zinc-400">
            大小 {formatBytes(available.fileSizeBytes)}
            {available.releaseDate && ` · 发布于 ${available.releaseDate}`}
          </div>
        </div>
      </div>
    );
  }

  if (phase === "ready" && available) {
    return (
      <div className="flex items-start gap-3 rounded-xl border border-emerald-500/30 bg-emerald-500/5 p-4">
        <div
          className={`flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-xl bg-gradient-to-br text-lg ${PHASE_TONE.ready}`}
        >
          ✓
        </div>
        <div className="space-y-1">
          <div className="text-sm font-medium text-zinc-100">
            v{available.version} 下载完成
          </div>
          <div className="text-[11px] leading-relaxed text-zinc-400">
            点击「重启安装」打开下载目录,需手动替换后重启应用
          </div>
        </div>
      </div>
    );
  }

  // checking / downloading 状态
  return (
    <div className="flex items-start gap-3 rounded-xl border border-zinc-800 bg-zinc-900/50 p-4">
      <div
        className={`flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-xl bg-gradient-to-br text-lg ${PHASE_TONE[phase]}`}
      >
        {PHASE_ICON[phase]}
      </div>
      <div className="space-y-1">
        <div className="text-sm font-medium text-zinc-200">
          {phase === "checking"
            ? "正在探测 GitHub Releases..."
            : "正在下载更新..."}
        </div>
        <div className="text-[11px] leading-relaxed text-zinc-500">
          请稍候,完成后会自动切换到下一步
        </div>
      </div>
    </div>
  );
}

function ProgressBar({ progress }: { progress: UpdateProgress }) {
  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between font-mono text-[11px] text-zinc-400">
        <span>{progress.percent}%</span>
        <span>
          {formatBytes(progress.downloadedBytes)} /{" "}
          {formatBytes(progress.totalBytes)}
        </span>
      </div>
      <div
        className="h-1.5 w-full overflow-hidden rounded-full bg-zinc-800"
        role="progressbar"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={progress.percent}
      >
        <div
          className="h-full bg-gradient-to-r from-blue-500 to-cyan-500 transition-all duration-300"
          style={{ width: `${progress.percent}%` }}
        />
      </div>
    </div>
  );
}

function NotesBlock({ notes }: { notes: string }) {
  return (
    <details className="group rounded-xl border border-zinc-800 bg-zinc-900/30 px-4 py-2 text-[11px]">
      <summary className="cursor-pointer text-zinc-400 transition hover:text-zinc-200">
        📋 Release Notes
      </summary>
      <pre className="mt-2 max-h-40 overflow-y-auto whitespace-pre-wrap break-words font-mono text-zinc-400">
        {notes}
      </pre>
    </details>
  );
}

function ErrorBlock({ message }: { message: string }) {
  return (
    <div
      role="alert"
      className="rounded-md border border-red-500/30 bg-red-500/10 px-3 py-2 text-[11px] text-red-300"
    >
      ⚠ {message}
    </div>
  );
}

function Footer({
  phase,
  busy,
  onCheck,
  onDownload,
  onInstall,
  onReset,
  onClose,
}: {
  phase: UpdatePhase;
  busy: boolean;
  onCheck: () => void;
  onDownload: () => void;
  onInstall: () => void;
  onReset: () => void;
  onClose: () => void;
}) {
  let primaryLabel: string;
  let primaryAction: () => void;
  let primaryDisabled = busy;

  switch (phase) {
    case "idle":
      primaryLabel = "检查更新";
      primaryAction = onCheck;
      break;
    case "available":
      primaryLabel = "下载更新";
      primaryAction = onDownload;
      break;
    case "ready":
      primaryLabel = "重启安装";
      primaryAction = () => void onInstall();
      break;
    default:
      // checking / downloading — no primary action
      primaryLabel = "处理中...";
      primaryAction = () => {};
      primaryDisabled = true;
  }

  return (
    <footer className="flex items-center justify-between gap-2 border-t border-zinc-800/60 px-6 py-4">
      {phase !== "idle" ? (
        <button
          type="button"
          onClick={onReset}
          className="text-[11px] text-zinc-500 transition hover:text-zinc-300"
        >
          ⟲ 重置
        </button>
      ) : (
        <div />
      )}
      <div className="flex gap-2">
        <button
          type="button"
          onClick={onClose}
          className="rounded-lg border border-zinc-800 bg-zinc-900 px-4 py-1.5 text-xs text-zinc-200 transition hover:border-zinc-700"
        >
          关闭
        </button>
        <button
          type="button"
          onClick={primaryAction}
          disabled={primaryDisabled}
          className="rounded-lg bg-gradient-to-r from-blue-500 to-violet-500 px-5 py-1.5 text-xs font-semibold text-white shadow shadow-blue-500/30 transition disabled:cursor-not-allowed disabled:opacity-40"
        >
          {primaryLabel}
        </button>
      </div>
    </footer>
  );
}

// 重新导出 UpdateState 类型 (供上层 store 或 test 引用)
export type { UpdateState };
