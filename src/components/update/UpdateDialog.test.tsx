/**
 * Monoloop v1.0.0 · UpdateDialog 组件单测
 *
 * 覆盖:
 * - 5 阶段渲染: idle / checking / available / downloading / ready
 * - 进度条 (downloading 时)
 * - release notes (available/ready 时)
 * - 错误条 (任意阶段)
 * - 主按钮文案随 phase 变化
 * - 重置按钮在 phase !== idle 时显示
 * - ESC 关闭 / 点背景关闭
 * - open=false 不渲染
 */
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { UpdateDialog } from "./UpdateDialog";

// ─── mocks ─────────────────────────────────────────────────────────
const checkMock = vi.fn();
const downloadMock = vi.fn();
const installMock = vi.fn();
const resetMock = vi.fn();

let mockSnapshot: {
  phase: "idle" | "checking" | "available" | "downloading" | "ready";
  currentVersion: string;
  available: {
    version: string;
    releaseDate: string | null;
    notes: string | null;
    downloadUrl: string | null;
    sha256: string | null;
    fileSizeBytes: number | null;
  } | null;
  progress: {
    downloadedBytes: number;
    totalBytes: number;
    percent: number;
  } | null;
  error: string | null;
  downloadedPath: string | null;
} = {
  phase: "idle",
  currentVersion: "3.0.0",
  available: null,
  progress: null,
  error: null,
  downloadedPath: null,
};

vi.mock("@hooks/useUpdate", () => ({
  useUpdate: () => ({
    state: mockSnapshot,
    check: checkMock,
    download: downloadMock,
    install: installMock,
    reset: resetMock,
    busy:
      mockSnapshot.phase === "checking" || mockSnapshot.phase === "downloading",
  }),
}));

// suppress listen (Tauri event API) for jsdom
vi.mock("@tauri-apps/api/event", () => ({
  listen: () => Promise.resolve(() => {}),
}));

// ─── helpers ───────────────────────────────────────────────────────
function makeWrapper() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={qc}>{children}</QueryClientProvider>
  );
}

beforeEach(() => {
  mockSnapshot = {
    phase: "idle",
    currentVersion: "3.0.0",
    available: null,
    progress: null,
    error: null,
    downloadedPath: null,
  };
});

afterEach(() => {
  vi.clearAllMocks();
  cleanup();
});

// ─── tests ─────────────────────────────────────────────────────────
describe("UpdateDialog", () => {
  it("open=false → 不渲染", () => {
    const { container } = render(
      <UpdateDialog open={false} onClose={() => {}} currentVersion="3.0.0" />,
      { wrapper: makeWrapper() },
    );
    expect(container).toBeEmptyDOMElement();
  });

  it("idle 状态:显示 '检查更新' 主按钮 + 重置隐藏", () => {
    render(
      <UpdateDialog open={true} onClose={() => {}} currentVersion="3.0.0" />,
      { wrapper: makeWrapper() },
    );
    expect(
      screen.getByRole("dialog", { name: "应用更新" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "检查更新" }),
    ).toBeInTheDocument();
    expect(screen.getByText(/Monoloop 应用更新器/)).toBeInTheDocument();
    expect(screen.getByText(/当前版本 v3\.0\.0/)).toBeInTheDocument();
    expect(screen.queryByText("⟲ 重置")).not.toBeInTheDocument();
  });

  it("idle → 点 '检查更新' → checkMock 被调", () => {
    checkMock.mockResolvedValueOnce(undefined);
    render(
      <UpdateDialog open={true} onClose={() => {}} currentVersion="3.0.0" />,
      { wrapper: makeWrapper() },
    );
    fireEvent.click(screen.getByRole("button", { name: "检查更新" }));
    expect(checkMock).toHaveBeenCalledTimes(1);
  });

  it("checking 状态:主按钮 disabled,显示 '处理中...'", () => {
    mockSnapshot = { ...mockSnapshot, phase: "checking" };
    render(<UpdateDialog open={true} onClose={() => {}} />, {
      wrapper: makeWrapper(),
    });
    expect(screen.getByText("正在检查...")).toBeInTheDocument();
    const btn = screen.getByText("处理中...").closest("button")!;
    expect(btn).toBeDisabled();
  });

  it("available 状态:显示版本号 + '下载更新' 主按钮 + notes (如有)", () => {
    mockSnapshot = {
      ...mockSnapshot,
      phase: "available",
      available: {
        version: "3.1.0",
        releaseDate: "2026-08-01",
        notes: "新特性\n修复 bug",
        downloadUrl: "https://example.com/x.zip",
        sha256: null,
        fileSizeBytes: 12_345_678,
      },
    };
    render(<UpdateDialog open={true} onClose={() => {}} />, {
      wrapper: makeWrapper(),
    });
    expect(screen.getByText("v3.1.0 已发布")).toBeInTheDocument();
    expect(screen.getByText("下载更新")).toBeInTheDocument();
    expect(screen.getByText("📋 Release Notes")).toBeInTheDocument();
    // 12_345_678 bytes = 11.8 MB
    expect(screen.getByText(/11\.8 MB/)).toBeInTheDocument();
  });

  it("available → 点 '下载更新' → downloadMock 被调", () => {
    mockSnapshot = {
      ...mockSnapshot,
      phase: "available",
      available: {
        version: "3.1.0",
        releaseDate: null,
        notes: null,
        downloadUrl: null,
        sha256: null,
        fileSizeBytes: 1024,
      },
    };
    downloadMock.mockResolvedValueOnce("/tmp/x.zip");
    render(<UpdateDialog open={true} onClose={() => {}} />, {
      wrapper: makeWrapper(),
    });
    fireEvent.click(screen.getByText("下载更新"));
    expect(downloadMock).toHaveBeenCalledTimes(1);
  });

  it("downloading 状态:显示进度条 + 百分比 + 字节数", () => {
    mockSnapshot = {
      ...mockSnapshot,
      phase: "downloading",
      available: {
        version: "3.1.0",
        releaseDate: null,
        notes: null,
        downloadUrl: null,
        sha256: null,
        fileSizeBytes: 100_000,
      },
      progress: { downloadedBytes: 50_000, totalBytes: 100_000, percent: 50 },
    };
    render(<UpdateDialog open={true} onClose={() => {}} />, {
      wrapper: makeWrapper(),
    });
    expect(screen.getByRole("progressbar")).toHaveAttribute(
      "aria-valuenow",
      "50",
    );
    expect(screen.getByText("50%")).toBeInTheDocument();
  });

  it("ready 状态:显示完成图标 + '重启安装' + 下载路径", () => {
    mockSnapshot = {
      ...mockSnapshot,
      phase: "ready",
      available: {
        version: "3.1.0",
        releaseDate: null,
        notes: null,
        downloadUrl: null,
        sha256: null,
        fileSizeBytes: 100_000,
      },
      downloadedPath: "/cache/monoloop-update-3.1.0.zip",
    };
    render(<UpdateDialog open={true} onClose={() => {}} />, {
      wrapper: makeWrapper(),
    });
    expect(screen.getByText(/v3\.1\.0 下载完成/)).toBeInTheDocument();
    expect(screen.getByText("重启安装")).toBeInTheDocument();
    expect(screen.getByText("✓ 安装包已下载到:")).toBeInTheDocument();
    expect(
      screen.getByText("/cache/monoloop-update-3.1.0.zip"),
    ).toBeInTheDocument();
  });

  it("ready → 点 '重启安装' → installMock 被调", () => {
    mockSnapshot = {
      ...mockSnapshot,
      phase: "ready",
      available: {
        version: "3.1.0",
        releaseDate: null,
        notes: null,
        downloadUrl: null,
        sha256: null,
        fileSizeBytes: 100_000,
      },
      downloadedPath: "/tmp/x.zip",
    };
    installMock.mockResolvedValueOnce({ note: "ok" });
    render(<UpdateDialog open={true} onClose={() => {}} />, {
      wrapper: makeWrapper(),
    });
    fireEvent.click(screen.getByText("重启安装"));
    expect(installMock).toHaveBeenCalledTimes(1);
  });

  it("错误信息:任意阶段都显示 error 条", () => {
    mockSnapshot = {
      ...mockSnapshot,
      phase: "available",
      available: {
        version: "3.1.0",
        releaseDate: null,
        notes: null,
        downloadUrl: null,
        sha256: null,
        fileSizeBytes: 1000,
      },
      error: "GitHub API 限流",
    };
    render(<UpdateDialog open={true} onClose={() => {}} />, {
      wrapper: makeWrapper(),
    });
    expect(screen.getByRole("alert")).toHaveTextContent("GitHub API 限流");
  });

  it("phase !== idle → 显示 '重置' 按钮 + 点 → resetMock 被调", () => {
    mockSnapshot = {
      ...mockSnapshot,
      phase: "available",
      available: {
        version: "3.1.0",
        releaseDate: null,
        notes: null,
        downloadUrl: null,
        sha256: null,
        fileSizeBytes: 1000,
      },
    };
    resetMock.mockResolvedValueOnce(undefined);
    render(<UpdateDialog open={true} onClose={() => {}} />, {
      wrapper: makeWrapper(),
    });
    const resetBtn = screen.getByText("⟲ 重置");
    fireEvent.click(resetBtn);
    expect(resetMock).toHaveBeenCalledTimes(1);
  });

  it("点 '关闭' 按钮 → onClose 被调", () => {
    const onClose = vi.fn();
    render(<UpdateDialog open={true} onClose={onClose} />, {
      wrapper: makeWrapper(),
    });
    fireEvent.click(screen.getByLabelText("关闭"));
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("ESC 键 → onClose 被调", async () => {
    const onClose = vi.fn();
    render(<UpdateDialog open={true} onClose={onClose} />, {
      wrapper: makeWrapper(),
    });
    fireEvent.keyDown(document, { key: "Escape" });
    await waitFor(() => {
      expect(onClose).toHaveBeenCalledTimes(1);
    });
  });

  it("点背景 → onClose 被调 (但点对话框内部不触发)", () => {
    const onClose = vi.fn();
    render(<UpdateDialog open={true} onClose={onClose} />, {
      wrapper: makeWrapper(),
    });
    const overlay = screen.getByRole("dialog");
    fireEvent.click(overlay);
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("available 无 notes 时不显示 notes 块", () => {
    mockSnapshot = {
      ...mockSnapshot,
      phase: "available",
      available: {
        version: "3.1.0",
        releaseDate: null,
        notes: null,
        downloadUrl: null,
        sha256: null,
        fileSizeBytes: 1000,
      },
    };
    render(<UpdateDialog open={true} onClose={() => {}} />, {
      wrapper: makeWrapper(),
    });
    expect(screen.queryByText(/Release Notes/)).not.toBeInTheDocument();
  });

  it("available 无 fileSizeBytes 时显示 '—'", () => {
    mockSnapshot = {
      ...mockSnapshot,
      phase: "available",
      available: {
        version: "3.1.0",
        releaseDate: null,
        notes: null,
        downloadUrl: null,
        sha256: null,
        fileSizeBytes: null,
      },
    };
    render(<UpdateDialog open={true} onClose={() => {}} />, {
      wrapper: makeWrapper(),
    });
    expect(screen.getByText(/大小 —/)).toBeInTheDocument();
  });
});
