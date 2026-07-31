#!/usr/bin/env python3
"""HelpPanel · Phase 3 内嵌帮助面板。

布局
====

::

    ┌────────────────────────────────────────────────────┐
    │  [搜索框 ____________________________]  [关闭]    │
    ├─────────────────────┬──────────────────────────────┤
    │  分类目录           │   Markdown 渲染区域          │
    │  ├ 快捷键          │   # Title                    │
    │  ├ FAQ             │   body...                    │
    │  ├ 新手引导         │                              │
    │  └ 指南 (66)       │                              │
    │  ...               │                              │
    └─────────────────────┴──────────────────────────────┘

集成点
======

* 主窗口：``main_window`` 通过 :py:class:`QDockWidget` 嵌入右侧。
* 命令面板：执行 ``help.open`` 命令 → 显示 dock 并聚焦搜索框。
* 悬浮提示：监听 :py:class:`HelpTooltipBridge.topicRequested` 信号自动跳转 topic。

i18n
====

面板文本来自 :mod:`app.help.content` 多语言条目池；UI 自身的标签走 ``app.i18n`` 翻译键。
"""

from __future__ import annotations

import logging

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSplitter,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from app.help.models import HelpTopic
from app.help.registry import HelpRegistry
from app.help.tooltip import get_bridge
from app.ui.i18n import t
from app.ui.main.pages.page_widgets import PaletteAwareMixin
from app.ui.theme.ds_tokens import _C, FontWeights, Radii, ui_font


def _tr(key: str, *, default: str | None = None) -> str:
    """``t(key)`` 的便捷封装，未命中时返回 ``default`` 而非 ``[key]``。"""
    text = t(key)
    if text == f"[{key}]" and default is not None:
        return default
    return text


logger = logging.getLogger(__name__)

__all__ = ["HelpPanelWidget"]


# ---------------------------------------------------------------------------
# 简易 Markdown → HTML 转换（够 help 面板用）
# ---------------------------------------------------------------------------


def _render_markdown(md: str) -> str:
    """非常克制的 Markdown → HTML。

    仅识别以下语法：
    - ``# / ## / ###`` 标题
    - ``**bold**``
    - `` `code` ``
    - `` ```code``` `` 块
    - ``- item`` / ``1. item`` 列表
    - 段落 / 空行

    链接只渲染文本（避免面板打开外部 URL 的复杂性）。
    """
    import re

    lines = md.splitlines()
    out: list[str] = []
    in_code = False
    code_buf: list[str] = []
    in_list = False
    list_type: str | None = None  # 'ul' / 'ol'

    def _flush_list() -> None:
        nonlocal in_list, list_type
        if in_list:
            out.append(f"</{list_type}>")
            in_list = False
            list_type = None

    def _flush_code() -> None:
        nonlocal in_code
        if in_code:
            body = "\n".join(code_buf).replace("&", "&amp;").replace(
                "<", "&lt;").replace(">", "&gt;")
            out.append(
                f"<pre style='background:{_C.BG_INPUT};padding:8px;border-radius:6px;'><code>{body}</code></pre>")
            code_buf.clear()
            in_code = False

    for raw in lines:
        stripped = raw.strip()

        # 代码块
        if stripped.startswith("```"):
            if in_code:
                _flush_code()
                continue
            _flush_list()
            in_code = True
            continue
        if in_code:
            code_buf.append(raw)
            continue

        # 标题
        m = re.match(r"^(#{1,6})\s+(.+)$", stripped)
        if m:
            _flush_list()
            level = len(m.group(1))
            content = _inline(m.group(2))
            size = {1: 22, 2: 18, 3: 15, 4: 13}.get(level, 12)
            out.append(
                f"<h{level} style='color:{_C.TEXT_PRIMARY};font-size:{size}px;"
                f"margin:14px 0 6px 0;'>{content}</h{level}>"
            )
            continue

        # 列表项
        ul_match = re.match(r"^[-*]\s+(.+)$", stripped)
        ol_match = re.match(r"^\d+\.\s+(.+)$", stripped)
        if ul_match or ol_match:
            new_type = "ul" if ul_match else "ol"
            content = _inline((ul_match or ol_match).group(1))
            if not in_list:
                list_type = new_type
                out.append(
                    f"<{list_type} style='margin:6px 0;padding-left:18px;color:{_C.TEXT_PRIMARY};'>")
                in_list = True
            elif list_type != new_type:
                _flush_list()
                list_type = new_type
                out.append(
                    f"<{list_type} style='margin:6px 0;padding-left:18px;color:{_C.TEXT_PRIMARY};'>")
                in_list = True
            out.append(f"<li style='margin:2px 0;'>{content}</li>")
            continue

        # 空行
        if not stripped:
            _flush_list()
            out.append("<br/>")
            continue

        # 普通段落
        _flush_list()
        out.append(
            f"<p style='margin:6px 0;color:{_C.TEXT_PRIMARY};line-height:1.5;'>{_inline(stripped)}</p>")

    _flush_list()
    _flush_code()
    return "\n".join(out)


def _inline(text: str) -> str:
    """行内格式：粗体 / 代码 / 链接。"""
    import re
    # 转义基础
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    # 代码（行内）— `xxx` → <code>xxx</code>
    text = re.sub(
        r"`([^`]+)`",
        r"<code style='background:\1bg;padding:1px 4px;border-radius:3px;font-family:monospace;'>\1</code>".replace(
            "\1bg", _C.BG_INPUT
        ),
        text,
    )
    # 粗体 **xxx**
    text = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", text)
    # 链接 [text](url) → text（面板不打开外链）
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    return text


# ---------------------------------------------------------------------------
# 面板 widget
# ---------------------------------------------------------------------------


_CATEGORY_LABELS = {
    "zh_CN": {
        "shortcut": "快捷键",
        "faq": "常见问题",
        "onboarding": "新手引导",
        "guide": "使用指南",
    },
    "en_US": {
        "shortcut": "Shortcuts",
        "faq": "FAQ",
        "onboarding": "Onboarding",
        "guide": "Guides",
    },
}


class HelpPanelWidget(PaletteAwareMixin, QWidget):
    """帮助面板主体 widget。

    Parameters
    ----------
    registry : HelpRegistry, optional
        数据源；默认走 :func:`app.help.tooltip.get_default_registry`。
    """

    topicSelected = Signal(str)  # topic_id

    DEFAULT_WIDTH: int = 720
    DEFAULT_HEIGHT: int = 540

    def __init__(
        self,
        registry: HelpRegistry | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._init_palette_registry()

        from app.help.tooltip import get_default_registry

        self._registry = registry or get_default_registry()
        self._all_items: list[tuple[str, HelpTopic]] = []  # (display, topic)

        self.setObjectName("help_panel_widget")
        self._build_ui()
        self._populate()

        # 订阅 tooltip bridge
        bridge = get_bridge()
        bridge.topicRequested.connect(self.open_topic)

    # ─── UI 构建 ───

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(14, 14, 14, 14)
        outer.setSpacing(10)

        # 顶部行：搜索框 + 关闭按钮
        top_row = QVBoxLayout()
        title = QLabel(_tr("help.panel.title", default="帮助中心"))
        title.setObjectName("help_panel_title")
        title.setFont(ui_font(14, FontWeights.SemiBold))
        top_row.addWidget(title)

        search_row = QVBoxLayout()
        self._search = QLineEdit()
        self._search.setObjectName("help_panel_search")
        self._search.setPlaceholderText(
            _tr("help.panel.search.placeholder", default="搜索主题、快捷键、FAQ…")
        )
        self._search.setFont(ui_font(13))
        self._search.setClearButtonEnabled(True)
        self._search.textChanged.connect(self._on_search_changed)
        search_row.addWidget(self._search)
        top_row.addLayout(search_row)
        outer.addLayout(top_row)

        # 主体：左侧目录 + 右侧内容
        splitter = QSplitter(Qt.Orientation.Horizontal, self)
        splitter.setObjectName("help_panel_splitter")
        splitter.setChildrenCollapsible(False)

        self._list = QListWidget()
        self._list.setObjectName("help_panel_list")
        self._list.setUniformItemSizes(False)
        self._list.itemActivated.connect(self._on_item_activated)
        self._list.currentItemChanged.connect(self._on_item_activated)
        splitter.addWidget(self._list)

        self._browser = QTextBrowser()
        self._browser.setObjectName("help_panel_browser")
        self._browser.setOpenExternalLinks(False)
        self._browser.document().setDefaultStyleSheet(
            f"a {{ color: {_C.NEON_CYAN}; }}"
        )
        splitter.addWidget(self._browser)

        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([220, 500])
        outer.addWidget(splitter, 1)

        # 底部状态行
        self._status = QLabel("")
        self._status.setObjectName("help_panel_status")
        self._status.setFont(ui_font(11))
        outer.addWidget(self._status)

        # 关闭按钮（仅当作为独立 widget 嵌入时使用，例如 SettingsPage）
        self._close_btn = QPushButton(
            _tr("help.panel.close", default="关闭")
        )
        self._close_btn.setObjectName("help_panel_close")
        self._close_btn.clicked.connect(self._on_close_clicked)
        self._close_btn.setVisible(False)  # 默认隐藏；作为 dock 时不需要
        outer.addWidget(self._close_btn)

    # ─── 数据加载 ───

    def _populate(self) -> None:
        """按分类加载所有 topic 到列表。"""
        self._list.clear()
        self._all_items.clear()
        lang = self._detect_language()
        labels = _CATEGORY_LABELS.get(lang, _CATEGORY_LABELS["zh_CN"])

        for category in self._registry.list_categories():
            display = labels.get(category, category)
            header = QListWidgetItem(f"— {display} —")
            header.setData(Qt.ItemDataRole.UserRole, ("__header__", None))
            header.setFlags(Qt.ItemFlag.NoItemFlags)  # 不可选中
            f = header.font()
            f.setBold(True)
            header.setFont(f)
            self._list.addItem(header)
            for topic in self._registry.by_category(category):
                item = QListWidgetItem(f"  {topic.title}")
                item.setData(Qt.ItemDataRole.UserRole, ("topic", topic))
                self._list.addItem(item)
                self._all_items.append((topic.title, topic))

        self._update_status()

    def _update_status(self) -> None:
        total = len(self._registry)
        self._status.setText(
            _tr(
                "help.panel.status",
                default=f"共 {total} 条主题",
            ).format(total=total)
        )

    def _detect_language(self) -> str:
        """从 i18n 探测当前语言。"""
        try:
            from app.i18n import get_current_language
            lang = get_current_language()
        except Exception:  # noqa: BLE001
            lang = "zh-CN"
        return "en_US" if lang.lower().startswith("en") else "zh_CN"

    # ─── 搜索 ───

    def _on_search_changed(self, text: str) -> None:
        text = (text or "").strip().lower()
        if not text:
            # 清空查询 → 显示全部
            for i in range(self._list.count()):
                self._list.item(i).setHidden(False)
            return

        # 有查询 → 走 registry.search
        results = self._registry.search(text, limit=100)
        matched_ids = {r.topic.id for r in results}
        for i in range(self._list.count()):
            item = self._list.item(i)
            payload = item.data(Qt.ItemDataRole.UserRole)
            if not isinstance(payload, tuple) or len(payload) != 2:
                item.setHidden(True)
                continue
            kind, topic = payload
            if kind == "topic" and topic.id in matched_ids:
                item.setHidden(False)
                # 命中：显示 matched_count 提示
            else:
                item.setHidden(True)
        self._update_status()

    # ─── 选中 ───

    def _on_item_activated(self, current: QListWidgetItem | None, _previous=None) -> None:
        if current is None:
            return
        payload = current.data(Qt.ItemDataRole.UserRole)
        if not isinstance(payload, tuple) or payload[0] != "topic":
            return
        topic: HelpTopic = payload[1]
        self._render_topic(topic)
        self.topicSelected.emit(topic.id)

    def _render_topic(self, topic: HelpTopic) -> None:
        """把 HelpTopic 渲染到 QTextBrowser。"""
        md_parts = [f"# {topic.title}"]
        if topic.summary:
            md_parts.append(f"\n_{topic.summary}_")
        if topic.body:
            md_parts.append(f"\n{topic.body}")
        for sec in topic.sections:
            md_parts.append(f"\n### {sec.heading}\n{sec.body}")
        if topic.source:
            md_parts.append(
                f"\n<sub style='color:{_C.TEXT_MUTED};'>来源：`{topic.source}`</sub>"
            )
        html = _render_markdown("\n".join(md_parts))
        self._browser.setHtml(html)

    # ─── 公共 API ───

    def open_topic(self, topic_id: str) -> None:
        """从外部请求打开指定 topic（如 tooltip bridge）。"""
        topic = self._registry.get(topic_id)
        if topic is None:
            return
        # 在列表中选中对应 item
        for i in range(self._list.count()):
            item = self._list.item(i)
            payload = item.data(Qt.ItemDataRole.UserRole)
            if isinstance(payload, tuple) and payload[0] == "topic" and payload[1].id == topic_id:
                self._list.setCurrentItem(item)
                self._render_topic(topic)
                return

    def set_registry(self, registry: HelpRegistry) -> None:
        """替换数据源。"""
        self._registry = registry
        self._populate()

    def _on_close_clicked(self) -> None:
        """当作为独立 widget 嵌入时调用的关闭钩子。"""
        window = self.window()
        if window is not None and hasattr(window, "hide_help_panel"):
            window.hide_help_panel()  # type: ignore[attr-defined]

    # ─── 主题 ───

    def _refresh_palette_brushes(self) -> None:
        # 列表项背景色由 QSS 控制；这里无需缓存 QColor
        return

    def apply_palette(self) -> None:  # type: ignore[override]
        super().apply_palette()
        # 重新渲染当前 topic（让 _C 颜色随主题切换）
        current = self._list.currentItem()
        if current is not None:
            payload = current.data(Qt.ItemDataRole.UserRole)
            if isinstance(payload, tuple) and payload[0] == "topic":
                self._render_topic(payload[1])

    def _apply_style(self) -> None:
        def _factory() -> str:
            return f"""
                #help_panel_widget {{
                    background: {_C.BG_GLASS};
                    color: {_C.TEXT_PRIMARY};
                }}
                #help_panel_title {{
                    color: {_C.TEXT_PRIMARY};
                }}
                #help_panel_search {{
                    background: {_C.BG_INPUT};
                    color: {_C.TEXT_PRIMARY};
                    border: 1px solid {_C.BORDER_SUBTLE};
                    border-radius: 8px;
                    padding: 8px 10px;
                }}
                #help_panel_search:focus {{
                    border-color: {_C.NEON_CYAN};
                }}
                #help_panel_list {{
                    background: transparent;
                    border: 1px solid {_C.BORDER_SUBTLE};
                    border-radius: 8px;
                    padding: 4px;
                    color: {_C.TEXT_PRIMARY};
                }}
                #help_panel_list::item {{
                    padding: 6px 8px;
                    border-radius: 4px;
                }}
                #help_panel_list::item:selected {{
                    background: {_C.PRIMARY_10};
                    color: {_C.NEON_CYAN};
                }}
                #help_panel_browser {{
                    background: transparent;
                    border: 1px solid {_C.BORDER_SUBTLE};
                    border-radius: 8px;
                    padding: 8px 12px;
                    color: {_C.TEXT_PRIMARY};
                }}
                #help_panel_status {{
                    color: {_C.TEXT_MUTED};
                    padding: 2px;
                }}
                #help_panel_close {{
                    background: {_C.BG_INPUT};
                    color: {_C.TEXT_PRIMARY};
                    border: 1px solid {_C.BORDER_SUBTLE};
                    border-radius: {Radii.sm};
                    padding: 6px 14px;
                }}
            """

        self._set_palette_style(self, _factory)

    def showEvent(self, event) -> None:  # type: ignore[override]
        super().showEvent(event)
        if self._list.count() > 0:
            # 默认选中第一项可点击的 topic（跳过 header）
            for i in range(self._list.count()):
                item = self._list.item(i)
                payload = item.data(Qt.ItemDataRole.UserRole)
                if isinstance(payload, tuple) and payload[0] == "topic":
                    self._list.setCurrentRow(i)
                    break
        self._search.setFocus()
