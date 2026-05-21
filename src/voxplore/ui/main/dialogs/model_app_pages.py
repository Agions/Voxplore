#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
国产模型快捷申请页面
提供便捷的国产AI模型API密钥申请流程
"""

import webbrowser
from typing import List
from dataclasses import dataclass
from enum import Enum

from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QGridLayout, QPushButton, QLabel, QFrame, QWidget,
    QGroupBox, QLineEdit, QTextEdit, QComboBox, QCheckBox, QMessageBox,
    QListWidget, QFormLayout, QWizardPage
)
from PySide6.QtCore import (
    Qt
)

from voxplore.ui.icon_manager import get_icon


class ApplicationStep(Enum):
    """申请步骤枚举"""
    SELECT_PROVIDER = "select_provider"
    VIEW_REQUIREMENTS = "view_requirements"
    FILL_APPLICATION = "fill_application"
    SUBMIT_APPLICATION = "submit_application"
    WAIT_APPROVAL = "wait_approval"
    CONFIGURE_MODEL = "configure_model"
    COMPLETE = "complete"


@dataclass
class ProviderInfo:
    """提供商信息"""
    name: str
    service_name: str
    website: str
    description: str
    application_url: str
    documentation_url: str
    requirements: List[str]
    estimated_time: str
    difficulty: str  # easy, medium, hard
    features: List[str]
    pricing: str


class ProviderSelectionPage(QWizardPage):
    """提供商选择页面"""

    def __init__(self, providers: List[ProviderInfo]):
        super().__init__()
        self.providers = providers
        self.selected_provider = None
        self._init_ui()

    def _init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        # 标题
        title = QLabel("选择AI服务提供商")
        title.setProperty("class", "wizard-title")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        # 描述
        desc = QLabel("请选择您要申请的AI服务提供商，每个提供商都有不同的特点和要求")
        desc.setProperty("class", "wizard-description")
        desc.setWordWrap(True)
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(desc)

        # 提供商选择区域
        providers_container = QWidget()
        providers_layout = QGridLayout(providers_container)

        # 添加提供商卡片
        for i, provider in enumerate(self.providers):
            card = self._create_provider_card(provider)
            providers_layout.addWidget(card, i // 2, i % 2)

        layout.addWidget(providers_container)
        layout.addStretch()

    def _create_provider_card(self, provider: ProviderInfo) -> QFrame:
        """创建提供商卡片"""
        card = QFrame()
        card.setFrameShape(QFrame.Shape.StyledPanel)
        card.setProperty("class", "provider-card")
        card.setFixedSize(280, 200)
        card.mousePressEvent = lambda e: self._select_provider(provider)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        # 提供商名称
        name_label = QLabel(provider.name)
        name_label.setProperty("class", "provider-name")
        name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(name_label)

        # 描述
        desc_label = QLabel(provider.description)
        desc_label.setProperty("class", "provider-description")
        desc_label.setWordWrap(True)
        desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(desc_label)

        # 特性标签
        features_layout = QHBoxLayout()
        for feature in provider.features[:3]:  # 只显示前3个特性
            feature_label = QLabel(feature)
            feature_label.setProperty("class", "provider-feature")
            features_layout.addWidget(feature_label)

        layout.addLayout(features_layout)

        # 难度和时间
        info_layout = QHBoxLayout()
        difficulty_label = QLabel(f"难度: {provider.difficulty}")
        difficulty_label.setProperty("class", "provider-info")
        info_layout.addWidget(difficulty_label)

        info_layout.addWidget(QLabel(" | "))

        time_label = QLabel(f"耗时: {provider.estimated_time}")
        time_label.setProperty("class", "provider-info")
        info_layout.addWidget(time_label)

        layout.addLayout(info_layout)

        # 价格
        price_label = QLabel(provider.pricing)
        price_label.setProperty("class", "provider-price")
        price_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(price_label)

        return card

    def _select_provider(self, provider: ProviderInfo):
        """选择提供商"""
        self.selected_provider = provider
        self.wizard().setProperty("selected_provider", provider)
        self.completeChanged.emit()

    def nextId(self) -> int:
        return 1

    def isComplete(self) -> bool:
        return self.selected_provider is not None


class RequirementsPage(QWizardPage):
    """申请要求页面"""

    def __init__(self):
        super().__init__()
        self.provider = None
        self._init_ui()

    def _init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        # 标题
        self.title_label = QLabel("申请要求")
        self.title_label.setProperty("class", "wizard-title")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.title_label)

        # 提供商信息
        self.provider_info_frame = QFrame()
        self.provider_info_frame.setFrameShape(QFrame.Shape.StyledPanel)
        self.provider_info_frame.setProperty("class", "provider-info-frame")
        provider_info_layout = QVBoxLayout(self.provider_info_frame)

        self.provider_name_label = QLabel()
        self.provider_name_label.setProperty("class", "provider-name")
        provider_info_layout.addWidget(self.provider_name_label)

        self.provider_desc_label = QLabel()
        self.provider_desc_label.setProperty("class", "provider-description")
        self.provider_desc_label.setWordWrap(True)
        provider_info_layout.addWidget(self.provider_desc_label)

        layout.addWidget(self.provider_info_frame)

        # 申请要求
        requirements_group = QGroupBox("申请要求")
        requirements_group.setProperty("class", "wizard-group")
        requirements_layout = QVBoxLayout(requirements_group)

        self.requirements_list = QListWidget()
        self.requirements_list.setProperty("class", "wizard-list")
        requirements_layout.addWidget(self.requirements_list)

        layout.addWidget(requirements_group)

        # 注意事项
        notes_group = QGroupBox("注意事项")
        notes_group.setProperty("class", "wizard-group")
        notes_layout = QVBoxLayout(notes_group)

        notes_label = QLabel(
            "1. 请确保您满足所有申请要求\n"
            "2. 申请过程可能需要实名认证\n"
            "3. 部分服务商可能需要企业认证\n"
            "4. 请仔细阅读服务商的使用条款\n"
            "5. API密钥请妥善保管，不要泄露给他人"
        )
        notes_label.setProperty("class", "wizard-notes")
        notes_label.setWordWrap(True)
        notes_layout.addWidget(notes_label)

        layout.addWidget(notes_group)

        # 按钮区域
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        # 查看文档按钮
        self.docs_btn = QPushButton(get_icon("document", 16), "查看文档")
        self.docs_btn.setFixedSize(100, 32)
        self.docs_btn.clicked.connect(self._view_documentation)
        button_layout.addWidget(self.docs_btn)

        # 访问官网按钮
        self.website_btn = QPushButton(get_icon("globe", 16), "访问官网")
        self.website_btn.setFixedSize(100, 32)
        self.website_btn.clicked.connect(self._visit_website)
        button_layout.addWidget(self.website_btn)

        layout.addLayout(button_layout)
        layout.addStretch()

    def initializePage(self):
        """初始化页面"""
        wizard = self.wizard()
        self.provider = wizard.property("selected_provider")

        if self.provider:
            self.title_label.setText(f"{self.provider.name} 申请要求")
            self.provider_name_label.setText(self.provider.name)
            self.provider_desc_label.setText(self.provider.description)

            # 更新要求列表
            self.requirements_list.clear()
            for requirement in self.provider.requirements:
                self.requirements_list.addItem(f"• {requirement}")

    def _view_documentation(self):
        """查看文档"""
        if self.provider:
            webbrowser.open(self.provider.documentation_url)

    def _visit_website(self):
        """访问官网"""
        if self.provider:
            webbrowser.open(self.provider.website)

    def nextId(self) -> int:
        return 2


class ApplicationFormPage(QWizardPage):
    """申请表单页面"""

    def __init__(self):
        super().__init__()
        self.provider = None
        self._init_ui()

    def _init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        # 标题
        self.title_label = QLabel("填写申请信息")
        self.title_label.setProperty("class", "wizard-title")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.title_label)

        # 表单区域
        form_group = QGroupBox("申请信息")
        form_group.setProperty("class", "wizard-group")
        form_layout = QFormLayout(form_group)

        # 申请类型
        self.app_type_combo = QComboBox()
        self.app_type_combo.addItems(["个人开发者", "企业开发者", "学术研究", "商业应用"])
        form_layout.addRow("申请类型:", self.app_type_combo)

        # 用途描述
        self.purpose_edit = QTextEdit()
        self.purpose_edit.setPlaceholderText("请描述您计划如何使用AI服务...")
        self.purpose_edit.setMaximumHeight(100)
        form_layout.addRow("用途描述:", self.purpose_edit)

        # 预期用量
        self.usage_combo = QComboBox()
        self.usage_combo.addItems(["少量测试", "个人项目", "小型商业", "中型商业", "大型商业"])
        form_layout.addRow("预期用量:", self.usage_combo)

        # 联系方式
        self.contact_edit = QLineEdit()
        self.contact_edit.setPlaceholderText("请输入您的联系方式")
        form_layout.addRow("联系方式:", self.contact_edit)

        layout.addWidget(form_group)

        # 申请须知
        terms_group = QGroupBox("申请须知")
        terms_group.setProperty("class", "wizard-group")
        terms_layout = QVBoxLayout(terms_group)

        self.terms_check = QCheckBox("我已阅读并同意相关服务条款和隐私政策")
        self.terms_check.setProperty("class", "wizard-checkbox")
        terms_layout.addWidget(self.terms_check)

        self.responsibility_check = QCheckBox("我承诺合规使用AI服务，不违反相关法律法规")
        self.responsibility_check.setProperty("class", "wizard-checkbox")
        terms_layout.addWidget(self.responsibility_check)

        layout.addWidget(terms_group)

        layout.addStretch()

    def initializePage(self):
        """初始化页面"""
        wizard = self.wizard()
        self.provider = wizard.property("selected_provider")

        if self.provider:
            self.title_label.setText(f"申请 {self.provider.name}")

    def nextId(self) -> int:
        return 3

    def isComplete(self) -> bool:
        return (self.purpose_edit.toPlainText().strip() and
                self.contact_edit.text().strip() and
                self.terms_check.isChecked() and
                self.responsibility_check.isChecked())


class SubmitApplicationPage(QWizardPage):
    """提交申请页面"""

    def __init__(self):
        super().__init__()
        self.provider = None
        self._init_ui()

    def _init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        # 标题
        self.title_label = QLabel("提交申请")
        self.title_label.setProperty("class", "wizard-title")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.title_label)

        # 申请摘要
        summary_group = QGroupBox("申请摘要")
        summary_group.setProperty("class", "wizard-group")
        summary_layout = QFormLayout(summary_group)

        self.provider_label = QLabel()
        summary_layout.addRow("服务商:", self.provider_label)

        self.app_type_label = QLabel()
        summary_layout.addRow("申请类型:", self.app_type_label)

        self.purpose_label = QLabel()
        self.purpose_label.setWordWrap(True)
        summary_layout.addRow("用途描述:", self.purpose_label)

        self.usage_label = QLabel()
        summary_layout.addRow("预期用量:", self.usage_label)

        self.contact_label = QLabel()
        summary_layout.addRow("联系方式:", self.contact_label)

        layout.addWidget(summary_group)

        # 提交按钮
        submit_layout = QHBoxLayout()
        submit_layout.addStretch()

        self.submit_btn = QPushButton(get_icon("send", 16), "提交申请")
        self.submit_btn.setFixedSize(120, 40)
        self.submit_btn.clicked.connect(self._submit_application)
        submit_layout.addWidget(self.submit_btn)

        layout.addLayout(submit_layout)
        layout.addStretch()

    def initializePage(self):
        """初始化页面"""
        wizard = self.wizard()
        self.provider = wizard.property("selected_provider")

        if self.provider:
            self.title_label.setText(f"提交 {self.provider.name} 申请")

            # 获取前面页面的信息
            app_type = wizard.page(2).app_type_combo.currentText()
            purpose = wizard.page(2).purpose_edit.toPlainText()
            usage = wizard.page(2).usage_combo.currentText()
            contact = wizard.page(2).contact_edit.text()

            # 更新摘要
            self.provider_label.setText(self.provider.name)
            self.app_type_label.setText(app_type)
            self.purpose_label.setText(purpose)
            self.usage_label.setText(usage)
            self.contact_label.setText(contact)

    def _submit_application(self):
        """提交申请"""
        if not self.provider:
            return

        # 这里可以实现实际的申请逻辑
        # 现在只是打开申请页面
        try:
            webbrowser.open(self.provider.application_url)
            QMessageBox.information(
                self,
                "申请已提交",
                f"已为您打开 {self.provider.name} 的申请页面。\n\n"
                f"请按照页面指引完成申请流程。\n\n"
                f"申请完成后，您将获得API密钥。\n\n"
                f"预计审核时间: {self.provider.estimated_time}"
            )
        except Exception as e:
            QMessageBox.warning(self, "打开失败", f"无法打开申请页面: {e}")

    def nextId(self) -> int:
        return -1  # 完成向导

