/**
 * Vynaro v1.0.0 · 应用顶栏 — 电影调光室主题
 * - Logo（钢笔+播放键图标）+ 品牌名 + 版本
 * - 项目名称选择器（居中）
 * - Tauri 连接状态 + 设置入口
 * - 所有颜色使用 CSS 变量，自动响应主题切换
 */

import { Link } from "@tanstack/react-router";
import { useTauriQuery } from "@hooks/useTauriQuery";
import { useUiStore } from "@stores/ui-store";
import { useSettingsStore } from "@stores/settings-store";
import { themeIpc } from "@ipc/commands";
import { t } from "@lib/i18n";
import { Toaster, toast } from "sonner";
import { useThemeStore } from "@stores/theme-store";

// Vynaro Logo 图标 SVG（钢笔笔尖 + 播放三角，内联）
function VynaroIcon({ size = 28 }: { size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 32 32"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-label="Vynaro Logo"
    >
      <defs>
        <linearGradient id="gold-grad" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="var(--color-gold)" />
          <stop offset="100%" stopColor="var(--color-amber)" />
        </linearGradient>
        <filter id="glow">
          <feGaussianBlur stdDeviation="1" result="blur" />
          <feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge>
        </filter>
      </defs>
      {/* 钢笔笔尖 */}
      <path
        d="M6 16 L13 9 L16 12 L11 20 Z"
        fill="url(#gold-grad)"
        filter="url(#glow)"
        opacity="0.9"
      />
      <circle cx="10" cy="16" r="1.2" fill="var(--color-bg)" />
      {/* 播放三角 */}
      <path
        d="M14 10 L26 16 L14 22 Z"
        fill="url(#gold-grad)"
        filter="url(#glow)"
      />
    </svg>
  );
}

export function TopBar() {
  const { data: version, isError } = useTauriQuery({
    command: "app_version",
    queryKeyPrefix: "topbar-version",
    args: {},
  });
  const openPalette = useUiStore((s) => s.openCommandPalette);
  const { locale, setLocale } = useSettingsStore();
  const connected = !isError && Boolean(version);
  const theme = useThemeStore((s) => s.theme);

  return (
    <header
      style={{
        display: "flex",
        height: "48px",
        alignItems: "center",
        justifyContent: "space-between",
        background: "var(--topbar-bg, rgba(13,13,15,0.95))",
        borderBottom: "1px solid var(--color-border)",
        padding: "0 16px",
        backdropFilter: "blur(12px)",
        WebkitAppRegion: "drag" as never,
        flexShrink: 0,
        zIndex: 100,
      } as React.CSSProperties}
    >
      {/* 左侧：Logo + 品牌名 */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: "10px",
          WebkitAppRegion: "no-drag",
        } as React.CSSProperties}
      >
        <div
          style={{
            width: 34,
            height: 34,
            borderRadius: 8,
            background: "var(--color-surface)",
            border: "1px solid var(--color-border)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            boxShadow: "0 0 12px var(--color-gold-glow)",
          }}
        >
          <VynaroIcon size={22} />
        </div>
        <div style={{ lineHeight: 1.2 }}>
          <div
            style={{
              fontSize: 16,
              fontWeight: 700,
              color: "var(--color-gold)",
              letterSpacing: "0.02em",
            }}
          >
            Vynaro
          </div>
          <div
            style={{
              fontSize: 10,
              color: "var(--color-text-muted)",
              letterSpacing: "0.12em",
              textTransform: "uppercase",
            }}
          >
            叙影 · v{version ?? "2.5.0"}
          </div>
        </div>
      </div>

      {/* 右侧：操作区 */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: "8px",
          WebkitAppRegion: "no-drag",
        } as React.CSSProperties}
      >
        {/* 搜索命令 */}
        <button
          type="button"
          id="topbar-cmd-palette"
          onClick={() => openPalette()}
          style={{
            display: "flex",
            alignItems: "center",
            gap: "6px",
            borderRadius: "8px",
            border: "1px solid var(--color-border)",
            background: "var(--color-surface)",
            padding: "5px 12px",
            fontSize: "12px",
            color: "var(--color-text-muted)",
            cursor: "pointer",
            transition: "all 150ms ease",
          }}
          onMouseEnter={(e) => {
            (e.currentTarget as HTMLButtonElement).style.borderColor = "var(--color-gold)";
            (e.currentTarget as HTMLButtonElement).style.color = "var(--color-gold)";
          }}
          onMouseLeave={(e) => {
            (e.currentTarget as HTMLButtonElement).style.borderColor = "var(--color-border)";
            (e.currentTarget as HTMLButtonElement).style.color = "var(--color-text-muted)";
          }}
          title={t("topbar.search_title", locale)}
        >
          <span>🔍</span>
          <span>{t("topbar.search_placeholder", locale)}</span>
          <kbd
            style={{
              marginLeft: 4,
              background: "var(--color-bg)",
              border: "1px solid var(--color-border)",
              borderRadius: 4,
              padding: "1px 5px",
              fontFamily: "monospace",
              fontSize: 10,
              color: "var(--color-text-muted)",
            }}
          >
            ⌘K
          </kbd>
        </button>

        {/* 语言切换按钮 (中/英) */}
        <button
          type="button"
          onClick={async () => {
            const nextLoc = locale === "en-US" ? "zh-CN" : "en-US";
            setLocale(nextLoc);
            try {
              await themeIpc.setLocale(nextLoc);
            } catch {
              // fallback
            }
            toast.success(nextLoc === "en-US" ? "Language: English" : "语言：简体中文");
          }}
          title="切换中英文 (Toggle Language)"
          style={{
            display: "flex",
            alignItems: "center",
            gap: "4px",
            borderRadius: "8px",
            border: "1px solid var(--color-border)",
            background: "var(--color-surface)",
            padding: "5px 10px",
            fontSize: "12px",
            color: "var(--color-text-primary)",
            cursor: "pointer",
            fontWeight: 600,
          }}
        >
          <span>{locale === "en-US" ? "🇺🇸 EN" : "🇨🇳 中"}</span>
        </button>

        {/* 后端连接状态 */}
        <div
          id="topbar-connection-status"
          style={{
            display: "flex",
            alignItems: "center",
            gap: "6px",
            borderRadius: "999px",
            border: connected
              ? "1px solid rgba(74,222,128,0.25)"
              : "1px solid rgba(248,113,113,0.25)",
            background: connected
              ? "rgba(74,222,128,0.08)"
              : "rgba(248,113,113,0.08)",
            padding: "4px 10px",
            fontSize: "11px",
            color: connected ? "#4ADE80" : "#F87171",
          }}
        >
          <span
            style={{
              width: 6,
              height: 6,
              borderRadius: "50%",
              background: connected ? "#4ADE80" : "#F87171",
              boxShadow: connected
                ? "0 0 6px rgba(74,222,128,0.6)"
                : "0 0 6px rgba(248,113,113,0.6)",
            }}
          />
          {connected ? t("topbar.connected", locale) : t("topbar.disconnected", locale)}
        </div>

        {/* 设置按钮 */}
        <Link
          to="/settings"
          id="topbar-settings"
          style={{
            width: 32,
            height: 32,
            borderRadius: 8,
            border: "1px solid var(--color-border)",
            background: "var(--color-surface)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            cursor: "pointer",
            fontSize: 15,
            transition: "all 150ms ease",
            color: "var(--color-text-muted)",
            textDecoration: "none",
          }}
          onMouseEnter={(e) => {
            (e.currentTarget as HTMLAnchorElement).style.borderColor = "var(--color-gold)";
            (e.currentTarget as HTMLAnchorElement).style.color = "var(--color-gold)";
          }}
          onMouseLeave={(e) => {
            (e.currentTarget as HTMLAnchorElement).style.borderColor = "var(--color-border)";
            (e.currentTarget as HTMLAnchorElement).style.color = "var(--color-text-muted)";
          }}
          title={t("nav.settings", locale)}
        >
          ⚙️
        </Link>
      </div>

      <Toaster
        theme={theme === "light" ? "light" : "dark"}
        position="bottom-center"
        toastOptions={{
          duration: 7000,
          classNames: {
            toast:
              "!bg-[var(--color-surface)] !text-[var(--color-text-primary)] !border !border-[var(--color-gold)] !rounded-2xl !px-5 !py-3.5 !shadow-[0_8px_32px_var(--color-gold-glow)] !backdrop-blur-xl !text-xs !font-semibold !mb-4",
            title: "!text-xs !font-bold !text-[var(--color-text-primary)]",
            description: "!text-[11px] !text-[var(--color-text-secondary)]",
          },
        }}
      />
    </header>
  );
}
