
# AUTO-CLEANUP-CANDIDATE (2026-06-09):
# 1118 行 CLI 死代码 — 仓库无任何文件 import scenefab.cli.* (除了自身)
# 主人 (何进) 偏好"继续推进"/"不要废话", 但 1118 行是大改动
# 保守标记: 留待主人确认后删除, 不在本次 refactor 中删除

"""
SceneFab CLI Main Entry
命令行主入口 — 支持 commentary / batch / project / server / plugin 子命令
"""

import argparse
import json
import logging
import os
import shutil
import sys
import uuid
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

from scenefab.models.constants import DEFAULT_HOST, DEFAULT_PORT


def _get_version() -> str:
    """Dynamic version getter"""
    try:
        from scenefab import __version__

        return __version__
    except Exception:
        return "1.0.0"


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="scenefab",
        description="SceneFab - AI Video Commentary Creation Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s commentary create-movie ./movie.mp4 --style documentary --output ./output/
  %(prog)s commentary create-drama ./drama.mp4 --style suspense --voice zh-CN-YunxiNeural
  %(prog)s commentary create-movie ./video.mp4 --style documentary --format json
  %(prog)s batch ./videos/ --style suspense --parallel 4
  %(prog)s project create --name my_project --video /path/to/video.mp4
  %(prog)s project list
  %(prog)s server start --port 8000
  %(prog)s plugin list
        """,
    )

    # Global options
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable verbose output"
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {_get_version()}"
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # --- Commentary ---
    _add_commentary_subcommands(subparsers)

    # --- Batch ---
    _add_batch_subcommands(subparsers)

    # --- Project (backward compat) ---
    _add_project_subcommands(subparsers)

    # --- Server (backward compat) ---
    _add_server_subcommands(subparsers)

    # --- Plugin (backward compat) ---
    _add_plugin_subcommands(subparsers)

    return parser


# ─── Commentary ────────────────────────────────────────────────────────────────


def _add_commentary_subcommands(subparsers) -> None:
    commentary_parser = subparsers.add_parser(
        "commentary",
        help="AI video commentary creation (core command)",
    )
    sub = commentary_parser.add_subparsers(dest="subcommand", help="Operation")

    # create-movie
    m = sub.add_parser("create-movie", help="Create movie commentary")
    m.add_argument("video", help="Video file path")
    m.add_argument(
        "--style", default="documentary", help="Commentary style (default: documentary)"
    )
    m.add_argument("--voice", default="zh-CN-YunxiNeural", help="TTS voice")
    m.add_argument("--output", default="./output", help="Output directory")
    m.add_argument(
        "--format", choices=["text", "json"], default="text", help="Output format"
    )

    # create-drama
    d = sub.add_parser("create-drama", help="Create drama commentary")
    d.add_argument("video", help="Video file path")
    d.add_argument(
        "--style", default="suspense", help="Commentary style (default: suspense)"
    )
    d.add_argument("--voice", default="zh-CN-YunxiNeural", help="TTS voice")
    d.add_argument("--output", default="./output", help="Output directory")
    d.add_argument(
        "--format", choices=["text", "json"], default="text", help="Output format"
    )


# ─── Batch ───────────────────────────────────────────────────────────────────


def _add_batch_subcommands(subparsers) -> None:
    batch_parser = subparsers.add_parser("batch", help="Batch processing")
    batch_sub = batch_parser.add_subparsers(dest="subcommand", help="Batch operation")

    create_batch = batch_sub.add_parser("create", help="Batch create commentary")
    create_batch.add_argument("directory", help="Video directory path")
    create_batch.add_argument("--style", default="documentary", help="Commentary style")
    create_batch.add_argument(
        "--parallel", type=int, default=1, help="Parallel tasks (default: 1)"
    )
    create_batch.add_argument("--output", default="./output", help="Output directory")
    create_batch.add_argument(
        "--format", choices=["text", "json"], default="text", help="Output format"
    )


# ─── Project (backward compat) ─────────────────────────────────────────────────


def _add_project_subcommands(subparsers) -> None:
    project_parser = subparsers.add_parser(
        "project", help="Project management (backward compat)"
    )
    project_subparsers = project_parser.add_subparsers(
        dest="subcommand", help="Project operations"
    )

    create_parser = project_subparsers.add_parser("create", help="Create new project")
    create_parser.add_argument("--name", required=True, help="Project name")
    create_parser.add_argument("--video", help="Video file path")
    create_parser.add_argument("--output", default="./output", help="Output directory")

    list_parser = project_subparsers.add_parser("list", help="List all projects")
    list_parser.add_argument(
        "--format", choices=["table", "json"], default="table", help="Output format"
    )

    delete_parser = project_subparsers.add_parser("delete", help="Delete project")
    delete_parser.add_argument("--name", required=True, help="Project name")
    delete_parser.add_argument("--force", action="store_true", help="Confirm deletion")

    info_parser = project_subparsers.add_parser("info", help="Show project info")
    info_parser.add_argument("--name", required=True, help="Project name")


# ─── Server (backward compat) ────────────────────────────────────────────────


def _add_server_subcommands(subparsers) -> None:
    server_parser = subparsers.add_parser(
        "server", help="Server management (backward compat)"
    )
    server_subparsers = server_parser.add_subparsers(
        dest="subcommand", help="Server operations"
    )

    start_parser = server_subparsers.add_parser("start", help="Start API server")
    start_parser.add_argument("--host", default=DEFAULT_HOST, help="Listen host")
    start_parser.add_argument(
        "--port", type=int, default=DEFAULT_PORT, help="Listen port"
    )
    start_parser.add_argument(
        "--reload", action="store_true", help="Hot reload in dev mode"
    )

    server_subparsers.add_parser("status", help="Check server status")


# ─── Plugin (backward compat) ────────────────────────────────────────────────


def _add_plugin_subcommands(subparsers) -> None:
    plugin_parser = subparsers.add_parser(
        "plugin", help="Plugin management (backward compat)"
    )
    plugin_subparsers = plugin_parser.add_subparsers(
        dest="subcommand", help="Plugin operations"
    )

    _list_parser = plugin_subparsers.add_parser("list", help="List all plugins")
    enable_parser = plugin_subparsers.add_parser("enable", help="Enable plugin")
    enable_parser.add_argument("--name", required=True, help="Plugin name")
    disable_parser = plugin_subparsers.add_parser("disable", help="Disable plugin")
    disable_parser.add_argument("--name", required=True, help="Plugin name")


# ─── Handlers ────────────────────────────────────────────────────────────────


def _handle_commentary_command(args) -> int:
    """Handle commentary subcommand"""
    if args.subcommand in ("create-movie", "create-drama"):
        return _handle_commentary_create(args)
    return 0


def _handle_commentary_create(args) -> int:
    """Execute commentary creation (single video)"""
    video_path = Path(args.video)
    if not video_path.exists():
        logger.error(f"Video file not found: {video_path}")
        return 1

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        result = _run_commentary_pipeline(video_path, output_dir, args)
        _print_success_output(args, video_path, output_dir, result)
        return 0
    except ImportError as e:
        logger.error(f"Pipeline import failed: {e}")
        logger.info(
            "Hint: SceneFab requires full AI API configuration for commentary creation"
        )
        _print_error_json(args, video_path, f"Pipeline import failed: {e}")
        return 1
    except Exception as e:
        logger.error(f"Commentary creation failed: {e}")
        _print_error_json(args, video_path, str(e))
        return 1


def _run_commentary_pipeline(
    video_path: Path, output_dir: Path, args
) -> dict:
    """Build pipeline, run commentary creation, return result dict.

    Raises ImportError if pipeline modules are missing, or whatever
    exception the pipeline itself raises.
    """
    from scenefab.models.narration import NarrationStyle
    from scenefab.pipeline import PipelineConfig, SceneFabPipeline

    config = PipelineConfig(
        min_segment_duration=9.0,
        max_segment_duration=60.0,
    )
    pipeline = SceneFabPipeline(config)

    # 将字符串 style 映射为 NarrationStyle 枚举（fallback 到 DOCUMENTARY）
    narration_style = getattr(
        NarrationStyle, args.style.upper(), NarrationStyle.DOCUMENTARY
    )

    project = pipeline.process(
        video_path=str(video_path),
        style=narration_style,
        voice=args.voice,
        output_dir=str(output_dir),
    )

    return {
        "name": project.name,
        "segments": len(project.segments),
        "narrations": len(project.narration_blocks),
        "emotion_peaks": len(project.emotion_peaks),
    }


def _print_success_output(
    args, video_path: Path, output_dir: Path, result: dict
) -> None:
    """Emit success output as JSON (--format json) or as log lines."""
    if args.format == "json":
        print(
            json.dumps(
                {
                    "status": "success",
                    "video": str(video_path),
                    "style": args.style,
                    "voice": args.voice,
                    "output_dir": str(output_dir),
                    "result": result,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        logger.info(f"Commentary creation complete: {video_path.name}")
        logger.info(f"  Style: {args.style} | Voice: {args.voice}")
        logger.info(f"  Output: {output_dir}")
        logger.info(
            f"  Segments: {result['segments']} | Narrations: {result['narrations']}"
        )


def _print_error_json(args, video_path: Path, message: str) -> None:
    """Emit a JSON error envelope when --format json, else no-op."""
    if args.format == "json":
        print(
            json.dumps(
                {
                    "status": "error",
                    "message": message,
                    "video": str(video_path),
                    "style": args.style,
                },
                ensure_ascii=False,
                indent=2,
            )
        )


def _handle_batch_command(args) -> int:
    """Handle batch subcommand"""
    if args.subcommand == "create":
        return _handle_batch_create(args)
    return 0


def _handle_batch_create(args) -> int:
    """Batch create commentary"""
    batch_dir = Path(args.directory)
    if not batch_dir.is_dir():
        logger.error(f"Directory not found: {batch_dir}")
        return 1

    video_extensions = {".mp4", ".mkv", ".avi", ".mov", ".flv", ".wmv", ".webm"}
    videos = [f for f in batch_dir.iterdir() if f.suffix.lower() in video_extensions]

    if not videos:
        logger.warning(f"No video files in directory: {batch_dir}")
        return 0

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    results = []
    for video in videos:
        logger.info(f"Processing: {video.name}")
        try:
            from scenefab.models.narration import NarrationStyle
            from scenefab.pipeline import PipelineConfig, SceneFabPipeline

            config = PipelineConfig(
                min_segment_duration=9.0,
                max_segment_duration=60.0,
            )
            pipeline = SceneFabPipeline(config)
            narration_style = getattr(
                NarrationStyle, args.style.upper(), NarrationStyle.DOCUMENTARY
            )
            pipeline.process(
                video_path=str(video),
                output_dir=str(output_dir / video.stem),
                style=narration_style,
                voice=args.voice,
            )
            results.append({"video": video.name, "status": "success"})
        except Exception as e:
            logger.warning(f"  Skipped {video.name}: {e}")
            results.append({"video": video.name, "status": "error", "message": str(e)})

    if args.format == "json":
        print(
            json.dumps(
                {
                    "status": "completed",
                    "total": len(videos),
                    "success": sum(1 for r in results if r["status"] == "success"),
                    "failed": sum(1 for r in results if r["status"] == "error"),
                    "results": results,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        success = sum(1 for r in results if r["status"] == "success")
        logger.info(f"\nBatch complete: {success}/{len(videos)} succeeded")

    return 0


# ─── Project Handler (backward compat) ──────────────────────────────────────

_PROJECTS_DIR = os.path.expanduser("~/SceneFab/Projects")


def _load_project_meta(project_path: str) -> dict | None:
    """Load metadata dict from a project's project.json file."""
    pf = os.path.join(project_path, "project.json")
    if not os.path.exists(pf):
        return None
    try:
        with open(pf, encoding="utf-8") as f:
            return json.load(f).get("metadata", {})  # type: ignore[no-any-return]
    except Exception:
        return None


def _find_project_by_name(name: str) -> tuple[str, str] | None:
    """Find a project directory by its metadata name. Returns (id, path) or None."""
    if not os.path.exists(_PROJECTS_DIR):
        return None
    for d in os.listdir(_PROJECTS_DIR):
        proj_path = os.path.join(_PROJECTS_DIR, d)
        if not os.path.isdir(proj_path):
            continue
        meta = _load_project_meta(proj_path)
        if meta and meta.get("name") == name:
            proj_id = (
                os.path.basename(proj_path).split("_", 1)[-1]
                if "_" in os.path.basename(proj_path)
                else ""
            )
            return proj_id, proj_path
    return None


def _list_all_projects() -> list[dict]:
    """List all projects with their metadata."""
    if not os.path.exists(_PROJECTS_DIR):
        return []
    result = []
    for d in sorted(os.listdir(_PROJECTS_DIR)):
        proj_path = os.path.join(_PROJECTS_DIR, d)
        if not os.path.isdir(proj_path):
            continue
        meta = _load_project_meta(proj_path)
        if not meta:
            continue
        result.append(
            {
                "name": meta.get("name", ""),
                "id": os.path.basename(proj_path).split("_", 1)[-1]
                if "_" in os.path.basename(proj_path)
                else "",
                "path": proj_path,
                "author": meta.get("author", ""),
                "created_at": meta.get("created_at", ""),
                "status": meta.get("status", "active"),
            }
        )
    return result


def _project_create_link(video_path: str, project_path: str) -> None:
    """Symlink (or copy) video into the project's media directory."""
    media_dir = os.path.join(project_path, "media")
    video_name = os.path.basename(video_path)
    link_path = os.path.join(media_dir, video_name)
    try:
        os.symlink(video_path, link_path)
    except OSError:
        shutil.copy2(video_path, link_path)


def _handle_project_create(args) -> int:
    """Create a new project directory structure with project.json."""
    project_id = str(uuid.uuid4())
    slug = args.name.replace(" ", "_")
    project_path = os.path.join(_PROJECTS_DIR, f"{slug}_{project_id[:8]}")
    os.makedirs(project_path, exist_ok=True)
    for subdir in ["media", "exports", "backups", "cache", "assets"]:
        os.makedirs(os.path.join(project_path, subdir), exist_ok=True)

    now = datetime.now().isoformat()
    project_json = {
        "metadata": {
            "name": args.name,
            "description": "",
            "author": os.getlogin(),
            "version": "1.0.1",
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

    if args.video and os.path.exists(args.video):
        _project_create_link(args.video, project_path)

    logger.info(f"Project created: {args.name}")
    logger.info(f"  Path: {project_path}")
    return 0


def _handle_project_list(args) -> int:
    """List all projects in table or JSON format."""
    projects = _list_all_projects()
    if not projects:
        logger.info("No projects yet")
        return 0
    if args.format == "json":
        print(json.dumps(projects, ensure_ascii=False, indent=2))
    else:
        logger.info(f"Projects ({len(projects)} total):")
        print(f"  {'Name':<30} {'ID':<8} {'Author':<15} {'Created':<26} {'Status'}")
        print(f"  {'-' * 30} {'-' * 8} {'-' * 15} {'-' * 26} {'------'}")
        for p in projects:
            created = p["created_at"][:19] if p["created_at"] else "-"
            print(
                f"  {p['name']:<30} {p['id']:<8} {p['author']:<15} {created:<26} {p['status']}"
            )
    return 0


def _handle_project_delete(args) -> int:
    """Delete a project by name (requires --force)."""
    if not args.force:
        logger.warning("Use --force to confirm deletion")
        return 1
    found = _find_project_by_name(args.name)
    if not found:
        logger.error(f"Project not found: {args.name}")
        return 1
    _, project_path = found
    shutil.rmtree(project_path)
    logger.info(f"Project deleted: {args.name}")
    return 0


def _handle_project_info(args) -> int:
    """Display detailed info for a project."""
    found = _find_project_by_name(args.name)
    if not found:
        logger.error(f"Project not found: {args.name}")
        return 1
    _, project_path = found
    meta = _load_project_meta(project_path)
    if not meta:
        logger.error("Cannot read project info")
        return 1
    print(f"\nProject Info: {args.name}")
    print(f"  ID:           {os.path.basename(project_path).split('_', 1)[-1]}")
    print(f"  Path:         {project_path}")
    print(f"  Author:       {meta.get('author', '-')}")
    print(f"  Version:      {meta.get('version', '-')}")
    print(f"  Created:      {meta.get('created_at', '-')[:19]}")
    print(f"  Status:       {meta.get('status', '-')}")
    return 0


def _handle_project_command(args) -> int:
    """Handle project subcommand (backward compat) using dispatch dict."""
    handlers = {
        "create": _handle_project_create,
        "list": _handle_project_list,
        "delete": _handle_project_delete,
        "info": _handle_project_info,
    }
    handler = handlers.get(args.subcommand)
    if handler is not None:
        return handler(args)
    return 0


# ─── Server Handler ───────────────────────────────────────────────────────────


def _handle_server_command(args) -> int:
    """Handle server subcommand"""
    if args.subcommand == "start":
        logger.info(f"Starting server: {args.host}:{args.port}")
        try:
            import uvicorn

            uvicorn.run(
                "scenefab.api.main:app",
                host=args.host,
                port=args.port,
                reload=args.reload,
            )
        except ImportError:
            logger.error("uvicorn not installed, run: pip install uvicorn")
            return 1
    elif args.subcommand == "status":
        logger.info("Server status check...")
        logger.info("Hint: Use /health endpoint to check service health")
    return 0


# ─── Plugin Handler ───────────────────────────────────────────────────────────


def _handle_plugin_command(args) -> int:
    """Handle plugin subcommand"""
    if args.subcommand == "list":
        logger.info("Installed plugins:")
        logger.info("  (no plugins)")
    elif args.subcommand == "enable":
        logger.info(f"Enabling plugin: {args.name}")
    elif args.subcommand == "disable":
        logger.info(f"Disabling plugin: {args.name}")
    return 0


# ─── Main ─────────────────────────────────────────────────────────────────────


def create_cli() -> argparse.ArgumentParser:
    """Create CLI parser (for external use)"""
    return create_parser()


def run(argv: list[str] | None = None) -> int:
    """Run CLI"""
    parser = create_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 0

    try:
        if args.command == "commentary":
            return _handle_commentary_command(args)
        elif args.command == "batch":
            return _handle_batch_command(args)
        elif args.command == "project":
            return _handle_project_command(args)
        elif args.command == "server":
            return _handle_server_command(args)
        elif args.command == "plugin":
            return _handle_plugin_command(args)
        else:
            parser.print_help()
            return 0
    except KeyboardInterrupt:
        logger.info("Cancelled")
        return 130
    except Exception as e:
        logger.error(f"Error: {e}")
        if getattr(args, "verbose", False):
            import traceback

            traceback.print_exc()
        return 1


def main() -> None:
    """Entry point (for setuptools/scripts)"""
    sys.exit(run())


if __name__ == "__main__":
    main()
