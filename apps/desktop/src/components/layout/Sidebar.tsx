/**
 * SceneFab v3.0 · 左侧导航栏
 * - 高亮当前路由
 * - 主区 4 项 + 二级帮助/更新
 */

import { Link } from "@tanstack/react-router";

export interface NavItem {
  to: string;
  label: string;
  icon: string; // 单字符 emoji 或 SVG glyph
  hint: string;
  primary?: boolean;
}

// 仅 4 项主导航 (M3.2 规范):
// - Updates / Help 由 TopBar 的"帮助"菜单接管,不再重复进侧栏
const NAV_ITEMS: NavItem[] = [
  { to: "/", label: "首页", icon: "🏠", hint: "工作台" },
  {
    to: "/production",
    label: "制作流水线",
    icon: "🎬",
    hint: "5 步叙事",
    primary: true,
  },
  { to: "/assets", label: "项目管理", icon: "📁", hint: "媒体 / 脚本" },
  { to: "/settings", label: "设置", icon: "⚙", hint: "LLM / TTS" },
];

interface SidebarProps {
  currentPath: string;
}

export function Sidebar({ currentPath }: SidebarProps) {
  return (
    <aside className="flex w-56 flex-col border-r border-zinc-800/80 bg-zinc-950/70">
      <nav className="flex-1 space-y-1 px-3 py-4">
        {NAV_ITEMS.map((item) => {
          const active =
            item.to === "/"
              ? currentPath === "/"
              : currentPath.startsWith(item.to);
          return (
            <Link
              key={item.to}
              to={item.to}
              className={`group flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition ${
                active
                  ? "bg-gradient-to-r from-blue-600/20 to-violet-600/10 text-blue-200 shadow-inner shadow-blue-500/10"
                  : "text-zinc-400 hover:bg-zinc-900/60 hover:text-zinc-100"
              }`}
            >
              <span
                className={`flex h-7 w-7 items-center justify-center rounded-md text-sm ${
                  active
                    ? "bg-blue-500/20 text-blue-200"
                    : "bg-zinc-800/60 text-zinc-400 group-hover:bg-zinc-800 group-hover:text-zinc-200"
                }`}
              >
                {item.icon}
              </span>
              <span className="flex flex-1 flex-col leading-tight">
                <span className="font-medium">{item.label}</span>
                <span className="text-[10px] text-zinc-500">{item.hint}</span>
              </span>
              {item.primary && active && (
                <span className="h-1.5 w-1.5 rounded-full bg-blue-400" />
              )}
            </Link>
          );
        })}
      </nav>

      <footer className="border-t border-zinc-800/80 px-4 py-3 text-[10px] text-zinc-600">
        <div className="flex items-center justify-between">
          <span>M3.2 · α</span>
          <span className="font-mono">rust+react</span>
        </div>
      </footer>
    </aside>
  );
}
