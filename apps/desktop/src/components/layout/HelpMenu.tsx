/**
 * SceneFab v3.0 · TopBar · 帮助下拉菜单 (M4 完整更新器)
 *
 * 规范 (项目 memory):
 * - "检查更新..." 触发后端 update_check,以 toast 反馈结果
 * - "关于 SceneFab..." 打开对话框 (不跳转)
 * - 两项之间用分隔线分开
 *
 * M4 更新:
 * - 移除内联 fetchLatestRemote (改用 useUpdate hook)
 * - 5 阶段状态机驱动: idle / checking / available / downloading / ready
 * - available 出现 → "下载 v1.2.3" 按钮; ready 后 → "重启安装" 按钮
 */

import { useEffect, useRef, useState } from "react";
import { useTauriQuery } from "@hooks/useTauriQuery";
import { useUpdate } from "@hooks/useUpdate";
import { formatBytes } from "@lib/format/bytes";
import { toast } from "sonner";

interface HelpMenuState {
  open: boolean;
  showAbout: boolean;
}

export function HelpMenu() {
  const [state, setState] = useState<HelpMenuState>({
    open: false,
    showAbout: false,
  });
  const wrapperRef = useRef<HTMLDivElement | null>(null);

  // Click outside to close
  useEffect(() => {
    function onDocClick(e: MouseEvent) {
      if (
        wrapperRef.current &&
        !wrapperRef.current.contains(e.target as Node)
      ) {
        setState((s) => ({ ...s, open: false }));
      }
    }
    if (state.open) {
      document.addEventListener("mousedown", onDocClick);
      return () => document.removeEventListener("mousedown", onDocClick);
    }
    return undefined;
  }, [state.open]);

  const { data: version } = useTauriQuery({
    command: "app_version",
    queryKeyPrefix: "help-about-version",
    args: {},
  });
  const { data: startedAt } = useTauriQuery({
    command: "app_started_at",
    queryKeyPrefix: "help-about-started",
    args: {},
  });
  const { data: sysInfo } = useTauriQuery({
    command: "app_system_info",
    queryKeyPrefix: "help-about-sys",
    args: {},
  });
  const { data: steps } = useTauriQuery({
    command: "pipeline_step_defs",
    queryKeyPrefix: "help-about-steps",
    args: {},
  });

  // 完整更新器 hook (内置 listen + 短轮询)
  const update = useUpdate({ currentVersion: version ?? undefined });

  // 后端 ready 后自动 toast 一次
  const readyNotifiedRef = useRef<string | null>(null);
  useEffect(() => {
    if (
      update.state.phase === "ready" &&
      update.state.downloadedPath &&
      readyNotifiedRef.current !== update.state.downloadedPath
    ) {
      readyNotifiedRef.current = update.state.downloadedPath;
      toast.success(`下载完成 v${update.state.available?.version ?? "?"}`, {
        description: "可点击菜单内的「重启安装」完成替换",
        duration: 6_000,
      });
    }
  }, [
    update.state.phase,
    update.state.downloadedPath,
    update.state.available?.version,
  ]);

  const handleCheckUpdate = async () => {
    setState((s) => ({ ...s, open: false }));
    const id = toast.loading("正在检查更新...", {
      description: "向 GitHub Releases 探测最新版本",
    });
    try {
      await update.check();
      const remote = update.state.available?.version;
      const cur = (version ?? "0.0.0").replace(/^v/, "");
      if (!remote) {
        toast.error("未读到远端版本信息", { id });
      } else if (remote === cur) {
        toast.success(`已是最新版本 v${cur}`, {
          id,
          description: "无需更新",
        });
      } else {
        toast.success(`发现新版本 v${remote}`, {
          id,
          description: `当前 v${cur} · 再次打开菜单可触发下载`,
          duration: 6_000,
        });
      }
    } catch (e) {
      const msg = (e as { message?: string })?.message ?? String(e);
      toast.error("检查更新失败", {
        id,
        description: msg.slice(0, 200),
      });
    }
  };

  const handleDownload = async () => {
    setState((s) => ({ ...s, open: false }));
    const id = toast.loading("正在下载更新...", {
      description: update.state.available
        ? `v${update.state.available.version} · ${formatBytes(update.state.available.fileSizeBytes)}`
        : "",
    });
    try {
      await update.download();
      toast.success("下载完成", {
        id,
        description: "请打开菜单点击「重启安装」",
      });
    } catch (e) {
      const msg = (e as { message?: string })?.message ?? String(e);
      toast.error("下载失败", { id, description: msg.slice(0, 200) });
    }
  };

  const handleInstall = async () => {
    setState((s) => ({ ...s, open: false }));
    const id = toast.loading("正在准备安装...", {
      description: "M4 阶段:打开下载目录,需手动替换后重启",
    });
    try {
      const r = await update.install();
      toast.success("安装包已就绪", {
        id,
        description: r.note,
        duration: 8_000,
      });
    } catch (e) {
      const msg = (e as { message?: string })?.message ?? String(e);
      toast.error("安装失败", { id, description: msg.slice(0, 200) });
    }
  };

  const handleReset = async () => {
    await update.reset();
    toast.info("已重置更新检查");
  };

  // 决定 Action 按钮的展示
  const phase = update.state.phase;
  const available = update.state.available;
  const progress = update.state.progress;
  const downloadedPath = update.state.downloadedPath;

  let actionIcon = "↻";
  let actionLabel = "检查更新...";
  let actionSub = `当前 v${version ?? "—"}`;
  let onAction = handleCheckUpdate;
  let actionDisabled = update.busy;

  if (phase === "checking") {
    actionIcon = "⏳";
    actionLabel = "正在检查...";
    actionSub = "探测 GitHub Releases";
    actionDisabled = true;
  } else if (phase === "available" && available) {
    actionIcon = "⬇";
    actionLabel = `下载 v${available.version}`;
    actionSub = `${formatBytes(available.fileSizeBytes)} · 大小约 ${
      available.fileSizeBytes ? "已确认" : "未知"
    }`;
    onAction = handleDownload;
  } else if (phase === "downloading") {
    actionIcon = "⏳";
    actionLabel = "下载中...";
    actionSub = `${progress?.percent ?? 0}% · ${formatBytes(
      progress?.downloadedBytes,
    )} / ${formatBytes(progress?.totalBytes)}`;
    actionDisabled = true;
  } else if (phase === "ready" && downloadedPath) {
    actionIcon = "🔄";
    actionLabel = "重启安装";
    actionSub = `v${available?.version ?? "?"} · 已下载到临时目录`;
    onAction = handleInstall;
  }

  return (
    <>
      <div ref={wrapperRef} className="relative">
        <button
          type="button"
          onClick={() => setState((s) => ({ ...s, open: !s.open }))}
          className="rounded-lg border border-zinc-800 bg-zinc-900/60 px-3 py-1.5 text-xs text-zinc-300 transition hover:border-zinc-700 hover:bg-zinc-900"
          aria-haspopup="menu"
          aria-expanded={state.open}
        >
          帮助 ▾
        </button>

        {state.open && (
          <div
            role="menu"
            className="absolute right-0 top-full z-50 mt-1 min-w-[240px] overflow-hidden rounded-xl border border-zinc-800 bg-zinc-950/95 shadow-2xl shadow-black/60 backdrop-blur"
          >
            <button
              type="button"
              role="menuitem"
              onClick={onAction}
              disabled={actionDisabled}
              className="flex w-full items-center gap-3 px-4 py-2.5 text-left text-sm text-zinc-200 transition hover:bg-zinc-900 disabled:opacity-50"
            >
              <span className="flex h-7 w-7 items-center justify-center rounded-md bg-blue-500/15 text-base">
                {actionIcon}
              </span>
              <div className="flex flex-col leading-tight">
                <span>{actionLabel}</span>
                <span className="text-[10px] text-zinc-500">{actionSub}</span>
              </div>
            </button>

            {/* 进度条 (downloading 时显示) */}
            {phase === "downloading" && progress && (
              <div className="px-4 pb-2">
                <div className="h-1 w-full overflow-hidden rounded-full bg-zinc-800">
                  <div
                    className="h-full bg-blue-500 transition-all duration-300"
                    style={{ width: `${progress.percent}%` }}
                  />
                </div>
              </div>
            )}

            {/* 错误信息 */}
            {update.state.error && (
              <div className="mx-4 mb-2 rounded-md border border-red-500/30 bg-red-500/10 px-3 py-2 text-[11px] text-red-300">
                {update.state.error}
              </div>
            )}

            <div className="my-1 h-px bg-zinc-800" />

            <button
              type="button"
              role="menuitem"
              onClick={() => {
                setState((s) => ({ ...s, open: false, showAbout: true }));
              }}
              className="flex w-full items-center gap-3 px-4 py-2.5 text-left text-sm text-zinc-200 transition hover:bg-zinc-900"
            >
              <span className="flex h-7 w-7 items-center justify-center rounded-md bg-violet-500/15 text-base">
                ⓘ
              </span>
              <div className="flex flex-col leading-tight">
                <span>关于 SceneFab...</span>
                <span className="text-[10px] text-zinc-500">
                  版本与系统信息
                </span>
              </div>
            </button>

            {/* 调试用:重置 (visible when phase !== idle) */}
            {phase !== "idle" && (
              <button
                type="button"
                role="menuitem"
                onClick={handleReset}
                className="flex w-full items-center gap-3 px-4 py-2 text-left text-xs text-zinc-500 transition hover:bg-zinc-900 hover:text-zinc-300"
              >
                <span className="flex h-6 w-6 items-center justify-center rounded-md text-base">
                  ⟲
                </span>
                <span>重置更新状态</span>
              </button>
            )}
          </div>
        )}
      </div>

      {state.showAbout && (
        <AboutDialog
          onClose={() => setState((s) => ({ ...s, showAbout: false }))}
          version={version ?? "—"}
          startedAt={startedAt ?? null}
          ffmpegAvailable={sysInfo?.ffmpegAvailable ?? false}
          ffmpegVersion={sysInfo?.ffmpegVersion ?? null}
          stepsCount={steps?.length ?? 5}
        />
      )}
    </>
  );
}

// ── AboutDialog ─────────────────────────────────────────────────────

function AboutDialog({
  onClose,
  version,
  startedAt,
  ffmpegAvailable,
  ffmpegVersion,
  stepsCount,
}: {
  onClose: () => void;
  version: string;
  startedAt: string | null;
  ffmpegAvailable: boolean;
  ffmpegVersion: string | null;
  stepsCount: number;
}) {
  // ESC 关闭
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="about-title"
        className="w-[480px] max-w-[90vw] overflow-hidden rounded-2xl border border-zinc-800 bg-zinc-950 shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b border-zinc-800/60 px-6 py-4">
          <h2 id="about-title" className="text-lg font-semibold text-zinc-100">
            关于 SceneFab
          </h2>
          <button
            type="button"
            onClick={onClose}
            className="rounded-md p-1 text-zinc-500 transition hover:bg-zinc-900 hover:text-zinc-100"
            aria-label="关闭"
          >
            ✕
          </button>
        </div>

        <div className="space-y-5 p-6">
          <div className="flex items-center gap-4">
            <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-blue-500 via-violet-500 to-fuchsia-500 text-2xl font-black text-white shadow-lg shadow-violet-500/30">
              S
            </div>
            <div className="space-y-1">
              <div className="text-xl font-bold text-zinc-100">SceneFab</div>
              <div className="font-mono text-xs text-zinc-500">
                v{version} · AI Video Narrator
              </div>
            </div>
          </div>

          <p className="text-sm leading-relaxed text-zinc-400">
            基于 Tauri 2 + Rust + React 19 的第一人称叙述视频编辑器。 5
            步流水线:素材 → 场景 → 脚本 → 配音字幕 → 导出。
          </p>

          <div className="grid grid-cols-2 gap-3 rounded-xl border border-zinc-800 bg-zinc-900/50 p-4 text-xs">
            <AboutRow label="流水线" value={`${stepsCount} 步`} />
            <AboutRow
              label="FFmpeg"
              value={ffmpegAvailable ? (ffmpegVersion ?? "就绪") : "未安装"}
              tone={ffmpegAvailable ? "ok" : "warn"}
            />
            <AboutRow
              label="启动"
              value={
                startedAt ? new Date(startedAt).toLocaleString("zh-CN") : "—"
              }
            />
            <AboutRow label="运行时" value="Tauri 2 + Rust" />
          </div>

          <div className="flex justify-end gap-2">
            <button
              type="button"
              onClick={onClose}
              className="rounded-lg border border-zinc-800 bg-zinc-900 px-4 py-1.5 text-xs text-zinc-200 hover:border-zinc-700"
            >
              关闭
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

function AboutRow({
  label,
  value,
  tone,
}: {
  label: string;
  value: string;
  tone?: "ok" | "warn";
}) {
  const toneCls =
    tone === "ok"
      ? "text-emerald-300"
      : tone === "warn"
        ? "text-amber-300"
        : "text-zinc-200";
  return (
    <div className="flex flex-col gap-0.5">
      <span className="text-[10px] uppercase tracking-wider text-zinc-500">
        {label}
      </span>
      <span className={`truncate font-mono text-xs ${toneCls}`}>{value}</span>
    </div>
  );
}
