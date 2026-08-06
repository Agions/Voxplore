/**
 * Vynaro v2.5.0 · 电影调光室左侧导航栏 (根据 Image 1 UI 设计原图与实际功能 100% 对齐重构)
 *
 * 核心区域结构:
 * 1. 顶部 Vynaro 品牌 V Logo 图标 (带金色发光)
 * 2. 主功能导航 (Home 🏠, Assets 📁, Pipeline 🎬, Projects 📂, AI Styles ✨, Export 📤)
 * 3. 底部系统导航 (Settings ⚙️, Help ❓, User Profile 👤)
 */

import { Link } from "@tanstack/react-router";
import { useState } from "react";
import { useSettingsStore } from "@stores/settings-store";
import { t } from "@lib/i18n";

interface NavItem {
  to: string;
  key: string;
  icon: string;
  hint: string;
  badge?: string;
}

const TOP_NAV_ITEMS: NavItem[] = [
  { to: "/",          key: "nav.home",       icon: "🏠", hint: "Home" },
  { to: "/assets",    key: "nav.assets",     icon: "📁", hint: "Assets" },
  { to: "/production",key: "nav.production", icon: "🎬", hint: "Pipeline", badge: "7-Step" },
  { to: "/assets",    key: "nav.projects",   icon: "📂", hint: "Projects" },
  { to: "/settings",  key: "nav.styles",     icon: "✨", hint: "AI Styles" },
  { to: "/production",key: "nav.export",     icon: "📤", hint: "Export" },
];

const BOTTOM_NAV_ITEMS: NavItem[] = [
  { to: "/settings", key: "nav.settings",   icon: "⚙️", hint: "Settings" },
  { to: "/help",     key: "nav.help",       icon: "❓", hint: "Help" },
];

interface SidebarProps {
  currentPath: string;
}

export function Sidebar({ currentPath }: SidebarProps) {
  const locale = useSettingsStore((s) => s.locale);
  const [showProfileModal, setShowProfileModal] = useState(false);

  return (
    <aside
      className="flex w-16 flex-col items-center justify-between border-r border-[#2A2A2F] bg-[#0D0D0F] py-3 flex-shrink-0 z-30 select-none"
      aria-label="Vynaro 主导航"
    >
      {/* 1. 顶部 Brand Logo */}
      <div className="flex flex-col items-center space-y-4 w-full">
        <Link
          to="/"
          className="group relative flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-[#F5C842] to-[#E8933A] text-zinc-950 font-black text-xl shadow-[0_0_16px_rgba(245,200,66,0.3)] transition-transform duration-300 hover:scale-105"
          title="Vynaro 叙影 AI 视频解说"
        >
          V
          <span className="absolute -bottom-1 -right-1 flex h-3 w-3">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[#F5C842] opacity-75" />
            <span className="relative inline-flex rounded-full h-3 w-3 bg-[#F5C842]" />
          </span>
        </Link>

        <div className="h-[1px] w-8 bg-[#2A2A2F]" />

        {/* 2. 主功能导航 */}
        <nav className="flex flex-col space-y-1.5 w-full px-2" role="navigation">
          {TOP_NAV_ITEMS.map((item) => {
            const active =
              item.to === "/"
                ? currentPath === "/"
                : currentPath === item.to || currentPath.startsWith(item.to + "/");

            return (
              <Link
                key={`${item.to}-${item.hint}`}
                to={item.to}
                title={`${t(item.key, locale)} (${item.hint})`}
                id={`sidebar-nav-${item.hint.toLowerCase()}`}
                className={`group relative flex flex-col items-center justify-center rounded-xl py-2 px-1 text-decoration-none transition-all duration-200 ${
                  active
                    ? "bg-[#F5C842]/15 border border-[#F5C842]/30 text-[#F5C842] shadow-[0_0_12px_rgba(245,200,66,0.15)]"
                    : "border border-transparent text-zinc-400 hover:bg-[#1E1E22] hover:border-[#2A2A2F] hover:text-zinc-200"
                }`}
                aria-current={active ? "page" : undefined}
              >
                {/* 激活态金线指针 */}
                {active && (
                  <span className="absolute -left-2 top-1/2 -translate-y-1/2 h-5 w-1 rounded-r-full bg-[#F5C842] shadow-[0_0_8px_#F5C842]" />
                )}

                <span className="text-lg leading-none transition-transform duration-200 group-hover:scale-110">
                  {item.icon}
                </span>

                <span
                  className={`mt-1 text-[9px] font-medium tracking-tight ${
                    active ? "text-[#F5C842] font-semibold" : "text-zinc-500 group-hover:text-zinc-300"
                  }`}
                >
                  {item.hint}
                </span>

                {/* Badge 提示 */}
                {item.badge && !active && (
                  <span className="absolute -top-1 -right-1 flex h-2 w-2 rounded-full bg-[#F5C842]" />
                )}
              </Link>
            );
          })}
        </nav>
      </div>

      {/* 3. 底部系统导航 & 用户 Profile */}
      <div className="flex flex-col items-center space-y-2 w-full px-2">
        <div className="h-[1px] w-8 bg-[#2A2A2F]" />

        {BOTTOM_NAV_ITEMS.map((item) => {
          const active = currentPath.startsWith(item.to);
          return (
            <Link
              key={item.to}
              to={item.to}
              title={t(item.key, locale)}
              id={`sidebar-nav-${item.hint.toLowerCase()}`}
              className={`group relative flex flex-col items-center justify-center w-full rounded-xl py-2 px-1 text-decoration-none transition-all duration-200 ${
                active
                  ? "bg-[#F5C842]/15 border border-[#F5C842]/30 text-[#F5C842]"
                  : "border border-transparent text-zinc-400 hover:bg-[#1E1E22] hover:text-zinc-200"
              }`}
            >
              <span className="text-lg leading-none transition-transform duration-200 group-hover:scale-110">
                {item.icon}
              </span>
              <span className="mt-1 text-[9px] text-zinc-500 font-medium group-hover:text-zinc-300">
                {item.hint}
              </span>
            </Link>
          );
        })}

        {/* User Profile Avatar Button */}
        <button
          type="button"
          onClick={() => setShowProfileModal(!showProfileModal)}
          className="group relative flex h-9 w-9 items-center justify-center rounded-full border border-zinc-700 bg-[#161619] text-xs font-bold text-amber-300 shadow-md transition-all duration-200 hover:border-[#F5C842] hover:shadow-[0_0_12px_rgba(245,200,66,0.3)]"
          title="Vynaro Workspace Profile"
        >
          👤
        </button>

        {/* Profile Quick Popup */}
        {showProfileModal && (
          <div className="absolute left-16 bottom-3 z-50 w-56 rounded-2xl border border-zinc-800 bg-[#161619] p-4 shadow-2xl backdrop-blur-xl animate-in fade-in zoom-in-95 duration-150">
            <div className="flex items-center gap-3 border-b border-zinc-800 pb-3">
              <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-[#F5C842] text-zinc-950 font-black text-sm">
                V
              </div>
              <div>
                <div className="text-xs font-semibold text-zinc-100">Vynaro Creator</div>
                <div className="text-[10px] font-mono text-emerald-400">● Local Pro Active</div>
              </div>
            </div>
            <div className="mt-3 space-y-1.5 text-xs text-zinc-400">
              <div className="flex justify-between py-1">
                <span>Version:</span>
                <span className="font-mono text-zinc-200">v2.5.0</span>
              </div>
              <div className="flex justify-between py-1">
                <span>Backend:</span>
                <span className="font-mono text-amber-300">Tauri 2 + Rust</span>
              </div>
            </div>
          </div>
        )}
      </div>
    </aside>
  );
}
