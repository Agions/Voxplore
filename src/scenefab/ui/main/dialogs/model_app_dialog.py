#!/usr/bin/env python3

"""
模型申请对话框

引导用户申请使用特定 AI 模型的向导式对话框。
"""

from PySide6.QtWidgets import QWizard

from ...icon_manager import get_icon
from .model_app_pages import (
    ApplicationFormPage,
    ProviderInfo,
    ProviderSelectionPage,
    RequirementsPage,
    SubmitApplicationPage,
)


class ModelApplicationDialog(QWizard):
    """AI模型申请对话框"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("AI模型申请向导")
        self.setFixedSize(800, 600)
        self.setWizardStyle(QWizard.WizardStyle.ModernStyle)
        self.setProperty("class", "model-application-wizard")

        # 设置提供商标题
        self.setPixmap(QWizard.WizardPixmap.LogoPixmap, get_icon("ai", 64).pixmap(64, 64))
        self.setPixmap(QWizard.WizardPixmap.BannerPixmap, get_icon("settings", 64).pixmap(64, 64))

        # 创建页面
        self._create_pages()

    def _create_pages(self):
        """创建页面"""
        # 提供商信息
        providers = [
            ProviderInfo(
                name="百度文心一言",
                service_name="wenxin",
                website="https://cloud.baidu.com/product/wenxinworkshop",
                description="百度文心一言大模型，支持多种理解和生成任务",
                application_url="https://cloud.baidu.com/product/wenxinworkshop",
                documentation_url="https://cloud.baidu.com/doc/WENXINWORKSHOP/s/6ltgkzya5",
                requirements=[
                    "需要注册百度云账号",
                    "需要完成实名认证",
                    "需要创建应用获取API密钥",
                    "部分功能需要企业认证"
                ],
                estimated_time="1-3个工作日",
                difficulty="easy",
                features=["文本生成", "翻译", "代码生成"],
                pricing="免费额度 + 按量付费"
            ),
            ProviderInfo(
                name="科大讯飞星火",
                service_name="spark",
                website="https://xinghuo.xfyun.cn",
                description="讯飞星火认知大模型，具备强大的理解和生成能力",
                application_url="https://xinghuo.xfyun.cn",
                documentation_url="https://www.xfyun.cn/doc/spark/HTTP%E8%B0%83%E7%94%A8%E6%96%87%E6%A1%A3.html",
                requirements=[
                    "需要注册讯飞开放平台账号",
                    "需要完成实名认证",
                    "需要创建应用获取API密钥",
                    "部分功能需要审核"
                ],
                estimated_time="1-2个工作日",
                difficulty="easy",
                features=["语音识别", "文本生成", "翻译"],
                pricing="免费额度 + 按量付费"
            ),
            ProviderInfo(
                name="阿里云通义千问",
                service_name="qwen",
                website="https://qianwen.aliyun.com",
                description="通义千问大模型，支持多种理解和生成任务",
                application_url="https://qianwen.aliyun.com",
                documentation_url="https://help.aliyun.com/zh/dashscope/developer-reference/api-details",
                requirements=[
                    "需要注册阿里云账号",
                    "需要完成实名认证",
                    "需要开通DashScope服务",
                    "需要创建API-KEY"
                ],
                estimated_time="1-3个工作日",
                difficulty="medium",
                features=["文本生成", "代码生成", "多模态"],
                pricing="按量付费"
            ),
            ProviderInfo(
                name="智谱AI",
                service_name="glm",
                website="https://open.bigmodel.cn",
                description="智谱GLM大模型，具备强大的理解和生成能力",
                application_url="https://open.bigmodel.cn",
                documentation_url="https://open.bigmodel.cn/dev/api#glm-5",
                requirements=[
                    "需要注册智谱AI平台账号",
                    "需要完成实名认证",
                    "需要创建应用获取API密钥",
                    "支持个人和企业用户"
                ],
                estimated_time="1-2个工作日",
                difficulty="easy",
                features=["文本生成", "代码生成", "长文本"],
                pricing="免费额度 + 按量付费"
            ),
            ProviderInfo(
                name="百川智能",
                service_name="baichuan",
                website="https://www.baichuan-ai.com",
                description="百川大模型，支持多种理解和生成任务",
                application_url="https://platform.baichuan-ai.com",
                documentation_url="https://platform.baichuan-ai.com/docs/api",
                requirements=[
                    "需要注册百川AI平台账号",
                    "需要完成实名认证",
                    "需要创建应用获取API密钥",
                    "支持个人和企业用户"
                ],
                estimated_time="1-2个工作日",
                difficulty="easy",
                features=["文本生成", "翻译", "代码生成"],
                pricing="免费额度 + 按量付费"
            ),
            ProviderInfo(
                name="月之暗面",
                service_name="moonshot",
                website="https://moonshot.cn",
                description="月之暗面大模型，支持超长上下文",
                application_url="https://platform.moonshot.cn",
                documentation_url="https://platform.moonshot.cn/docs/api-reference",
                requirements=[
                    "需要注册月之暗面平台账号",
                    "需要完成实名认证",
                    "需要创建API密钥",
                    "支持个人和企业用户"
                ],
                estimated_time="1-2个工作日",
                difficulty="easy",
                features=["长文本", "文本生成", "代码生成"],
                pricing="按量付费"
            )
        ]

        # 添加页面
        self.addPage(ProviderSelectionPage(providers))
        self.addPage(RequirementsPage())
        self.addPage(ApplicationFormPage())
        self.addPage(SubmitApplicationPage())

    def accept(self):
        """接受对话框"""
        super().accept()

    def reject(self):
        """拒绝对话框"""
        super().reject()