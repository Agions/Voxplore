/**
 * Vynaro v2.5.0 · useProject hook 单测 (renderHook)
 *
 * 测试策略:
 * - mock @ipc/commands 中的 projectIpc / pipelineIpc
 * - mock useProjectStore 为可控版本(便于注入初始状态)
 * - 用 QueryClientProvider 包裹 renderHook(hook 内用到 useQueryClient)
 * - 覆盖:open / save / saveAs / close + 错误处理 + loading 状态
 */
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, renderHook, waitFor, act } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useProject } from "./useProject";
import type { Project, ProjectRecord } from "@ipc/types.gen";

// ─── mocks ─────────────────────────────────────────────────────────
const projectLoadMock = vi.fn();
const projectSaveMock = vi.fn();
const pipelineCancelMock = vi.fn();

vi.mock("../ipc/commands", () => ({
  projectIpc: {
    load: (...a: unknown[]) => projectLoadMock(...a),
    save: (...a: unknown[]) => projectSaveMock(...a),
  },
  pipelineIpc: {
    cancel: () => pipelineCancelMock(),
  },
}));

// useProjectStore 也 mock,这样可以在测试间重置
let storeState: {
  current: Project | null;
  currentPath: string | null;
  setCurrentRecord: ReturnType<typeof vi.fn>;
  setCurrent: ReturnType<typeof vi.fn>;
  setCurrentPath: ReturnType<typeof vi.fn>;
  clear: ReturnType<typeof vi.fn>;
};

vi.mock("../stores/project-store", () => ({
  useProjectStore: (selector: (s: typeof storeState) => unknown) =>
    selector(storeState),
}));

// ─── helpers ───────────────────────────────────────────────────────
const sampleProject: Project = {
  id: "test-uuid",
  name: "示例项目",
  created_at: "2026-01-01T00:00:00.000Z",
  updated_at: "2026-01-01T00:00:00.000Z",
  version: "1.0",
  settings: {
    resolution: "1920x1080",
    fps: 30,
    bitrate: "5000k",
    container: "mp4",
    codec: "h264",
    four_strategy: "single",
  },
  media_files: [],
  timeline: { tracks: [] },
  scripts: [],
  exports: [],
};

const sampleRecord: ProjectRecord = {
  path: "/tmp/test.vynaro.json",
  project: { ...sampleProject, name: "已加载项目" },
};

function makeWrapper() {
  const qc = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={qc}>{children}</QueryClientProvider>
  );
}

beforeEach(() => {
  storeState = {
    current: null,
    currentPath: null,
    setCurrentRecord: vi.fn((path: string, project: Project) => {
      storeState.current = project;
      storeState.currentPath = path;
    }),
    setCurrent: vi.fn((project: Project | null) => {
      storeState.current = project;
    }),
    setCurrentPath: vi.fn((path: string) => {
      storeState.currentPath = path;
    }),
    clear: vi.fn(() => {
      storeState.current = null;
      storeState.currentPath = null;
    }),
  };
});

afterEach(() => {
  vi.clearAllMocks();
  cleanup();
});

// ─── tests ─────────────────────────────────────────────────────────
describe("useProject", () => {
  describe("初始状态", () => {
    it("没有项目 → hasProject=false", () => {
      const { result } = renderHook(() => useProject(), {
        wrapper: makeWrapper(),
      });
      expect(result.current.project).toBeNull();
      expect(result.current.currentPath).toBeNull();
      expect(result.current.hasProject).toBe(false);
      expect(result.current.loading).toBe(false);
      expect(result.current.error).toBeNull();
    });
  });

  describe("open", () => {
    it("成功加载 → setCurrentRecord 被调,sync 到 query cache", async () => {
      projectLoadMock.mockResolvedValueOnce(sampleRecord);
      const { result } = renderHook(() => useProject(), {
        wrapper: makeWrapper(),
      });

      await act(async () => {
        await result.current.open("/tmp/test.vynaro.json");
      });

      expect(projectLoadMock).toHaveBeenCalledWith("/tmp/test.vynaro.json");
      expect(storeState.setCurrentRecord).toHaveBeenCalledWith(
        "/tmp/test.vynaro.json",
        sampleRecord.project,
      );
      await waitFor(() => {
        expect(result.current.loading).toBe(false);
      });
      expect(result.current.error).toBeNull();
    });

    it("加载失败 → error 被设,抛错", async () => {
      projectLoadMock.mockRejectedValueOnce(new Error("文件不存在"));
      const { result } = renderHook(() => useProject(), {
        wrapper: makeWrapper(),
      });

      let caught: unknown = null;
      await act(async () => {
        try {
          await result.current.open("/bad/path.json");
        } catch (e) {
          caught = e;
        }
      });

      expect((caught as Error).message).toBe("文件不存在");
      await waitFor(() => {
        expect(result.current.error).toBeInstanceOf(Error);
      });
      expect((result.current.error as Error).message).toBe("文件不存在");
    });

    it("加载期间 loading=true → 完成后 loading=false", async () => {
      let resolveFn: (v: ProjectRecord) => void = () => {};
      projectLoadMock.mockReturnValueOnce(
        new Promise((r) => {
          resolveFn = r;
        }),
      );
      const { result } = renderHook(() => useProject(), {
        wrapper: makeWrapper(),
      });

      // 触发 open 但不 await 内部 promise
      let openPromise!: Promise<void>;
      await act(async () => {
        openPromise = result.current.open("/tmp/x.json");
        // 让 setLoading(true) flush
        await Promise.resolve();
      });
      expect(result.current.loading).toBe(true);

      // resolve 后端 promise
      await act(async () => {
        resolveFn(sampleRecord);
        await openPromise;
      });
      expect(result.current.loading).toBe(false);
    });
  });

  describe("save", () => {
    it("没有 project → 抛 '没有打开的项目'", async () => {
      const { result } = renderHook(() => useProject(), {
        wrapper: makeWrapper(),
      });
      let caught: unknown = null;
      await act(async () => {
        try {
          await result.current.save();
        } catch (e) {
          caught = e;
        }
      });
      expect((caught as Error).message).toBe("没有打开的项目");
      await waitFor(() => {
        expect(result.current.error).toBeInstanceOf(Error);
      });
    });

    it("有 project 但没有 currentPath → 抛 '请改用 saveAs'", async () => {
      storeState.current = sampleProject;
      storeState.currentPath = null;
      const { result } = renderHook(() => useProject(), {
        wrapper: makeWrapper(),
      });
      let caught: unknown = null;
      await act(async () => {
        try {
          await result.current.save();
        } catch (e) {
          caught = e;
        }
      });
      expect((caught as Error).message).toMatch(/saveAs/);
    });

    it("正常 save → 写 updated_at 并同步 store", async () => {
      storeState.current = sampleProject;
      storeState.currentPath = "/tmp/test.vynaro.json";
      projectSaveMock.mockResolvedValueOnce(undefined);
      const { result } = renderHook(() => useProject(), {
        wrapper: makeWrapper(),
      });

      const before = Date.now();
      await act(async () => {
        await result.current.save();
      });
      const after = Date.now();

      expect(projectSaveMock).toHaveBeenCalledWith(
        "/tmp/test.vynaro.json",
        expect.objectContaining({ name: "示例项目" }),
      );
      // setCurrent 被调,updated_at 应在 before-after 之间
      expect(storeState.setCurrent).toHaveBeenCalledTimes(1);
      const saved = storeState.setCurrent.mock.calls[0]![0] as Project;
      const updatedAtMs = Date.parse(saved.updated_at);
      expect(updatedAtMs).toBeGreaterThanOrEqual(before);
      expect(updatedAtMs).toBeLessThanOrEqual(after);
    });

    it("save 失败 → error 被设,抛错", async () => {
      storeState.current = sampleProject;
      storeState.currentPath = "/tmp/test.vynaro.json";
      projectSaveMock.mockRejectedValueOnce(new Error("磁盘写失败"));
      const { result } = renderHook(() => useProject(), {
        wrapper: makeWrapper(),
      });

      let caught: unknown = null;
      await act(async () => {
        try {
          await result.current.save();
        } catch (e) {
          caught = e;
        }
      });
      expect((caught as Error).message).toBe("磁盘写失败");
      await waitFor(() => {
        expect((result.current.error as Error).message).toBe("磁盘写失败");
      });
    });
  });

  describe("saveAs", () => {
    it("没有 project → 抛错", async () => {
      const { result } = renderHook(() => useProject(), {
        wrapper: makeWrapper(),
      });
      let caught: unknown = null;
      await act(async () => {
        try {
          await result.current.saveAs("/tmp/new.json");
        } catch (e) {
          caught = e;
        }
      });
      expect((caught as Error).message).toBe("没有打开的项目");
    });

    it("正常 saveAs → setCurrentPath 被调为新路径", async () => {
      storeState.current = sampleProject;
      projectSaveMock.mockResolvedValueOnce(undefined);
      const { result } = renderHook(() => useProject(), {
        wrapper: makeWrapper(),
      });

      await act(async () => {
        await result.current.saveAs("/tmp/new.json");
      });
      expect(projectSaveMock).toHaveBeenCalledWith(
        "/tmp/new.json",
        sampleProject,
      );
      expect(storeState.setCurrentPath).toHaveBeenCalledWith("/tmp/new.json");
    });
  });

  describe("close", () => {
    it("清空 store + remove 所有 query key + pipelineIpc.cancel", async () => {
      storeState.current = sampleProject;
      storeState.currentPath = "/tmp/x.json";
      pipelineCancelMock.mockResolvedValueOnce(undefined);
      const { result } = renderHook(() => useProject(), {
        wrapper: makeWrapper(),
      });

      await act(async () => {
        await result.current.close();
      });

      expect(storeState.clear).toHaveBeenCalledTimes(1);
      expect(pipelineCancelMock).toHaveBeenCalledTimes(1);
    });

    it("pipelineIpc.cancel 失败不阻塞 close", async () => {
      storeState.current = sampleProject;
      storeState.currentPath = "/tmp/x.json";
      pipelineCancelMock.mockRejectedValueOnce(new Error("无流水线在跑"));
      const { result } = renderHook(() => useProject(), {
        wrapper: makeWrapper(),
      });

      await expect(
        act(async () => {
          await result.current.close();
        }),
      ).resolves.toBeUndefined();
      expect(storeState.clear).toHaveBeenCalledTimes(1);
    });
  });

  describe("hasProject 派生", () => {
    it("current 非 null → hasProject=true", () => {
      storeState.current = sampleProject;
      const { result } = renderHook(() => useProject(), {
        wrapper: makeWrapper(),
      });
      expect(result.current.hasProject).toBe(true);
    });
  });
});
