"""
页面加载器 - 处理页面动态加载
"""

from typing import Dict


class PageLoader:
    """页面加载器"""

    # 页面配置映射（仅包含 main_window 实际使用的页面）
    PAGES_CONFIG = [
        {"id": "creator", "name": "AI视频创作", "class": "CreationWizardPage", "attribute": "creation_wizard_page"},
        {"id": "settings", "name": "设置页面", "class": "SettingsPage", "attribute": "settings_page"},
    ]

    @staticmethod
    def get_page_class(page_class_name: str):
        """获取页面类"""
        mapping = {
            "CreationWizardPage": "app.ui.main.pages.creation_wizard_page",
            "SettingsPage": "app.ui.main.pages.settings_page",
            "ProjectsPage": "app.ui.main.pages.projects_page",
            "VideoEditorPage": "app.ui.main.pages.video_editor_page",
        }

        module_path = mapping.get(page_class_name)
        if not module_path:
            raise ImportError(f"未知的页面类: {page_class_name}")

        from importlib import import_module
        module = import_module(module_path)
        return getattr(module, page_class_name)

    @staticmethod
    def get_pages_to_load() -> list:
        """获取要加载的页面列表"""
        return PageLoader.PAGES_CONFIG.copy()

    @staticmethod
    def validate_page_config(config: Dict[str, str]) -> bool:
        """验证页面配置"""
        required_keys = ["id", "name", "class", "attribute"]
        return all(key in config for key in required_keys)
