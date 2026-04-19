#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Voxplore 主窗口 — 薄壳架构 v2
REDESIGNED: 页面切换动画（OutCubic 250ms）· 导航宽度 64px
"""

import os
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QStackedWidget, QStatusBar, QFrame, QLabel, QPushButton
)
from PySide6.QtCore import Qt, Signal, QPropertyAnimation, QEasingCurve, QRect
from PySide6.QtGui import QFont

from ...core.application import Application
from ...core.logger import Logger
from app.ui.components.design_system import Colors


class VoxploreWindow(QMainWindow):
    """主窗口 v2 — 导航 64px + 页面滑入动画"""

    status_updated = Signal(str)

    def __init__(self, application: Application):
        super().__init__()
        self.application = application
        self.logger = application.get_service_by_name("logger") or Logger("VoxploreWindow")
        self.setWindowTitle("Voxplore — AI First-Person Video Narrator")
        self.resize(1280, 800)
        self.setMinimumSize(900, 600)

        qss_path = os.path.join(os.path.dirname(__file__), "../theme/narrafiilm.qss")
        if os.path.exists(qss_path):
            self.setStyleSheet(open(qss_path).read())

        self._pages = {}
        self._current_page = None
        self._is_animating = False
        self._init_ui()
        self._load_pages()
        self._navigate_to("creator")
        self.logger.info("Voxplore 主窗口初始化完成 (v2)")

    def _init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.left_panel = QFrame()
        self.left_panel.setObjectName("left_panel")
        self.left_panel.setFixedWidth(64)
        self._build_nav()
        main_layout.addWidget(self.left_panel)

        self.page_stack = QStackedWidget()
        self.page_stack.setObjectName("page_stack")
        main_layout.addWidget(self.page_stack, 1)

        self.status_bar = QStatusBar()
        self.status_bar.setFixedHeight(26)
        self.status_bar.setStyleSheet(f"QStatusBar {{ color: {Colors.TextMuted}; font-size: 11px; background: {Colors.BgBase}; }}")
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("就绪")

    def _build_nav(self):
        layout = QVBoxLayout(self.left_panel)
        layout.setContentsMargins(0, 16, 0, 16)
        layout.setSpacing(8)

        logo_icon = QLabel("🎬")
        logo_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo_icon.setStyleSheet("font-size: 22px; padding: 4px;")
        logo_layout = QVBoxLayout()
        logo_layout.setContentsMargins(0, 0, 0, 0)
        logo_layout.setSpacing(2)
        logo_layout.addWidget(logo_icon)
        logo_text = QLabel("NARR")
        logo_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo_text.setStyleSheet(f"color: {Colors.Primary}; font-size: 8px; font-weight: 800; letter-spacing: 0.15em;")
        logo_layout.addWidget(logo_text)
        logo_container = QWidget()
        logo_container.setLayout(logo_layout)
        layout.addWidget(logo_container)
        layout.addSpacing(16)

        self.nav_buttons = {}
        nav_items = [("creator", "🏠", "创作台"), ("settings", "⚙️", "设置")]
        for page_id, icon, tip in nav_items:
            btn = QPushButton(icon)
            btn.setObjectName("nav_icon_btn")
            btn.setFixedSize(40, 40)
            btn.setToolTip(tip)
            btn.setCheckable(True)
            btn.setStyleSheet(
                f"QPushButton {{ background: transparent; border: none; border-radius: 10px; font-size: 18px; }} "
                f"QPushButton:hover {{ background: {Colors.BgElevated}; }} "
                f"QPushButton:checked {{ background: {Colors.PrimarySubtle}; }}"
            )
            btn.clicked.connect(lambda _, p=page_id: self._navigate_to(p))
            layout.addWidget(btn, alignment=Qt.AlignmentFlag.AlignCenter)
            self.nav_buttons[page_id] = btn

        layout.addStretch()
        ver = QLabel("v3.2")
        ver.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ver.setStyleSheet(f"color: {Colors.TextMuted}; font-size: 9px; font-weight: 600;")
        layout.addWidget(ver, alignment=Qt.AlignmentFlag.AlignCenter)

    def _load_pages(self):
        from .pages.creation_wizard_page import CreationWizardPage
        creator = CreationWizardPage("creator", "创作台", self.application)
        creator.create_content()
        creator.page_activated.connect(self._on_page_activated)
        self.page_stack.addWidget(creator)
        self._pages["creator"] = creator

        from .pages.settings_page import SettingsPage
        settings = SettingsPage("settings", "设置", self.application)
        settings.create_content()
        settings.page_activated.connect(self._on_page_activated)
        self.page_stack.addWidget(settings)
        self._pages["settings"] = settings

    def _navigate_to(self, page_id: str):
        if page_id not in self._pages or self._is_animating or page_id == self._current_page:
            return
        for pid, btn in self.nav_buttons.items():
            btn.setChecked(pid == page_id)
        self._is_animating = True
        old_page = self._pages.get(self._current_page)
        new_page = self._pages[page_id]
        rect = self.page_stack.geometry()
        if rect.isNull() or rect.width() == 0:
            new_page.setGeometry(rect)
            self.page_stack.setCurrentWidget(new_page)
            self._is_animating = False
        else:
            new_page.setGeometry(rect.right(), 0, rect.width(), rect.height())
            self.page_stack.setCurrentWidget(new_page)
            self._slide_animation(old_page, new_page, rect)
        self._current_page = page_id
        new_page.activate()

    def _slide_animation(self, old_page, new_page, rect):
        if old_page is None:
            new_page.setGeometry(rect)
            self._is_animating = False
            return
        old_anim = QPropertyAnimation(old_page, b"geometry")
        old_anim.setDuration(250)
        old_anim.setStartValue(rect)
        old_anim.setEndValue(QRect(rect.left() - rect.width() // 2, 0, rect.width(), rect.height()))
        old_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        new_anim = QPropertyAnimation(new_page, b"geometry")
        new_anim.setDuration(250)
        new_anim.setStartValue(QRect(rect.right(), 0, rect.width(), rect.height()))
        new_anim.setEndValue(rect)
        new_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        old_anim.start()
        new_anim.start()
        old_anim.finished.connect(lambda: old_page.setGeometry(rect) if old_page else None)
        new_anim.finished.connect(lambda: setattr(self, '_is_animating', False))

    def _on_page_activated(self):
        pass

    def show_status(self, msg: str):
        self.status_bar.showMessage(msg)


MainWindow = VoxploreWindow
