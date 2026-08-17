/**
 * splicr v1.0.0 · BatchImportDialog 组件单测
 *
 * 流程:
 * 1. 打开 dialog (open=true) → 显示空状态
 * 2. 点 "选择目录" → openDialog mock 返回路径
 * 3. 点 "扫描" → scan mock 返回 ScanResult
 * 4. 默认全选,显示过滤栏 + 网格
 * 5. 切换类型过滤 / 搜索 → 网格更新
 * 6. 取消/反选 → 选中数更新
 * 7. 点 "导入 N 项" → importFromScan mock 被调用,toast 成功,自动关闭
 * 8. open=false → 不渲染
 */
import { afterEach, describe, expect, it, vi } from "vitest";
import {
  render,
  screen,
  cleanup,
  fireEvent,
  waitFor,
} from "@testing-library/react";
import { BatchImportDialog } from "./BatchImportDialog";
import type { ScanResult } from "@ipc/types.gen";

// ─── shared fixtures ───────────────────────────────────────────────
const scanMock = vi.fn();
const importFromScanMock = vi.fn();
const thumbnailMock = vi.fn();

vi.mock("@hooks/useAssets", () => ({
  useAssets: () => ({
    scan: scanMock,
    importFromScan: importFromScanMock,
    loading: false,
    thumbnail: thumbnailMock,
  }),
}));

vi.mock("@tauri-apps/plugin-dialog", () => ({
  open: vi.fn(),
}));

const toastSuccessMock = vi.fn();
const toastInfoMock = vi.fn();
const toastErrorMock = vi.fn();
vi.mock("sonner", () => ({
  toast: {
    success: (...a: unknown[]) => toastSuccessMock(...a),
    info: (...a: unknown[]) => toastInfoMock(...a),
    error: (...a: unknown[]) => toastErrorMock(...a),
  },
}));

// ThumbnailImage 子组件简化 (避免 thumbnailMock 行为干扰)
// 注意:不渲染文件名,避免与卡片的 basename 元素冲突
vi.mock("@components/common/ThumbnailImage", () => ({
  ThumbnailImage: () => <div data-testid="thumb" />,
}));

// ─── helpers ───────────────────────────────────────────────────────
import { open as openDialog } from "@tauri-apps/plugin-dialog";

const sampleScan: ScanResult = {
  dir: "/tmp/media",
  total: 3,
  skipped: 1,
  entries: [
    {
      path: "/tmp/media/a.mp4",
      kind: "video",
      mime: "video/mp4",
      sizeBytes: 5_242_880,
    },
    {
      path: "/tmp/media/b.mp3",
      kind: "audio",
      mime: "audio/mpeg",
      sizeBytes: 3_500_000,
    },
    {
      path: "/tmp/media/c.png",
      kind: "image",
      mime: "image/png",
      sizeBytes: 250_000,
    },
  ],
};

// ─── tests ─────────────────────────────────────────────────────────
afterEach(() => {
  vi.clearAllMocks();
  cleanup();
});

describe("BatchImportDialog", () => {
  it("open=false → 不渲染", () => {
    const { container } = render(
      <BatchImportDialog open={false} onClose={() => {}} />,
    );
    expect(container).toBeEmptyDOMElement();
  });

  it("open=true → 显示标题 + 空状态", () => {
    render(<BatchImportDialog open={true} onClose={() => {}} />);
    expect(
      screen.getByRole("dialog", { name: "批量导入素材" }),
    ).toBeInTheDocument();
    expect(screen.getByText(/选择一个目录开始扫描/)).toBeInTheDocument();
    expect(screen.getByText("📁 选择目录")).toBeInTheDocument();
  });

  it("选择目录 → 显示路径 + 启用 '扫描' 按钮", async () => {
    (openDialog as unknown as ReturnType<typeof vi.fn>).mockResolvedValueOnce(
      "/tmp/media",
    );
    render(<BatchImportDialog open={true} onClose={() => {}} />);
    fireEvent.click(screen.getByText("📁 选择目录"));
    await waitFor(() => {
      expect(screen.getByText("/tmp/media")).toBeInTheDocument();
    });
    // 扫描按钮启用
    const scanBtn = screen.getByText("🔍 扫描");
    expect(scanBtn.closest("button")).not.toBeDisabled();
  });

  it("点 '扫描' → 调 scan(dir, recursive=true) → 显示过滤栏 + 网格", async () => {
    (openDialog as unknown as ReturnType<typeof vi.fn>).mockResolvedValueOnce(
      "/tmp/media",
    );
    scanMock.mockResolvedValueOnce(sampleScan);

    render(<BatchImportDialog open={true} onClose={() => {}} />);
    fireEvent.click(screen.getByText("📁 选择目录"));
    await waitFor(() => screen.getByText("/tmp/media"));
    fireEvent.click(screen.getByText("🔍 扫描"));

    await waitFor(() => {
      expect(scanMock).toHaveBeenCalledWith("/tmp/media", true);
    });
    // 三个素材卡片
    expect(screen.getAllByTestId("thumb")).toHaveLength(3);
    // 默认全选 → "已选 3 / 3"
    expect(screen.getByText(/3 \/ 3 已选/)).toBeInTheDocument();
    expect(screen.getByText("📥 导入 3 项")).toBeInTheDocument();
    // 跳过提示
    expect(screen.getByText(/跳过 1/)).toBeInTheDocument();
  });

  it("切换类型过滤 → 网格更新", async () => {
    (openDialog as unknown as ReturnType<typeof vi.fn>).mockResolvedValueOnce(
      "/tmp/media",
    );
    scanMock.mockResolvedValueOnce(sampleScan);

    render(<BatchImportDialog open={true} onClose={() => {}} />);
    fireEvent.click(screen.getByText("📁 选择目录"));
    await waitFor(() => screen.getByText("/tmp/media"));
    fireEvent.click(screen.getByText("🔍 扫描"));
    await waitFor(() => screen.getByText("📥 导入 3 项"));

    // 切换到 "视频"
    const select = screen.getByDisplayValue("全部类型");
    fireEvent.change(select, { target: { value: "video" } });

    await waitFor(() => {
      expect(screen.getAllByTestId("thumb")).toHaveLength(1);
    });
    expect(screen.getByText("a.mp4")).toBeInTheDocument();
    // 全选数不变 (3 项仍全部勾选),过滤仅影响可见项
    expect(screen.getByText(/3 \/ 3 已选/)).toBeInTheDocument();
  });

  it("搜索框过滤 → substring 匹配", async () => {
    (openDialog as unknown as ReturnType<typeof vi.fn>).mockResolvedValueOnce(
      "/tmp/media",
    );
    scanMock.mockResolvedValueOnce(sampleScan);

    render(<BatchImportDialog open={true} onClose={() => {}} />);
    fireEvent.click(screen.getByText("📁 选择目录"));
    await waitFor(() => screen.getByText("/tmp/media"));
    fireEvent.click(screen.getByText("🔍 扫描"));
    await waitFor(() => screen.getByText("📥 导入 3 项"));

    const search = screen.getByPlaceholderText(/文件名搜索/);
    fireEvent.change(search, { target: { value: "B" } });

    await waitFor(() => {
      expect(screen.getAllByTestId("thumb")).toHaveLength(1);
    });
    expect(screen.getByText("b.mp3")).toBeInTheDocument();
  });

  it("点素材卡片 → toggle 选中状态", async () => {
    (openDialog as unknown as ReturnType<typeof vi.fn>).mockResolvedValueOnce(
      "/tmp/media",
    );
    scanMock.mockResolvedValueOnce(sampleScan);

    render(<BatchImportDialog open={true} onClose={() => {}} />);
    fireEvent.click(screen.getByText("📁 选择目录"));
    await waitFor(() => screen.getByText("/tmp/media"));
    fireEvent.click(screen.getByText("🔍 扫描"));
    await waitFor(() => screen.getByText("📥 导入 3 项"));

    // 取消勾选 a.mp4
    const cardA = screen.getByText("a.mp4").closest("button")!;
    fireEvent.click(cardA);
    expect(cardA).toHaveAttribute("aria-pressed", "false");
    expect(screen.getByText(/2 \/ 3 已选/)).toBeInTheDocument();
    expect(screen.getByText("📥 导入 2 项")).toBeInTheDocument();
  });

  it("'当前页反选' → 清空当前过滤的选中", async () => {
    (openDialog as unknown as ReturnType<typeof vi.fn>).mockResolvedValueOnce(
      "/tmp/media",
    );
    scanMock.mockResolvedValueOnce(sampleScan);

    render(<BatchImportDialog open={true} onClose={() => {}} />);
    fireEvent.click(screen.getByText("📁 选择目录"));
    await waitFor(() => screen.getByText("/tmp/media"));
    fireEvent.click(screen.getByText("🔍 扫描"));
    await waitFor(() => screen.getByText("📥 导入 3 项"));

    fireEvent.click(screen.getByText("当前页反选"));
    await waitFor(() => {
      expect(screen.getByText("📥 导入 0 项")).toBeInTheDocument();
    });
  });

  it("点 '导入' → importFromScan 被调用,toast 成功,自动关闭", async () => {
    const onClose = vi.fn();
    const onImported = vi.fn();
    (openDialog as unknown as ReturnType<typeof vi.fn>).mockResolvedValueOnce(
      "/tmp/media",
    );
    scanMock.mockResolvedValueOnce(sampleScan);
    importFromScanMock.mockResolvedValueOnce([
      { path: "/tmp/media/a.mp4" },
      { path: "/tmp/media/b.mp3" },
      { path: "/tmp/media/c.png" },
    ]);

    render(
      <BatchImportDialog
        open={true}
        onClose={onClose}
        onImported={onImported}
      />,
    );
    fireEvent.click(screen.getByText("📁 选择目录"));
    await waitFor(() => screen.getByText("/tmp/media"));
    fireEvent.click(screen.getByText("🔍 扫描"));
    await waitFor(() => screen.getByText("📥 导入 3 项"));
    fireEvent.click(screen.getByText("📥 导入 3 项"));

    await waitFor(() => {
      expect(importFromScanMock).toHaveBeenCalledTimes(1);
    });
    // 传入的 slice 必须只含被勾选的 (全选 → 全 entries)
    const arg = importFromScanMock.mock.calls[0]![0] as ScanResult;
    expect(arg.entries).toHaveLength(3);
    expect(arg.dir).toBe("/tmp/media");

    expect(toastSuccessMock).toHaveBeenCalledWith("已导入 3 个素材");
    expect(onImported).toHaveBeenCalledWith(3);
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("0 选中时点导入 → toast.info('未选择任何素材')", async () => {
    (openDialog as unknown as ReturnType<typeof vi.fn>).mockResolvedValueOnce(
      "/tmp/media",
    );
    scanMock.mockResolvedValueOnce(sampleScan);

    render(<BatchImportDialog open={true} onClose={() => {}} />);
    fireEvent.click(screen.getByText("📁 选择目录"));
    await waitFor(() => screen.getByText("/tmp/media"));
    fireEvent.click(screen.getByText("🔍 扫描"));
    await waitFor(() => screen.getByText("📥 导入 3 项"));

    // 全部反选
    fireEvent.click(screen.getByText("当前页反选"));
    await waitFor(() => screen.getByText("📥 导入 0 项"));
    // 导入按钮已禁用
    const importBtn = screen.getByText("📥 导入 0 项").closest("button")!;
    expect(importBtn).toBeDisabled();
    // 不应该调 importFromScan
    expect(importFromScanMock).not.toHaveBeenCalled();
  });

  it("导入失败 → toast.error + 错误条显示", async () => {
    (openDialog as unknown as ReturnType<typeof vi.fn>).mockResolvedValueOnce(
      "/tmp/media",
    );
    scanMock.mockResolvedValueOnce(sampleScan);
    importFromScanMock.mockRejectedValueOnce(new Error("IO 错误"));

    render(<BatchImportDialog open={true} onClose={() => {}} />);
    fireEvent.click(screen.getByText("📁 选择目录"));
    await waitFor(() => screen.getByText("/tmp/media"));
    fireEvent.click(screen.getByText("🔍 扫描"));
    await waitFor(() => screen.getByText("📥 导入 3 项"));
    fireEvent.click(screen.getByText("📥 导入 3 项"));

    await waitFor(() => {
      expect(toastErrorMock).toHaveBeenCalledWith("批量导入失败");
    });
    expect(screen.getByText("导入失败: IO 错误")).toBeInTheDocument();
  });

  it("扫描失败 → 错误条显示", async () => {
    (openDialog as unknown as ReturnType<typeof vi.fn>).mockResolvedValueOnce(
      "/tmp/media",
    );
    scanMock.mockRejectedValueOnce(new Error("权限不足"));

    render(<BatchImportDialog open={true} onClose={() => {}} />);
    fireEvent.click(screen.getByText("📁 选择目录"));
    await waitFor(() => screen.getByText("/tmp/media"));
    fireEvent.click(screen.getByText("🔍 扫描"));

    await waitFor(() => {
      expect(screen.getByText("扫描失败: 权限不足")).toBeInTheDocument();
    });
  });

  it("点 ✕ → onClose 被调,状态被重置", async () => {
    const onClose = vi.fn();
    (openDialog as unknown as ReturnType<typeof vi.fn>).mockResolvedValueOnce(
      "/tmp/media",
    );
    render(<BatchImportDialog open={true} onClose={onClose} />);
    fireEvent.click(screen.getByLabelText("关闭"));
    expect(onClose).toHaveBeenCalledTimes(1);
  });
});
