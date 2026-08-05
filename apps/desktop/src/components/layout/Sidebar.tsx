/**
 * Vynaro v2.5.0 · 左侧图标导航栏（56px 窄版）
 * 电影调光室主题：所有颜色使用 CSS 变量，自动响应主题切换
 */

import { Link } from "@tanstack/react-router";
import { useSettingsStore } from "@stores/settings-store";
import { t } from "@lib/i18n";

const NAV_ITEMS = [
  { to: "/",          key: "nav.home",       icon: "🏠", hint: "Home" },
  { to: "/production",key: "nav.production", icon: "🎬", hint: "Pipeline", primary: true },
  { to: "/assets",    key: "nav.assets",     icon: "📁", hint: "Projects" },
  { to: "/settings",  key: "nav.settings",   icon: "⚙️", hint: "Settings" },
] as const;

interface SidebarProps {
  currentPath: string;
}

export function Sidebar({ currentPath }: SidebarProps) {
  const locale = useSettingsStore((s) => s.locale);
  return (
    <aside
      style={{
        width: "56px",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        background: "var(--color-bg)",
        borderRight: "1px solid var(--color-border)",
        paddingTop: "8px",
        paddingBottom: "8px",
        flexShrink: 0,
        gap: "4px",
        transition: "background 200ms ease, border-color 200ms ease",
      }}
      aria-label="主导航"
    >
      {/* 主导航项 */}
      <nav
        style={{ display: "flex", flexDirection: "column", gap: "4px", flex: 1, width: "100%" }}
        role="navigation"
      >
        {NAV_ITEMS.map((item) => {
          const active =
            item.to === "/"
              ? currentPath === "/"
              : currentPath.startsWith(item.to);

          return (
            <Link
              key={item.to}
              to={item.to}
              title={t(item.key, locale)}
              id={`sidebar-nav-${item.hint.toLowerCase()}`}
              style={{
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                justifyContent: "center",
                padding: "10px 4px",
                borderRadius: "10px",
                margin: "0 6px",
                textDecoration: "none",
                background: active ? "var(--color-gold-muted)" : "transparent",
                border: active ? "1px solid rgba(245,200,66,0.25)" : "1px solid transparent",
                transition: "all 150ms ease",
                position: "relative",
              }}
              onMouseEnter={(e) => {
                if (!active) {
                  (e.currentTarget as HTMLAnchorElement).style.background = "var(--color-surface-elevated)";
                  (e.currentTarget as HTMLAnchorElement).style.borderColor = "var(--color-border)";
                }
              }}
              onMouseLeave={(e) => {
                if (!active) {
                  (e.currentTarget as HTMLAnchorElement).style.background = "transparent";
                  (e.currentTarget as HTMLAnchorElement).style.borderColor = "transparent";
                }
              }}
              aria-current={active ? "page" : undefined}
            >
              {/* 激活态左边金色条 */}
              {active && (
                <span
                  style={{
                    position: "absolute",
                    left: "-6px",
                    top: "50%",
                    transform: "translateY(-50%)",
                    width: "3px",
                    height: "20px",
                    background: "var(--color-gold)",
                    borderRadius: "0 3px 3px 0",
                    boxShadow: "0 0 6px var(--color-gold-glow)",
                  }}
                />
              )}
              <span style={{ fontSize: "18px", lineHeight: 1 }}>{item.icon}</span>
              <span
                style={{
                  fontSize: "9px",
                  color: active ? "var(--color-gold)" : "var(--color-text-muted)",
                  marginTop: "4px",
                  letterSpacing: "0.04em",
                  fontWeight: active ? 600 : 400,
                  transition: "color 150ms ease",
                }}
              >
                {item.hint}
              </span>
            </Link>
          );
        })}
      </nav>

      {/* 底部分割线 + 版本 */}
      <div
        style={{
          width: "32px",
          height: "1px",
          background: "var(--color-border)",
          margin: "4px 0",
        }}
      />
      <div
        style={{
          fontSize: "9px",
          color: "var(--color-text-muted)",
          letterSpacing: "0.08em",
          textAlign: "center",
          lineHeight: 1.6,
        }}
        title="Vynaro v2.5.0"
      >
        v2.5
      </div>
    </aside>
  );
}
