/**
 * Vynaro v2.5.0 · formatBytes 单元测试
 *
 * 验证 src/lib/format/bytes.ts 统一接口
 */
import { describe, expect, it } from "vitest";
import { formatBytes } from "./bytes";

describe("formatBytes", () => {
  describe("null/undefined/非有限数", () => {
    it("null → '—' (代表未知)", () => {
      expect(formatBytes(null)).toBe("—");
    });

    it("undefined → '—'", () => {
      expect(formatBytes(undefined)).toBe("—");
    });

    it("NaN → '—'", () => {
      expect(formatBytes(Number.NaN)).toBe("—");
    });

    it("Infinity → '—'", () => {
      expect(formatBytes(Number.POSITIVE_INFINITY)).toBe("—");
    });

    it("负 Infinity → '—'", () => {
      expect(formatBytes(Number.NEGATIVE_INFINITY)).toBe("—");
    });
  });

  describe("合法零值 / 负数", () => {
    it("0 → '0 B'", () => {
      expect(formatBytes(0)).toBe("0 B");
    });

    it("负数 → '0 B'", () => {
      expect(formatBytes(-100)).toBe("0 B");
    });
  });

  describe("B 级别", () => {
    it("< 1024 → '<n> B'", () => {
      expect(formatBytes(1)).toBe("1 B");
      expect(formatBytes(512)).toBe("512 B");
      expect(formatBytes(1023)).toBe("1023 B");
    });
  });

  describe("KB 边界", () => {
    it("1024 → '1.0 KB'", () => {
      expect(formatBytes(1024)).toBe("1.0 KB");
    });

    it("> 100 KB → 整数 (无小数)", () => {
      expect(formatBytes(150 * 1024)).toBe("150 KB");
      expect(formatBytes(1023 * 1024)).toBe("1023 KB");
    });

    it("< 100 KB → 1 位小数", () => {
      expect(formatBytes(1.5 * 1024)).toBe("1.5 KB");
      expect(formatBytes(99.4 * 1024)).toBe("99.4 KB");
    });
  });

  describe("MB 级别", () => {
    it("1024^2 → '1.0 MB'", () => {
      expect(formatBytes(1024 * 1024)).toBe("1.0 MB");
    });

    it("5 MB → '5.0 MB'", () => {
      expect(formatBytes(5 * 1024 * 1024)).toBe("5.0 MB");
    });

    it("150 MB → '150 MB' (整数)", () => {
      expect(formatBytes(150 * 1024 * 1024)).toBe("150 MB");
    });
  });

  describe("GB 级别", () => {
    it("1 GB → '1.0 GB'", () => {
      expect(formatBytes(1024 ** 3)).toBe("1.0 GB");
    });

    it("2.5 GB → '2.5 GB'", () => {
      expect(formatBytes(2.5 * 1024 ** 3)).toBe("2.5 GB");
    });

    it("1023 GB → '1023 GB' (整数)", () => {
      expect(formatBytes(1023 * 1024 ** 3)).toBe("1023 GB");
    });
  });

  describe("TB 级别", () => {
    it("1 TB → '1.0 TB'", () => {
      expect(formatBytes(1024 ** 4)).toBe("1.0 TB");
    });

    it("2 TB → '2.0 TB'", () => {
      expect(formatBytes(2 * 1024 ** 4)).toBe("2.0 TB");
    });
  });
});
