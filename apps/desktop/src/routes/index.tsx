/**
 * Vynaro v2.5.0 · 欢迎页 (M3.2 视觉化重设计)
 *
 * 去文字堆砌:
 * - 顶部 Hero:渐变大字 + 1 句价值主张 + 2 个 CTA
 * - 中段工作流:视觉化 5 步流水线 (StepFlow 组件)
 * - 下段系统状态:紧凑贴纸式
 * - 不再展示"6 个页面链接"列表(已由 Sidebar 接管)
 * - 所有颜色使用 CSS 变量，自动响应主题切换
 */

import { Link, createFileRoute, useNavigate } from "@tanstack/react-router";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { StepFlow } from "@components/common/StepFlow";
import { BatchImportDialog } from "@components/dialogs/BatchImportDialog";
import { ThumbnailImage } from "@components/common/ThumbnailImage";
import {
  appIpc,
  pipelineIpc,
  projectIpc,
  type ProjectRecord,
} from "@ipc/commands";

export const Route = createFileRoute("/")({
  component: HomePage,
});

function HomePage() {
  return (
    <div className="mx-auto max-w-6xl space-y-10 px-8 py-10">
      <Hero />
      <WorkflowSection />
      <RecentProjectsStrip />
      <MediaOverview />
      <SystemStatusStrip />
    </div>
  );
}

// ── 工作流介绍（真实 IPC）─────────────────────────────────

const STEP_ICON: Record<string, string> = {
  intake: "📥",
  detect: "✂️",
  script: "🤖",
  voice: "🎙️",
  subtitle: "📝",
  compose: "🎬",
  export: "📤",
};

function WorkflowSection() {
  const { data: stepDefs, isLoading } = useQuery({
    queryKey: ["home-steps"],
    queryFn: pipelineIpc.stepDefs,
  });

  const steps = stepDefs && stepDefs.length > 0
    ? stepDefs.map((s) => ({
        id: s.id,
        label: s.label_zh,
        icon: STEP_ICON[s.id] ?? "📦",
        status: "pending" as const,
      }))
    : null;

  return (
    <section>
      <SectionHeader
        kicker="工作流"
        title="一段视频,多步成型"
        subtitle="从原始素材到可发布短片的全自动链路"
      />
      {isLoading ? (
        <div style={{ display: "flex", gap: "8px" }}>
          {[1, 2, 3, 4, 5].map((i) => (
            <div key={i} style={{
              flex: 1,
              height: "120px",
              borderRadius: "14px",
              background: "var(--color-surface)",
              border: "1px solid var(--color-border)",
              animation: "pulse 1.5s ease-in-out infinite",
            }} />
          ))}
        </div>
      ) : steps ? (
        <StepFlow steps={steps} activeIndex={-1} />
      ) : (
        <div style={{
          padding: "24px",
          borderRadius: "14px",
          border: "1px dashed var(--color-border)",
          textAlign: "center",
          color: "var(--color-text-muted)",
          fontSize: "13px",
        }}>
          流水线步骤加载失败，请检查后端连接
        </div>
      )}
    </section>
  );
}

// ── Hero ────────────────────────────────────────────────────────────

function Hero() {
  return (
    <section style={{
      position: "relative",
      overflow: "hidden",
      borderRadius: "24px",
      border: "1px solid var(--color-border)",
      background: "var(--color-surface)",
      padding: "40px",
      boxShadow: "var(--shadow-elevated)",
      transition: "background 200ms ease, border-color 200ms ease",
    }}>
      {/* Decorative glow */}
      <div style={{
        position: "absolute",
        top: "-60px",
        right: "-60px",
        width: "300px",
        height: "300px",
        borderRadius: "50%",
        background: "radial-gradient(circle, var(--color-gold-glow) 0%, transparent 70%)",
        pointerEvents: "none",
      }} />
      <div style={{ display: "grid", gridTemplateColumns: "1.2fr 1fr", gap: "32px", alignItems: "center", position: "relative" }}>
        <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
          <div style={{
            display: "inline-flex",
            alignItems: "center",
            gap: "8px",
            background: "var(--color-gold-muted)",
            border: "1px solid rgba(245,200,66,0.3)",
            borderRadius: "999px",
            padding: "4px 14px",
            width: "fit-content",
            fontSize: "12px",
            color: "var(--color-gold)",
            fontWeight: 600,
          }}>
            <span style={{ width: 6, height: 6, borderRadius: "50%", background: "var(--color-gold)", boxShadow: "0 0 6px var(--color-gold)" }} />
            Vynaro v2.5.0 · AI 第一人称解说引擎
          </div>

          <h1 style={{
            fontSize: "40px",
            fontWeight: 800,
            lineHeight: 1.15,
            color: "var(--color-text-primary)",
            letterSpacing: "-0.02em",
            margin: 0,
          }}>
            把影视与短剧交给 AI
            <br />
            <span style={{ background: "linear-gradient(135deg, var(--color-gold) 0%, var(--color-amber) 100%)", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>
              打造爆款第一人称解说
            </span>
          </h1>

          <p style={{ fontSize: "14px", color: "var(--color-text-secondary)", margin: 0, lineHeight: 1.6 }}>
            智能拆条 · AI 第一人称脚本 · 3秒人声克隆配音 · VAD动态字幕 · 画面节奏对齐 · 一键导出剪映草稿。
          </p>

          <div style={{ display: "flex", gap: "12px" }}>
            <Link to="/production" className="btn-primary" style={{ display: "inline-flex", alignItems: "center", gap: "8px", textDecoration: "none" }}>
              🎬 开始 7 步解说制作 <span>→</span>
            </Link>
            <Link to="/assets" className="btn-secondary" style={{ display: "inline-flex", alignItems: "center", gap: "8px", textDecoration: "none" }}>
              📦 管理项目资产
            </Link>
          </div>
        </div>

        <HeroVisual />
      </div>
    </section>
  );
}

function HeroVisual() {
  return (
    <div style={{ position: "relative", borderRadius: "16px", overflow: "hidden", border: "1px solid var(--color-border)" }}>
      <img src="/empty-state.jpg" alt="Vynaro Cinema Journey" style={{ width: "100%", height: "240px", objectFit: "cover" }} />
    </div>
  );
}

// ── Section header ─────────────────────────────────────────────────

function SectionHeader({
  kicker,
  title,
  subtitle,
}: {
  kicker: string;
  title: string;
  subtitle: string;
}) {
  return (
    <div className="mb-5 space-y-1">
      <div style={{ fontSize: "10px", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.2em", color: "var(--color-gold)" }}>
        {kicker}
      </div>
      <h2 style={{ fontSize: "20px", fontWeight: 600, letterSpacing: "-0.02em", color: "var(--color-text-primary)", margin: 0 }}>
        {title}
      </h2>
      <p style={{ fontSize: "14px", color: "var(--color-text-secondary)", margin: 0 }}>{subtitle}</p>
    </div>
  );
}

// ── Recent projects strip ──────────────────────────────────────────

function RecentProjectsStrip() {
  const { data: recent } = useQuery({
    queryKey: ["home-recent"],
    queryFn: () => projectIpc.listRecent(),
  });

  return (
    <section>
      <SectionHeader kicker="历史" title="最近的项目" subtitle="点击继续编辑" />
      {recent && recent.length > 0 ? (
        <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
          {recent.slice(0, 8).map((path, i) => (
            <button
              key={path}
              type="button"
              style={{
                display: "flex",
                flexDirection: "column",
                alignItems: "flex-start",
                gap: "8px",
                borderRadius: "12px",
                border: "1px solid var(--color-border)",
                background: "var(--color-surface)",
                padding: "16px",
                textAlign: "left",
                cursor: "pointer",
                transition: "all 150ms ease",
              }}
              onMouseEnter={(e) => {
                (e.currentTarget as HTMLButtonElement).style.borderColor = "var(--color-gold)";
                (e.currentTarget as HTMLButtonElement).style.background = "var(--color-surface-elevated)";
              }}
              onMouseLeave={(e) => {
                (e.currentTarget as HTMLButtonElement).style.borderColor = "var(--color-border)";
                (e.currentTarget as HTMLButtonElement).style.background = "var(--color-surface)";
              }}
            >
              <div style={{
                width: 40,
                height: 40,
                borderRadius: "10px",
                background: "var(--color-surface-elevated)",
                border: "1px solid var(--color-border)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontSize: "14px",
                fontWeight: 700,
                color: "var(--color-text-secondary)",
              }}>
                {i + 1}
              </div>
              <div style={{ fontSize: "12px", color: "var(--color-text-primary)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", maxWidth: "100%" }}>
                {path.split("/").pop()}
              </div>
              <div style={{ fontSize: "10px", color: "var(--color-text-muted)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", maxWidth: "100%" }}>{path}</div>
            </button>
          ))}
        </div>
      ) : (
        <EmptyRecent />
      )}
    </section>
  );
}

function EmptyRecent() {
  return (
    <div style={{
      display: "flex",
      alignItems: "center",
      justifyContent: "space-between",
      borderRadius: "16px",
      border: "1px dashed var(--color-border)",
      background: "var(--color-surface)",
      padding: "32px 24px",
    }}>
      <div>
        <div style={{ fontSize: "15px", fontWeight: 500, color: "var(--color-text-primary)" }}>还没有项目</div>
        <div style={{ fontSize: "13px", color: "var(--color-text-muted)", marginTop: "4px" }}>创建一个空白项目开始制作</div>
      </div>
      <Link
        to="/production"
        className="btn-primary"
        style={{ textDecoration: "none", display: "inline-flex", alignItems: "center" }}
      >
        新建项目
      </Link>
    </div>
  );
}

// ── System status strip (compact, 1 line) ──────────────────────────

function SystemStatusStrip() {
  const version = useQuery({
    queryKey: ["home-version"],
    queryFn: appIpc.version,
  });
  const stepDefs = useQuery({
    queryKey: ["home-steps"],
    queryFn: pipelineIpc.stepDefs,
  });
  const sysInfo = useQuery({
    queryKey: ["home-sys"],
    queryFn: appIpc.systemInfo,
  });

  const ok = !version.isError && !stepDefs.isError && !sysInfo.isError;
  const ffmpegOk = sysInfo.data?.ffmpegAvailable ?? false;

  return (
    <section style={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: "8px", fontSize: "11px" }}>
      <Pill tone={ok ? "ok" : "err"}>{ok ? "Tauri 已连接" : "后端断连"}</Pill>
      <Pill tone="info">v{version.data ?? "—"}</Pill>
      <Pill tone="info">{stepDefs.data?.length ?? 5} 步流水线</Pill>
      <Pill tone={ffmpegOk ? "ok" : "warn"}>
        ffmpeg {ffmpegOk ? "就绪" : "未安装"}
      </Pill>
      <Pill tone="neutral">Rust backend</Pill>
    </section>
  );
}

function Pill({
  tone,
  children,
}: {
  tone: "ok" | "err" | "warn" | "info" | "neutral";
  children: React.ReactNode;
}) {
  const map: Record<string, { border: string; bg: string; color: string }> = {
    ok:      { border: "rgba(74,222,128,0.3)",  bg: "rgba(74,222,128,0.08)",  color: "#4ADE80" },
    err:     { border: "rgba(248,113,113,0.3)", bg: "rgba(248,113,113,0.08)", color: "#F87171" },
    warn:    { border: "rgba(251,191,36,0.3)",  bg: "rgba(251,191,36,0.08)",  color: "#FBBF24" },
    info:    { border: "rgba(96,165,250,0.3)",  bg: "rgba(96,165,250,0.08)",  color: "#60A5FA" },
    neutral: { border: "var(--color-border)",   bg: "var(--color-surface)",   color: "var(--color-text-muted)" },
  };
  const s = map[tone] ?? map.neutral;
  return (
    <span style={{
      display: "inline-flex",
      alignItems: "center",
      gap: "6px",
      borderRadius: "999px",
      border: `1px solid ${s!.border}`,
      background: s!.bg,
      color: s!.color,
      padding: "2px 10px",
    }}>
      {children}
    </span>
  );
}

// ── 素材总览 (M3 后续: 当前项目素材) ─────────────────────────────

function MediaOverview() {
  const qc = useQueryClient();
  const navigate = useNavigate();
  const [openImport, setOpenImport] = useState(false);

  const currentProject =
    (qc.getQueryData(["current-project"]) as ProjectRecord | undefined) ?? null;
  const media = currentProject?.project.media_files ?? [];
  const preview = media.slice(0, 6);
  const remaining = Math.max(media.length - preview.length, 0);
  const projectName = currentProject?.project.name ?? null;

  return (
    <section>
      <div style={{ marginBottom: "20px", display: "flex", alignItems: "flex-end", justifyContent: "space-between" }}>
        <SectionHeader
          kicker="素材"
          title={projectName ? `当前项目 · ${projectName}` : "素材总览"}
          subtitle={
            projectName
              ? `共 ${media.length} 个素材`
              : "打开或新建一个项目后可在此预览"
          }
        />
        <div style={{ display: "flex", gap: "8px" }}>
          <button
            type="button"
            onClick={() => setOpenImport(true)}
            disabled={!currentProject}
            title={!currentProject ? "请先打开项目" : undefined}
            style={{
              borderRadius: "8px",
              border: "1px solid rgba(96,165,250,0.4)",
              background: "rgba(96,165,250,0.08)",
              padding: "6px 12px",
              fontSize: "12px",
              color: "#60A5FA",
              cursor: currentProject ? "pointer" : "not-allowed",
              opacity: currentProject ? 1 : 0.4,
              transition: "all 150ms ease",
            }}
          >
            📂 导入
          </button>
          <button
            type="button"
            onClick={() => void navigate({ to: "/assets" })}
            style={{
              borderRadius: "8px",
              border: "1px solid var(--color-border)",
              background: "var(--color-surface)",
              padding: "6px 12px",
              fontSize: "12px",
              color: "var(--color-text-secondary)",
              cursor: "pointer",
              transition: "all 150ms ease",
            }}
          >
            📦 进入素材页 →
          </button>
        </div>
      </div>

      {!currentProject ? (
        <div style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          borderRadius: "16px",
          border: "1px dashed var(--color-border)",
          background: "var(--color-surface)",
          padding: "32px 24px",
        }}>
          <div>
            <div style={{ fontSize: "14px", fontWeight: 500, color: "var(--color-text-primary)" }}>还没有打开的项目</div>
            <div style={{ fontSize: "12px", color: "var(--color-text-muted)", marginTop: "4px" }}>前往制作流水线页新建项目,或将素材直接导入现有项目</div>
          </div>
          <Link
            to="/production"
            className="btn-primary"
            style={{ textDecoration: "none", display: "inline-flex", alignItems: "center" }}
          >
            🎬 前往制作
          </Link>
        </div>
      ) : media.length === 0 ? (
        <div style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          borderRadius: "16px",
          border: "1px solid rgba(251,191,36,0.3)",
          background: "rgba(251,191,36,0.05)",
          padding: "32px 24px",
        }}>
          <div>
            <div style={{ fontSize: "14px", fontWeight: 500, color: "var(--color-text-primary)" }}>当前项目还没有素材</div>
            <div style={{ fontSize: "12px", color: "var(--color-text-muted)", marginTop: "4px" }}>导入 1 个或多个视频后即可启动流水线</div>
          </div>
          <button
            type="button"
            onClick={() => setOpenImport(true)}
            className="btn-primary"
          >
            📂 立即导入
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-6">
          {preview.map((m) => (
            <button
              type="button"
              key={m.path}
              onClick={() => void navigate({ to: "/assets" })}
              style={{
                display: "flex",
                flexDirection: "column",
                gap: "6px",
                borderRadius: "12px",
                border: "1px solid var(--color-border)",
                background: "var(--color-surface)",
                padding: "8px",
                textAlign: "left",
                cursor: "pointer",
                transition: "all 150ms ease",
              }}
              onMouseEnter={(e) => {
                (e.currentTarget as HTMLButtonElement).style.borderColor = "var(--color-gold)";
                (e.currentTarget as HTMLButtonElement).style.background = "var(--color-surface-elevated)";
              }}
              onMouseLeave={(e) => {
                (e.currentTarget as HTMLButtonElement).style.borderColor = "var(--color-border)";
                (e.currentTarget as HTMLButtonElement).style.background = "var(--color-surface)";
              }}
            >
              <ThumbnailImage source={m.path} kind="video" width={200} />
              <div style={{ padding: "0 4px 4px" }}>
                <div style={{ fontSize: "10px", fontFamily: "monospace", color: "var(--color-text-primary)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }} title={m.path}>
                  {m.path.split(/[/\\]/).pop() ?? m.path}
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "10px", color: "var(--color-text-muted)", marginTop: "2px" }}>
                  <span>{Math.round(m.duration_seconds)}s</span>
                  {m.resolution && (
                    <>
                      <span>·</span>
                      <span>{m.resolution}</span>
                    </>
                  )}
                </div>
              </div>
            </button>
          ))}
          {remaining > 0 && (
            <button
              type="button"
              onClick={() => void navigate({ to: "/assets" })}
              style={{
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                justifyContent: "center",
                borderRadius: "12px",
                border: "1px dashed var(--color-border)",
                background: "var(--color-surface)",
                fontSize: "12px",
                color: "var(--color-text-muted)",
                cursor: "pointer",
                transition: "all 150ms ease",
                aspectRatio: "16/9",
              }}
              onMouseEnter={(e) => {
                (e.currentTarget as HTMLButtonElement).style.borderColor = "var(--color-gold)";
                (e.currentTarget as HTMLButtonElement).style.color = "var(--color-gold)";
              }}
              onMouseLeave={(e) => {
                (e.currentTarget as HTMLButtonElement).style.borderColor = "var(--color-border)";
                (e.currentTarget as HTMLButtonElement).style.color = "var(--color-text-muted)";
              }}
            >
              <div style={{ fontSize: "24px" }}>＋</div>
              <div>还有 {remaining} 项</div>
            </button>
          )}
        </div>
      )}

      <BatchImportDialog
        open={openImport}
        onClose={() => setOpenImport(false)}
        onImported={() => {
          setOpenImport(false);
        }}
      />
    </section>
  );
}
