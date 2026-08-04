#!/usr/bin/env python3
"""GlassCard · 毛玻璃卡片（Phase 2 · Dashboard 基础组件）。

设计要点：

* 半透明背景（``BG_GLASS``），在不同主题下分别使用
  ``rgba(255,255,255,0.7)`` / ``rgba(17,24,39,0.6)``。
* 1px 贡虹边框（``PRIMARY`` 颜色 + 33 alpha 弱化），hover 时切换为
  完整饱和的 ``NEON_CYAN``。
* 主题切换时通过 :py:class:`app.ui.main.pages.page_widgets.PaletteAwareMixin`
  重新刷新样式表，保证 dark/light 切换时颜色一致。

注意事项：

* 本组件是 *纯容器*，不持有任何业务数据；调用方在 ``__init__`` 里
  拿到 ``inner_layout`` 添加自己的内容。
* 不引入第三方依赖；不使用 vibrancy 等系统级效果（PySide6 6.9
  ``QGraphicsBlurEffect`` 在不同平台表现差异较大），改用 QSS 模拟。
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QVBoxLayout

from app.ui.main.pages.page_widgets import PaletteAwareMixin
from app.ui.theme.ds_tokens import _C, QSSComponents


class GlassCard(PaletteAwareMixin, QFrame):
    """毛玻璃风格卡片。

    Parameters
    ----------
    parent : QWidget, optional
        父控件。
    title : str, optional
        可选标题（会以加粗中号字渲染在卡片顶部）。
    glow : bool, default ``False``
        是否在 hover 时启用贡虹辉光（额外添加 ``Shadows.GLOW_CYAN``）。
    """

    def __init__(
        self,
        parent=None,
        *,
        title: str | None = None,
        glow: bool = False,
    ) -> None:
        super().__init__(parent)
        self._init_palette_registry()
        self.setObjectName("glass_card")
        self._glow = bool(glow)
        self._title_text = title

        # 内部布局 —— 调用方通过 self.inner_layout 添加子控件
        outer = QVBoxLayout(self)
        outer.setContentsMargins(14, 12, 14, 12)
        outer.setSpacing(10)

        self._title_lbl = None
        if title:
            from PySide6.QtWidgets import QLabel

            self._title_lbl = QLabel(title)
            self._title_lbl.setObjectName("glass_card_title")
            self._set_palette_style(
                self._title_lbl,
                lambda: f"""
                    color: {_C.TEXT_SECONDARY};
                    font-weight: 600;
                    letter-spacing: 0.4px;
                """,
            )
            outer.addWidget(self._title_lbl)

        self.inner_layout = QVBoxLayout()
        self.inner_layout.setContentsMargins(0, 0, 0, 0)
        self.inner_layout.setSpacing(8)
        outer.addLayout(self.inner_layout)

        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._apply_style()

    # ──────────────────────────────────────────────────────────
    # 公开 API
    # ──────────────────────────────────────────────────────────

    def set_title(self, text: str) -> None:
        """动态修改标题（不会重建内部布局）。"""
        if self._title_lbl is not None:
            self._title_lbl.setText(text)
            self._title_text = text

    def set_glow(self, enabled: bool) -> None:
        """切换 hover 贡虹辉光效果。"""
        if self._glow != bool(enabled):
            self._glow = bool(enabled)
            self._apply_style()

    # ──────────────────────────────────────────────────────────
    # 内部
    # ──────────────────────────────────────────────────────────

    def _apply_style(self) -> None:
        """根据当前主题 + glow 设置重写 QSS。

        注意：QSS 字符串必须是**惰性**的，每次重新评估以拿到最新
        的 :py:data:`_C` token 值（在 ``set_theme_mode`` 调用后
        ``_C.BG_GLASS`` 等会重新绑定）。
        """

        def _factory() -> str:
            base = QSSComponents.glass_card()
            if not self._glow:
                return base
            extra = (
                f"QFrame#glass_card:hover {{"
                f"border: 1px solid {_C.NEON_CYAN};"
                f" }}"
            )
            return base + extra

        self._set_palette_style(self, _factory)


__all__ = ["GlassCard"]
