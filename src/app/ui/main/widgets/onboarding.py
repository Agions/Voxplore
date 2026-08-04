#!/usr/bin/env python3
"""Onboarding Tooltip 组件 (v2.5.0 端到端流程优化 Phase 4)。

设计目标:
- 冷启动引导: 用户首次启动时,在关键 UI 元素旁边显示「这是什么」气泡
- 状态持久化: 用 ``QSettings`` 的 ``onboarding/done`` 键记录已看过的 hint 列表
- 轻量: 不阻挡主流程,只是温和提示
- 可重看: 设置页"重置新手引导"会清空标记,下次启动重演

设计契约:
1. 5 个 hint 点位,按 v2.5.0 端到端流程的关键节点
2. 每个 hint 有: 标题 + 描述 + 「下一步」/「我知道了」按钮
3. 关闭后通过 ``QSettings`` 写盘,跨进程持久化
4. 单元测试覆盖: 5 个 hint 列表 + 关闭事件 + 持久化(用 monkeypatch QSettings)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from PySide6.QtCore import QSettings, Qt, Signal
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from ...i18n import MessageKey, t
from ...theme.ds_tokens import _C, FontSizes, FontWeights, Radii, Spacing, ui_font

if TYPE_CHECKING:
    pass

# ── 引导点数据契约 ─────────────────────────────────────────────────
# v2.5.0: 5 个 hint 点位,锚定端到端流程的关键节点
# 每个 hint 用 i18n key 引用文案,运行时再 t() 解析,支持语言切换


@dataclass(frozen=True)
class _OnboardingHint:
    """单个新手引导 hint 的数据契约。

    Attributes:
        hint_id: 唯一标识(也是 QSettings 中已观看列表的元素)
        title_key: 标题 i18n key
        body_key: 正文 i18n key
        target_object_name: 目标 widget objectName,UI 测试可定位(可选)
    """

    hint_id: str
    title_key: str
    body_key: str
    target_object_name: str = ""


# v2.5.0 Phase 4: 5 个核心 hint 点,覆盖端到端流程
_HINTS: tuple[_OnboardingHint, ...] = (
    _OnboardingHint(
        hint_id="import_video",
        title_key="onboarding.import_video.title",
        body_key="onboarding.import_video.body",
        target_object_name="video_dropzone",
    ),
    _OnboardingHint(
        hint_id="pipeline_steps",
        title_key="onboarding.pipeline_steps.title",
        body_key="onboarding.pipeline_steps.body",
        target_object_name="production_pipeline",
    ),
    _OnboardingHint(
        hint_id="start_ai",
        title_key="onboarding.start_ai.title",
        body_key="onboarding.start_ai.body",
        target_object_name="start_ai_btn",
    ),
    _OnboardingHint(
        hint_id="summary_card",
        title_key="onboarding.summary_card.title",
        body_key="onboarding.summary_card.body",
        target_object_name="production_summary_card",
    ),
    _OnboardingHint(
        hint_id="toast_notifications",
        title_key="onboarding.toast_notifications.title",
        body_key="onboarding.toast_notifications.body",
        target_object_name="",
    ),
)


# QSettings 路径
_ORG_NAME = "SceneFab"
_APP_NAME = "Application"
_ONBOARDING_KEY = "onboarding/done"


def _load_seen_hints() -> set[str]:
    """从 ``QSettings`` 读取已观看 hint 列表。"""
    settings = QSettings(_ORG_NAME, _APP_NAME)
    raw = settings.value(_ONBOARDING_KEY, "", type=str)
    if not raw:
        return set()
    return {h for h in raw.split(",") if h}


def _save_seen_hints(seen: set[str]) -> None:
    """把已观看 hint 列表写回 ``QSettings``。"""
    settings = QSettings(_ORG_NAME, _APP_NAME)
    settings.setValue(_ONBOARDING_KEY, ",".join(sorted(seen)))
    settings.sync()


def reset_onboarding() -> None:
    """清除所有已观看 hint(由设置页"重置新手引导"按钮调用)。"""
    settings = QSettings(_ORG_NAME, _APP_NAME)
    settings.remove(_ONBOARDING_KEY)
    settings.sync()


# ═══════════════════════════════════════════════════════════════════
# 公共 API
# ═══════════════════════════════════════════════════════════════════


def get_pending_hints() -> list[_OnboardingHint]:
    """返回用户尚未看过的 hint 列表(按 ``_HINTS`` 顺序)。

    单元测试可断言:完成所有 hint 后,此函数应返回空列表。
    """
    seen = _load_seen_hints()
    return [h for h in _HINTS if h.hint_id not in seen]


def mark_hint_seen(hint_id: str) -> None:
    """标记单个 hint 为已观看,落盘 ``QSettings``。"""
    seen = _load_seen_hints()
    seen.add(hint_id)
    _save_seen_hints(seen)


# ═══════════════════════════════════════════════════════════════════
# Tooltip widget
# ═══════════════════════════════════════════════════════════════════


class OnboardingTooltip(QFrame):
    """单条 onboarding hint 的气泡 widget。

    自带标题、正文、下一步/跳过按钮;关闭或点下一步后通过
    :func:`mark_hint_seen` 落盘。
    """

    # 完成当前 hint(点下一步/知道了/点 X)
    hint_acknowledged = Signal(str)  # hint_id
    # 关闭整个 tour(用户点 X 或「不再显示」)
    tour_dismissed = Signal()

    def __init__(
        self, hint: _OnboardingHint, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self._hint = hint
        self.setObjectName(f"onboarding_tooltip_{hint.hint_id}")
        self.setWindowFlags(
            Qt.WindowType.ToolTip | Qt.WindowType.FramelessWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self._build_ui()

    def _build_ui(self) -> None:
        # 气泡外观:浅色背景 + 圆角 + 4px primary 左边框
        self.setStyleSheet(
            f"""
            QFrame#{self.objectName()} {{
                background: {_C.BG_SURFACE};
                border: 1px solid {_C.BORDER_SUBTLE};
                border-left: 4px solid {_C.PRIMARY};
                border-radius: {Radii.md};
            }}
            """
        )
        self.setMinimumWidth(280)
        self.setMaximumWidth(360)
        self.setSizePolicy(QSizePolicy.Policy.Fixed,
                           QSizePolicy.Policy.Preferred)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(
            Spacing.md, Spacing.sm, Spacing.md, Spacing.sm
        )
        layout.setSpacing(Spacing.xs)

        # 标题
        self._title_lbl = QLabel(t(self._hint.title_key))
        self._title_lbl.setFont(ui_font(FontSizes.sm, FontWeights.SemiBold))
        self._title_lbl.setWordWrap(True)
        self._title_lbl.setStyleSheet(f"color: {_C.TEXT_PRIMARY};")
        layout.addWidget(self._title_lbl)

        # 正文
        self._body_lbl = QLabel(t(self._hint.body_key))
        self._body_lbl.setFont(ui_font(FontSizes.xs))
        self._body_lbl.setWordWrap(True)
        self._body_lbl.setStyleSheet(f"color: {_C.TEXT_SECONDARY};")
        layout.addWidget(self._body_lbl)

        # 操作按钮行
        actions = QHBoxLayout()
        actions.setContentsMargins(0, Spacing.xs, 0, 0)
        actions.setSpacing(Spacing.xs)
        actions.addStretch(1)

        # 「我知道了」按钮
        self._ack_btn = QPushButton(t(MessageKey.ONBOARDING_ACKNOWLEDGE))
        self._ack_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._ack_btn.setStyleSheet(
            f"""
            QPushButton {{
                background: {_C.PRIMARY};
                color: white;
                border: none;
                border-radius: {Radii.sm};
                padding: 6px 14px;
                font-weight: {FontWeights.Medium};
            }}
            QPushButton:hover {{
                background: {_C.PRIMARY_DARK if hasattr(_C, 'PRIMARY_DARK') else _C.PRIMARY};
            }}
            """
        )
        self._ack_btn.clicked.connect(self._on_acknowledge)
        actions.addWidget(self._ack_btn)

        layout.addLayout(actions)

    def _on_acknowledge(self) -> None:
        mark_hint_seen(self._hint.hint_id)
        self.hint_acknowledged.emit(self._hint.hint_id)
        self.hide()

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802 - Qt API
        # 用户点 X:不标记为已看(允许下次再次显示)
        self.tour_dismissed.emit()
        super().closeEvent(event)


__all__ = [
    "OnboardingTooltip",
    "get_pending_hints",
    "mark_hint_seen",
    "reset_onboarding",
]
