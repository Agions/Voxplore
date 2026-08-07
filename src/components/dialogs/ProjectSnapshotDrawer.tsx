/**
 * Vynaro v1.0.1 · ProjectSnapshotDrawer
 *
 * 右侧滑出式解说工程版本历史与快照面板 (100% 对齐架构设计图)
 */

import { useEffect, useState } from "react";
import { useSnapshot } from "../../hooks/useSnapshot";
import { useProjectStore } from "../../stores/project-store";

export function ProjectSnapshotDrawer() {
  const { current } = useProjectStore();
  const {
    snapshots,
    fetchSnapshots,
    createSnapshot,
    restoreSnapshot,
    forkSnapshot,
    deleteSnapshot,
    isDrawerOpen,
    closeDrawer,
  } = useSnapshot();

  const [isCreating, setIsCreating] = useState(false);
  const [manualName, setManualName] = useState("");

  // 打开抽屉时拉取快照
  useEffect(() => {
    if (isDrawerOpen && current?.id) {
      void fetchSnapshots();
    }
  }, [isDrawerOpen, current?.id, fetchSnapshots]);

  // Esc 键关闭抽屉
  useEffect(() => {
    function onKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape" && isDrawerOpen) {
        closeDrawer();
      }
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [isDrawerOpen, closeDrawer]);

  if (!isDrawerOpen) return null;

  const handleManualCreate = async () => {
    if (!manualName.trim()) return;
    await createSnapshot(manualName.trim(), "manual");
    setManualName("");
    setIsCreating(false);
  };

  return (
    <div className="fixed inset-0 z-50 overflow-hidden bg-black/60 backdrop-blur-sm animate-fade-in">
      {/* 点击背景遮罩关闭 */}
      <div className="absolute inset-0" onClick={closeDrawer} />

      {/* 滑出抽屉主体 */}
      <div className="absolute right-0 top-0 bottom-0 w-full max-w-lg border-l border-[var(--color-gold)]/40 bg-[var(--color-surface)]/95 p-6 shadow-[0_0_50px_var(--color-gold-glow)] backdrop-blur-2xl flex flex-col justify-between transition-transform animate-slide-in">
        {/* 顶部 Heading */}
        <div className="space-y-4 border-b border-[var(--color-border)] pb-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="flex h-8 w-8 items-center justify-center rounded-xl bg-[var(--color-gold-muted)] text-base font-bold text-[var(--color-gold)] border border-[var(--color-gold)]/30 shadow-sm">
                📸
              </span>
              <div>
                <h2 className="text-base font-black tracking-tight text-[var(--color-text-primary)]">
                  解说工程版本历史与快照
                </h2>
                <p className="text-[11px] text-[var(--color-text-muted)] font-mono">
                  PROJECT VERSION SNAPSHOTS · {current?.name ?? "当前工程"}
                </p>
              </div>
            </div>

            <button
              type="button"
              onClick={closeDrawer}
              className="flex h-8 w-8 items-center justify-center rounded-xl border border-[var(--color-border)] text-[var(--color-text-secondary)] hover:border-[var(--color-gold)] hover:text-[var(--color-gold)] transition"
              aria-label="关闭抽屉"
            >
              ✕
            </button>
          </div>

          {/* 手动打快照触发栏 */}
          {!isCreating ? (
            <button
              type="button"
              onClick={() => setIsCreating(true)}
              className="w-full flex items-center justify-center gap-2 rounded-xl border border-[var(--color-gold)] bg-[var(--color-gold-muted)] py-2.5 text-xs font-bold text-[var(--color-gold)] shadow-[0_0_12px_var(--color-gold-glow)] hover:brightness-110 transition"
            >
              <span>📸</span> 创建手动版本快照
            </button>
          ) : (
            <div className="space-y-2 rounded-xl border border-[var(--color-gold)] bg-[var(--color-surface-elevated)] p-3 animate-fade-in">
              <input
                type="text"
                value={manualName}
                onChange={(e) => setManualName(e.target.value)}
                placeholder="输入快照备注 (如: 改动第一人称开场白)..."
                className="w-full rounded-lg border border-[var(--color-border)] bg-[var(--color-bg)] px-3 py-1.5 text-xs text-[var(--color-text-primary)] outline-none focus:border-[var(--color-gold)]"
                autoFocus
                onKeyDown={(e) => {
                  if (e.key === "Enter") void handleManualCreate();
                }}
              />
              <div className="flex items-center justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setIsCreating(false)}
                  className="rounded-lg border border-[var(--color-border)] px-3 py-1 text-xs text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]"
                >
                  取消
                </button>
                <button
                  type="button"
                  onClick={() => void handleManualCreate()}
                  className="rounded-lg bg-[var(--color-gold)] px-3 py-1 text-xs font-bold text-zinc-950 shadow-sm hover:brightness-110"
                >
                  保存快照
                </button>
              </div>
            </div>
          )}
        </div>

        {/* 中间时间轴列表 */}
        <div className="flex-1 overflow-y-auto py-4 space-y-4 pr-1">
          {snapshots.length === 0 ? (
            <div className="py-16 text-center text-xs text-[var(--color-text-muted)] space-y-2">
              <div className="text-2xl">⏳</div>
              <div>暂无历史版本快照</div>
              <p className="text-[11px] opacity-70">
                推进 7 步流水线或点击上方按钮将自动捕获版本点
              </p>
            </div>
          ) : (
            <div className="relative pl-6 space-y-6 before:absolute before:left-3 before:top-3 before:bottom-3 before:w-[2px] before:bg-[var(--color-border)]">
              {snapshots.map((snap) => (
                <div
                  key={snap.id}
                  className="relative group rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface-elevated)] p-4 space-y-3 transition-all hover:border-[var(--color-gold)] hover:shadow-[0_0_20px_var(--color-gold-glow)]"
                >
                  {/* 时间轴节点琥珀金徽章 */}
                  <div className="absolute -left-9 top-4 flex h-6 w-6 items-center justify-center rounded-full bg-[var(--color-surface)] border-2 border-[var(--color-gold)] text-[10px] font-mono font-bold text-[var(--color-gold)] shadow-[0_0_10px_var(--color-gold-glow)]">
                    ●
                  </div>

                  {/* 头部元信息 */}
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="rounded-lg bg-[var(--color-gold-muted)] border border-[var(--color-gold)]/40 px-2 py-0.5 font-mono text-xs font-black text-[var(--color-gold)]">
                        {snap.versionTag}
                      </span>
                      <span
                        className={`rounded-md px-1.5 py-0.5 text-[10px] font-bold ${
                          snap.kind === "auto"
                            ? "bg-blue-500/10 text-blue-400 border border-blue-500/30"
                            : "bg-emerald-500/10 text-emerald-400 border border-emerald-500/30"
                        }`}
                      >
                        {snap.kind === "auto" ? "AUTO 自动" : "MANUAL 手动"}
                      </span>
                    </div>

                    <div className="flex items-center gap-2 text-[11px] font-mono text-[var(--color-text-muted)]">
                      <span>
                        {new Date(snap.createdAt).toLocaleString("zh-CN", {
                          hour12: false,
                        })}
                      </span>
                      <button
                        type="button"
                        onClick={() => void deleteSnapshot(snap.id)}
                        className="opacity-0 group-hover:opacity-100 text-rose-400 hover:text-rose-300 transition"
                        title="删除此快照"
                      >
                        🗑️
                      </button>
                    </div>
                  </div>

                  {/* 快照名称备注 */}
                  <div className="text-xs font-bold text-[var(--color-text-primary)]">
                    {snap.name}
                  </div>

                  {/* 操作按钮区 */}
                  <div className="flex items-center gap-2 pt-1 border-t border-[var(--color-border)]/50">
                    <button
                      type="button"
                      onClick={() => void restoreSnapshot(snap.id)}
                      className="flex-1 flex items-center justify-center gap-1 rounded-xl border border-[var(--color-gold)]/50 bg-[var(--color-bg)] py-1.5 text-xs font-bold text-[var(--color-gold)] hover:bg-[var(--color-gold-muted)] transition"
                    >
                      🔄 还原此版本
                    </button>
                    <button
                      type="button"
                      onClick={() => void forkSnapshot(snap)}
                      className="flex-1 flex items-center justify-center gap-1 rounded-xl border border-[var(--color-border)] bg-[var(--color-bg)] py-1.5 text-xs font-bold text-[var(--color-text-secondary)] hover:border-[var(--color-gold)] hover:text-[var(--color-gold)] transition"
                    >
                      🌿 衍生新工程
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* 底部 Footer 帮助说明 */}
        <div className="border-t border-[var(--color-border)] pt-3 text-[11px] text-[var(--color-text-muted)] flex items-center justify-between font-mono">
          <span>容量防护: 最多保留 30 个版本</span>
          <span>按 Esc 快速关闭</span>
        </div>
      </div>
    </div>
  );
}
