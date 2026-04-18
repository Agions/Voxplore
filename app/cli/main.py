"""
Voxplore CLI Main Entry
命令行主入口
"""

import argparse
import sys
import os
from pathlib import Path
from typing import Optional, List

# 添加项目根目录到 Python 路径
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def create_parser() -> argparse.ArgumentParser:
    """创建 CLI 参数解析器"""
    parser = argparse.ArgumentParser(
        prog="voxplore",
        description="Voxplore - AI 第一人称视频解说工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s project create --name my_project --video /path/to/video.mp4
  %(prog)s project list
  %(prog)s server start --port 8000
  %(prog)s plugin list
        """,
    )

    # 全局选项
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="启用详细输出"
    )
    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s 1.0.0"
    )

    # 子命令
    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # project 子命令
    _add_project_subcommands(subparsers)

    # server 子命令
    _add_server_subcommands(subparsers)

    # plugin 子命令
    _add_plugin_subcommands(subparsers)

    return parser


def _add_project_subcommands(subparsers) -> None:
    """添加 project 子命令"""
    project_parser = subparsers.add_parser("project", help="项目管理")
    project_subparsers = project_parser.add_subparsers(dest="subcommand", help="项目操作")

    # project create
    create_parser = project_subparsers.add_parser("create", help="创建新项目")
    create_parser.add_argument("--name", required=True, help="项目名称")
    create_parser.add_argument("--video", required=True, help="视频文件路径")
    create_parser.add_argument("--output", default="./output", help="输出目录")

    # project list
    list_parser = project_subparsers.add_parser("list", help="列出所有项目")
    list_parser.add_argument("--format", choices=["table", "json"], default="table", help="输出格式")

    # project delete
    delete_parser = project_subparsers.add_parser("delete", help="删除项目")
    delete_parser.add_argument("--name", required=True, help="项目名称")
    delete_parser.add_argument("--force", action="store_true", help="强制删除")

    # project info
    info_parser = project_subparsers.add_parser("info", help="显示项目信息")
    info_parser.add_argument("--name", required=True, help="项目名称")


def _add_server_subcommands(subparsers) -> None:
    """添加 server 子命令"""
    server_parser = subparsers.add_parser("server", help="服务器管理")
    server_subparsers = server_parser.add_subparsers(dest="subcommand", help="服务器操作")

    # server start
    start_parser = server_subparsers.add_parser("start", help="启动 API 服务器")
    start_parser.add_argument("--host", default="0.0.0.0", help="监听主机")
    start_parser.add_argument("--port", type=int, default=8000, help="监听端口")
    start_parser.add_argument("--reload", action="store_true", help="启用热重载")

    # server status
    server_subparsers.add_parser("status", help="查看服务器状态")


def _add_plugin_subcommands(subparsers) -> None:
    """添加 plugin 子命令"""
    plugin_parser = subparsers.add_parser("plugin", help="插件管理")
    plugin_subparsers = plugin_parser.add_subparsers(dest="subcommand", help="插件操作")

    # plugin list
    list_parser = plugin_subparsers.add_parser("list", help="列出所有插件")
    list_parser.add_argument("--enabled", action="store_true", help="仅显示已启用插件")

    # plugin enable
    enable_parser = plugin_subparsers.add_parser("enable", help="启用插件")
    enable_parser.add_argument("--name", required=True, help="插件名称")

    # plugin disable
    disable_parser = plugin_subparsers.add_parser("disable", help="禁用插件")
    disable_parser.add_argument("--name", required=True, help="插件名称")


def _handle_project_command(args) -> int:
    """处理 project 子命令"""
    if args.subcommand == "create":
        print(f"创建项目: {args.name}")
        print(f"视频文件: {args.video}")
        print(f"输出目录: {args.output}")
        # TODO: 实现项目创建逻辑
        return 0

    elif args.subcommand == "list":
        format_type = args.format
        if format_type == "json":
            print("[]")  # TODO: 返回实际项目列表
        else:
            print("项目列表:")
            print("  (暂无项目)")
        return 0

    elif args.subcommand == "delete":
        print(f"删除项目: {args.name}")
        if not args.force:
            print("使用 --force 确认删除")
        return 0

    elif args.subcommand == "info":
        print(f"项目信息: {args.name}")
        return 0

    return 0


def _handle_server_command(args) -> int:
    """处理 server 子命令"""
    if args.subcommand == "start":
        print(f"启动服务器: {args.host}:{args.port}")
        try:
            import uvicorn
            from app.api.main import app
            uvicorn.run(
                "app.api.main:app",
                host=args.host,
                port=args.port,
                reload=args.reload,
            )
        except ImportError:
            print("错误: 需要安装 uvicorn (pip install uvicorn)")
            return 1
        except Exception as e:
            print(f"服务器启动失败: {e}")
            return 1
        return 0

    elif args.subcommand == "status":
        print("服务器状态: 未运行")
        return 0

    return 0


def _handle_plugin_command(args) -> int:
    """处理 plugin 子命令"""
    if args.subcommand == "list":
        print("插件列表:")
        # TODO: 从 PluginRegistry 获取实际插件列表
        print("  (暂无插件)")
        return 0

    elif args.subcommand == "enable":
        print(f"启用插件: {args.name}")
        return 0

    elif args.subcommand == "disable":
        print(f"禁用插件: {args.name}")
        return 0

    return 0


def create_cli() -> argparse.ArgumentParser:
    """创建 CLI 解析器 (供外部调用)"""
    return create_parser()


def run(argv: Optional[List[str]] = None) -> int:
    """
    运行 CLI
    
    Args:
        argv: 命令行参数 (None 则使用 sys.argv)
        
    Returns:
        退出码
    """
    parser = create_parser()
    args = parser.parse_args(argv)

    # 无子命令时显示帮助
    if args.command is None:
        parser.print_help()
        return 0

    # 根据命令分发处理
    try:
        if args.command == "project":
            return _handle_project_command(args)
        elif args.command == "server":
            return _handle_server_command(args)
        elif args.command == "plugin":
            return _handle_plugin_command(args)
        else:
            parser.print_help()
            return 0
    except KeyboardInterrupt:
        print("\n已取消")
        return 130
    except Exception as e:
        print(f"错误: {e}")
        if getattr(args, "verbose", False):
            import traceback
            traceback.print_exc()
        return 1


def main() -> None:
    """入口点 (供 setuptools/scripts 调用)"""
    sys.exit(run())


if __name__ == "__main__":
    main()
