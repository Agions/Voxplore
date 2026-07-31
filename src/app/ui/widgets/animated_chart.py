#!/usr/bin/env python3
"""RingChart & LineChart · 轻量自绘图表控件（Phase 2 · Dashboard 资源监控）。

设计要点
---------

* **零依赖**：纯 ``QPainter`` 实现，没有 matplotlib / pyqtgraph。
* **主题感知**：颜色全部通过 ``_C.*`` 懒求值，且仅用作 painter 笔刷；
  主题切换时直接调用 ``apply_palette()`` 即可。
* **环形动画**：``RingChart.set_value`` 启用 ``QPropertyAnimation`` 插值，
  让 1Hz 采样更新看起来是平滑滚动而不是闪烁跳变。
* **LineChart** 维护一个固定长度的 ``deque`` 历史窗口，超过窗口的老样本
  自动丢弃；多 series 通过不同的 ``stroke_color`` 区分。
"""

from __future__ import annotations

from collections import deque
from typing import Iterable, Sequence

from PySide6.QtCore import (
    Property,
    QEasingCurve,
    QPropertyAnimation,
    QRectF,
    Qt,
    Signal,
)
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QSizePolicy, QWidget

from app.ui.main.pages.page_widgets import PaletteAwareMixin
from app.ui.theme.ds_tokens import FontWeights, _C, ui_font


# ─────────────────────────────────────────────────────────────────────
#  RingChart
# ─────────────────────────────────────────────────────────────────────


class RingChart(PaletteAwareMixin, QWidget):
    """环形进度图。

    Parameters
    ----------
    parent : QWidget, optional
    minimum, maximum : float
        数值范围；``set_value(v)`` 内部按线性映射到 0-100% 进度。
    unit : str
        显示在中心数字下方的小字（默认 ``"%"``）。
    label : str, optional
        中心数字下方第二行（可以用来标资源名）。
    thickness : float
        圆环相对外径的宽度，默认 ``0.18`` (18%)。
    animated : bool
        是否启用进度切换动画（默认 ``True``）。
    """

    valueChanged = Signal(float)

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        minimum: float = 0.0,
        maximum: float = 100.0,
        unit: str = "%",
        label: str | None = None,
        thickness: float = 0.18,
        animated: bool = True,
    ) -> None:
        super().__init__(parent)
        self._init_palette_registry()

        self._min = float(minimum)
        self._max = float(maximum)
        self._unit = unit
        self._label = label
        self._thickness = max(0.05, min(0.5, float(thickness)))
        self._animated = bool(animated)

        self._display = 0.0  # 实际显示在屏幕上的值，用于动画插值
        self._target = 0.0  # 最近一次 set_value 设置的目标
        self._anim: QPropertyAnimation | None = None

        self.setMinimumSize(96, 96)
        self.setSizePolicy(QSizePolicy.Policy.Expanding,
                           QSizePolicy.Policy.Expanding)

        # 主题感知笔刷（每次 paint 重新读取）
        self._refresh_palette_brushes()
        self._apply_style()

    # ── 公开 API ──

    def set_value(self, value: float) -> None:
        """设置当前进度值（动画过渡）。"""
        clamped = max(self._min, min(self._max, float(value)))
        if not self._animated:
            self._display = clamped
            self._target = clamped
            self.update()
            self.valueChanged.emit(clamped)
            return

        # 启动一个 200ms 的插值动画
        if self._anim is not None:
            self._anim.stop()
        anim = QPropertyAnimation(self, b"displayValue", self)
        anim.setDuration(220)
        anim.setStartValue(self._display)
        anim.setEndValue(clamped)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim.finished.connect(lambda v=clamped: self.valueChanged.emit(v))
        self._anim = anim
        self._target = clamped
        anim.start()

    def set_label(self, label: str | None) -> None:
        self._label = label
        self.update()

    def set_unit(self, unit: str) -> None:
        self._unit = unit
        self.update()

    # ── Qt 属性：动画驱动 ──

    def _get_display(self) -> float:
        return self._display

    def _set_display(self, value: float) -> None:
        self._display = value
        self.update()

    displayValue = Property(  # noqa: N815 — Qt 属性名风格
        float,
        fget=_get_display,
        fset=_set_display,
    )

    # ── 主题 / 绘制 ──

    def _refresh_palette_brushes(self) -> None:
        self._track_color = QColor(_C.BORDER_SUBTLE)
        self._progress_color = QColor(_C.NEON_CYAN)
        self._text_color = QColor(_C.TEXT_PRIMARY)
        self._muted_color = QColor(_C.TEXT_MUTED)
        self._grid_color = QColor(_C.GRID_LINE)

    def _apply_style(self) -> None:
        # RingChart 只画图，没 widget QSS；保留方法让主题切换被触发
        self._refresh_palette_brushes()
        self.update()

    def apply_palette(self) -> None:  # type: ignore[override]
        super().apply_palette()
        self._refresh_palette_brushes()
        self.update()

    def paintEvent(self, _event) -> None:  # noqa: D401
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)

        side = min(self.width(), self.height())
        margin = 6.0
        rect = QRectF(
            (self.width() - side) / 2 + margin,
            (self.height() - side) / 2 + margin,
            side - 2 * margin,
            side - 2 * margin,
        )

        ring_pen_width = max(4.0, side * self._thickness)
        radius_offset = ring_pen_width / 2.0
        ring_rect = rect.adjusted(
            radius_offset,
            radius_offset,
            -radius_offset,
            -radius_offset,
        )

        # 1. 底环
        track_pen = QPen(self._track_color, ring_pen_width,
                         Qt.PenStyle.SolidLine)
        track_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(track_pen)
        painter.drawArc(ring_rect, 0, 360 * 16)

        # 2. 进度弧（从顶端 -90° 处开始，顺时针）
        if self._max > self._min:
            ratio = (self._display - self._min) / (self._max - self._min)
        else:
            ratio = 0.0
        ratio = max(0.0, min(1.0, ratio))

        progress_pen = QPen(self._progress_color,
                            ring_pen_width, Qt.PenStyle.SolidLine)
        progress_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(progress_pen)

        span = -int(round(ratio * 360 * 16))  # 顺时针 → 负 span
        if span != 0:
            painter.drawArc(ring_rect, 90 * 16, span)

        # 3. 中心数字 + label
        painter.setPen(QPen(self._text_color))

        number = int(round(self._display)
                     ) if self._max <= 100 and self._min >= 0 else self._display
        big = ui_font(int(side * 0.22), FontWeights.Bold)
        small = ui_font(int(side * 0.10), FontWeights.Medium)

        cx, cy = rect.center().x(), rect.center().y()
        painter.setFont(big)
        painter.drawText(
            QRectF(rect.left(), rect.top(), rect.width(), rect.height() * 0.5),
            Qt.AlignmentFlag.AlignCenter,
            f"{number}{self._unit}",
        )
        if self._label:
            painter.setPen(QPen(self._muted_color))
            painter.setFont(small)
            painter.drawText(
                QRectF(
                    rect.left(),
                    rect.top() + rect.height() * 0.5,
                    rect.width(),
                    rect.height() * 0.4,
                ),
                Qt.AlignmentFlag.AlignCenter,
                self._label,
            )
        painter.end()


# ─────────────────────────────────────────────────────────────────────
#  LineChart
# ─────────────────────────────────────────────────────────────────────


class LineChart(PaletteAwareMixin, QWidget):
    """轻量折线图，零依赖 QPainter 实现。

    Parameters
    ----------
    parent : QWidget, optional
    capacity : int
        历史窗口长度（样本数）。默认 60，配合 1Hz 采样就是 1 分钟。
    ymin, ymax : float
        Y 轴上下界（不传则按 ``add_sample`` 入参动态自适应）。
    stroke_color_token : str
        ``_C`` 上的颜色属性名，默认 ``"NEON_CYAN"``。
    fill : bool
        是否在折线下方填充淡色（半透明 stroke）。
    """

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        capacity: int = 60,
        ymin: float | None = None,
        ymax: float | None = None,
        stroke_color_token: str = "NEON_CYAN",
        fill: bool = True,
    ) -> None:
        super().__init__(parent)
        self._init_palette_registry()

        self._capacity = max(2, int(capacity))
        self._samples: deque[float] = deque(maxlen=self._capacity)
        self._ymin_override = ymin
        self._ymax_override = ymax
        self._stroke_token = stroke_color_token
        self._fill = bool(fill)

        self.setMinimumHeight(80)
        self.setSizePolicy(QSizePolicy.Policy.Expanding,
                           QSizePolicy.Policy.Expanding)

        self._refresh_palette_brushes()
        self._apply_style()

    # ── API ──

    def add_sample(self, value: float) -> None:
        """追加一个样本；超过 ``capacity`` 自动丢弃最老的。"""
        self._samples.append(float(value))
        self.update()

    def extend_samples(self, values: Iterable[float]) -> None:
        for v in values:
            self._samples.append(float(v))
        # 截断到 capacity（deque maxlen 在 append 时已处理，但批量插入仍需裁剪）
        while len(self._samples) > self._capacity:
            self._samples.popleft()
        self.update()

    def clear(self) -> None:
        self._samples.clear()
        self.update()

    @property
    def capacity(self) -> int:
        return self._capacity

    @property
    def samples(self) -> Sequence[float]:
        return tuple(self._samples)

    # ── 主题 / 绘制 ──

    def _refresh_palette_brushes(self) -> None:
        self._stroke_color = QColor(
            getattr(_C, self._stroke_token, _C.NEON_CYAN))
        self._grid_color = QColor(_C.GRID_LINE)
        self._text_color = QColor(_C.TEXT_MUTED)

    def apply_palette(self) -> None:  # type: ignore[override]
        super().apply_palette()
        self._refresh_palette_brushes()
        self.update()

    def _apply_style(self) -> None:
        self._refresh_palette_brushes()

    # ── 计算 ──

    def _y_bounds(self) -> tuple[float, float]:
        if self._ymin_override is not None and self._ymax_override is not None:
            lo, hi = self._ymin_override, self._ymax_override
            if hi <= lo:
                hi = lo + 1.0
            return float(lo), float(hi)

        if not self._samples:
            return 0.0, 1.0
        lo = min(self._samples)
        hi = max(self._samples)
        if hi - lo < 1e-6:
            hi = lo + 1.0
        pad = (hi - lo) * 0.12
        return float(lo - pad), float(hi + pad)

    # ── 绘制 ──

    def paintEvent(self, _event) -> None:  # noqa: D401
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        inset = 6.0
        plot_rect = QRectF(
            inset,
            inset,
            self.width() - 2 * inset,
            self.height() - 2 * inset,
        )

        # 网格线（4 条横线）
        grid_pen = QPen(self._grid_color, 1.0, Qt.PenStyle.SolidLine)
        painter.setPen(grid_pen)
        for i in range(1, 4):
            y = plot_rect.top() + plot_rect.height() * i / 4.0
            painter.drawLine(
                plot_rect.left(),
                y,
                plot_rect.right(),
                y,
            )

        if len(self._samples) < 2:
            painter.end()
            return

        ylo, yhi = self._y_bounds()
        yspan = yhi - ylo if yhi != ylo else 1.0

        n = len(self._samples)
        step_x = plot_rect.width() / (self._capacity -
                                      1) if self._capacity > 1 else plot_rect.width()

        def to_xy(i: int, value: float) -> tuple[float, float]:
            x = plot_rect.left() + step_x * i
            y = plot_rect.bottom() - (value - ylo) / yspan * plot_rect.height()
            return x, y

        # 填充区域
        if self._fill and n >= 2:
            path = QPainterPath()
            x0, y0 = to_xy(0, self._samples[0])
            path.moveTo(x0, plot_rect.bottom())
            path.lineTo(x0, y0)
            for i in range(1, n):
                x, y = to_xy(i, self._samples[i])
                path.lineTo(x, y)
            x_last, _ = to_xy(n - 1, self._samples[-1])
            path.lineTo(x_last, plot_rect.bottom())
            path.closeSubpath()
            fill_color = QColor(self._stroke_color)
            fill_color.setAlphaF(0.18)
            painter.fillPath(path, fill_color)

        # 折线
        line_pen = QPen(self._stroke_color, 2.0, Qt.PenStyle.SolidLine)
        line_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        line_pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(line_pen)

        prev = to_xy(0, self._samples[0])
        for i in range(1, n):
            cur = to_xy(i, self._samples[i])
            painter.drawLine(prev[0], prev[1], cur[0], cur[1])
            prev = cur

        # 最后一个点的实心圆点
        last_x, last_y = to_xy(n - 1, self._samples[-1])
        painter.setBrush(self._stroke_color)
        painter.setPen(Qt.PenStyle.NoPen)
        radius = 3.5
        painter.drawEllipse(
            QRectF(last_x - radius, last_y - radius, radius * 2, radius * 2)
        )
        painter.end()


__all__ = ["RingChart", "LineChart"]
