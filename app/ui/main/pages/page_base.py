#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
UI 页面基类扩展
提供通用页面功能，减少重复代码
"""

from typing import Optional, Dict, Any, TYPE_CHECKING
from abc import ABC

from PySide6.QtCore import Signal

if TYPE_CHECKING:
    from ..main_window import MainWindow


class PageState:
    """页面状态管理"""
    
    def __init__(self):
        self._state: Dict[str, Any] = {}
    
    def get(self, key: str, default: Any = None) -> Any:
        return self._state.get(key, default)
    
    def set(self, key: str, value: Any):
        self._state[key] = value
    
    def clear(self):
        self._state.clear()


class PageBase(ABC):
    """
    页面(QWidget基类
    
    提供通用页面功能：
    - 状态管理
    - 生命周期
    - 服务访问
    - 配置访问
    """
    
    # 信号
    state_changed = Signal(str, object)  # key, value
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._main_window: Optional["MainWindow"] = None
        self._page_state = PageState()
        self._is_initialized = False
        self._is_visible = False
    
    def set_main_window(self, main_window: "MainWindow"):
        """设置主窗口引用"""
        self._main_window = main_window
    
    @property
    def main_window(self) -> Optional["MainWindow"]:
        """获取主窗口"""
        return self._main_window
    
    @property
    def app(self):
        """获取应用实例"""
        if self._main_window:
            return self._main_window.app
        return None
    
    # ===== 生命周期 =====
    
    def on_page_show(self):
        """页面显示时调用"""
        self._is_visible = True
    
    def on_page_hide(self):
        """页面隐藏时调用"""
        self._is_visible = False
    
    def on_page_enter(self):
        """进入页面"""
        if not self._is_initialized:
            self.on_init()
            self._is_initialized = True
        self.on_page_show()
    
    def on_page_leave(self):
        """离开页面"""
        self.on_page_hide()
    
    def on_init(self):
        """初始化 - 只调用一次"""
        pass
    
    def on_resize(self, width: int, height: int):
        """窗口大小改变"""
        pass
    
    # ===== 状态管理 =====
    
    def get_state(self, key: str, default: Any = None) -> Any:
        """获取状态"""
        return self._page_state.get(key, default)
    
    def set_state(self, key: str, value: Any):
        """设置状态"""
        self._page_state.set(key, value)
        self.state_changed.emit(key, value)
    
    def clear_state(self):
        """清空状态"""
        self._page_state.clear()
    
    # ===== 服务访问 =====
    
    def get_service(self, service_type: type):
        """获取服务"""
        from app.services import ServiceManager
        return ServiceManager.get(service_type)
    
    def get_config(self, key: str = None, default: Any = None) -> Any:
        """获取配置"""
        from app.utils.config import get_config
        config = get_config()
        if key is None:
            return config
        return config.get(key, default)
    
    # ===== 便捷方法 =====
    
    def show_message(self, message: str, level: str = "info"):
        """显示消息"""
        if self._main_window:
            self._main_window.show_message(message, level)
    
    def show_loading(self, show: bool = True):
        """显示加载"""
        if self._main_window:
            self._main_window.show_loading(show)
    
    def navigate_to(self, page_id: str, **kwargs):
        """导航到页面"""
        if self._main_window:
            self._main_window.navigate_to(page_id, **kwargs)


class PageRegistry:
    """页面注册表"""
    
    _pages: Dict[str, type] = {}
    
    @classmethod
    def register(cls, page_id: str, page_class: type):
        """注册页面"""
        cls._pages[page_id] = page_class
    
    @classmethod
    def get(cls, page_id: str) -> Optional[type]:
        """获取页面类"""
        return cls._pages.get(page_id)
    
    @classmethod
    def list_pages(cls) -> Dict[str, type]:
        """列出所有页面"""
        return cls._pages.copy()


# 便捷装饰器
def register_page(page_id: str):
    """页面注册装饰器"""
    def decorator(cls):
        PageRegistry.register(page_id, cls)
        return cls
    return decorator
