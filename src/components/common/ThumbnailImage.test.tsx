/**
 * Vynaro v2.5.0 · ThumbnailImage 组件单测
 *
 * 状态机:
 * - 挂载 → "loading" (显示 "生成缩略图...")
 * - thumbnail resolve → "ready" (显示 <img>)
 * - thumbnail reject → "error" (显示 "无法生成")
 * - source 变化 → 重置回 "loading"
 * - 卸载 (cancelled) → 不更新 state
 */
import { afterEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor, cleanup } from "@testing-library/react";
import { ThumbnailImage } from "./ThumbnailImage";

// ─── mocks ─────────────────────────────────────────────────────────
const thumbnailMock = vi.fn();
vi.mock("@hooks/useAssets", () => ({
  useAssets: () => ({
    thumbnail: thumbnailMock,
  }),
}));
vi.mock("@tauri-apps/api/core", () => ({
  convertFileSrc: (p: string) => `tauri://localhost/${p}`,
}));

// ─── tests ─────────────────────────────────────────────────────────
afterEach(() => {
  vi.clearAllMocks();
  cleanup();
});

describe("ThumbnailImage", () => {
  it("初始状态 = loading,显示 '生成缩略图...'", () => {
    thumbnailMock.mockReturnValue(new Promise(() => {})); // 永不 resolve
    render(<ThumbnailImage source="/video.mp4" kind="video" />);
    expect(screen.getByText("生成缩略图...")).toBeInTheDocument();
    expect(screen.getByText("video.mp4")).toBeInTheDocument();
    expect(screen.queryByRole("img")).not.toBeInTheDocument();
  });

  it("thumbnail resolve → 显示 <img>,aria-label=文件名", async () => {
    thumbnailMock.mockResolvedValue({ thumbnailPath: "/cache/abc.jpg" });
    render(<ThumbnailImage source="/video.mp4" kind="video" />);
    const img = await screen.findByRole("img");
    expect(img).toHaveAttribute("src", "tauri://localhost//cache/abc.jpg");
    expect(img).toHaveAttribute("alt", "video.mp4");
    await waitFor(() => {
      expect(screen.queryByText("生成缩略图...")).not.toBeInTheDocument();
    });
  });

  it("thumbnail reject → 显示 '无法生成'", async () => {
    thumbnailMock.mockRejectedValue(new Error("ffmpeg 失败"));
    render(<ThumbnailImage source="/broken.mp4" kind="video" />);
    await waitFor(() => {
      expect(screen.getByText("无法生成")).toBeInTheDocument();
    });
    expect(screen.queryByRole("img")).not.toBeInTheDocument();
  });

  it("kind=audio → 显示 🎵 占位符", () => {
    thumbnailMock.mockReturnValue(new Promise(() => {}));
    render(<ThumbnailImage source="/song.mp3" kind="audio" />);
    expect(screen.getByText("🎵")).toBeInTheDocument();
  });

  it("kind=image → 显示 🖼 占位符", () => {
    thumbnailMock.mockReturnValue(new Promise(() => {}));
    render(<ThumbnailImage source="/pic.png" kind="image" />);
    expect(screen.getByText("🖼")).toBeInTheDocument();
  });

  it("自定义 alt 优先于 basename", async () => {
    thumbnailMock.mockResolvedValue({ thumbnailPath: "/c.jpg" });
    render(<ThumbnailImage source="/long/path/clip.mp4" alt="我的素材" />);
    const img = await screen.findByRole("img");
    expect(img).toHaveAttribute("alt", "我的素材");
  });

  it("卸载时 cancelled=true → 不更新 state (防止内存泄漏)", async () => {
    let resolveFn: (v: { thumbnailPath: string }) => void = () => {};
    thumbnailMock.mockReturnValue(
      new Promise((r) => {
        resolveFn = r;
      }),
    );
    const { unmount } = render(<ThumbnailImage source="/v.mp4" />);
    // 卸载
    unmount();
    // 现在 resolve,此时组件已卸载,不应抛 "setState on unmounted" 警告
    resolveFn({ thumbnailPath: "/x.jpg" });
    // 等待微任务队列清空
    await new Promise((r) => setTimeout(r, 10));
    // 没断言错误就算通过 (此前的实现曾出现过 setState-on-unmount 警告)
  });

  it("source 变化 → 重置为 loading 状态", async () => {
    thumbnailMock.mockResolvedValue({ thumbnailPath: "/c1.jpg" });
    const { rerender } = render(<ThumbnailImage source="/a.mp4" />);
    await screen.findByRole("img");
    // 第二次调用:不 resolve,观察重置
    thumbnailMock.mockReturnValue(new Promise(() => {}));
    rerender(<ThumbnailImage source="/b.mp4" />);
    expect(screen.getByText("生成缩略图...")).toBeInTheDocument();
    expect(screen.getByText("b.mp4")).toBeInTheDocument();
  });
});
