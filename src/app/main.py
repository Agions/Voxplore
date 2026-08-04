#!/usr/bin/env python3
"""
SceneFab 主程序入口
专业的AI视频编辑器
"""

import logging
import os
import sys
from pathlib import Path

from app.ui.i18n import t


# 自动检测无头环境，设置 Qt 平台
def _setup_headless_platform():
    """检测无头环境并设置合适的 Qt 平台。

    注意: macOS 使用 Quartz/WindowServer，不依赖 DISPLAY 环境变量，
    因此必须跳过 macOS 的无头检测，否则会错误启用 offscreen 模式。
    """
    if sys.platform == "darwin":
        return  # macOS 始终有显示器 (WindowServer)
    if not os.environ.get("DISPLAY") and not os.environ.get("WAYLAND_DISPLAY"):
        # Linux 无显示器环境，使用 offscreen 平台
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        # 禁用多媒体 pipewire 警告
        os.environ.setdefault("QT_LOGGING_TO_STDOUT", "1")


_setup_headless_platform()

# 抑制 Qt 内部字体别名解析警告 (macOS "Sans Serif" 别名, 非应用代码触发)
os.environ.setdefault("QT_LOGGING_RULES", "qt.qpa.fonts=false")

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 设置日志
logger = logging.getLogger("SceneFab")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(message)s", datefmt="%H:%M:%S"
        )
    )
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


def _check_update_async(window, updater_service):
    """启动后异步检测更新，有新版本时提示用户。

    修复要点（Phase 1 · TD-11）：
        旧版使用 ``threading.Thread`` + ``QMetaObject.invokeMethod(window,
        "show_message", ...)`` 来调 ``show_message``，但 ``show_message`` 是
        普通 Python 方法，Qt 的 ``invokeMethod`` 要求目标 ``QObject`` 必须是
        ``@Slot`` 装饰过的槽函数；不满足时调用静默失败，UI 看不到任何提示。

    修复方案：
        使用 :class:`app.updater.UpdaterService`，它在工作线程中运行，
        通过 :class:`PySide6.QtCore.Signal` 推送结果——Signal 的跨线程
        ``Qt.QueuedConnection`` 由 Qt 自己处理，无需再调
        ``invokeMethod``。检测结果表 query 表达式传回主线程后，连接
        到 ``main_window.show_message_safe``，实现线程安全的 toast。
    """
    from app.updater import UpdaterService

    if updater_service is None:
        return

    service: UpdaterService = updater_service

    def on_update_available(manifest) -> None:
        # 注意：这个回调在 main thread 上运行（信号 Qt.QueuedConnection）。
        try:
            version = getattr(manifest, "version", "")
            notes = getattr(manifest, "release_notes", "") or ""
            body = (
                t("update.notification.new_version", version=version)
                + "\n\n"
                + (notes or t("update.dialog.confirm_install.message", version=version))
            )
            window.show_message_safe(body, level="info")
        except Exception as exc:  # pragma: no cover - safety net
            logger.debug("Update notification dispatch failed: %s", exc)

    def on_error(code: str, message: str) -> None:
        try:
            window.show_message_safe(
                t("update.error.check_failed", error=f"[{code}] {message}"),
                level="warning",
            )
        except Exception as exc:  # pragma: no cover
            logger.debug("Update error dispatch failed: %s", exc)

    signals = getattr(service, "signals", None)
    if signals is not None:
        try:
            signals.update_available.connect(on_update_available)
            signals.error_occurred.connect(on_error)
        except Exception:  # pragma: no cover - signals missing in headless
            pass

    # 用纯 Python 线程跑检测 — Qt 信号会安全跨线程（QueuedConnection 由 Qt 调度）。
    # 之前的 QMetaObject.invokeMethod + 普通方法跨线程调用是 bug 源头，
    # 现在全部靠 Signal/Slot 传递，不需额外 invokeMethod。
    import threading

    def _worker() -> None:
        try:
            service.check(timeout=10.0)
        except Exception as exc:  # pragma: no cover
            logger.debug(f"Update check failed: {exc}")

    thread = threading.Thread(
        target=_worker,
        name="scenefab-updater-check",
        daemon=True,
    )
    thread.start()


def main() -> None:
    """主函数"""
    from app.utils.version import __version__

    logger.info("=" * 50)
    logger.info("🎬 SceneFab - AI 视频创作工具")
    logger.info("=" * 50)
    logger.info(f"版本: {__version__}")
    logger.info("作者: Agions")

    # 检查依赖
    check_dependencies()

    # 启动 GUI
    try:
        from PySide6.QtWidgets import QApplication

        from app.application import Application

        qt_app = QApplication(sys.argv)
        qt_app.setApplicationName("SceneFab")
        qt_app.setApplicationVersion(str(__version__))

        # 加载并动态挂载苹果 SF Pro / 苹方原生视觉字体包
        from app.ui.theme.font_loader import init_application_fonts

        init_application_fonts()

        # 初始化核心应用程序实例
        from app.config import ConfigManager

        config_mgr = ConfigManager()
        app_config = {"config_manager": config_mgr}
        application = Application(app_config)

        # 初始化应用程序服务
        if not application.initialize(sys.argv):
            logger.error("应用程序初始化失败")
            sys.exit(1)

        # 启动应用程序
        if not application.start():
            logger.error("应用程序启动失败")
            sys.exit(1)

        # 创建主窗口并注入 application 实例 (Phase 1.5 接线)
        from app.ui.main.main_window import SceneFabMainWindow

        window = SceneFabMainWindow(application=application)
        window.show()
        window.raise_()
        window.activateWindow()

        # 实例化并注册 UpdaterService（Phase 1 · TD-03 自动升级闭环）。
        # 这样 UpdatePage 可以从 DI 容器拿到同一个实例，主窗口绑定后，
        # notify 机制也不会因为多实例重复检测。
        from app.updater import UpdaterService

        try:
            updater_service = UpdaterService.from_settings()
            application.register_service("updater_service", updater_service)
        except Exception as exc:  # pragma: no cover - 服务不可用时不阻断启动
            logger.debug("UpdaterService bootstrap failed: %s", exc)
            updater_service = None

        # 启动后 3 秒异步检测更新（非阻塞）
        from PySide6.QtCore import QTimer

        QTimer.singleShot(
            3000,
            lambda: _check_update_async(window, updater_service),
        )

        exit_code = qt_app.exec()

        # 关闭应用程序
        application.shutdown()

        sys.exit(exit_code)

    except (ImportError, ModuleNotFoundError) as e:
        logger.warning(f"GUI 桌面端启动失败 ({e})，已回退到命令行模式")
        logger.info("👉 提示：如需唤起 GUI 桌面客户端，请在终端执行：pip install PySide6")
        logger.info("正在启动命令行模式...")
        run_cli_mode()


def check_dependencies() -> None:
    """检查依赖"""
    logger.info("检查依赖...")

    required = {
        "ffmpeg": "FFmpeg 视频处理",
        "ffprobe": "FFprobe 视频分析",
    }

    import shutil

    missing = []
    for cmd, desc in required.items():
        if shutil.which(cmd):
            logger.info(f"  ✅ {desc}")
        else:
            logger.error(f"  ❌ {desc} - 未找到")
            missing.append(cmd)

    if missing:
        logger.warning(f"缺少依赖: {', '.join(missing)}")
        logger.info("请安装 FFmpeg: https://ffmpeg.org/download.html")


def run_cli_mode() -> None:
    """命令行模式"""
    print("SceneFab 命令行模式")
    print("-" * 30)
    print("可用功能:")
    print("  1. AI 第一人称解说")
    print("  2. 剪映草稿导出")
    print("  3. 退出")
    print()

    while True:
        try:
            choice = input("请选择功能 (1-3): ").strip()

            if choice == "1":
                run_commentary()
            elif choice == "2":
                run_export()
            elif choice == "3":
                print("\n再见! 👋")
                break
            else:
                print("无效选择，请输入 1-3")

        except KeyboardInterrupt:
            print("\n\n再见! 👋")
            break
        except (OSError, EOFError):
            print("\n\n再见! 👋")
            break
        except Exception as e:
            print(f"错误: {e}")


def run_commentary() -> None:
    """运行解说功能 — 使用 MonologueMaker 作为第一人称解说"""
    print("\n--- AI 第一人称解说 ---")
    print("(SceneFab 核心功能)")

    video_path = input("输入视频路径: ").strip()
    if not video_path or not Path(video_path).exists():
        print("视频文件不存在")
        return

    topic = input("输入解说主题: ").strip() or "分析这段视频内容"

    from app.services.video import MonologueMaker

    maker = MonologueMaker(voice_provider="edge")

    def on_progress(stage, progress):
        print(f"  [{stage}] {progress * 100:.0f}%")

    maker.set_progress_callback(on_progress)

    print("\n创建项目...")
    project = maker.create_project(
        source_video=video_path,
        context=topic,
        emotion="平静",
    )

    print(f"视频时长: {project.video_duration:.1f}秒")

    use_custom = input("\n使用自定义解说词? (y/n): ").strip().lower() == "y"

    if use_custom:
        print("输入解说词 (输入空行结束):")
        lines = []
        while True:
            line = input()
            if not line:
                break
            lines.append(line)
        custom_script = "\n".join(lines)
        maker.generate_script(project, custom_script=custom_script)
    else:
        try:
            maker.generate_script(project)
        except ValueError as e:
            print(f"错误: {e}")
            print("使用默认解说词...")
            maker.generate_script(
                project,
                custom_script="欢迎观看这段视频，这是一段精彩的瞬间希望大家喜欢。",
            )

    print("\n生成配音...")
    maker.generate_voice(project)

    print("生成字幕...")
    maker.generate_captions(project, style="cinematic")

    output_dir = input("\n输入剪映草稿目录 (默认 ./output/jianying_drafts): ").strip()
    output_dir = output_dir or "./output/jianying_drafts"

    print("导出草稿...")
    draft_path = maker.export_to_jianying(project, output_dir)

    print(f"\n✅ 完成! 草稿路径: {draft_path}")


def run_export() -> None:
    """运行导出功能"""
    print("\n--- 剪映草稿导出 ---")

    from app.services.export import (
        JianyingConfig,
        JianyingExporter,
        Segment,
        TimeRange,
        Track,
        TrackType,
        VideoMaterial,
    )

    video_path = input("输入视频路径: ").strip()
    if not video_path or not Path(video_path).exists():
        print("视频文件不存在")
        return

    project_name = input("项目名称: ").strip() or "新建项目"

    exporter = JianyingExporter(
        JianyingConfig(
            canvas_ratio="9:16",
            copy_materials=True,
        )
    )

    draft = exporter.create_draft(project_name)

    # 添加视频
    video_track = Track(type=TrackType.VIDEO, attribute=1)
    draft.add_track(video_track)

    video_material = VideoMaterial(path=video_path)
    draft.add_video(video_material)

    # Probe actual video duration instead of hardcoding 30s
    from app.services.video.ffmpeg_tool import FFmpegTool

    duration = FFmpegTool.get_duration(video_path) or 30.0

    segment = Segment(
        material_id=video_material.id,
        source_timerange=TimeRange.from_seconds(0, duration),
        target_timerange=TimeRange.from_seconds(0, duration),
    )
    video_track.add_segment(segment)

    output_dir = input("\n输入剪映草稿目录: ").strip() or "./output/jianying_drafts"

    draft_path = exporter.export(draft, output_dir)

    print(f"\n✅ 完成! 草稿路径: {draft_path}")


if __name__ == "__main__":
    main()
