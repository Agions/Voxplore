/**
 * Vynaro v2.5.0 · useTauriQuery — React Query + Tauri Invoke 通用封装
 *
 * 自动处理:
 * - Query Key 命名空间 (避免与其它 query 冲突)
 * - 错误抛出 VynaroError (可在 onError 中统一 toast)
 * - 禁用 retry (因为 Tauri 错误不是网络抖动)
 * - 缓存 5s (frontend 频繁 query 时降级 IPC 调用)
 */

import { invoke } from "@tauri-apps/api/core";
import {
  useQuery,
  type UseQueryOptions,
  type UseQueryResult,
} from "@tanstack/react-query";
import type {
  CommandResultOf,
  IpcCommand,
  VynaroError,
} from "@ipc/types.gen";

export interface UseTauriQueryOptions<C extends IpcCommand> extends Omit<
  UseQueryOptions<CommandResultOf<C>, VynaroError, CommandResultOf<C>>,
  "queryKey" | "queryFn"
> {
  command: C;
  args?: Record<string, unknown>;
  queryKeyPrefix: string;
}

export function useTauriQuery<C extends IpcCommand>(
  options: UseTauriQueryOptions<C>,
): UseQueryResult<CommandResultOf<C>, VynaroError> {
  const { command, args, queryKeyPrefix, ...rest } = options;
  return useQuery<CommandResultOf<C>, VynaroError, CommandResultOf<C>>({
    queryKey: [queryKeyPrefix, command, args] as const,
    queryFn: async () => {
      try {
        return await invoke<CommandResultOf<C>>(command, args ?? {});
      } catch (err) {
        if (
          err &&
          typeof err === "object" &&
          "kind" in err &&
          "message" in err &&
          typeof (err as { kind: unknown }).kind === "string"
        ) {
          throw err as VynaroError;
        }
        throw {
          kind: "other",
          message: err instanceof Error ? err.message : String(err),
        } satisfies VynaroError;
      }
    },
    retry: false,
    staleTime: 5_000,
    ...rest,
  });
}
