/**
 * Vynaro v1.0.0 · VideoPlanPreview 组件单测
 *
 * 验证:
 * - 4 个策略按钮 (single / concat / batch / series) 全部渲染
 * - 默认策略 concat → invoke("video_build_plans", ...) 被调用
 * - 切换策略 → 重新调用 invoke 带新 strategy
 * - 成功时显示 OutputPlan 卡片(name + ordered_sources)
 * - IPC 错误时显示错误提示(VynaroError)
 */
import { afterEach, describe, expect, it, vi } from "vitest";
import {
  render,
  screen,
  cleanup,
  fireEvent,
  waitFor,
} from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { VideoPlanPreview } from "./VideoPlanPreview";
import type { OutputPlan } from "@ipc/types.gen";

// ── mock Tauri invoke ──────────────────────────────────────────────
const invokeMock = vi.fn();
vi.mock("@tauri-apps/api/core", () => ({
  invoke: (...args: unknown[]) => invokeMock(...args),
}));

// ── fixtures ───────────────────────────────────────────────────────
const SAMPLE_PLANS_CONCAT: OutputPlan[] = [
  {
    name: "vlog",
    ordered_sources: ["/abs/a.mp4", "/abs/b.mp4"],
    episode_number: null,
    episode_label: null,
    series_context: null,
  },
];

const SAMPLE_PLANS_BATCH: OutputPlan[] = [
  {
    name: "output-01",
    ordered_sources: ["/abs/a.mp4"],
    episode_number: null,
    episode_label: null,
    series_context: null,
  },
  {
    name: "output-02",
    ordered_sources: ["/abs/b.mp4"],
    episode_number: null,
    episode_label: null,
    series_context: null,
  },
];

const SAMPLE_PLANS_SERIES: OutputPlan[] = [
  {
    name: "EP01_intro",
    ordered_sources: ["/abs/a.mp4"],
    episode_number: 1,
    episode_label: "intro",
    series_context: "vynaro-demo",
  },
  {
    name: "EP02_body",
    ordered_sources: ["/abs/b.mp4"],
    episode_number: 2,
    episode_label: "body",
    series_context: "vynaro-demo",
  },
];

// ── helpers ────────────────────────────────────────────────────────
function makeWrapper() {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false, staleTime: 0 } },
  });
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
  };
}

function setup(mediaPaths: string[]) {
  const Wrapper = makeWrapper();
  return render(<VideoPlanPreview mediaPaths={mediaPaths} />, {
    wrapper: Wrapper,
  });
}

afterEach(() => {
  cleanup();
  invokeMock.mockReset();
});

// ── tests ──────────────────────────────────────────────────────────
describe("VideoPlanPreview", () => {
  it("渲染 4 个策略按钮(single/concat/batch/series)", () => {
    invokeMock.mockResolvedValueOnce(SAMPLE_PLANS_CONCAT);
    setup(["/abs/a.mp4", "/abs/b.mp4"]);

    expect(screen.getByRole("button", { name: /单文件/ })).toBeDefined();
    expect(screen.getByRole("button", { name: /拼接/ })).toBeDefined();
    expect(screen.getByRole("button", { name: /批处理/ })).toBeDefined();
    expect(screen.getByRole("button", { name: /系列/ })).toBeDefined();
  });

  it("默认 concat 策略 → 调用 video_build_plans 一次,展示 OutputPlan", async () => {
    invokeMock.mockResolvedValueOnce(SAMPLE_PLANS_CONCAT);
    setup(["/abs/a.mp4", "/abs/b.mp4"]);

    await waitFor(() => {
      expect(invokeMock).toHaveBeenCalledWith(
        "video_build_plans",
        expect.objectContaining({
          sources: ["/abs/a.mp4", "/abs/b.mp4"],
          strategy: "concat",
        }),
      );
    });

    const cards = await screen.findAllByTestId("video-plan-card");
    expect(cards).toHaveLength(1);
    expect(screen.getByText("vlog")).toBeDefined();
  });

  it("切换策略 → 重新调用 invoke 带新 strategy", async () => {
    invokeMock
      .mockResolvedValueOnce(SAMPLE_PLANS_CONCAT)
      .mockResolvedValueOnce(SAMPLE_PLANS_BATCH);
    setup(["/abs/a.mp4", "/abs/b.mp4"]);

    // 等待首次 concat 调用
    await waitFor(() => {
      expect(invokeMock).toHaveBeenCalledTimes(1);
    });

    // 切到 batch
    fireEvent.click(screen.getByRole("button", { name: /批处理/ }));

    await waitFor(() => {
      expect(invokeMock).toHaveBeenCalledTimes(2);
    });
    expect(invokeMock).toHaveBeenLastCalledWith(
      "video_build_plans",
      expect.objectContaining({ strategy: "batch" }),
    );

    // 切到 batch 后,OutputPlan 列表更新
    const cards = await screen.findAllByTestId("video-plan-card");
    expect(cards).toHaveLength(2);
    expect(screen.getByText("output-01")).toBeDefined();
    expect(screen.getByText("output-02")).toBeDefined();
  });

  it("series 策略展示 episode 编号 + series_context", async () => {
    invokeMock.mockImplementation((_cmd, args) =>
      args?.strategy === "series"
        ? Promise.resolve(SAMPLE_PLANS_SERIES)
        : Promise.resolve(SAMPLE_PLANS_CONCAT),
    );
    setup(["/abs/a.mp4", "/abs/b.mp4"]);

    // 等待首次 concat 调用
    await waitFor(() => {
      expect(invokeMock).toHaveBeenCalledTimes(1);
    });

    // 切到 series 并填写 series_context
    fireEvent.click(screen.getByRole("button", { name: /系列/ }));
    const seriesInput = await screen.findByPlaceholderText("例如：斗罗大陆第一季");
    fireEvent.change(seriesInput, { target: { value: "vynaro-demo" } });

    await waitFor(() => {
      expect(invokeMock).toHaveBeenCalledWith(
        "video_build_plans",
        expect.objectContaining({
          strategy: "series",
          options: expect.objectContaining({
            series_context: "vynaro-demo",
          }),
        }),
      );
    });

    const cards = await screen.findAllByTestId("video-plan-card");
    expect(cards).toHaveLength(2);
    expect(screen.getByText("EP01 · intro")).toBeDefined();
    expect(screen.getAllByText("vynaro-demo").length).toBeGreaterThan(0);
  });

  it("IPC 失败 → 显示 VynaroError 错误提示", async () => {
    invokeMock.mockRejectedValueOnce({
      kind: "video_plan_error",
      message: "SourceCountMismatch: single 策略要求 1 个源,实际 2 个",
    });
    setup(["/abs/a.mp4", "/abs/b.mp4"]);

    await waitFor(() => {
      expect(screen.getByText(/SourceCountMismatch/)).toBeDefined();
    });
  });
});
