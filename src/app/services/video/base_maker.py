"""
视频制作器基类 (Base Video Maker)

为所有视频制作器提供公共抽象。
当前活跃实现:
- MonologueMaker: AI 第一人称独白（核心）
"""

import uuid
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Generic, TypeVar

from ..ai.scene_analyzer import SceneAnalyzer, SceneInfo
from ..export.jianying_adapter import (
    JianyingConfig,
    JianyingDraft,
)
from ..export.jianying_exporter import JianyingExporter


@dataclass
class BaseProject:
    """项目基类"""

    id: str = ""
    name: str = "新建项目"
    source_video: str = ""
    video_duration: float = 0.0
    output_dir: str = ""
    scenes: list[SceneInfo] = field(default_factory=list)


T = TypeVar("T", bound=BaseProject)


class ProgressMixin:
    """进度回调 Mixin"""

    def __init__(self):
        self._progress_callback: Callable[[str, float], None] | None = None

    def set_progress_callback(self, callback: Callable[[str, float], None]) -> None:
        """设置进度回调"""
        self._progress_callback = callback

    def _report_progress(self, stage: str, progress: float) -> None:
        """报告进度"""
        if self._progress_callback:
            self._progress_callback(stage, progress)


class BaseVideoMaker(ABC, Generic[T], ProgressMixin):
    """
    视频制作器基类

    提供公共功能:
    - 进度报告
    - 视频分析
    - 剪映导出
    - FFmpeg 导出
    """

    def __init__(self):
        super().__init__()
        self.scene_analyzer = SceneAnalyzer()
        self.jianying_exporter = JianyingExporter()

    @abstractmethod
    def create_project(
        self,
        source_video: str,
        name: str | None = None,
        output_dir: str | None = None,
        **kwargs,
    ) -> T:
        """创建项目（子类实现）"""
        pass

    def _init_project(
        self,
        project: T,
        source_video: str,
        name: str | None = None,
        output_dir: str | None = None,
    ) -> T:
        """初始化项目公共属性"""
        source_path = Path(source_video)
        if not source_path.exists():
            raise FileNotFoundError(f"视频文件不存在: {source_video}")

        project.id = str(uuid.uuid4())[:8]
        project.name = name or source_path.stem
        project.source_video = str(source_path.absolute())
        project.output_dir = output_dir or str(source_path.parent / "output")

        # 分析场景
        project.scenes = self.scene_analyzer.analyze(source_video)
        project.video_duration = (
            sum(s.duration for s in project.scenes) if project.scenes else 0
        )

        return project

    def export_to_jianying(
        self,
        project: T,
        jianying_drafts_dir: str,
    ) -> str:
        """
        导出到剪映草稿（基类实现）

        子类可重写以自定义导出逻辑
        """
        self._report_progress("导出剪映", 0.0)

        exporter = JianyingExporter(
            JianyingConfig(
                canvas_ratio="9:16",
                copy_materials=True,
            )
        )

        self._report_progress("构建轨道", 0.0)
        draft = exporter.create_draft(project.name)

        # 子类可重写此方法来添加自定义轨道
        self._build_jianying_tracks(draft, project)
        self._report_progress("构建轨道", 1.0)

        def _on_exporter_progress(phase: str, phase_p: float):
            # 将导出器的子阶段映射到 0.5-1.0
            overall_p = 0.5 + phase_p * 0.5
            self._report_progress(f"导出: {phase}", overall_p)

        draft_path = exporter.export(
            draft, jianying_drafts_dir, progress_callback=_on_exporter_progress
        )
        self._report_progress("导出剪映", 1.0)

        return draft_path

    def _build_jianying_tracks(self, draft: JianyingDraft, project: T) -> None:
        """
        构建剪映轨道

        子类重写此方法实现自定义轨道
        """
        pass


__all__ = [
    "BaseProject",
    "BaseVideoMaker",
    "ProgressMixin",
]
