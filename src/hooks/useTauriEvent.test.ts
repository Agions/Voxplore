/**
 * Vynaro v2.5.0 · useTauriEvent 单测 (M4.5)
 *
 * 覆盖:
 * - mount 时 listen 被调用,event 名匹配
 * - 收到事件后 handler 被触发,payload 透传
 * - unmount 时 unlisten 被调用(清理)
 * - listen 抛错时(非 Tauri 环境)静默,不崩溃
 */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, renderHook } from "@testing-library/react";
import { useTauriEvent } from "./useTauriEvent";

// ─── listen mock ────────────────────────────────────────────────
const listenMock = vi.fn();
const unlistenMock = vi.fn();

vi.mock("@tauri-apps/api/event", () => ({
  listen: (...args: unknown[]) => listenMock(...args),
}));

beforeEach(() => {
  listenMock.mockReset();
  unlistenMock.mockReset();
  listenMock.mockResolvedValue(unlistenMock);
});

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

// ─── tests ──────────────────────────────────────────────────────
describe("useTauriEvent", () => {
  it("mount 后调用 listen(event 名匹配)", async () => {
    renderHook(() => useTauriEvent("app:locale_changed", () => {}));

    await vi.waitFor(() => {
      expect(listenMock).toHaveBeenCalledTimes(1);
      expect(listenMock).toHaveBeenCalledWith(
        "app:locale_changed",
        expect.any(Function),
      );
    });
  });

  it("后端 emit 事件 → handler 被触发,payload 透传", async () => {
    const handler = vi.fn();
    let capturedCb: ((e: { payload: unknown }) => void) | undefined;

    listenMock.mockImplementation(
      async (_evt: string, cb: (e: { payload: unknown }) => void) => {
        capturedCb = cb;
        return unlistenMock;
      },
    );

    renderHook(() => useTauriEvent("app:locale_changed", handler));

    await vi.waitFor(() => expect(capturedCb).toBeDefined());

    // 模拟后端 emit
    capturedCb!({ payload: { locale: "en-US" } });

    expect(handler).toHaveBeenCalledWith({ payload: { locale: "en-US" } });
  });

  it("unmount 时自动调用 unlisten", async () => {
    const { unmount } = renderHook(() =>
      useTauriEvent("pipeline:event", () => {}),
    );

    await vi.waitFor(() => expect(listenMock).toHaveBeenCalled());

    expect(unlistenMock).not.toHaveBeenCalled();
    unmount();

    await vi.waitFor(() => expect(unlistenMock).toHaveBeenCalledTimes(1));
  });

  it("listen 抛错(非 Tauri 环境)→ 静默不崩溃", async () => {
    const consoleDebug = vi
      .spyOn(console, "debug")
      .mockImplementation(() => {});
    listenMock.mockRejectedValueOnce(new Error("not in Tauri webview"));

    expect(() => {
      renderHook(() => useTauriEvent("app:locale_changed", () => {}));
    }).not.toThrow();

    await vi.waitFor(() => {
      expect(consoleDebug).toHaveBeenCalled();
    });

    consoleDebug.mockRestore();
  });

  it("event 名变化时重新 listen,旧 unlisten 被调用", async () => {
    const { rerender } = renderHook(
      ({ evt }: { evt: string }) => useTauriEvent(evt, () => {}),
      { initialProps: { evt: "a:1" } },
    );

    await vi.waitFor(() => expect(listenMock).toHaveBeenCalledTimes(1));

    rerender({ evt: "a:2" });

    await vi.waitFor(() => expect(listenMock).toHaveBeenCalledTimes(2));
    expect(unlistenMock).toHaveBeenCalledTimes(1);
    expect(listenMock).toHaveBeenLastCalledWith("a:2", expect.any(Function));
  });
});
