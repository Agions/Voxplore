/**
 * splicr v1.0.0 · 电影调光室左侧导航栏 (完美响应多主题切换)
 * 采用 useNavigate 与 useRouterState 确保点击 100% 页面即时响应与高亮
 */

import { useNavigate, useRouterState } from "@tanstack/react-router";
import { useSettingsStore } from "@stores/settings-store";
import { t } from "@lib/i18n";

interface NavItem {
  to: "/" | "/production" | "/assets" | "/settings" | "/help";
  key: string;
  icon: string;
  hint: string;
  badge?: string;
}

const TOP_NAV_ITEMS: NavItem[] = [
  { to: "/",          key: "nav.home",       icon: "🏠", hint: "首页" },
  { to: "/production",key: "nav.production", icon: "🎬", hint: "AI 工作台", badge: "Agent" },
  { to: "/assets",    key: "nav.assets",     icon: "📁", hint: "资产库" },
];

const BOTTOM_NAV_ITEMS: NavItem[] = [
  { to: "/settings", key: "nav.settings",   icon: "⚙️", hint: "设置" },
  { to: "/help",     key: "nav.help",       icon: "❓", hint: "帮助" },
];

interface SidebarProps {
  currentPath: string;
}

export function Sidebar({ currentPath }: SidebarProps) {
  const locale = useSettingsStore((s) => s.locale);
  const navigate = useNavigate();
  const routerState = useRouterState();
  const activePath = routerState.location.pathname || currentPath;

  return (
    <aside
      className="flex w-16 flex-col items-center justify-between border-r border-[var(--color-border)] bg-[var(--color-bg)] py-3 flex-shrink-0 z-30 select-none transition-colors duration-200"
      aria-label="splicr 主导航"
    >
      {/* 1. 顶部 Brand Logo */}
      <div className="flex flex-col items-center space-y-4 w-full">
        <button
          type="button"
          onClick={() => void navigate({ to: "/" })}
          className="group relative flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-[#F5C842] to-[#E8933A] text-zinc-950 font-black text-xl shadow-[0_0_16px_rgba(245,200,66,0.3)] transition-transform duration-300 hover:scale-105"
          title="splicr 叙影 AI 视频解说"
        >
          S
          <span className="absolute -bottom-1 -right-1 flex h-3 w-3">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[#F5C842] opacity-75" />
            <span className="relative inline-flex rounded-full h-3 w-3 bg-[#F5C842]" />
          </span>
        </button>

        <div className="h-[1px] w-8 bg-[var(--color-border)]" />

        {/* 2. 主功能导航 */}
        <nav className="flex flex-col space-y-1.5 w-full px-2" role="navigation">
          {TOP_NAV_ITEMS.map((item) => {
            const active =
              item.to === "/"
                ? activePath === "/"
                : activePath === item.to || activePath.startsWith(item.to + "/");

            return (
              <button
                key={item.to}
                type="button"
                onClick={() => void navigate({ to: item.to })}
                title={`${t(item.key, locale)} (${item.hint})`}
                id={`sidebar-nav-${item.hint.toLowerCase()}`}
                className={`group relative flex flex-col items-center justify-center rounded-xl py-2.5 px-1 cursor-pointer transition-all duration-200 ${
                  active
                    ? "bg-[var(--color-gold-muted)] border border-[var(--color-gold)]/40 text-[var(--color-gold)] shadow-[0_0_12px_var(--color-gold-glow)] font-bold"
                    : "border border-transparent text-[var(--color-text-secondary)] hover:bg-[var(--color-surface-elevated)] hover:border-[var(--color-border)] hover:text-[var(--color-text-primary)]"
                }`}
                aria-current={active ? "page" : undefined}
              >
                {/* 激活态金线指针 */}
                {active && (
                  <span className="absolute -left-2 top-1/2 -translate-y-1/2 h-5 w-1 rounded-r-full bg-[var(--color-gold)] shadow-[0_0_8px_var(--color-gold-glow)]" />
                )}

                <span className="text-xl leading-none transition-transform duration-200 group-hover:scale-110">
                  {item.icon}
                </span>

                <span
                  className={`mt-1 text-[10px] tracking-tight ${
                    active ? "text-[var(--color-gold)] font-bold" : "text-[var(--color-text-secondary)] group-hover:text-[var(--color-text-primary)]"
                  }`}
                >
                  {item.hint}
                </span>

                {/* Badge 提示 */}
                {item.badge && !active && (
                  <span className="absolute -top-1 -right-1 flex h-2 w-2 rounded-full bg-[var(--color-gold)]" />
                )}
              </button>
            );
          })}
        </nav>
      </div>

      {/* 3. 底部系统导航 */}
      <div className="flex flex-col items-center space-y-2 w-full px-2">
        <div className="h-[1px] w-8 bg-[var(--color-border)]" />

        {BOTTOM_NAV_ITEMS.map((item) => {
          const active = activePath.startsWith(item.to);
          return (
            <button
              key={item.to}
              type="button"
              onClick={() => void navigate({ to: item.to })}
              title={t(item.key, locale)}
              id={`sidebar-nav-${item.hint.toLowerCase()}`}
              className={`group relative flex flex-col items-center justify-center w-full rounded-xl py-2 px-1 cursor-pointer transition-all duration-200 ${
                active
                  ? "bg-[var(--color-gold-muted)] border border-[var(--color-gold)]/40 text-[var(--color-gold)]"
                  : "border border-transparent text-[var(--color-text-secondary)] hover:bg-[var(--color-surface-elevated)] hover:text-[var(--color-text-primary)]"
              }`}
            >
              <span className="text-lg leading-none transition-transform duration-200 group-hover:scale-110">
                {item.icon}
              </span>
              <span className="mt-1 text-[10px] text-[var(--color-text-secondary)] font-medium group-hover:text-[var(--color-text-primary)]">
                {item.hint}
              </span>
            </button>
          );
        })}
      </div>
    </aside>
  );
}
