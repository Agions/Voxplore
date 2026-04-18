"""
主窗口事件处理器
"""

import logging
from typing import Dict, Any
from datetime import datetime


class MainWindowEventHandler:
    """主窗口事件处理器"""
    
    def __init__(self, window):
        self.window = window
        self.logger = logging.getLogger(__name__)
        
        # 状态消息映射
        self._status_messages: Dict[str, str] = {
            "initializing": "正在初始化...",
            "ready": "就绪",
            "loading": "正在加载...",
            "processing": "处理中...",
            "error": "发生错误",
        }
    
    def on_theme_changed(self, theme_name: str):
        """处理主题变更"""
        self.window.is_dark_theme = theme_name == "dark"
        self.window._apply_theme()
        self.window._apply_style()
    
    def on_layout_changed(self, layout_name: str):
        """处理布局变更"""
        self.window.layout_changed.emit(layout_name)
        self.logger.info(f"布局变更为: {layout_name}")
    
    def on_state_changed(self, state: Any):
        """处理应用状态变化"""
        from app.core.application import ApplicationState
        
        status_messages = {
            ApplicationState.INITIALIZING: "正在初始化...",
            ApplicationState.READY: "就绪",
            ApplicationState.LOADING: "正在加载...",
            ApplicationState.PROCESSING: "处理中...",
            ApplicationState.ERROR: "发生错误",
        }
        
        message = status_messages.get(state, str(state))
        self.window.statusBar().showMessage(message)
    
    def on_error(self, error_type: str, error_message: str):
        """处理错误事件"""
        self.logger.error(f"应用错误: {error_type} - {error_message}")
        self.window.statusBar().showMessage(f"错误: {error_message}", 5000)
    
    def update_current_time(self):
        """更新当前时间显示"""
        try:
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            if hasattr(self.window, 'current_time'):
                self.window.current_time.setText(current_time)
        except Exception as e:
            self.logger.error(f"更新时间失败: {e}")
    
    def get_status_message(self, state_key: str) -> str:
        """获取状态消息"""
        return self._status_messages.get(state_key, str(state_key))
