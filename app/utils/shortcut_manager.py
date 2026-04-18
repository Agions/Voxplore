"""
快捷键管理器
提供统一的快捷键配置和管理功能
"""

import logging
from typing import Dict, Callable, Optional, List, Any
from dataclasses import dataclass
from enum import Enum
from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QKeySequence, QShortcut

logger = logging.getLogger(__name__)


class ShortcutCategory(Enum):
    """快捷键分类"""
    FILE = "文件"
    EDIT = "编辑"
    VIEW = "视图"
    PLAYBACK = "播放"
    EXPORT = "导出"
    AI = "AI 功能"
    CUSTOM = "自定义"


@dataclass
class ShortcutInfo:
    """快捷键信息"""
    id: str
    name: str
    category: ShortcutCategory
    sequence: str  # 如 "Ctrl+S"
    description: str
    handler: Optional[Callable] = None
    enabled: bool = True


class ShortcutManager(QObject):
    """快捷键管理器"""
    
    # 信号
    shortcut_triggered = Signal(str)  # 快捷键触发信号
    
    # 默认快捷键配置
    DEFAULT_SHORTCUTS: List[ShortcutInfo] = [
        # 文件操作
        ShortcutInfo("new_project", "新建项目", ShortcutCategory.FILE, "Ctrl+N", "创建新项目"),
        ShortcutInfo("open_project", "打开项目", ShortcutCategory.FILE, "Ctrl+O", "打开已有项目"),
        ShortcutInfo("save_project", "保存项目", ShortcutCategory.FILE, "Ctrl+S", "保存当前项目"),
        ShortcutInfo("save_as", "另存为", ShortcutCategory.FILE, "Ctrl+Shift+S", "另存为"),
        ShortcutInfo("export", "导出视频", ShortcutCategory.FILE, "Ctrl+E", "导出当前项目"),
        ShortcutInfo("quit", "退出应用", ShortcutCategory.FILE, "Ctrl+Q", "退出应用"),
        
        # 编辑操作
        ShortcutInfo("undo", "撤销", ShortcutCategory.EDIT, "Ctrl+Z", "撤销上一步操作"),
        ShortcutInfo("redo", "重做", ShortcutCategory.EDIT, "Ctrl+Y", "重做撤销的操作"),
        ShortcutInfo("cut", "剪切", ShortcutCategory.EDIT, "Ctrl+X", "剪切选中的片段"),
        ShortcutInfo("copy", "复制", ShortcutCategory.EDIT, "Ctrl+C", "复制选中的片段"),
        ShortcutInfo("paste", "粘贴", ShortcutCategory.EDIT, "Ctrl+V", "粘贴复制的片段"),
        ShortcutInfo("delete", "删除", ShortcutCategory.EDIT, "Delete", "删除选中的片段"),
        ShortcutInfo("select_all", "全选", ShortcutCategory.EDIT, "Ctrl+A", "选中所有片段"),
        
        # 视图操作
        ShortcutInfo("toggle_sidebar", "切换侧边栏", ShortcutCategory.VIEW, "Ctrl+B", "显示/隐藏侧边栏"),
        ShortcutInfo("toggle_preview", "切换预览", ShortcutCategory.VIEW, "Space", "播放/暂停预览"),
        ShortcutInfo("zoom_in", "放大", ShortcutCategory.VIEW, "Ctrl+=", "放大时间轴"),
        ShortcutInfo("zoom_out", "缩小", ShortcutCategory.VIEW, "Ctrl+-", "缩小时间轴"),
        ShortcutInfo("fit_timeline", "适应窗口", ShortcutCategory.VIEW, "Ctrl+0", "时间轴适应窗口"),
        
        # 播放操作
        ShortcutInfo("play_pause", "播放/暂停", ShortcutCategory.PLAYBACK, "Space", "播放或暂停"),
        ShortcutInfo("stop", "停止", ShortcutCategory.PLAYBACK, "Escape", "停止播放"),
        ShortcutInfo("frame_forward", "下一帧", ShortcutCategory.PLAYBACK, "Right", "前进一帧"),
        ShortcutInfo("frame_backward", "上一帧", ShortcutCategory.PLAYBACK, "Left", "后退一帧"),
        ShortcutInfo("go_to_start", "跳转到开始", ShortcutCategory.PLAYBACK, "Home", "跳转到视频开始"),
        ShortcutInfo("go_to_end", "跳转到结束", ShortcutCategory.PLAYBACK, "End", "跳转到视频结束"),
        ShortcutInfo("set_in_point", "设置入点", ShortcutCategory.PLAYBACK, "I", "设置入点"),
        ShortcutInfo("set_out_point", "设置出点", ShortcutCategory.PLAYBACK, "O", "设置出点"),
        
        # 导出操作
        ShortcutInfo("quick_export", "快速导出", ShortcutCategory.EXPORT, "Ctrl+Shift+E", "使用默认设置快速导出"),
        ShortcutInfo("export_settings", "导出设置", ShortcutCategory.EXPORT, "Ctrl+Alt+E", "打开导出设置"),
        
        # AI 功能
        ShortcutInfo("ai_analyze", "AI 分析", ShortcutCategory.AI, "Ctrl+Shift+A", "分析当前视频"),
        ShortcutInfo("ai_clip", "AI 剪辑", ShortcutCategory.AI, "Ctrl+Shift+C", "智能剪辑"),
        ShortcutInfo("ai_subtitle", "AI 字幕", ShortcutCategory.AI, "Ctrl+Shift+S", "生成字幕"),
        ShortcutInfo("ai_voice", "AI 配音", ShortcutCategory.AI, "Ctrl+Shift+V", "生成配音"),
        ShortcutInfo("ai_dub", "AI 翻译", ShortcutCategory.AI, "Ctrl+Shift+T", "翻译配音"),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._shortcuts: Dict[str, ShortcutInfo] = {}
        self._q_shortcuts: Dict[str, QShortcut] = {}
        self._handlers: Dict[str, Callable] = {}
        self._enabled = True
        
        # 初始化默认快捷键
        self._init_default_shortcuts()

    def _init_default_shortcuts(self) -> None:
        """初始化默认快捷键"""
        for shortcut in self.DEFAULT_SHORTCUTS:
            self._shortcuts[shortcut.id] = shortcut

    def register_shortcut(
        self,
        shortcut_id: str,
        name: str,
        sequence: str,
        category: ShortcutCategory,
        description: str,
        handler: Optional[Callable] = None
    ) -> bool:
        """
        注册自定义快捷键
        
        Args:
            shortcut_id: 快捷键 ID
            name: 快捷键名称
            sequence: 快捷键序列
            category: 分类
            description: 描述
            handler: 处理函数
            
        Returns:
            是否注册成功
        """
        try:
            shortcut = ShortcutInfo(
                id=shortcut_id,
                name=name,
                category=category,
                sequence=sequence,
                description=description,
                handler=handler,
                enabled=True
            )
            self._shortcuts[shortcut_id] = shortcut
            
            if handler:
                self._handlers[shortcut_id] = handler
                self._register_q_shortcut(shortcut)
                
            logger.info(f"注册快捷键: {shortcut_id} -> {sequence}")
            return True
            
        except Exception as e:
            logger.error(f"注册快捷键失败: {shortcut_id}, {e}")
            return False

    def _register_q_shortcut(self, shortcut: ShortcutInfo) -> None:
        """注册 Qt 快捷键"""
        try:
            app = QApplication.instance()
            if app is None:
                return
                
            key_sequence = QKeySequence(shortcut.sequence)
            q_shortcut = QShortcut(key_sequence, app)
            q_shortcut.activated.connect(
                lambda: self._handle_shortcut(shortcut.id)
            )
            self._q_shortcuts[shortcut.id] = q_shortcut
            
        except Exception as e:
            logger.warning(f"注册 Qt 快捷键失败: {shortcut.id}, {e}")

    def _handle_shortcut(self, shortcut_id: str) -> None:
        """处理快捷键触发"""
        if not self._enabled:
            return
            
        shortcut = self._shortcuts.get(shortcut_id)
        if shortcut and shortcut.enabled:
            handler = self._handlers.get(shortcut_id)
            if handler:
                try:
                    handler()
                except Exception as e:
                    logger.error(f"执行快捷键失败: {shortcut_id}, {e}")
                    
            self.shortcut_triggered.emit(shortcut_id)

    def unregister_shortcut(self, shortcut_id: str) -> bool:
        """注销快捷键"""
        if shortcut_id in self._shortcuts:
            del self._shortcuts[shortcut_id]
            
        if shortcut_id in self._q_shortcuts:
            self._q_shortcuts[shortcut_id].deleteLater()
            del self._q_shortcuts[shortcut_id]
            
        if shortcut_id in self._handlers:
            del self._handlers[shortcut_id]
            
        return True

    def set_handler(self, shortcut_id: str, handler: Callable) -> bool:
        """设置快捷键处理函数"""
        if shortcut_id in self._shortcuts:
            self._handlers[shortcut_id] = handler
            
            # 重新注册 Qt 快捷键
            if shortcut_id in self._q_shortcuts:
                self._q_shortcuts[shortcut_id].deleteLater()
                
            self._register_q_shortcut(self._shortcuts[shortcut_id])
            return True
        return False

    def enable_shortcut(self, shortcut_id: str) -> bool:
        """启用快捷键"""
        if shortcut_id in self._shortcuts:
            self._shortcuts[shortcut_id].enabled = True
            if shortcut_id in self._q_shortcuts:
                self._q_shortcuts[shortcut_id].setEnabled(True)
            return True
        return False

    def disable_shortcut(self, shortcut_id: str) -> bool:
        """禁用快捷键"""
        if shortcut_id in self._shortcuts:
            self._shortcuts[shortcut_id].enabled = False
            if shortcut_id in self._q_shortcuts:
                self._q_shortcuts[shortcut_id].setEnabled(False)
            return True
        return False

    def update_sequence(self, shortcut_id: str, sequence: str) -> bool:
        """更新快捷键序列"""
        if shortcut_id in self._shortcuts:
            self._shortcuts[shortcut_id].sequence = sequence
            
            # 重新注册 Qt 快捷键
            if shortcut_id in self._q_shortcuts:
                self._q_shortcuts[shortcut_id].deleteLater()
                
            self._register_q_shortcut(self._shortcuts[shortcut_id])
            return True
        return False

    def get_shortcut(self, shortcut_id: str) -> Optional[ShortcutInfo]:
        """获取快捷键信息"""
        return self._shortcuts.get(shortcut_id)

    def get_shortcuts_by_category(self, category: ShortcutCategory) -> List[ShortcutInfo]:
        """获取分类下的所有快捷键"""
        return [
            s for s in self._shortcuts.values()
            if s.category == category
        ]

    def get_all_shortcuts(self) -> List[ShortcutInfo]:
        """获取所有快捷键"""
        return list(self._shortcuts.values())

    def set_enabled(self, enabled: bool) -> None:
        """设置全局启用/禁用"""
        self._enabled = enabled
        for q_shortcut in self._q_shortcuts.values():
            q_shortcut.setEnabled(enabled)

    def reset_to_default(self) -> None:
        """重置为默认快捷键"""
        # 清理现有
        self._shortcuts.clear()
        self._q_shortcuts.clear()
        self._handlers.clear()
        
        # 重新初始化
        self._init_default_shortcuts()

    def export_config(self) -> Dict[str, Any]:
        """导出配置"""
        return {
            shortcut_id: {
                "sequence": shortcut.sequence,
                "enabled": shortcut.enabled
            }
            for shortcut_id, shortcut in self._shortcuts.items()
        }

    def import_config(self, config: Dict[str, Any]) -> None:
        """导入配置"""
        for shortcut_id, settings in config.items():
            if shortcut_id in self._shortcuts:
                if "sequence" in settings:
                    self.update_sequence(shortcut_id, settings["sequence"])
                if "enabled" in settings:
                    if settings["enabled"]:
                        self.enable_shortcut(shortcut_id)
                    else:
                        self.disable_shortcut(shortcut_id)


# 全局实例
_shortcut_manager: Optional[ShortcutManager] = None


def get_shortcut_manager() -> ShortcutManager:
    """获取全局快捷键管理器"""
    global _shortcut_manager
    if _shortcut_manager is None:
        _shortcut_manager = ShortcutManager()
    return _shortcut_manager
