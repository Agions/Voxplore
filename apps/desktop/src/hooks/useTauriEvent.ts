/**
 * SceneFab v3.0 · useTauriEvent — Tauri 事件订阅通用 hook
 *
 * 自动处理:
 * - listen() 返回 Promise<UnlistenFn>,用 useEffect lifecycle 配对
 * - mounted 标志防止在 unmount 后 setState
 * - 错误兜底(webview only 模式 listen 不可用时静默)
 *
 * @example
 *   useTauriEvent("app:locale_changed", (e) => {
 *     const { locale } = e.payload as { locale: string };
 *     setLocale(locale);
 *   });
 */

import { useEffect, type DependencyList } from "react";
import { listen, type Event, type UnlistenFn } from "@tauri-apps/api/event";

export type TauriEventHandler<T = unknown> = (event: Event<T>) => void;

/**
 * 订阅一个 Tauri 后端事件,组件卸载时自动 unlisten。
 *
 * @param event 事件名(如 "app:locale_changed")
 * @param handler 事件回调
 * @param deps 额外依赖(默认 [])
 */
export function useTauriEvent<T = unknown>(
  event: string,
  handler: TauriEventHandler<T>,
  deps: DependencyList = [],
): void {
  useEffect(() => {
    let unlisten: UnlistenFn | undefined;
    let mounted = true;
    (async () => {
      try {
        unlisten = await listen<T>(event, (e) => {
          if (mounted) handler(e);
        });
      } catch (e) {
        // webview only / 非 Tauri 环境:静默忽略
        // eslint-disable-next-line no-console
        console.debug(`[useTauriEvent] listen(${event}) unavailable`, e);
      }
    })();
    return () => {
      mounted = false;
      if (unlisten) unlisten();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [event, ...deps]);
}
