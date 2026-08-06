/**
 * Vynaro v1.0.0 · IPC command 调用 hook (低阶版)
 *
 * 与 useTauriQuery 关系:
 * - useTauriQuery: 基于 TanStack Query 的高阶 hook(自动 cache/loading/error/retry)
 * - useTauriCommand: 基于 useState + useEffect 的低阶 hook(适合 side-effect 触发,无需 cache)
 *
 * 选择建议:
 * - 列表/详情/数据展示 → useTauriQuery
 * - 一次性 trigger (启动流水线/导入素材) → useTauriCommand
 */

import { useCallback, useEffect, useState } from "react";
import { callIpc } from "../ipc/client";
import type {
  CommandArgs,
  CommandResultOf,
  IpcCommand,
} from "../ipc/types.gen";

export interface UseTauriCommandState<C extends IpcCommand> {
  data: CommandResultOf<C> | null;
  loading: boolean;
  error: unknown;
}

export interface UseTauriCommandReturn<C extends IpcCommand> {
  state: UseTauriCommandState<C>;
  /** 手动触发一次 */
  run: (
    ...args: CommandArgs<C> extends void ? [] : [args: CommandArgs<C>]
  ) => Promise<void>;
  /** 重置 state */
  reset: () => void;
}

/**
 * 触发式 invoke hook
 *
 * @example
 *   const { state, run } = useTauriCommand("project_create_blank");
 *   <button onClick={() => run()}>新建空白项目</button>
 */
export function useTauriCommand<C extends IpcCommand>(
  command: C,
): UseTauriCommandReturn<C> {
  const [state, setState] = useState<UseTauriCommandState<C>>({
    data: null,
    loading: false,
    error: null,
  });

  const run = useCallback(
    async (
      ...args: CommandArgs<C> extends void ? [] : [args: CommandArgs<C>]
    ) => {
      setState((s) => ({ ...s, loading: true, error: null }));
      try {
        const data = await callIpc<C>(command, ...args);
        setState({ data, loading: false, error: null });
      } catch (err) {
        setState({ data: null, loading: false, error: err });
      }
    },
    [command],
  );

  const reset = useCallback(() => {
    setState({ data: null, loading: false, error: null });
  }, []);

  // 命令名变化时 reset 一次(防止 stale state)
  useEffect(() => {
    reset();
  }, [command, reset]);

  return { state, run, reset };
}
