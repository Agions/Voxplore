"""
Export Plugin Interface
导出格式插件接口
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, IO
from dataclasses import dataclass
from pathlib import Path
from app.plugins.interfaces.base import BasePlugin, PluginType


class BaseExportPlugin(ABC, BasePlugin):
    """
    导出格式插件基类
    
    实现此接口以添加新的导出格式支持
    """

    plugin_type = PluginType.EXPORT

    @abstractmethod
    def get_format_name(self) -> str:
        """获取导出格式名称，如 'MP4', '剪映草稿', 'Adobe Premiere XML'"""
        ...

    @abstractmethod
    def get_file_extension(self) -> str:
        """获取文件扩展名，如 '.mp4', '.json', '.xml'"""
        ...

    @abstractmethod
    def export(
        self,
        project_data: Dict[str, Any],
        output_path: Path,
        options: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        导出项目
        
        Args:
            project_data: 项目数据（包含视频、解说、字幕等信息）
            output_path: 输出文件路径
            options: 导出选项
            
        Returns:
            是否导出成功
        """
        ...

    @abstractmethod
    def get_export_options(self) -> List[Dict[str, Any]]:
        """
        获取导出选项定义
        
        Returns:
            选项列表，每项包含:
            {
                "name": str,
                "type": "string|number|boolean|select",
                "default": Any,
                "choices": List[str],  # for select type
                "description": str,
            }
        """
        ...

    def validate_project(self, project_data: Dict[str, Any]) -> List[str]:
        """
        验证项目数据是否满足导出要求
        
        Returns:
            错误列表，空则验证通过
        """
        errors = []
        if "video_path" not in project_data:
            errors.append("Missing required field: video_path")
        if "narration" not in project_data:
            errors.append("Missing required field: narration")
        return errors
