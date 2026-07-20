"""
字幕合并器 (Subtitle Merger)

将 OCR 字幕和语音字幕合并，去重，生成最终字幕。

策略：
- 时间重叠且文本相似 → 保留语音版（时间更准）
- 仅 OCR 有 → 保留（可能是画面中的标题/注释）
- 仅语音有 → 保留（可能是画外音）
"""

import bisect
import logging

from .subtitle_types import SubtitleExtractionResult, SubtitleSegment

logger = logging.getLogger(__name__)

__all__ = ["SubtitleMerger"]


class SubtitleMerger:
    """
    字幕合并器
    将 OCR 字幕和语音字幕合并，去重，生成最终字幕
    """

    @staticmethod
    def merge(
        ocr_result: SubtitleExtractionResult,
        speech_result: SubtitleExtractionResult,
        overlap_threshold: float = 0.5,
    ) -> SubtitleExtractionResult:
        """
        合并两种来源的字幕

        策略：
        - 时间重叠且文本相似 → 保留语音版（时间更准）
        - 仅 OCR 有 → 保留（可能是画面中的标题/注释）
        - 仅语音有 → 保留（可能是画外音）
        """
        merged, speech_segs, ocr_segs = SubtitleMerger._prepare(
            ocr_result, speech_result
        )
        used_ocr = SubtitleMerger._merge_speech_with_ocr_overlap(
            merged, speech_segs, ocr_segs, overlap_threshold
        )
        SubtitleMerger._append_unmatched_ocr(merged, ocr_segs, used_ocr)
        SubtitleMerger._finalize(merged)
        return merged

    @staticmethod
    def _prepare(
        ocr_result: SubtitleExtractionResult,
        speech_result: SubtitleExtractionResult,
    ) -> tuple[SubtitleExtractionResult, list[SubtitleSegment], list[SubtitleSegment]]:
        """构造结果容器并拷贝两侧片段列表。"""
        merged = SubtitleExtractionResult(
            video_path=ocr_result.video_path,
            duration=max(ocr_result.duration, speech_result.duration),
            method="both",
        )
        speech_segs = list(speech_result.segments)
        ocr_segs = list(ocr_result.segments)
        return merged, speech_segs, ocr_segs

    @staticmethod
    def _merge_speech_with_ocr_overlap(
        merged: SubtitleExtractionResult,
        speech_segs: list[SubtitleSegment],
        ocr_segs: list[SubtitleSegment],
        overlap_threshold: float,
    ) -> set[int]:
        """
        以语音为主线加入结果，并把与之时间重叠的 OCR 段索引记入 used_ocr。

        ✅ 优化：OCR 段按 start 排序后用二分查找，O((n+m) log m) 而非 O(n*m)
        """
        used_ocr: set[int] = set()

        if ocr_segs:
            # OCR start 排序 + 二分查找候选窗口
            ocr_sorted = sorted(enumerate(ocr_segs), key=lambda x: x[1].start)
            ocr_starts = [seg.start for _, seg in ocr_sorted]

            for sp_seg in speech_segs:
                merged.segments.append(
                    SubtitleSegment(
                        start=sp_seg.start,
                        end=sp_seg.end,
                        text=sp_seg.text,
                        confidence=sp_seg.confidence,
                        source="speech",
                    )
                )
                SubtitleMerger._mark_overlapping_ocr(
                    sp_seg, ocr_sorted, ocr_starts, overlap_threshold, used_ocr
                )
        else:
            for sp_seg in speech_segs:
                merged.segments.append(
                    SubtitleSegment(
                        start=sp_seg.start,
                        end=sp_seg.end,
                        text=sp_seg.text,
                        confidence=sp_seg.confidence,
                        source="speech",
                    )
                )

        return used_ocr

    @staticmethod
    def _mark_overlapping_ocr(
        sp_seg: SubtitleSegment,
        ocr_sorted: list[tuple[int, SubtitleSegment]],
        ocr_starts: list[float],
        overlap_threshold: float,
        used_ocr: set[int],
    ) -> None:
        """
        二分查找可能重叠的 OCR 字幕范围，标记 overlap_ratio 超阈值的索引。
        OCR start ≤ sp_seg.end + max_span 的都是候选。
        """
        max_span = max(sp_seg.end - sp_seg.start, 0.001)
        lo = bisect.bisect_left(ocr_starts, sp_seg.start - max_span)
        hi = bisect.bisect_right(ocr_starts, sp_seg.end + max_span)
        for idx in range(lo, hi):
            orig_idx, ocr_seg = ocr_sorted[idx]
            if SubtitleMerger._overlap_ratio(sp_seg, ocr_seg) > overlap_threshold:
                used_ocr.add(orig_idx)

    @staticmethod
    def _append_unmatched_ocr(
        merged: SubtitleExtractionResult,
        ocr_segs: list[SubtitleSegment],
        used_ocr: set[int],
    ) -> None:
        """添加未匹配的 OCR 字幕（画面标题、注释等）。"""
        for i, ocr_seg in enumerate(ocr_segs):
            if i not in used_ocr and ocr_seg.text.strip():
                merged.segments.append(
                    SubtitleSegment(
                        start=ocr_seg.start,
                        end=ocr_seg.end,
                        text=f"[画面] {ocr_seg.text}",
                        confidence=ocr_seg.confidence,
                        source="ocr",
                    )
                )

    @staticmethod
    def _finalize(merged: SubtitleExtractionResult) -> None:
        """按时间排序并拼接 full_text。"""
        merged.segments.sort(key=lambda s: s.start)
        merged.full_text = " ".join(s.text for s in merged.segments)

    @staticmethod
    def _overlap_ratio(a: SubtitleSegment, b: SubtitleSegment) -> float:
        """计算两个时间段的重叠比例"""
        overlap_start = max(a.start, b.start)
        overlap_end = min(a.end, b.end)
        overlap = max(0, overlap_end - overlap_start)
        total = max(a.end - a.start, b.end - b.start, 0.001)
        return overlap / total
