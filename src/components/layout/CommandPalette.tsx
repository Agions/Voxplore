/**
 * Vynaro v1.0.0 · ⌘K 全局命令面板 (M4)
 *
 * - 使用 cmdk 作为命令面板核心 (已在 deps)
 * - 4 个分类:
 *   · 页面 (navigate)
 *   · 项目 (recent projects from listRecent)
 *   · 动作 (新建/导入/检查更新/主题)
 *   · 流水线 (启动/取消/重置 — 依赖当前 Project 上下文)
 * - 全局快捷键:⌘K (mac) / Ctrl+K (others) 打开/关闭;Esc 关闭
 * - 视觉:遮罩 + 居中 modal + 渐变描边 + 命令行风格光标
 */

import { useEffect, useMemo, useState } from "react";
import { Command } from "cmdk";
import { useNavigate } from "@tanstack/react-router";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { open as openDialog } from "@tauri-apps/plugin-dialog";
import { useUiStore } from "@stores/ui-store";
import { useThemeStore } from "@stores/theme-store";
import { projectIpc, pipelineIpc } from "@ipc/commands";
import type { MediaFile } from "@ipc/types.gen";

interface ActionItem {
  id: string;
  label: string;
  hint?: string;
  icon: string;
  group: "pages" | "projects" | "actions" | "pipeline";
  shortcut?: string;
  keywords?: string;
  run: () => void | Promise<void>;
}

export function CommandPalette() {
  const open = useUiStore((s) => s.commandPaletteOpen);
  const close = useUiStore((s) => s.closeCommandPalette);
  const openPalette = useUiStore((s) => s.openCommandPalette);
  const theme = useThemeStore((s) => s.theme);
  const toggleTheme = useThemeStore((s) => s.toggle);
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [search, setSearch] = useState("");

  // recent projects (for dynamic group)
  const { data: recents } = useQuery<string[]>({
    queryKey: ["assets-recent"],
    queryFn: projectIpc.listRecent,
    enabled: open,
  });

  const checkUpdateRemote = async () => {
    const id = toast.loading("正在检查更新...");
    try {
      const r = await fetch(
        "https://api.github.com/repos/qingshanyanyu/Vynaro/releases/latest",
      );
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const data = (await r.json()) as { tag_name?: string };
      const remote = (data.tag_name ?? "").replace(/^v/, "");
      if (remote) {
        toast.success(`最新版本 v${remote}`, { id });
      } else {
        toast.success("已是最新版本", { id });
      }
    } catch (e) {
      toast.error("检查更新失败", {
        id,
        description: e instanceof Error ? e.message : String(e),
      });
    }
  };

  const navigateTo = (path: string) => {
    void navigate({ to: path });
    close();
  };

  const handleImportMedia = async () => {
    close();
    try {
      const selected = await openDialog({
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
      const mfs: MediaFile[] = paths.map((p) => ({
        path: p,
        duration_seconds: 0,
        resolution: null,
        codec: null,
        file_size_bytes: 0,
        import_time: new Date().toISOString(),
      }));
      qc.setQueryData(["assets-pending-media"], (old: MediaFile[] = []) => [
        ...old,
        ...mfs,
      ]);
      toast.success(`已暂存 ${mfs.length} 个文件`, {
        description: "前往项目管理页查看",
      });
    } catch (e) {
      toast.error("导入失败", {
        description: e instanceof Error ? e.message : String(e),
      });
    }
  };

  const createBlank = async () => {
    close();
    try {
      const rec = await projectIpc.createBlank();
      qc.setQueryData(["assets-current-project"], rec.project);
      void qc.invalidateQueries({ queryKey: ["assets-recent"] });
      toast.success(`已创建空白项目 ${rec.project.name ?? rec.path}`);
      navigateTo("/production");
    } catch (e) {
      toast.error("创建失败", {
        description: e instanceof Error ? e.message : String(e),
      });
    }
  };

  const cancelPipeline = async () => {
    close();
    try {
      await pipelineIpc.cancel();
      toast.success("已请求取消流水线");
    } catch (e) {
      toast.error("取消失败", {
        description: e instanceof Error ? e.message : String(e),
      });
    }
  };

  const resetPipeline = async () => {
    close();
    try {
      await pipelineIpc.reset();
      toast.success("流水线已重置");
    } catch (e) {
      toast.error("重置失败", {
        description: e instanceof Error ? e.message : String(e),
      });
    }
  };

  // 静态条目
  const staticItems: ActionItem[] = useMemo(
    () => [
      {
        id: "page-home",
        label: "首页",
        icon: "🏠",
        group: "pages",
        shortcut: "G H",
        keywords: "首页 home 工作台 dashboard",
        run: () => navigateTo("/"),
      },
      {
        id: "page-production",
        label: "制作流水线",
        icon: "🎬",
        group: "pages",
        shortcut: "G P",
        keywords: "流水线 pipeline 制作 production",
        run: () => navigateTo("/production"),
      },
      {
        id: "page-assets",
        label: "项目管理",
        icon: "📁",
        group: "pages",
        shortcut: "G A",
        keywords: "项目 assets 资产 媒体 media",
        run: () => navigateTo("/assets"),
      },
      {
        id: "page-settings",
        label: "设置",
        icon: "⚙",
        group: "pages",
        shortcut: "G S",
        keywords: "设置 settings 配置 config",
        run: () => navigateTo("/settings"),
      },
      {
        id: "page-help",
        label: "快捷键帮助",
        icon: "❓",
        group: "pages",
        shortcut: "G ?",
        keywords: "帮助 help 快捷键 shortcut",
        run: () => navigateTo("/help"),
      },
      {
        id: "action-new-project",
        label: "新建空白项目",
        icon: "✨",
        group: "actions",
        shortcut: "⌘N",
        keywords: "新建 create new blank project",
        run: () => void createBlank(),
      },
      {
        id: "action-import-media",
        label: "导入媒体文件…",
        icon: "📥",
        group: "actions",
        keywords: "导入 import upload media 视频 video",
        run: () => void handleImportMedia(),
      },
      {
        id: "action-check-update",
        label: "检查更新…",
        icon: "🔄",
        group: "actions",
        keywords: "更新 update 检查 check",
        run: () => {
          close();
          void checkUpdateRemote();
        },
      },
      {
        id: "action-toggle-theme",
        label: `切换主题 (当前: ${theme})`,
        icon: theme === "dark" ? "🌙" : theme === "light" ? "☀️" : "🖥",
        group: "actions",
        keywords: "主题 theme 切换 dark light system",
        run: () => {
          toggleTheme();
          close();
        },
      },
      {
        id: "action-goto-settings",
        label: "管理 LLM / TTS 凭据",
        icon: "🔑",
        group: "actions",
        keywords: "凭据 credentials api key tts llm",
        run: () => navigateTo("/settings"),
      },
      {
        id: "action-goto-help",
        label: "查看快捷键与文档",
        icon: "📖",
        group: "actions",
        keywords: "文档 docs 帮助 help",
        run: () => navigateTo("/help"),
      },
      {
        id: "pipeline-cancel",
        label: "取消当前流水线",
        icon: "🛑",
        group: "pipeline",
        shortcut: "⌘.",
        keywords: "取消 cancel stop 中断 abort",
        run: () => void cancelPipeline(),
      },
      {
        id: "pipeline-reset",
        label: "重置流水线状态",
        icon: "♻",
        group: "pipeline",
        keywords: "重置 reset clear 清除",
        run: () => void resetPipeline(),
      },
      {
        id: "pipeline-go",
        label: "前往流水线页面",
        icon: "▶",
        group: "pipeline",
        shortcut: "⌘R",
        keywords: "启动 run start 流水线 制作",
        run: () => navigateTo("/production"),
      },
    ],
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [theme, navigate],
  );

  const projectItems: ActionItem[] = useMemo(
    () =>
      (recents ?? []).slice(0, 6).map((path) => {
        const base = path.split(/[\\/]/).pop() ?? path;
        return {
          id: `proj-${path}`,
          label: `打开 ${base}`,
          icon: "🗂",
          group: "projects" as const,
          keywords: `${path} project open`,
          run: async () => {
            close();
            try {
              const full = await projectIpc.load(path);
              qc.setQueryData(["assets-current-project"], full.project);
              toast.success(`已加载 ${full.project.name ?? base}`);
              navigateTo("/production");
            } catch (e) {
              toast.error("加载失败", {
                description: e instanceof Error ? e.message : String(e),
              });
            }
          },
        };
      }),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [recents, navigate, qc],
  );

  const allItems = useMemo(
    () => [...staticItems, ...projectItems],
    [staticItems, projectItems],
  );

  const grouped = useMemo(() => {
    const groups: Record<ActionItem["group"], ActionItem[]> = {
      pages: [],
      projects: [],
      actions: [],
      pipeline: [],
    };
    for (const item of allItems) groups[item.group].push(item);
    return groups;
  }, [allItems]);

  // ⌘K / Ctrl+K 全局开关 与 ESC 关闭
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape" && useUiStore.getState().commandPaletteOpen) {
        e.preventDefault();
        close();
        return;
      }
      const mod = e.metaKey || e.ctrlKey;
      if (mod && (e.key === "k" || e.key === "K")) {
        e.preventDefault();
        if (useUiStore.getState().commandPaletteOpen) {
          close();
        } else {
          openPalette();
        }
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [openPalette, close]);

  // 打开时清空 query
  useEffect(() => {
    if (open) setSearch("");
  }, [open]);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center pt-[12vh]"
      role="dialog"
      aria-modal="true"
      aria-label="命令面板"
      onClick={(e) => {
        if (e.target === e.currentTarget) close();
      }}
    >
      {/* 背景遮罩 */}
      <div className="absolute inset-0 bg-black/55 backdrop-blur-md" />

      <div className="relative w-full max-w-2xl px-4">
        <Command
          className="overflow-hidden rounded-2xl border border-zinc-800 bg-zinc-950/95 shadow-2xl shadow-violet-500/10"
          shouldFilter
        >
          {/* 渐变描边 */}
          <div className="pointer-events-none absolute inset-0 rounded-2xl ring-1 ring-inset ring-gradient-to-r from-violet-500/40 via-fuchsia-500/30 to-blue-500/40" />

          <div className="flex items-center gap-3 border-b border-zinc-800/80 px-4 py-3">
            <span className="text-lg text-zinc-500">🔍</span>
            <Command.Input
              autoFocus
              value={search}
              onValueChange={setSearch}
              placeholder="输入命令、页面或动作…"
              className="flex-1 bg-transparent text-base text-zinc-100 placeholder-zinc-600 outline-none"
            />
            <kbd
              onClick={close}
              className="cursor-pointer rounded border border-zinc-800 bg-zinc-900 px-1.5 py-0.5 text-[10px] font-medium text-zinc-400 hover:border-zinc-600 hover:text-zinc-100"
            >
              ESC
            </kbd>
          </div>

          <Command.List className="max-h-[55vh] overflow-y-auto px-2 py-2">
            <Command.Empty className="py-12 text-center text-sm text-zinc-600">
              没有匹配的命令
            </Command.Empty>

            {/* Pages */}
            {grouped.pages.length > 0 && (
              <Command.Group
                heading="页面"
                className="[&_[cmdk-group-heading]]:px-2 [&_[cmdk-group-heading]]:py-1.5 [&_[cmdk-group-heading]]:text-[10px] [&_[cmdk-group-heading]]:font-semibold [&_[cmdk-group-heading]]:uppercase [&_[cmdk-group-heading]]:tracking-[0.18em] [&_[cmdk-group-heading]]:text-zinc-500"
              >
                {grouped.pages.map((item) => (
                  <PaletteItem key={item.id} item={item} />
                ))}
              </Command.Group>
            )}

            {/* Projects */}
            {grouped.projects.length > 0 && (
              <Command.Group
                heading="最近项目"
                className="[&_[cmdk-group-heading]]:px-2 [&_[cmdk-group-heading]]:py-1.5 [&_[cmdk-group-heading]]:text-[10px] [&_[cmdk-group-heading]]:font-semibold [&_[cmdk-group-heading]]:uppercase [&_[cmdk-group-heading]]:tracking-[0.18em] [&_[cmdk-group-heading]]:text-zinc-500"
              >
                {grouped.projects.map((item) => (
                  <PaletteItem key={item.id} item={item} />
                ))}
              </Command.Group>
            )}

            {/* Actions */}
            {grouped.actions.length > 0 && (
              <Command.Group
                heading="动作"
                className="[&_[cmdk-group-heading]]:px-2 [&_[cmdk-group-heading]]:py-1.5 [&_[cmdk-group-heading]]:text-[10px] [&_[cmdk-group-heading]]:font-semibold [&_[cmdk-group-heading]]:uppercase [&_[cmdk-group-heading]]:tracking-[0.18em] [&_[cmdk-group-heading]]:text-zinc-500"
              >
                {grouped.actions.map((item) => (
                  <PaletteItem key={item.id} item={item} />
                ))}
              </Command.Group>
            )}

            {/* Pipeline */}
            {grouped.pipeline.length > 0 && (
              <Command.Group
                heading="流水线"
                className="[&_[cmdk-group-heading]]:px-2 [&_[cmdk-group-heading]]:py-1.5 [&_[cmdk-group-heading]]:text-[10px] [&_[cmdk-group-heading]]:font-semibold [&_[cmdk-group-heading]]:uppercase [&_[cmdk-group-heading]]:tracking-[0.18em] [&_[cmdk-group-heading]]:text-zinc-500"
              >
                {grouped.pipeline.map((item) => (
                  <PaletteItem key={item.id} item={item} />
                ))}
              </Command.Group>
            )}
          </Command.List>

          <div className="flex items-center justify-between border-t border-zinc-800/80 px-4 py-2 text-[11px] text-zinc-500">
            <div className="flex items-center gap-3">
              <span className="flex items-center gap-1">
                <kbd className="rounded border border-zinc-800 bg-zinc-900 px-1.5">
                  ↑↓
                </kbd>
                移动
              </span>
              <span className="flex items-center gap-1">
                <kbd className="rounded border border-zinc-800 bg-zinc-900 px-1.5">
                  ↵
                </kbd>
                执行
              </span>
            </div>
            <span className="flex items-center gap-1">
              <kbd className="rounded border border-zinc-800 bg-zinc-900 px-1.5">
                ⌘K
              </kbd>
              切换
            </span>
          </div>
        </Command>
      </div>
    </div>
  );
}

function PaletteItem({ item }: { item: ActionItem }) {
  return (
    <Command.Item
      value={`${item.label} ${item.keywords ?? ""}`}
      onSelect={() => void item.run()}
      onClick={() => void item.run()}
      className="flex cursor-pointer items-center justify-between gap-3 rounded-lg px-3 py-2 text-sm text-zinc-200 aria-selected:bg-gradient-to-r aria-selected:from-violet-500/15 aria-selected:via-fuchsia-500/10 aria-selected:to-blue-500/15 aria-selected:text-zinc-50 data-[selected=true]:bg-gradient-to-r data-[selected=true]:from-violet-500/15 data-[selected=true]:via-fuchsia-500/10 data-[selected=true]:to-blue-500/15 data-[selected=true]:text-zinc-50"
    >
      <div className="flex items-center gap-3 truncate">
        <span className="text-base">{item.icon}</span>
        <span className="truncate">{item.label}</span>
      </div>
      {item.shortcut && (
        <kbd className="shrink-0 rounded border border-zinc-800 bg-zinc-900 px-1.5 py-0.5 text-[10px] text-zinc-500">
          {item.shortcut}
        </kbd>
      )}
    </Command.Item>
  );
}
