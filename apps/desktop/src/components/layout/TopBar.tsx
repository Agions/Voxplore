/**
 * SceneFab v2.5.0 · 应用顶栏
 * - Logo + 产品名 + 版本徽章
 * - 实时 Tauri 后端连接状态点
 * - 主题切换按钮
 */

import { useTauriQuery } from "@hooks/useTauriQuery";
import { useThemeStore } from "@stores/theme-store";
import { useUiStore } from "@stores/ui-store";
import { HelpMenu } from "./HelpMenu";
import { Toaster } from "sonner";

export function TopBar() {
  const { data: version, isError } = useTauriQuery({
    command: "app_version",
    queryKeyPrefix: "topbar-version",
    args: {},
  });
  const theme = useThemeStore((s) => s.theme);
  const toggle = useThemeStore((s) => s.toggle);
  const openPalette = useUiStore((s) => s.openCommandPalette);

  const connected = !isError && Boolean(version);

  return (
    <header className="flex h-14 items-center justify-between border-b border-zinc-800/80 bg-zinc-950/80 px-6 backdrop-blur-md">
      <div className="flex items-center gap-3">
        <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-blue-500 via-violet-500 to-fuchsia-500 text-white shadow-lg shadow-violet-500/20">
          <span className="text-base font-black">S</span>
        </div>
        <div className="flex flex-col leading-tight">
          <span className="text-base font-semibold tracking-tight text-zinc-50">
            SceneFab
          </span>
          <span className="text-[10px] font-medium uppercase tracking-[0.2em] text-zinc-500">
            AI Video Narrator · v{version ?? "—"}
          </span>
        </div>
      </div>

      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={() => openPalette()}
          className="flex items-center gap-2 rounded-lg border border-zinc-800 bg-zinc-900/60 px-3 py-1.5 text-xs text-zinc-400 transition hover:border-zinc-700 hover:bg-zinc-900 hover:text-zinc-200"
          title="打开命令面板"
        >
          <span className="text-zinc-500">🔍</span>
          <span>搜索命令</span>
          <kbd className="ml-2 rounded border border-zinc-800 bg-zinc-950 px-1.5 py-0.5 font-mono text-[10px] text-zinc-500">
            ⌘K
          </kbd>
        </button>

        <div
          className={`flex items-center gap-2 rounded-full border px-3 py-1 text-[11px] ${
            connected
              ? "border-emerald-700/40 bg-emerald-950/30 text-emerald-300"
              : "border-rose-800/40 bg-rose-950/30 text-rose-300"
          }`}
        >
          <span
            className={`h-1.5 w-1.5 rounded-full ${
              connected ? "bg-emerald-400" : "bg-rose-400"
            }`}
          />
          {connected ? "Tauri 已连接" : "后端未连接"}
        </div>

        <HelpMenu />

        <button
          type="button"
          onClick={toggle}
          className="rounded-lg border border-zinc-800 bg-zinc-900/60 px-3 py-1.5 text-xs text-zinc-300 transition hover:border-zinc-700 hover:bg-zinc-900"
          title={`当前: ${theme}`}
        >
          {theme === "dark" ? "🌙" : theme === "light" ? "☀️" : "🖥"}
        </button>
      </div>
      <Toaster
        theme="dark"
        position="bottom-right"
        toastOptions={{
          classNames: {
            toast:
              "!bg-zinc-900 !text-zinc-100 !border !border-zinc-800 !rounded-xl",
          },
        }}
      />
    </header>
  );
}
