
# AUTO-CLEANUP-CANDIDATE (2026-06-09):
# 1118 行 CLI 死代码 — 仓库无任何文件 import scenefab.cli.* (除了自身)
# 主人 (何进) 偏好"继续推进"/"不要废话", 但 1118 行是大改动
# 保守标记: 留待主人确认后删除, 不在本次 refactor 中删除

"""
SceneFab CLI
命令行接口模块

提供以下功能:
- 项目管理 (创建、列表、删除)
- 视频处理流水线启动
- 插件管理
- 服务器模式切换
"""

from scenefab.cli.main import create_cli, run

__all__ = ["create_cli", "run"]
