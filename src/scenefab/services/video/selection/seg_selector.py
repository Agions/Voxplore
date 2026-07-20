"""Compatibility wrapper for the renamed segment selector module."""

from .segment_selector import (
    MockNarrativeAnalyzer,
    NarrativeAnalyzer,
    SegmentSelector,
    SelectionStrategy,
)

__all__ = [
    "SegmentSelector",
    "SelectionStrategy",
    "NarrativeAnalyzer",
    "MockNarrativeAnalyzer",
]
