"""
Pipeline 控制器 — 串联 MonologueMaker 各阶段，提供 Qt 信号驱动 UI 更新
"""

import traceback
from enum import Enum
from typing import Optional

from PySide6.QtCore import QObject, Signal

from app.services.video.monologue_maker import MonologueMaker, MonologueProject
from app.core.logger import Logger


class PipelineStage(Enum):
    """Pipeline 阶段"""
    IDLE = "idle"
    ANALYZING = "analyzing"      # Step1: 分析视频
    SCRIPT = "script"             # Step2: 生成文案
    VOICE = "voice"              # Step2: 生成配音
    CAPTION = "caption"          # Step2: 生成字幕
    EXPORTING = "exporting"       # Step3: 导出
    DONE = "done"
    ERROR = "error"


class PipelineController(QObject):
    """
    Pipeline 控制器

    职责：
    - 管理 MonologueMaker 的阶段性执行
    - 通过 Qt Signal 将进度推送至 UI
    - 持有当前 Project，支持暂停/跳过/重试
    """

    # ====== Qt Signals ======
    # 阶段状态变化: (stage, description)
    stage_changed = Signal(str, str)
    # 阶段进度更新: (stage, 0.0~1.0)
    stage_progress = Signal(str, float)
    # Pipeline 完成: (output_path)
    finished = Signal(str)
    # Pipeline 错误: (error_message)
    error_occurred = Signal(str)

    # ====== 内部阶段映射 ======
    _STAGE_LABELS = {
        PipelineStage.IDLE: "就绪",
        PipelineStage.ANALYZING: "分析视频",
        PipelineStage.SCRIPT: "生成解说",
        PipelineStage.VOICE: "生成配音",
        PipelineStage.CAPTION: "生成字幕",
        PipelineStage.EXPORTING: "导出视频",
        PipelineStage.DONE: "完成",
        PipelineStage.ERROR: "错误",
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.logger = Logger("PipelineController")
        self._maker = MonologueMaker()
        self._project: Optional[MonologueProject] = None
        self._current_stage = PipelineStage.IDLE
        self._is_running = False
        self._is_paused = False

        # 注册进度回调
        self._maker.set_progress_callback(self._on_maker_progress)

    # ==============================================================
    # 公共 API
    # ==============================================================

    def is_running(self) -> bool:
        return self._is_running

    def current_project(self) -> Optional[MonologueProject]:
        return self._project

    def current_stage(self) -> PipelineStage:
        return self._current_stage

    def start_pipeline(
        self,
        video_path: str,
        context: str,
        emotion: str,
        style,
        output_dir: str,
    ) -> None:
        """
        启动完整 Pipeline（Step1 + Step2 + Step3）

        Args:
            video_path: 源视频路径
            context: 场景/情境描述
            emotion: 情感基调
            style: MonologueStyle
            output_dir: 输出目录
        """
        if self._is_running:
            self.logger.warn("Pipeline 已在运行中，忽略重复启动")
            return

        self._is_running = True
        self._is_paused = False

        try:
            # --- Stage 1: 创建项目 & 分析视频 ---
            self._set_stage(PipelineStage.ANALYZING)
            self._project = self._maker.create_project(
                source_video=video_path,
                context=context,
                emotion=emotion,
                output_dir=output_dir,
            )
            self._project.style = style

            # --- Stage 2: 生成文案 ---
            self._set_stage(PipelineStage.SCRIPT)
            self._maker.generate_script(self._project)

            # --- Stage 3: 生成配音 ---
            self._set_stage(PipelineStage.VOICE)
            self._maker.generate_voice(self._project)

            # --- Stage 4: 生成字幕 ---
            self._set_stage(PipelineStage.CAPTION)
            self._maker.generate_captions(self._project)

            # --- Stage 5: 导出 ---
            self._set_stage(PipelineStage.EXPORTING)
            draft_path = self._maker.export_to_jianying(
                self._project,
                output_dir + "/jianying_drafts",
            )

            # --- 完成 ---
            self._set_stage(PipelineStage.DONE)
            self._is_running = False
            self.finished.emit(draft_path)

        except Exception as e:
            self._is_running = False
            err_msg = f"{type(e).__name__}: {e}\n{traceback.format_exc()}"
            self.logger.error(f"Pipeline 执行出错: {err_msg}")
            self._set_stage(PipelineStage.ERROR)
            self.error_occurred.emit(str(e))

    def retry_stage(self, stage: PipelineStage) -> None:
        """
        重试指定阶段

        Args:
            stage: 要重试的阶段（SCRIPT / VOICE / CAPTION）
        """
        if self._project is None:
            self.logger.error("无 Project，无法重试阶段")
            return

        if self._is_running:
            self.logger.warn("Pipeline 正在运行中")
            return

        self._is_running = True

        try:
            if stage == PipelineStage.SCRIPT:
                self._set_stage(PipelineStage.SCRIPT)
                self._maker.generate_script(self._project)
            elif stage == PipelineStage.VOICE:
                self._set_stage(PipelineStage.VOICE)
                self._maker.generate_voice(self._project)
            elif stage == PipelineStage.CAPTION:
                self._set_stage(PipelineStage.CAPTION)
                self._maker.generate_captions(self._project)

            self._is_running = False
        except Exception as e:
            self._is_running = False
            self.logger.error(f"重试阶段 {stage.value} 失败: {e}")
            self._set_stage(PipelineStage.ERROR)
            self.error_occurred.emit(str(e))

    def reset(self) -> None:
        """重置 Pipeline 到初始状态"""
        self._maker = MonologueMaker()
        self._maker.set_progress_callback(self._on_maker_progress)
        self._project = None
        self._is_running = False
        self._is_paused = False
        self._set_stage(PipelineStage.IDLE)

    # ==============================================================
    # 内部方法
    # ==============================================================

    def _set_stage(self, stage: PipelineStage) -> None:
        self._current_stage = stage
        label = self._STAGE_LABELS.get(stage, stage.value)
        self.stage_changed.emit(stage.value, label)
        if stage != PipelineStage.DONE and stage != PipelineStage.ERROR:
            self.stage_progress.emit(stage.value, 0.0)

    def _on_maker_progress(self, stage_label: str, progress: float) -> None:
        """
        接收 MonologueMaker 的进度回调，转发为 Qt Signal
        stage_label 格式如 "分析视频" / "生成独白" / "生成配音" / "生成字幕"
        """
        # 映射 MonologueMaker 阶段标签 → PipelineStage
        mapping = {
            "分析视频": PipelineStage.ANALYZING,
            "生成独白": PipelineStage.SCRIPT,
            "生成配音": PipelineStage.VOICE,
            "生成字幕": PipelineStage.CAPTION,
        }
        stage = mapping.get(stage_label, self._current_stage)
        self.stage_progress.emit(stage.value, progress)
