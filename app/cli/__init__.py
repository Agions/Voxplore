"""
Voxplore CLI
命令行接口模块

提供以下功能:
- 项目管理 (创建、列表、删除)
- 视频处理流水线启动
- 插件管理
- 服务器模式切换
"""

from app.cli.main import create_cli, run

__all__ = ["create_cli", "run"]
