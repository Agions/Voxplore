/**
 * Vynaro v2.5.0 · 素材 probe 转换 纯函数单测
 *
 * 覆盖:
 * - pathToMediaFileEmpty: path 保留 / 默认值正确 / ISO 时间戳
 * - applyProbe: 标准 probe / 零宽高 / null codec / 零 sizeBytes fallback / audio-only
 * - basename: POSIX / Windows / 尾部斜杠 / 空字符串
 * - formatBytes: B/KB/MB/GB / 0 / 负数 / NaN / Infinity / 边界四舍五入
 */
import { describe, expect, it } from "vitest";
import {
  applyProbe,
  basename,
  formatBytes,
  pathToMediaFileEmpty,
} from "./probe";
import type { FfmpegProbe, MediaFile } from "@ipc/types.gen";

describe("pathToMediaFileEmpty", () => {
  it("保留 path,其他字段填默认值", () => {
    const mf = pathToMediaFileEmpty("/Users/foo/clip.mp4");
    expect(mf.path).toBe("/Users/foo/clip.mp4");
    expect(mf.duration_seconds).toBe(0);
    expect(mf.resolution).toBeNull();
    expect(mf.codec).toBeNull();
    expect(mf.file_size_bytes).toBe(0);
  });

  it("import_time 是合法 ISO 字符串", () => {
    const mf = pathToMediaFileEmpty("/x.mp4");
    expect(mf.import_time).toMatch(
      /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$/,
    );
    // 必须能被 Date 解析
    expect(Number.isNaN(Date.parse(mf.import_time))).toBe(false);
  });

  it("两次调用返回不同对象 (不共享引用)", () => {
    const a = pathToMediaFileEmpty("/a.mp4");
    const b = pathToMediaFileEmpty("/a.mp4");
    expect(a).not.toBe(b);
    expect(a).toEqual(b);
  });

  it("path 包含 Unicode 仍保留", () => {
    const mf = pathToMediaFileEmpty("/Users/用户/影片/视频🎬.mp4");
    expect(mf.path).toBe("/Users/用户/影片/视频🎬.mp4");
  });
});

const baseProbe: FfmpegProbe = {
  durationSeconds: 12.5,
  width: 1920,
  height: 1080,
  videoCodec: "h264",
  audioCodec: "aac",
  sizeBytes: 5_242_880,
};

const baseMf: MediaFile = pathToMediaFileEmpty("/v.mp4");

describe("applyProbe", () => {
  it("标准 probe → 填入全部字段", () => {
    const out = applyProbe(baseMf, baseProbe);
    expect(out.path).toBe(baseMf.path);
    expect(out.import_time).toBe(baseMf.import_time);
    expect(out.duration_seconds).toBe(12.5);
    expect(out.resolution).toBe("1920x1080");
    expect(out.codec).toBe("h264");
    expect(out.file_size_bytes).toBe(5_242_880);
  });

  it("width=0 或 height=0 → resolution 保留原值", () => {
    const zeroProbe: FfmpegProbe = { ...baseProbe, width: 0, height: 0 };
    const mf: MediaFile = { ...baseMf, resolution: "1280x720" };
    const out = applyProbe(mf, zeroProbe);
    expect(out.resolution).toBe("1280x720");
  });

  it("width=负数 → resolution 保留原值 (防御)", () => {
    const negProbe: FfmpegProbe = { ...baseProbe, width: -1, height: 1080 };
    const mf: MediaFile = { ...baseMf, resolution: "640x480" };
    const out = applyProbe(mf, negProbe);
    expect(out.resolution).toBe("640x480");
  });

  it("videoCodec=null + audioCodec=aac → codec 落 aac", () => {
    const p: FfmpegProbe = { ...baseProbe, videoCodec: null };
    const out = applyProbe(baseMf, p);
    expect(out.codec).toBe("aac");
  });

  it("videoCodec=null + audioCodec=null → 保留 mf.codec", () => {
    const p: FfmpegProbe = { ...baseProbe, videoCodec: null, audioCodec: null };
    const mf: MediaFile = { ...baseMf, codec: "hevc" };
    const out = applyProbe(mf, p);
    expect(out.codec).toBe("hevc");
  });

  it("sizeBytes=0 → 保留原 file_size_bytes (避免清零已有值)", () => {
    const p: FfmpegProbe = { ...baseProbe, sizeBytes: 0 };
    const mf: MediaFile = { ...baseMf, file_size_bytes: 999 };
    const out = applyProbe(mf, p);
    expect(out.file_size_bytes).toBe(999);
  });

  it("sizeBytes > 0 → 覆盖 file_size_bytes", () => {
    const p: FfmpegProbe = { ...baseProbe, sizeBytes: 1234 };
    const mf: MediaFile = { ...baseMf, file_size_bytes: 999 };
    const out = applyProbe(mf, p);
    expect(out.file_size_bytes).toBe(1234);
  });

  it("音频专用 probe (无 videoCodec,仅 audioCodec) → resolution 保留原值", () => {
    const audioProbe: FfmpegProbe = {
      durationSeconds: 180,
      width: 0,
      height: 0,
      videoCodec: null,
      audioCodec: "mp3",
      sizeBytes: 3_500_000,
    };
    const out = applyProbe(baseMf, audioProbe);
    expect(out.resolution).toBeNull(); // mf 默认 null
    expect(out.codec).toBe("mp3");
    expect(out.duration_seconds).toBe(180);
  });

  it("duration 精确覆盖 (含小数)", () => {
    const p: FfmpegProbe = { ...baseProbe, durationSeconds: 1.234567 };
    const out = applyProbe(baseMf, p);
    expect(out.duration_seconds).toBe(1.234567);
  });

  it("不修改入参 mf / probe", () => {
    const mf: MediaFile = { ...baseMf };
    const p: FfmpegProbe = { ...baseProbe };
    applyProbe(mf, p);
    expect(mf.duration_seconds).toBe(0);
    expect(p).toEqual(baseProbe);
  });
});

describe("basename", () => {
  it("POSIX 路径", () => {
    expect(basename("/Users/foo/bar.mp4")).toBe("bar.mp4");
  });

  it("Windows 路径 (反斜杠)", () => {
    expect(basename("C:\\Users\\foo\\bar.mp4")).toBe("bar.mp4");
  });

  it("混合分隔符", () => {
    expect(basename("/Users/foo\\bar.mp4")).toBe("bar.mp4");
  });

  it("只有文件名", () => {
    expect(basename("clip.mp4")).toBe("clip.mp4");
  });

  it("尾部斜杠 → 返回 path 自身", () => {
    expect(basename("/Users/foo/")).toBe("");
    expect(basename("/Users/foo/")).toBe("");
  });

  it("空字符串 → 空字符串", () => {
    expect(basename("")).toBe("");
  });

  it("尾部有空格 → trim 后保留", () => {
    expect(basename("  hello.mp4  ")).toBe(
      "  hello.mp4  ".split(/[/\\]/).pop(),
    );
  });
});

describe("formatBytes", () => {
  it("0 → '0 B'", () => {
    expect(formatBytes(0)).toBe("0 B");
  });

  it("负数 → '0 B'", () => {
    expect(formatBytes(-100)).toBe("0 B");
  });

  it("NaN / Infinity → '—' (代表未知)", () => {
    expect(formatBytes(Number.NaN)).toBe("—");
    expect(formatBytes(Number.POSITIVE_INFINITY)).toBe("—");
  });

  it("null / undefined → '—' (后端 Option<u64> 缺失场景)", () => {
    expect(formatBytes(null)).toBe("—");
    expect(formatBytes(undefined)).toBe("—");
  });

  it("B 级别 (< 1024)", () => {
    expect(formatBytes(512)).toBe("512 B");
    expect(formatBytes(1023)).toBe("1023 B");
  });

  it("KB 边界 1024 → '1.0 KB'", () => {
    expect(formatBytes(1024)).toBe("1.0 KB");
  });

  it("MB 级别", () => {
    expect(formatBytes(1024 * 1024)).toBe("1.0 MB");
    expect(formatBytes(5 * 1024 * 1024)).toBe("5.0 MB");
  });

  it("GB 级别", () => {
    expect(formatBytes(2 * 1024 * 1024 * 1024)).toBe("2.0 GB");
  });

  it("TB 级别", () => {
    // 1 TB = 1024^4 字节 → 升级到 TB 单位,1 位小数
    expect(formatBytes(1024 ** 4)).toBe("1.0 TB");
    expect(formatBytes(2 * 1024 ** 4)).toBe("2.0 TB");
  });

  it(">= 100 数值去掉小数 (B/KB/MB)", () => {
    expect(formatBytes(150 * 1024 * 1024)).toBe("150 MB");
    // 2500 MB 会被进一步升级到 GB 单位 (2.4 GB)
    expect(formatBytes(2500 * 1024 * 1024)).toBe("2.4 GB");
  });

  it("KB 级别保留 1 位小数 (< 100)", () => {
    expect(formatBytes(1.5 * 1024)).toBe("1.5 KB");
    expect(formatBytes(99.4 * 1024)).toBe("99.4 KB");
  });
});
