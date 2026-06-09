"""Pipeline configuration dataclasses."""

from dataclasses import dataclass


@dataclass(slots=True)
class PipelineConfig:
    """流水线配置 V2"""

    min_segment_duration: float = 9.0
    max_segment_duration: float = 60.0
    frame_sample_interval: float = 1.0
    min_confidence: float = 0.6
    visual_weight: float = 0.7
    audio_weight: float = 0.3
    max_workers: int = 4
    batch_size: int = 10  # 批量大小
    enable_parallel: bool = True  # 并行处理开关
