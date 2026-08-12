/**
 * Monoloop v1.0.0 · HelpPage 单测 (M4.5)
 *
 * 覆盖场景:
 * - 加载状态(loading)
 * - 加载完成后展示 6 张主题卡片
 * - 分类筛选:点 chip → 重新 query
 * - 搜索:输入文字 → 200ms debounce → help_search 触发
 * - 主题详情 modal:点卡片 → help_topic_get → 展示 content
 * - 错误状态:IPC 失败时显示错误信息
 */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { HelpPage } from "@components/help/HelpPage";
import type { HelpTopic } from "../ipc/types.gen";

// ─── invoke mock ─────────────────────────────────────────────────
const invokeMock = vi.fn();
vi.mock("@tauri-apps/api/core", () => ({
  invoke: (...args: unknown[]) => invokeMock(...args),
}));

// ─── fixture ─────────────────────────────────────────────────────
const SAMPLE_TOPICS: HelpTopic[] = [
  {
    id: "quick-start",
    category: "guide",
    title: "快速上手",
    summary: "5 分钟了解 5 步流水线",
    content: "# 快速上手\n\n正文内容",
    keywords: ["入门", "流水线"],
    related: ["ai-video"],
  },
  {
    id: "ai-video",
    category: "guide",
    title: "AI 视频生成指南",
    summary: "从脚本提示词到成片的最佳实践",
    content: "",
    keywords: ["LLM"],
    related: [],
  },
  {
    id: "cli-reference",
    category: "reference",
    title: "CLI 参考",
    summary: "命令行参数与配置文件字段",
    content: "",
    keywords: ["命令"],
    related: [],
  },
  {
    id: "python-api",
    category: "reference",
    title: "Python API",
    summary: "为高级用户提供的程序化控制",
    content: "",
    keywords: ["脚本"],
    related: [],
  },
  {
    id: "troubleshooting",
    category: "troubleshooting",
    title: "故障排查",
    summary: "常见错误与解决方案",
    content: "",
    keywords: ["错误"],
    related: [],
  },
  {
    id: "narration-spec",
    category: "reference",
    title: "叙述规范",
    summary: "第一人称脚本撰写语法说明",
    content: "",
    keywords: ["第一人称"],
    related: [],
  },
];

// ─── helpers ─────────────────────────────────────────────────────
function makeWrapper() {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={qc}>{children}</QueryClientProvider>
  );
}

// ─── lifecycle ───────────────────────────────────────────────────
beforeEach(() => {
  invokeMock.mockReset();
  invokeMock.mockImplementation((cmd: string) => {
    if (cmd === "app_version") return Promise.resolve("2.5.0");
    if (cmd === "help_topics") return Promise.resolve(SAMPLE_TOPICS);
    if (cmd === "help_search") return Promise.resolve([]);
    if (cmd === "help_topic_get") return Promise.resolve(SAMPLE_TOPICS[0]);
    return Promise.resolve(null);
  });
});

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

// ─── tests ───────────────────────────────────────────────────────
describe("HelpPage", () => {
  it("加载完成后展示 6 张主题卡片(默认全部分类)", async () => {
    render(<HelpPage />, { wrapper: makeWrapper() });

    await waitFor(() => {
      expect(screen.getByText("快速上手")).toBeInTheDocument();
    });

    expect(screen.getByText("AI 视频生成指南")).toBeInTheDocument();
    expect(screen.getByText("CLI 参考")).toBeInTheDocument();
    expect(screen.getByText("Python API")).toBeInTheDocument();
    // 6 个主题标题严格验证(快速上手、CLI 参考、Python API、叙述规范都是唯一)
    // 故障排查出现在 chip + 卡片,使用 getAllByText 计数
    expect(screen.getAllByText("故障排查").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("叙述规范")).toBeInTheDocument();
  });

  it("点 '教程' chip → 重新调用 help_topics({category:'guide'})", async () => {
    const user = userEvent.setup();
    render(<HelpPage />, { wrapper: makeWrapper() });

    await waitFor(() => screen.getByText("快速上手"));
    invokeMock.mockClear();

    await user.click(screen.getByRole("button", { name: "教程" }));

    await waitFor(() => {
      const calls = invokeMock.mock.calls.filter(([c]) => c === "help_topics");
      expect(calls.length).toBeGreaterThan(0);
      const last = calls[calls.length - 1];
      expect(last?.[1]).toEqual({ category: "guide" });
    });
  });

  it("输入搜索词 → 200ms 后触发 help_search", async () => {
    const user = userEvent.setup();
    render(<HelpPage />, { wrapper: makeWrapper() });

    await waitFor(() => screen.getByText("快速上手"));

    const input = screen.getByPlaceholderText(/搜索主题/);
    await user.type(input, "流水线");

    // 等待 debounce 200ms + 一帧
    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 300));
    });

    await waitFor(() => {
      const searchCalls = invokeMock.mock.calls.filter(
        ([c]) => c === "help_search",
      );
      expect(searchCalls.length).toBeGreaterThan(0);
      const last = searchCalls[searchCalls.length - 1];
      expect(last?.[1]).toEqual({ query: "流水线" });
    });
  });

  it("点击主题卡片 → 打开详情 modal + 调用 help_topic_get", async () => {
    const user = userEvent.setup();
    render(<HelpPage />, { wrapper: makeWrapper() });

    await waitFor(() => screen.getByText("快速上手"));

    invokeMock.mockClear();

    await user.click(screen.getByRole("button", { name: /快速上手/ }));

    await waitFor(() => {
      const getCalls = invokeMock.mock.calls.filter(
        ([c]) => c === "help_topic_get",
      );
      expect(getCalls.length).toBeGreaterThan(0);
      const last = getCalls[getCalls.length - 1];
      expect(last?.[1]).toEqual({ id: "quick-start" });
    });

    // modal 中显示 content
    await waitFor(() => {
      expect(screen.getByText(/# 快速上手/)).toBeInTheDocument();
    });
  });

  it("Esc 关闭详情 modal", async () => {
    const user = userEvent.setup();
    render(<HelpPage />, { wrapper: makeWrapper() });

    await waitFor(() => screen.getByText("快速上手"));
    await user.click(screen.getByRole("button", { name: /快速上手/ }));

    await waitFor(() =>
      expect(screen.getByText(/# 快速上手/)).toBeInTheDocument(),
    );

    await user.keyboard("{Escape}");

    await waitFor(() => {
      expect(screen.queryByText(/# 快速上手/)).not.toBeInTheDocument();
    });
  });

  it("帮助主题 IPC 失败时显示错误信息", async () => {
    invokeMock.mockImplementation((cmd: string) => {
      if (cmd === "app_version") return Promise.resolve("2.5.0");
      if (cmd === "help_topics") {
        return Promise.reject(new Error("IPC 失败: help backend down"));
      }
      return Promise.resolve(null);
    });

    render(<HelpPage />, { wrapper: makeWrapper() });

    await waitFor(() => {
      expect(screen.getByText(/加载失败/)).toBeInTheDocument();
    });
  });

  it("搜索无结果时显示空状态", async () => {
    invokeMock.mockImplementation((cmd: string) => {
      if (cmd === "app_version") return Promise.resolve("2.5.0");
      if (cmd === "help_topics") return Promise.resolve(SAMPLE_TOPICS);
      if (cmd === "help_search") return Promise.resolve([]);
      return Promise.resolve(null);
    });

    const user = userEvent.setup();
    render(<HelpPage />, { wrapper: makeWrapper() });

    await waitFor(() => screen.getByText("快速上手"));

    const input = screen.getByPlaceholderText(/搜索主题/);
    await user.type(input, "完全不存在");

    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 300));
    });

    await waitFor(() => {
      expect(screen.getByText(/没有匹配/)).toBeInTheDocument();
    });
  });

  it("静态 SHORTCUTS 仍然展示", () => {
    render(<HelpPage />, { wrapper: makeWrapper() });
    expect(screen.getByText("命令面板")).toBeInTheDocument();
    expect(screen.getByText("启动流水线")).toBeInTheDocument();
    expect(screen.getByText("取消流水线")).toBeInTheDocument();
  });
});
