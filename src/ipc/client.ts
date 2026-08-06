/**
 * Vynaro v2.5.0 · Tauri Invoke 统一封装
 *
 * 设计:
 * - 唯一对 @tauri-apps/api 的强依赖点 (其它文件 import '@/ipc/client' 即可)
 * - 编译期类型保障: callIpc<C>('cmd', args) 时 args / result 自动强类型
 * - 错误统一: 异常 JSON 反序列化为 VynaroError
 */

import { invoke } from "@tauri-apps/api/core";
import type {
  CommandArgs,
  CommandResultOf,
  IpcCommand,
  VynaroError,
} from "./types.gen";

/** 强类型 callIpc,穿透到 Rust 端 command */
export async function callIpc<C extends IpcCommand>(
  command: C,
  ...args: CommandArgs<C> extends void ? [] : [args: CommandArgs<C>]
): Promise<CommandResultOf<C>> {
  const payload = args[0] ?? (undefined as unknown);
  try {
    return await invoke<CommandResultOf<C>>(
      command,
      payload as Record<string, unknown>,
    );
  } catch (err) {
    // Rust 端返回 Result<T, VynaroError> 时,Err 序列化为 { kind, message }
    if (
      err &&
      typeof err === "object" &&
      "kind" in err &&
      "message" in err &&
      typeof (err as { kind: unknown }).kind === "string"
    ) {
      throw err as VynaroError;
    }
    // 兜底: 包装成 VynaroError.other
    throw {
      kind: "other",
      message: err instanceof Error ? err.message : String(err),
    } satisfies VynaroError;
  }
}

// ─────────────────────────────────────────────────────────────────────────
// 6 个示例 command 的 typed facade (M2 范围)
// ─────────────────────────────────────────────────────────────────────────

export const appIpc = {
  version: () => callIpc("app_version"),
  startedAt: () => callIpc("app_started_at"),
} as const;

export const projectIpc = {
  listRecent: () => callIpc("project_list_recent"),
  createBlank: () => callIpc("project_create_blank"),
} as const;

export const pipelineIpc = {
  stepDefs: () => callIpc("pipeline_step_defs"),
} as const;
