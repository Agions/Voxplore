/**
 * Vynaro v2.5.0 · 字节数格式化 (统一接口)
 *
 * 设计:
 * - 接收 number | null | undefined (兼容后端 Option<u64>)
 * - 统一返回 "—" / "0 B" / "<n> KB|MB|GB"
 * - 单元测试覆盖:src/lib/format/bytes.test.ts
 */

const UNITS = ["B", "KB", "MB", "GB", "TB"] as const;

/** 字节数 → 人类可读 (B / KB / MB / GB / TB) */
export function formatBytes(n: number | null | undefined): string {
  // null / undefined / 非有限数 → "—" (代表"未知"或"不可用")
  if (n == null || !Number.isFinite(n)) return "—";
  // 0 或负数 → "0 B" (合法零值)
  if (n <= 0) return "0 B";
  let v = n;
  let u = 0;
  while (v >= 1024 && u < UNITS.length - 1) {
    v /= 1024;
    u++;
  }
  // 整数 → 0 位小数;< 100 → 1 位小数;>= 100 → 0 位小数 (避免冗余)
  const decimals = v >= 100 || u === 0 ? 0 : 1;
  return `${v.toFixed(decimals)} ${UNITS[u]}`;
}
