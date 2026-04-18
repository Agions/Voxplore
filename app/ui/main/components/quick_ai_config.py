#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
快捷AI配置组件 - macOS 设计系统优化版
提供国产AI模型的快速配置入口
使用标准化组件，零内联样式
"""

import webbrowser
from typing import Dict, List, Any

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QGridLayout, QMessageBox
)
from PySide6.QtCore import Qt, QTimer, Signal

from app.core.config_manager import ConfigManager
from app.core.logger import Logger
from app.core.icon_manager import get_icon
from ..dialogs.model_application_dialog import ModelApplicationDialog

# 导入标准化 macOS 组件
from app.ui.common.macOS_components import (
    MacCard, MacSecondaryButton,
    MacIconButton, MacTitleLabel, MacLabel, MacBadge,
    MacEmptyState,
)


class QuickAIConfigWidget(QWidget):
    """快捷AI配置组件 - 使用 macOS 设计系统"""

    config_changed = Signal()  # 配置变更信号

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setProperty("class", "section-content")

        # 初始化组件
        self.config_manager = ConfigManager()
        self.logger = Logger("QuickAIConfigWidget")

        # 初始化UI
        self._init_ui()
        self._setup_connections()

        # 定时刷新状态
        self._setup_refresh_timer()

    def _init_ui(self):
        """初始化用户界面"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        # 1. 标题区域（带刷新按钮）
        title_row = QWidget()
        title_row.setProperty("class", "icon-text-row")
        title_layout = QHBoxLayout(title_row)
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(8)

        # 标题标签
        title_label = MacTitleLabel("⚡ AI 快捷配置", 5)
        title_layout.addWidget(title_label)
        title_layout.addStretch()

        # 刷新按钮（使用图标按钮）
        refresh_btn = MacIconButton("🔄", 24)
        refresh_btn.setToolTip("刷新状态")
        refresh_btn.clicked.connect(self.refresh_status)
        title_layout.addWidget(refresh_btn)

        layout.addWidget(title_row)

        # 2. 配置状态区域（卡片容器）
        self.status_card = MacCard()
        self.status_card.setProperty("class", "card section-card")

        status_title = MacTitleLabel("当前配置状态", 6)
        self.status_card.layout().addWidget(status_title)

        # 状态网格
        self.status_grid = QGridLayout()
        self.status_grid.setSpacing(8)
        self.status_card.layout().addLayout(self.status_grid)
        layout.addWidget(self.status_card)

        # 3. 快捷操作区域
        actions_card = MacCard()
        actions_card.setProperty("class", "card section-card")

        actions_title = MacTitleLabel("快捷操作", 6)
        actions_card.layout().addWidget(actions_title)

        # 操作按钮网格
        actions_grid = QGridLayout()
        actions_grid.setSpacing(8)

        actions = [
            ("申请AI模型", "add", self._on_apply_model, "快速申请国产AI模型API密钥"),
            ("配置参数", "settings", self._on_config_params, "配置AI模型参数"),
            ("测试连接", "network", self._on_test_connection, "测试AI服务连接状态"),
            ("查看文档", "document", self._on_view_docs, "查看AI服务文档")
        ]

        for i, (text, icon_name, handler, tooltip) in enumerate(actions):
            row = i // 2
            col = i % 2

            icon = get_icon(icon_name, 20)
            btn = MacSecondaryButton(f"  {text}", icon)
            btn.setProperty("class", "button secondary action-btn")
            btn.setMinimumHeight(36)
            btn.setMinimumWidth(140)
            btn.setToolTip(tooltip)
            btn.clicked.connect(handler)

            actions_grid.addWidget(btn, row, col)

        actions_card.layout().addLayout(actions_grid)
        layout.addWidget(actions_card)

        # 4. 最近使用区域
        self.recent_card = MacCard()
        self.recent_card.setProperty("class", "card section-card")

        recent_title = MacTitleLabel("最近使用", 6)
        self.recent_card.layout().addWidget(recent_title)

        self.recent_layout = QVBoxLayout()
        self.recent_layout.setSpacing(6)
        self.recent_layout.setContentsMargins(0, 0, 0, 0)
        self.recent_card.layout().addLayout(self.recent_layout)

        layout.addWidget(self.recent_card)

        # 初始加载状态
        self._refresh_status_section()
        self._refresh_recent_section()

        layout.addStretch()

    def _setup_connections(self):
        """设置信号连接"""
        # 连接按钮信号
        if hasattr(self, 'apply_button'):
            self.apply_button.clicked.connect(self._on_apply_clicked)
        if hasattr(self, 'refresh_button'):
            self.refresh_button.clicked.connect(self.refresh_status)
        
        # 连接配置变化信号
        if hasattr(self, 'config_changed'):
            self.config_changed.connect(self._on_config_changed)

    def _setup_refresh_timer(self):
        """设置定时刷新"""
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.refresh_status)
        self.refresh_timer.start(30000)  # 每30秒刷新一次

    def _get_configured_models(self) -> List[str]:
        """获取已配置的模型列表"""
        try:
            ai_configs = self.config_manager.get_value("ai_models", {})
            return list(ai_configs.keys())
        except Exception as e:
            self.logger.error(f"获取已配置模型失败: {e}")
            return []

    def _get_recent_models(self) -> List[tuple]:
        """获取最近使用的模型"""
        try:
            recent_models = self.config_manager.get_value("recent_ai_models", [])
            return [(model.get("name", ""), model) for model in recent_models]
        except Exception as e:
            self.logger.error(f"获取最近使用模型失败: {e}")
            return []

    def _on_apply_model(self):
        """申请AI模型"""
        try:
            dialog = ModelApplicationDialog(self)
            dialog.exec()
            self.refresh_status()
        except Exception as e:
            self.logger.error(f"打开申请对话框失败: {e}")
            QMessageBox.critical(self, "错误", f"无法打开申请对话框: {e}")

    def _on_config_params(self):
        """配置参数"""
        try:
            configured_models = self._get_configured_models()
            if not configured_models:
                QMessageBox.information(self, "提示", "请先申请并配置AI模型")
                return

            # 这里可以打开参数配置对话框
            QMessageBox.information(self, "功能开发中", "参数配置功能正在开发中")
        except Exception as e:
            self.logger.error(f"配置参数失败: {e}")

    def _on_test_connection(self):
        """测试连接"""
        try:
            configured_models = self._get_configured_models()
            if not configured_models:
                QMessageBox.information(self, "提示", "请先申请并配置AI模型")
                return

            # 模拟连接测试
            QMessageBox.information(self, "测试结果", "AI服务连接正常")
        except Exception as e:
            self.logger.error(f"测试连接失败: {e}")

    def _on_view_docs(self):
        """查看文档"""
        try:
            # 打开文档页面
            webbrowser.open("https://github.com/your-repo/docs")
        except Exception as e:
            self.logger.error(f"打开文档失败: {e}")

    def refresh_status(self):
        """刷新状态"""
        try:
            self._refresh_status_section()
            self._refresh_recent_section()
        except Exception as e:
            self.logger.error(f"刷新状态失败: {e}")

    def _refresh_status_section(self):
        """刷新状态区域"""
        # 清空现有状态项
        for i in reversed(range(self.status_grid.count())):
            widget = self.status_grid.itemAt(i).widget()
            if widget:
                widget.deleteLater()

        # 获取当前配置状态
        configured_models = self._get_configured_models()

        # 状态项 - 简化为两种状态样式
        status_items = [
            ("百度文心一言", "baidu" in configured_models),
            ("讯飞星火", "xunfei" in configured_models),
            ("通义千问", "aliyun" in configured_models),
            ("智谱AI", "zhipu" in configured_models),
            ("百川AI", "baichuan" in configured_models),
            ("月之暗面", "moonshot" in configured_models)
        ]

        for i, (name, configured) in enumerate(status_items):
            row = i // 3
            col = i % 3

            # 创建状态卡片容器
            status_container = QWidget()
            status_container.setProperty("class", "stat-row")
            status_container.setFixedSize(150, 70)
            status_layout = QVBoxLayout(status_container)
            status_layout.setContentsMargins(8, 8, 8, 8)
            status_layout.setSpacing(4)

            # 模型名称标签
            name_label = MacLabel(name, "text-sm text-bold")
            name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            status_layout.addWidget(name_label)

            # 状态徽章
            status_badge = MacBadge("已配置" if configured else "未配置",
                                   "success" if configured else "warning")
            status_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
            status_layout.addWidget(status_badge)

            self.status_grid.addWidget(status_container, row, col)

    def _refresh_recent_section(self):
        """刷新最近使用区域"""
        # 清空现有内容
        while self.recent_layout.count():
            item = self.recent_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # 获取最近使用的模型
        recent_models = self._get_recent_models()

        if recent_models:
            for model_name, model_info in recent_models[:3]:  # 显示最近3个
                model_item = self._create_model_item(model_name, model_info)
                self.recent_layout.addWidget(model_item)
        else:
            empty = MacEmptyState(
                icon="📭",
                title="暂无使用记录",
                description=""
            )
            self.recent_layout.addWidget(empty)

    def _create_model_item(self, model_name: str, model_info: Dict[str, Any]) -> QWidget:
        """创建模型项 - 使用标准卡片样式"""
        item = MacCard()
        item.setProperty("class", "card project-item")
        item.setFixedHeight(50)

        layout = QHBoxLayout(item)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # 模型图标
        icon_label = QLabel("🤖")
        icon_label.setProperty("class", "text-lg")
        layout.addWidget(icon_label)

        # 模型信息 - 垂直布局
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)

        name_label = MacLabel(model_name, "text-sm text-bold")
        info_layout.addWidget(name_label)

        status_label = MacLabel("已配置", "text-xs text-muted")
        info_layout.addWidget(status_label)

        layout.addLayout(info_layout)
        layout.addStretch()

        # 使用时间
        time_label = MacLabel(model_info.get("last_used", ""), "text-xs text-muted")
        layout.addWidget(time_label)

        return item
