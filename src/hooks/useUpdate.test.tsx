/**
 * Vynaro v1.0.0 · useUpdate hook 单测 (renderHook)
 *
 * 测试策略:
 * - mock @ipc/commands 中的 updateIpc
 * - mock useUpdateStore 为可控版本
 * - mock @tauri-apps/api/event 的 listen (jsdom 不支持 Tauri 事件)
 * - 用 QueryClientProvider 包裹 renderHook
 * - 覆盖:check / download / install / reset + busy 标志
 */
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, cleanup, renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useUpdate } from "./useUpdate";
import type {
  UpdateInfo,
  UpdateInstallResult,
  UpdateState,
} from "../ipc/types.gen";

// ─── mocks ─────────────────────────────────────────────────────────
const getStateMock = vi.fn();
const checkIpcMock = vi.fn();
const downloadIpcMock = vi.fn();
const installIpcMock = vi.fn();
const resetIpcMock = vi.fn();

vi.mock("../ipc/commands", () => ({
  updateIpc: {
    getState: (...a: unknown[]) => getStateMock(...a),
    check: (...a: unknown[]) => checkIpcMock(...a),
    download: (...a: unknown[]) => downloadIpcMock(...a),
    install: (...a: unknown[]) => installIpcMock(...a),
    reset: (...a: unknown[]) => resetIpcMock(...a),
  },
}));

// Tauri listen 在 jsdom 不可用,直接 resolve 一个 noop unlisten
vi.mock("@tauri-apps/api/event", () => ({
  listen: () => Promise.resolve(() => {}),
}));

// useUpdateStore 用 closure mock
type StoreShape = {
  snapshot: UpdateState;
  setSnapshot: ReturnType<typeof vi.fn>;
  setAvailable: ReturnType<typeof vi.fn>;
  setPhase: ReturnType<typeof vi.fn>;
  setDownloadedPath: ReturnType<typeof vi.fn>;
  setError: ReturnType<typeof vi.fn>;
  reset: ReturnType<typeof vi.fn>;
};

let storeState: StoreShape;

vi.mock("../stores/update-store", () => ({
  useUpdateStore: (selector: (s: StoreShape) => unknown) =>
    selector(storeState),
}));

// ─── helpers ───────────────────────────────────────────────────────
const EMPTY_STATE: UpdateState = {
  phase: "idle",
  currentVersion: "",
  available: null,
  progress: null,
  error: null,
  downloadedPath: null,
};

const sampleInfo: UpdateInfo = {
  version: "3.1.0",
  releaseDate: "2026-08-01",
  notes: "新特性",
  downloadUrl: "https://example.com/x.zip",
  sha256: "abc123",
  fileSizeBytes: 12_345_678,
};

const sampleInstallResult: UpdateInstallResult = {
  downloadedPath: "/cache/update.zip",
  note: "请手动替换后重启",
};

function makeWrapper() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={qc}>{children}</QueryClientProvider>
  );
}

beforeEach(() => {
  // 默认 getState 返回 EMPTY_STATE (避免 useUpdateStore.snapshot 被 setSnapshot(undefined) 覆盖)
  getStateMock.mockResolvedValue(EMPTY_STATE);
  storeState = {
    snapshot: { ...EMPTY_STATE },
    setSnapshot: vi.fn((s: UpdateState) => {
      // 防御:undefined 入参视为 EMPTY_STATE (避免后续 .currentVersion 抛错)
      storeState.snapshot = s ?? { ...EMPTY_STATE };
    }),
    setAvailable: vi.fn((info: UpdateInfo | null) => {
      storeState.snapshot = { ...storeState.snapshot, available: info };
    }),
    setPhase: vi.fn((phase) => {
      storeState.snapshot = {
        ...storeState.snapshot,
        phase,
        error: null,
      };
    }),
    setDownloadedPath: vi.fn((path) => {
      storeState.snapshot = { ...storeState.snapshot, downloadedPath: path };
    }),
    setError: vi.fn((error) => {
      storeState.snapshot = { ...storeState.snapshot, error };
    }),
    reset: vi.fn((currentVersion: string) => {
      storeState.snapshot = { ...EMPTY_STATE, currentVersion };
    }),
  };
});

afterEach(() => {
  vi.clearAllMocks();
  cleanup();
});

// ─── tests ─────────────────────────────────────────────────────────
describe("useUpdate", () => {
  describe("currentVersion 注入", () => {
    it("传入 currentVersion → store.reset 被调一次 (后续 prop 变化不重复)", async () => {
      const { rerender } = renderHook(
        ({ version }: { version: string }) =>
          useUpdate({ currentVersion: version }),
        {
          wrapper: makeWrapper(),
          initialProps: { version: "3.0.0" },
        },
      );

      await waitFor(() => {
        expect(storeState.reset).toHaveBeenCalledWith("3.0.0");
      });
      expect(storeState.reset).toHaveBeenCalledTimes(1);

      // 重渲染传不同版本,不应再调 reset
      rerender({ version: "3.0.1" });
      expect(storeState.reset).toHaveBeenCalledTimes(1);
    });

    it("不传 currentVersion → store.reset 不被调", async () => {
      renderHook(() => useUpdate(), { wrapper: makeWrapper() });
      await waitFor(() => {
        expect(getStateMock).toHaveBeenCalled();
      });
      expect(storeState.reset).not.toHaveBeenCalled();
    });
  });

  describe("check", () => {
    it("成功 → setAvailable 被调 + refetch 触发", async () => {
      checkIpcMock.mockResolvedValueOnce(sampleInfo);
      getStateMock.mockResolvedValue(EMPTY_STATE);

      const { result } = renderHook(() => useUpdate(), {
        wrapper: makeWrapper(),
      });
      await waitFor(() => expect(getStateMock).toHaveBeenCalled());

      await act(async () => {
        await result.current.check();
      });

      expect(checkIpcMock).toHaveBeenCalledTimes(1);
      expect(storeState.setAvailable).toHaveBeenCalledWith(sampleInfo);
      // refetch 会再次调用 getState
      expect(getStateMock.mock.calls.length).toBeGreaterThanOrEqual(2);
    });

    it("失败 → setError 被调,available 不会被设", async () => {
      checkIpcMock.mockRejectedValueOnce(new Error("网络错误"));
      getStateMock.mockResolvedValue(EMPTY_STATE);

      const { result } = renderHook(() => useUpdate(), {
        wrapper: makeWrapper(),
      });
      await waitFor(() => expect(getStateMock).toHaveBeenCalled());

      await act(async () => {
        await result.current.check();
      });

      expect(checkIpcMock).toHaveBeenCalledTimes(1);
      expect(storeState.setError).toHaveBeenCalledWith("网络错误");
      expect(storeState.setAvailable).not.toHaveBeenCalled();
    });
  });

  describe("download", () => {
    it("成功 → setDownloadedPath + setPhase('ready') 被调", async () => {
      downloadIpcMock.mockResolvedValueOnce("/cache/update.zip");
      getStateMock.mockResolvedValue(EMPTY_STATE);

      const { result } = renderHook(() => useUpdate(), {
        wrapper: makeWrapper(),
      });
      await waitFor(() => expect(getStateMock).toHaveBeenCalled());

      await act(async () => {
        await result.current.download();
      });

      expect(downloadIpcMock).toHaveBeenCalledTimes(1);
      expect(storeState.setDownloadedPath).toHaveBeenCalledWith(
        "/cache/update.zip",
      );
      expect(storeState.setPhase).toHaveBeenCalledWith("ready");
    });

    it("失败 → setError 被调,phase 不会切到 ready", async () => {
      downloadIpcMock.mockRejectedValueOnce(new Error("磁盘满"));
      getStateMock.mockResolvedValue(EMPTY_STATE);

      const { result } = renderHook(() => useUpdate(), {
        wrapper: makeWrapper(),
      });
      await waitFor(() => expect(getStateMock).toHaveBeenCalled());

      await act(async () => {
        await result.current.download();
      });

      expect(storeState.setError).toHaveBeenCalledWith("磁盘满");
      expect(storeState.setPhase).not.toHaveBeenCalledWith("ready");
    });
  });

  describe("install", () => {
    it("成功 → 返回 UpdateInstallResult", async () => {
      installIpcMock.mockResolvedValueOnce(sampleInstallResult);
      getStateMock.mockResolvedValue(EMPTY_STATE);

      const { result } = renderHook(() => useUpdate(), {
        wrapper: makeWrapper(),
      });
      await waitFor(() => expect(getStateMock).toHaveBeenCalled());

      let returned: UpdateInstallResult | undefined;
      await act(async () => {
        returned = await result.current.install();
      });
      expect(installIpcMock).toHaveBeenCalledTimes(1);
      expect(returned).toEqual(sampleInstallResult);
    });

    it("失败 → setError + 抛错", async () => {
      installIpcMock.mockRejectedValueOnce(new Error("安装失败"));
      getStateMock.mockResolvedValue(EMPTY_STATE);

      const { result } = renderHook(() => useUpdate(), {
        wrapper: makeWrapper(),
      });
      await waitFor(() => expect(getStateMock).toHaveBeenCalled());

      let caught: unknown = null;
      await act(async () => {
        try {
          await result.current.install();
        } catch (e) {
          caught = e;
        }
      });
      expect((caught as Error).message).toBe("安装失败");
      expect(storeState.setError).toHaveBeenCalledWith("安装失败");
    });
  });

  describe("reset", () => {
    it("调 updateIpc.reset + 写回 currentVersion 到 store", async () => {
      storeState.snapshot = { ...EMPTY_STATE, currentVersion: "3.0.0" };
      resetIpcMock.mockResolvedValueOnce(undefined);
      getStateMock.mockResolvedValue(EMPTY_STATE);

      const { result } = renderHook(
        () => useUpdate({ currentVersion: "3.0.0" }),
        { wrapper: makeWrapper() },
      );
      await waitFor(() => expect(getStateMock).toHaveBeenCalled());

      await act(async () => {
        await result.current.reset();
      });
      expect(resetIpcMock).toHaveBeenCalledTimes(1);
      // snapshot.currentVersion 写入 store
      expect(storeState.snapshot.currentVersion).toBe("3.0.0");
    });
  });

  describe("busy 派生", () => {
    it("phase=checking → busy=true", () => {
      storeState.snapshot = { ...EMPTY_STATE, phase: "checking" };
      getStateMock.mockResolvedValue(storeState.snapshot);
      const { result } = renderHook(() => useUpdate(), {
        wrapper: makeWrapper(),
      });
      return waitFor(() => expect(result.current.busy).toBe(true));
    });

    it("phase=downloading → busy=true", () => {
      storeState.snapshot = { ...EMPTY_STATE, phase: "downloading" };
      getStateMock.mockResolvedValue(storeState.snapshot);
      const { result } = renderHook(() => useUpdate(), {
        wrapper: makeWrapper(),
      });
      return waitFor(() => expect(result.current.busy).toBe(true));
    });

    it("phase=idle → busy=false", () => {
      storeState.snapshot = { ...EMPTY_STATE, phase: "idle" };
      getStateMock.mockResolvedValue(storeState.snapshot);
      const { result } = renderHook(() => useUpdate(), {
        wrapper: makeWrapper(),
      });
      return waitFor(() => expect(result.current.busy).toBe(false));
    });

    it("phase=available → busy=false", () => {
      storeState.snapshot = { ...EMPTY_STATE, phase: "available" };
      getStateMock.mockResolvedValue(storeState.snapshot);
      const { result } = renderHook(() => useUpdate(), {
        wrapper: makeWrapper(),
      });
      return waitFor(() => expect(result.current.busy).toBe(false));
    });
  });
});
