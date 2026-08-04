#!/usr/bin/env python3
"""Error Recovery 错误降级模块 (v2.5.0 端到端流程优化 Phase 5)。

设计目标:
- 步骤失败时,根据错误类型给出三类恢复建议:
  1. RETRY: 临时错误(网络超时/限流),自动重试 + UI 暴露「重试」按钮
  2. SKIP: 非关键步骤(可选增强),允许「跳过」继续
  3. FAIL: 致命错误(配置缺失),只能终止
- 与 Toast / Summary 协调: 重试结果也通过 Toast 反馈

设计契约:
1. ``classify_error(exc)`` —— 纯函数,基于异常类型返回 RecoveryAction
2. ``STEP_RECOVERY_POLICY`` —— 步骤级别的策略映射(关键步骤不能跳过)
3. ``StepErrorBanner`` widget —— 在 step row 下方显示「重试 / 跳过」按钮
4. 信号: ``retry_requested(step_index)`` / ``skip_requested(step_index)``
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Final

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from ...i18n import t
from ...theme.ds_tokens import _C, FontSizes, FontWeights, Radii, Spacing, ui_font

# ═══════════════════════════════════════════════════════════════════
# 纯逻辑:错误分类
# ═══════════════════════════════════════════════════════════════════


class RecoveryAction(str, Enum):
    """单步失败后的恢复建议。"""

    RETRY = "retry"  # 临时错误,可重试
    SKIP = "skip"  # 非关键步骤,可跳过
    FAIL = "fail"  # 致命错误,必须终止


# 5 步流水线中,每步的关键性标记
# True = 关键(不可跳过),False = 可选(允许跳过)
STEP_CRITICAL: Final[tuple[bool, ...]] = (
    True,  # 01 素材导入 —— 关键,无视频无法继续
    False,  # 02 场景拆分 —— 可选,失败时回退到默认切分
    False,  # 03 脚本生成 —— 可选,失败时回退到占位脚本
    True,  # 04 配音字幕 —— 关键,无音频成片没意义
    True,  # 05 导出发布 —— 关键,产物必须落地
)


# 错误分类规则(基于异常类型 / 错误消息关键字)
_NETWORK_PATTERNS: Final[tuple[str, ...]] = (
    "timeout",
    "timed out",
    "connection",
    "network",
    "rate limit",
    "temporarily unavailable",
    "服务暂时不可用",
    "网络",
    "超时",
    "限流",
)
_CONFIG_PATTERNS: Final[tuple[str, ...]] = (
    "api key",
    "apikey",
    "未配置",
    "missing key",
    "invalid key",
    "unauthorized",
    "401",
    "403",
)


def is_network_error(exc: BaseException) -> bool:
    """判断异常是否属于「网络/临时」类(可重试)。"""
    msg = (str(exc) or "").lower()
    return any(p in msg for p in _NETWORK_PATTERNS)


def is_config_error(exc: BaseException) -> bool:
    """判断异常是否属于「配置缺失」类(致命,不可重试)。"""
    msg = (str(exc) or "").lower()
    return any(p in msg for p in _CONFIG_PATTERNS)


def classify_error(
    exc: BaseException, step_index: int
) -> RecoveryAction:
    """根据异常类型 + 步骤关键性,返回恢复建议。

    决策矩阵:
    - 网络错误 + 任意步骤 → RETRY
    - 配置错误 → FAIL(任何步骤都不能继续)
    - 其他错误 + 关键步骤 → FAIL
    - 其他错误 + 非关键步骤 → SKIP
    """
    if is_config_error(exc):
        return RecoveryAction.FAIL
    if is_network_error(exc):
        return RecoveryAction.RETRY
    # 通用异常:基于步骤关键性判断
    if 0 <= step_index < len(STEP_CRITICAL) and STEP_CRITICAL[step_index]:
        return RecoveryAction.FAIL
    return RecoveryAction.SKIP


# ═══════════════════════════════════════════════════════════════════
# i18n 文案 contract
# ═══════════════════════════════════════════════════════════════════

# v2.5.0 Phase 5: 每种恢复动作的用户可见文案
_BANNER_TEXT_KEYS: Final[dict[RecoveryAction, tuple[str, str]]] = {
    RecoveryAction.RETRY: (
        "production.error.retry_banner",
        "production.error.retry_action",
    ),
    RecoveryAction.SKIP: (
        "production.error.skip_banner",
        "production.error.skip_action",
    ),
    RecoveryAction.FAIL: (
        "production.error.fail_banner",
        "production.error.fail_action",
    ),
}


def banner_text(action: RecoveryAction, error_message: str) -> str:
    """渲染错误条幅文案(已本地化)。"""
    banner_key, _ = _BANNER_TEXT_KEYS[action]
    return t(banner_key).format(error=error_message)


def action_button_label(action: RecoveryAction) -> str:
    """渲染「重试/跳过/查看详情」按钮文案(已本地化)。"""
    _, btn_key = _BANNER_TEXT_KEYS[action]
    return t(btn_key)


# ═══════════════════════════════════════════════════════════════════
# UI:StepErrorBanner
# ═══════════════════════════════════════════════════════════════════


class StepErrorBanner(QFrame):
    """失败步骤的错误降级条幅 widget。

    显示在对应 step row 下方,提供「重试」或「跳过」按钮(基于
    :func:`classify_error` 决策)。
    """

    retry_requested = Signal(int)  # step_index
    skip_requested = Signal(int)  # step_index
    fail_dismissed = Signal(int)  # step_index (致命错误条幅关闭)

    def __init__(
        self,
        step_index: int,
        action: RecoveryAction,
        error_message: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._step_index = step_index
        self._action = action
        self._error_message = error_message
        self.setObjectName(f"step_error_banner_{step_index}")
        self._build_ui()

    @property
    def step_index(self) -> int:
        return self._step_index

    @property
    def action(self) -> RecoveryAction:
        return self._action

    def _build_ui(self) -> None:
        # 致命错误用红色,其他用 warning 黄
        accent = "#ef4444" if self._action == RecoveryAction.FAIL else "#f59e0b"
        self.setStyleSheet(
            f"""
            QFrame#{self.objectName()} {{
                background: {_C.BG_SURFACE};
                border: 1px solid {accent};
                border-left: 4px solid {accent};
                border-radius: {Radii.sm};
            }}
            """
        )
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(
            Spacing.md, Spacing.sm, Spacing.md, Spacing.sm
        )
        layout.setSpacing(Spacing.xs)

        # 错误消息(单行 + 省略号)
        self._msg_lbl = QLabel(banner_text(self._action, self._error_message))
        self._msg_lbl.setFont(ui_font(FontSizes.xs))
        self._msg_lbl.setWordWrap(True)
        self._msg_lbl.setStyleSheet(f"color: {_C.TEXT_SECONDARY};")
        layout.addWidget(self._msg_lbl)

        # 操作按钮行
        actions = QHBoxLayout()
        actions.setContentsMargins(0, 0, 0, 0)
        actions.setSpacing(Spacing.xs)
        actions.addStretch(1)

        if self._action == RecoveryAction.RETRY:
            self._action_btn = QPushButton(action_button_label(self._action))
            self._action_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self._action_btn.setStyleSheet(
                f"""
                QPushButton {{
                    background: {_C.PRIMARY};
                    color: white;
                    border: none;
                    border-radius: {Radii.sm};
                    padding: 5px 12px;
                    font-weight: {FontWeights.Medium};
                }}
                """
            )
            self._action_btn.clicked.connect(self._on_retry)
            actions.addWidget(self._action_btn)
        elif self._action == RecoveryAction.SKIP:
            self._action_btn = QPushButton(action_button_label(self._action))
            self._action_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self._action_btn.setStyleSheet(
                f"""
                QPushButton {{
                    background: transparent;
                    color: {_C.TEXT_SECONDARY};
                    border: 1px solid {_C.BORDER_SUBTLE};
                    border-radius: {Radii.sm};
                    padding: 5px 12px;
                }}
                QPushButton:hover {{
                    background: {_C.BG_BASE};
                }}
                """
            )
            self._action_btn.clicked.connect(self._on_skip)
            actions.addWidget(self._action_btn)
        else:  # FAIL
            self._action_btn = QPushButton(action_button_label(self._action))
            self._action_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self._action_btn.setStyleSheet(
                f"""
                QPushButton {{
                    background: transparent;
                    color: {_C.TEXT_MUTED};
                    border: 1px solid {_C.BORDER_SUBTLE};
                    border-radius: {Radii.sm};
                    padding: 5px 12px;
                }}
                """
            )
            self._action_btn.clicked.connect(self._on_dismiss)
            actions.addWidget(self._action_btn)

        layout.addLayout(actions)

    def _on_retry(self) -> None:
        self.retry_requested.emit(self._step_index)
        self.hide()

    def _on_skip(self) -> None:
        self.skip_requested.emit(self._step_index)
        self.hide()

    def _on_dismiss(self) -> None:
        self.fail_dismissed.emit(self._step_index)
        self.hide()


# ═══════════════════════════════════════════════════════════════════
# VM 集成 helper
# ═══════════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class StepFailureContext:
    """失败上下文,VM 失败时构造,UI 据此显示错误条幅。"""

    step_index: int
    action: RecoveryAction
    error_message: str

    @classmethod
    def from_exception(
        cls, step_index: int, exc: BaseException
    ) -> StepFailureContext:
        action = classify_error(exc, step_index)
        return cls(
            step_index=step_index,
            action=action,
            error_message=str(exc) or exc.__class__.__name__,
        )


__all__ = [
    "RecoveryAction",
    "STEP_CRITICAL",
    "StepErrorBanner",
    "StepFailureContext",
    "action_button_label",
    "banner_text",
    "classify_error",
    "is_config_error",
    "is_network_error",
]
