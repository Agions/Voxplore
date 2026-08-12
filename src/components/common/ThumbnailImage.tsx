/**
 * Vynaro v1.0.0 · 缩略图通用组件
 *
 * 设计:
 * - 调用 useAssets().thumbnail(source, width) 生成首帧 jpg
 *   (写入 ~/.cache/vynaro/thumb/<sha256>.jpg)
 * - 通过 @tauri-apps/api/core convertFileSrc 把本地路径转为 <img src> 可加载 URL
 * - 占位符:加载前/失败时显示 kind 图标 + 文件名尾部
 */

import { useEffect, useState } from "react";
import { convertFileSrc } from "@tauri-apps/api/core";
import { useAssets } from "@hooks/useAssets";
import { basename } from "@lib/assets/probe";

export interface ThumbnailImageProps {
  /** 素材源路径 */
  source: string;
  /** 素材类型 (决定占位图标) */
  kind?: "video" | "audio" | "image" | "subtitle" | "other";
  /** 缩略图宽度 (默认 240) */
  width?: number;
  /** CSS class */
  className?: string;
  /** alt 文本 (默认取文件 basename) */
  alt?: string;
}

const KIND_ICON: Record<string, string> = {
  video: "🎞",
  audio: "🎵",
  image: "🖼",
  subtitle: "💬",
  other: "📄",
};

const KIND_TONE: Record<string, string> = {
  video: "bg-blue-950/60 text-blue-300",
  audio: "bg-violet-950/60 text-violet-300",
  image: "bg-emerald-950/60 text-emerald-300",
  subtitle: "bg-amber-950/60 text-amber-300",
  other: "bg-zinc-800 text-zinc-400",
};

/**
 * 缩略图组件 — 包装 useAssets().thumbnail
 * - 自动 fallback 占位符:Spinner → 🎞/🎵/…/📄
 * - 失败不抛错,只在 UI 显示 fallback
 */
export function ThumbnailImage({
  source,
  kind = "other",
  width = 240,
  className,
  alt,
}: ThumbnailImageProps) {
  const { thumbnail } = useAssets();
  const [thumbPath, setThumbPath] = useState<string | null>(null);
  const [state, setState] = useState<"loading" | "ready" | "error">("loading");

  useEffect(() => {
    let cancelled = false;
    setThumbPath(null);
    setState("loading");
    thumbnail(source, width)
      .then((res) => {
        if (cancelled) return;
        setThumbPath(res.thumbnailPath);
        setState("ready");
      })
      .catch(() => {
        if (cancelled) return;
        setState("error");
      });
    return () => {
      cancelled = true;
    };
  }, [source, width, thumbnail]);

  const tail = (alt ?? basename(source)).trim();
  const placeholderIcon = KIND_ICON[kind] ?? "📄";
  const placeholderTone = KIND_TONE[kind] ?? KIND_TONE.other;

  return (
    <div
      className={`relative flex aspect-video w-full items-center justify-center overflow-hidden rounded-lg ${placeholderTone} ${className ?? ""}`}
      aria-label={tail}
    >
      {state === "ready" && thumbPath ? (
        <img
          src={convertFileSrc(thumbPath)}
          alt={tail}
          className="h-full w-full object-cover"
          draggable={false}
        />
      ) : (
        <div className="flex flex-col items-center gap-1.5">
          <div className="text-3xl leading-none">{placeholderIcon}</div>
          <div className="line-clamp-2 max-w-[90%] text-center font-mono text-[10px] text-current/70">
            {tail}
          </div>
          {state === "loading" && (
            <div className="text-[10px] opacity-60">生成缩略图...</div>
          )}
          {state === "error" && (
            <div className="text-[10px] opacity-60">无法生成</div>
          )}
        </div>
      )}
    </div>
  );
}
