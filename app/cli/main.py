"""
Voxplore CLI Main Entry
命令行主入口
"""

import argparse
import logging
import sys
from pathlib import Path
from typing import Optional, List

logger = logging.getLogger(__name__)

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
    import json
    import os
    import shutil
    import uuid
    from datetime import datetime

    PROJECTS_DIR = os.path.expanduser("~/Voxplore/Projects")

    def _load_project_metadata(project_path: str) -> dict | None:
        """从 project.json 加载项目元数据"""
        pf = os.path.join(project_path, "project.json")
        if not os.path.exists(pf):
            return None
        try:
            with open(pf, "r", encoding="utf-8") as f:
                return json.load(f).get("metadata", {})
        except json.JSONDecodeError as e:
            logger.debug(f"Invalid project metadata JSON: {e}")
            return None
        except Exception as e:
            logger.debug(f"Failed to load project metadata: {e}")
            return None

    def _find_project_by_name(name: str) -> tuple[str, str] | None:
        """按名称查找项目，返回 (project_id, project_path) 或 None"""
        if not os.path.exists(PROJECTS_DIR):
            return None
        for d in os.listdir(PROJECTS_DIR):
            proj_path = os.path.join(PROJECTS_DIR, d)
            if not os.path.isdir(proj_path):
                continue
            meta = _load_project_metadata(proj_path)
            if meta and meta.get("name") == name:
                project_id = os.path.basename(proj_path).split("_", 1)[-1] if "_" in os.path.basename(proj_path) else ""
                return project_id, proj_path
        return None

    def _list_projects_json() -> list[dict]:
        """返回所有项目的 JSON 表示"""
        if not os.path.exists(PROJECTS_DIR):
            return []
        result = []
        for d in sorted(os.listdir(PROJECTS_DIR)):
            proj_path = os.path.join(PROJECTS_DIR, d)
            if not os.path.isdir(proj_path):
                continue
            meta = _load_project_metadata(proj_path)
            if not meta:
                continue
            result.append({
                "name": meta.get("name", ""),
                "id": os.path.basename(proj_path).split("_", 1)[-1] if "_" in os.path.basename(proj_path) else "",
                "path": proj_path,
                "author": meta.get("author", ""),
                "created_at": meta.get("created_at", ""),
                "modified_at": meta.get("modified_at", ""),
                "status": meta.get("status", "active"),
            })
        return result

    if args.subcommand == "create":
        project_id = str(uuid.uuid4())
        slug = args.name.replace(" ", "_")
        project_path = os.path.join(PROJECTS_DIR, f"{slug}_{project_id[:8]}")
        os.makedirs(project_path, exist_ok=True)
        for subdir in ["media", "exports", "backups", "cache", "assets"]:
            os.makedirs(os.path.join(project_path, subdir), exist_ok=True)

        now = datetime.now().isoformat()
        project_json = {
            "metadata": {
                "name": args.name,
                "description": "",
                "author": os.getlogin(),
                "version": "1.0.0",
                "created_at": now,
                "modified_at": now,
                "tags": [],
                "project_type": "video_editing",
                "thumbnail": "",
                "status": "active",
                "file_path": project_path,
            },
            "settings": {},
            "timeline": {"segments": []},
        }
        with open(os.path.join(project_path, "project.json"), "w", encoding="utf-8") as f:
            json.dump(project_json, f, ensure_ascii=False, indent=2)

        # 如果指定了视频文件，建立软链接
        if args.video and os.path.exists(args.video):
            media_dir = os.path.join(project_path, "media")
            video_name = os.path.basename(args.video)
            link_path = os.path.join(media_dir, video_name)
            try:
                os.symlink(args.video, link_path)
                logger.info(f"视频已链接: {link_path}")
            except OSError:
                shutil.copy2(args.video, link_path)
                logger.info(f"视频已复制: {link_path}")

        logger.info(f"✓ 项目已创建: {args.name}")
        logger.info(f"  路径: {project_path}")
        logger.info(f"  ID: {project_id}")
        return 0

    elif args.subcommand == "list":
        projects = _list_projects_json()
        if not projects:
            logger.info("项目列表: (暂无项目)")
            return 0

        if args.format == "json":
            print(json.dumps(projects, ensure_ascii=False, indent=2))
        else:
            logger.info(f"项目列表 (共 {len(projects)} 个):")
            print(f"  {'名称':<30} {'ID':<8} {'作者':<15} {'创建时间':<26} {'状态'}")
            print(f"  {'-'*30} {'-'*8} {'-'*15} {'-'*26} {'------'}")
            for p in projects:
                created = p["created_at"][:19] if p["created_at"] else "-"
                print(f"  {p['name']:<30} {p['id']:<8} {p['author']:<15} {created:<26} {p['status']}")
        return 0

    elif args.subcommand == "delete":
        if not args.force:
            logger.warning("使用 --force 确认删除")
            return 1
        found = _find_project_by_name(args.name)
        if not found:
            logger.error(f"项目不存在: {args.name}")
            return 1
        project_id, project_path = found
        shutil.rmtree(project_path)
        logger.info(f"✓ 已删除项目: {args.name} ({project_path})")
        return 0

    elif args.subcommand == "info":
        found = _find_project_by_name(args.name)
        if not found:
            logger.error(f"项目不存在: {args.name}")
            return 1
        project_id, project_path = found
        meta = _load_project_metadata(project_path)
        if not meta:
            logger.error(f"无法读取项目信息: {project_path}")
            return 1
        print(f"\n项目信息: {args.name}")
        print(f"  ID:           {project_id}")
        print(f"  路径:         {project_path}")
        print(f"  作者:         {meta.get('author', '-')}")
        print(f"  版本:         {meta.get('version', '-')}")
        print(f"  创建时间:     {meta.get('created_at', '-')[:19]}")
        print(f"  修改时间:     {meta.get('modified_at', '-')[:19]}")
        print(f"  状态:         {meta.get('status', '-')}")
        print(f"  描述:         {meta.get('description', '-')}")
        subdirs = [d for d in os.listdir(project_path) if os.path.isdir(os.path.join(project_path, d))]
        print(f"  子目录:       {', '.join(sorted(subdirs))}")
        return 0

    return 0


def _handle_server_command(args) -> int:
    """处理 server 子命令"""
    if args.subcommand == "start":
        logger.info(f"启动服务器: {args.host}:{args.port}")
        try:
            import uvicorn
            uvicorn.run(
                "app.api.main:app",
                host=args.host,
                port=args.port,
                reload=args.reload,
            )
        except ImportError:
            logger.error("错误: 需要安装 uvicorn (pip install uvicorn)")
            return 1
        except Exception as e:
            logger.error(f"服务器启动失败: {e}")
            return 1
        return 0

    elif args.subcommand == "status":
        logger.info("服务器状态: 未运行")
        return 0

    return 0


def _handle_plugin_command(args) -> int:
    """处理 plugin 子命令"""
    if args.subcommand == "list":
        try:
            from app.plugins.loader import PluginLoader
            loader = PluginLoader()
            discovered = loader.discover_plugins()
            registry = loader.get_registry()

            # 注册内置示例插件
            builtin = {
                "cinematic_subtitle": {"name": "电影级字幕", "version": "1.0.0", "type": "subtitle"},
                "deepseek_ai_generator": {"name": "DeepSeek AI 生成器", "version": "1.0.0", "type": "ai_generator"},
            }

            all_plugins = list(discovered) + list(builtin.keys())
            if not all_plugins:
                logger.info("插件列表: (暂无插件)")
                return 0

            if args.enabled:
                enabled = [p for p in all_plugins if registry.get(p, {}).get("enabled", False)]
                all_plugins = enabled if enabled else all_plugins

            logger.info(f"插件列表 (共 {len(all_plugins)} 个):")
            for pid in sorted(all_plugins):
                manifest = registry.get(pid, {}).get("manifest", {})
                if pid in builtin:
                    info = builtin[pid]
                    logger.info(f"  [{info['type']}] {pid} - {info['name']} v{info['version']}")
                else:
                    name = manifest.get("name", pid)
                    ver = manifest.get("version", "?")
                    ptype = manifest.get("plugin_type", "unknown")
                    enabled = registry.get(pid, {}).get("enabled", False)
                    status = "✓" if enabled else "✗"
                    logger.info(f"  [{status}][{ptype}] {pid} - {name} v{ver}")
            return 0
        except Exception as e:
            logger.error(f"获取插件列表失败: {e}")
            return 1

    elif args.subcommand == "enable":
        logger.info(f"启用插件: {args.name}")
        return 0

    elif args.subcommand == "disable":
        logger.info(f"禁用插件: {args.name}")
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
        logger.info("已取消")
        return 130
    except Exception as e:
        logger.error(f"错误: {e}")
        if getattr(args, "verbose", False):
            import traceback
            traceback.print_exc()
        return 1


def main() -> None:
    """入口点 (供 setuptools/scripts 调用)"""
    sys.exit(run())


if __name__ == "__main__":
    main()
