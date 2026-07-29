#!/usr/bin/env python3
"""
SceneFab 主窗口包

职责划分(Phase 1 重构后):
- ``MainWindow``  本类 — 仅负责装配 Sidebar / TopBar / ContentArea / StatusBar
  并把信号接起来。无业务、无路由、无托盘。
- ``PageRouter``     — 懒加载 + 页面切换 (ui/main/page_router.py)
- ``SystemTrayController`` — 托盘菜单 + 关闭拦截 (ui/main/system_tray.py)
- ``registry``       — 页面元数据 + 工厂 (ui/main/registry.py)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QSettings, Qt
from PySide6.QtGui import QAction, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QMainWindow,
    QMessageBox,
    QVBoxLayout,
    QWidget,
)

from scenefab.ui.main.main_window.content_area import ContentArea
from scenefab.ui.main.main_window.nav_components import Sidebar
from scenefab.ui.main.main_window.status_bar import StatusBar
from scenefab.ui.main.main_window.top_bar import TopBar
from scenefab.ui.main.page_router import PageRouter
from scenefab.ui.main.registry import NAV_ITEMS, PAGE_TITLES
from scenefab.ui.main.system_tray import SystemTrayController
from scenefab.ui.theme.ds_tokens import (
    _C,
    FontSizes,
    QSSComponents,
    Radii,
    set_theme_mode,
)
from scenefab.ui.theme.runtime import ThemeAwareMixin, restyle_app

if TYPE_CHECKING:
    from scenefab.application import Application

# 支持拖入的视频文件扩展名
_VIDEO_EXTENSIONS = (".mp4", ".mov", ".avi", ".mkv")

# Worker 进度 → 生产页步骤名映射（来自 FIRST_PERSON_WORKFLOW 的 6 个步骤）
_PROGRESS_STEP_MAP = {
    1: "素材审片",  # 场景分析
    2: "冲突拆解",  # 脚本生成
    3: "配音字幕",  # 配音合成
    4: "配音字幕",  # 字幕生成（续）
}

# 完成某步后，下一步进入"进行中"的步骤名
_NEXT_ACTIVE_STEP = {
    1: "冲突拆解",
    2: "配音字幕",
}

# FIRST_PERSON_WORKFLOW 的全部 6 个步骤名
_ALL_PRODUCTION_STEPS = (
    "素材审片",
    "冲突拆解",
    "第一人称钩子",
    "爽点节奏",
    "配音字幕",
    "发布复盘",
)


class SceneFabMainWindow(QMainWindow, ThemeAwareMixin):
    """SceneFab 主窗口 — 装配器,只做信号路由。

    Phase 1 之后不直接持有页面、不直接读 services、不直接管托盘。
    注入的 ``application`` 实例在 Phase 2 才会被 ViewModel 消费。
    """

    def __init__(self, application: Application | None = None) -> None:
        super().__init__()
        self._application = application
        self.setWindowTitle("SceneFab")
        self.setMinimumSize(1200, 720)
        self.setAcceptDrops(True)
        self._quitting = False
        self._last_project = None
        self._theme_manager = None

        ThemeAwareMixin.__init__(self)
        self.setStyleSheet(self.build_global_stylesheet())

        self._setup_ui()

        # 恢复窗口几何
        settings = QSettings("SceneFab", "Application")
        geometry = settings.value("window/geometry")
        if geometry:
            self.restoreGeometry(geometry)
        else:
            self.resize(1200, 720)

        # 系统托盘控制器（必须在 _connect_signals 之前创建，
        # 后者会连接 self.tray 的信号）
        self.tray = SystemTrayController(self)

        self._connect_signals()

    def _setup_ui(self) -> None:
        self._create_menu_bar()
        central = QWidget()
        self.setCentralWidget(central)

        outer = QVBoxLayout(central)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # 顶部栏
        self.topbar = TopBar("工作台")
        outer.addWidget(self.topbar)

        body = QWidget()
        root_layout = QHBoxLayout(body)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        self.sidebar = Sidebar(NAV_ITEMS)
        root_layout.addWidget(self.sidebar)

        self.content = ContentArea()
        self.router = PageRouter(self.content, application=self._application, parent=self)
        root_layout.addWidget(self.content, 1)

        outer.addWidget(body, 1)

        self.statusbar = StatusBar()
        outer.addWidget(self.statusbar)

        cancel_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Escape), self)
        cancel_shortcut.activated.connect(self._on_cancel_production)

    def _create_menu_bar(self):
        """创建原生菜单栏 (TopBar 保留为菜单栏下方的工具栏式组件)"""
        menubar = self.menuBar()

        def add_action(menu, text, shortcut, slot):
            action = QAction(text, menu)
            if shortcut:
                action.setShortcut(QKeySequence(shortcut))
            action.triggered.connect(slot)
            menu.addAction(action)
            return action

        # 文件
        file_menu = menubar.addMenu("文件")
        add_action(
            file_menu, "新建项目", "Ctrl+N", lambda: self._on_navigate("create")
        )
        add_action(file_menu, "打开项目", "Ctrl+O", lambda: self._on_open_project())
        add_action(file_menu, "保存项目", "Ctrl+S", lambda: self._on_save_project())
        add_action(file_menu, "导入素材", "Ctrl+I", lambda: self._on_import_assets())
        add_action(file_menu, "导出", "Ctrl+E", lambda: self._on_export())
        file_menu.addSeparator()
        add_action(file_menu, "退出", "Ctrl+Q", lambda: self._quit_application())

        # 编辑
        edit_menu = menubar.addMenu("编辑")
        add_action(
            edit_menu, "系统设置", "Ctrl+,", lambda: self._on_navigate("settings")
        )

        # 视图
        view_menu = menubar.addMenu("视图")
        add_action(view_menu, "工作台", "Ctrl+1", lambda: self._on_navigate("home"))
        add_action(
            view_menu, "创作流程", "Ctrl+2", lambda: self._on_navigate("create")
        )
        add_action(
            view_menu, "项目资产", "Ctrl+3", lambda: self._on_navigate("assets")
        )
        add_action(
            view_menu, "系统设置", "Ctrl+4", lambda: self._on_navigate("settings")
        )

        # 帮助
        help_menu = menubar.addMenu("帮助")
        add_action(help_menu, "关于 SceneFab", "", lambda: self._show_about())

    def _lazy_load_pages(self):
        from scenefab.ui.main.pages.assets_page import AssetsPage
        from scenefab.ui.main.pages.home_page import HomePage
        from scenefab.ui.main.pages.production_page import ProductionPage
        from scenefab.ui.main.pages.settings_page import SettingsPage

        project_manager = None
        settings_manager = None
        if self._application is not None:
            project_manager = self._application.get_service_by_name("project_manager")
            settings_manager = self._application.get_service_by_name(
                "settings_manager"
            )

        home = HomePage(project_manager=project_manager)
        home.create_project.connect(lambda: self._on_navigate("create"))
        home.open_project.connect(self._on_open_project)
        home.navigate.connect(self._on_navigate)
        self._home_page = home

        production = ProductionPage()
        production.start_requested.connect(self._on_start_production)
        production.cancel_requested.connect(self._on_cancel_production)
        self._production_page = production

        assets = AssetsPage(project_manager=project_manager)
        assets.import_requested.connect(self._on_import_assets)
        assets.navigate.connect(self._on_navigate)
        self._assets_page = assets
        self._project_manager = project_manager

        settings = SettingsPage(
            settings_manager=settings_manager,
            theme_manager=self._theme_manager,
            project_manager=project_manager,
        )

        self.content.add_page("home", home)
        self.content.add_page("create", production)
        self.content.add_page("assets", assets)
        self.content.add_page("settings", settings)

        # 页面挂载到窗口后重新加载设置，确保托盘等窗口级状态同步
        if settings_manager is not None:
            settings.load_settings()

        # Populate HomePage with real data from ProjectManager
        if project_manager is not None:
            projects = project_manager.scan_projects()
            home.update_stats(
                projects_count=len(projects),
                assets_count=sum(
                    len(p.media_files) for p in project_manager.get_all_projects()
                ),
            )
            home.update_recent_projects(project_manager.get_recent_projects())

    def _connect_signals(self) -> None:
        self.sidebar.navigated.connect(self._on_navigate)
        self.router.page_changed.connect(self._on_page_changed)
        self.topbar.action_triggered.connect(self._on_action)
        self.tray.show_window_requested.connect(self._restore_from_tray)
        self.tray.open_settings_requested.connect(self._open_settings_from_tray)
        self.tray.quit_requested.connect(self._quit_application)

    def _on_page_changed(self, page_id: str) -> None:
        spec = PAGE_TITLES.get(page_id)
        if spec is None:
            return
        self.topbar.set_title(spec.title, spec.breadcrumb)
        self.statusbar.set_status(f"当前: {spec.title}")
        if page_id == "settings":
            self._wire_theme_switcher()

    def _wire_theme_switcher(self) -> None:
        if getattr(self, "_theme_signal_wired", False):
            return
        page = self.router._page_map.get("settings")
        connect = getattr(page, "theme_changed", None)
        if connect is None:
            return
        connect.connect(self._on_theme_switched)
        self._theme_signal_wired = True

    def _on_theme_switched(self, mode: str) -> None:
        """Apply a new theme: rebind tokens -> restyle the whole tree."""
        set_theme_mode(mode)
        self.apply_theme()
        for page in getattr(self.router, "_page_map", {}).values():
            apply = getattr(page, "apply_theme", None)
            if callable(apply):
                try:
                    apply()
                except Exception:
                    pass
        restyle_app()
    def show_message(self, message: str, level: str = "info"):
        """显示消息提示"""

        if level == "error":
            QMessageBox.critical(self, "错误", message)
        elif level == "warning":
            QMessageBox.warning(self, "警告", message)
        else:
            QMessageBox.information(self, "提示", message)

    def show_loading(self, show: bool = True):
        """显示/隐藏加载状态"""
        self.statusbar.set_status("加载中..." if show else "就绪")

    def _on_action(self, action_id: str):
        if action_id == "export":
            self._on_export()

    def _on_export(self):
        """导出对话框：选择格式和输出目录，执行导出"""
        from PySide6.QtWidgets import QFileDialog, QInputDialog

        # 必须已完成生产流程，才有真实项目数据可供导出
        if self._last_project is None:
            QMessageBox.warning(self, "无法导出", "请先完成生产流程")
            return

        # 选择导出格式
        formats = ["剪映草稿", "MP4 视频"]
        fmt_choice, ok = QInputDialog.getItem(
            self, "导出格式", "请选择导出格式:", formats, 0, False
        )
        if not ok:
            return

        # 选择输出目录
        output_dir = QFileDialog.getExistingDirectory(self, "选择导出目录")
        if not output_dir:
            return

        # 执行导出
        from scenefab.services.export.export_manager import (
            ExportConfig,
            ExportFormat,
            ExportManager,
        )

        export_format = (
            ExportFormat.JIANYING if fmt_choice == "剪映草稿" else ExportFormat.MP4
        )
        config = ExportConfig(format=export_format, output_path=output_dir)

        try:
            manager = ExportManager()
            project_data = self._build_export_data(export_format)
            manager.export(project_data, config)
            self.statusbar.set_status("导出成功")
            if hasattr(self, "_home_page"):
                self._home_page.update_export_status("已完成")
            QMessageBox.information(self, "导出成功", f"已导出到:\n{output_dir}")
        except Exception as e:
            self.statusbar.set_status(f"导出失败: {e}")
            QMessageBox.critical(self, "导出失败", f"导出过程中出错:\n{e}")

    def _build_export_data(self, export_format):
        """将最近生产的项目转换为 ExportManager 期望的数据格式"""
        from scenefab.services.export.export_manager import ExportFormat

        project = self._last_project
        if export_format == ExportFormat.JIANYING:
            # 剪映导出需要带真实轨道的 JianyingDraft
            from scenefab.services.export.jianying_adapter import JianyingDraft
            from scenefab.services.video.track_builder import build_monologue_tracks

            draft = JianyingDraft(name=project.name)
            build_monologue_tracks(
                draft=draft,
                source_video=project.source_video,
                video_duration=project.video_duration,
                segments=project.segments,
                caption_style=project.caption_style,
            )
            return draft
        # MP4/MOV/GIF: DirectVideoExporter.export_commentary 需要项目对象本身
        return project

    # ══════════════════════════════════════════════════════════════
    # 生产流程接线
    # ══════════════════════════════════════════════════════════════

    def _on_start_production(self):
        """开始新生产流程：选择源视频 → 设置创作参数 → 后台运行 MonologueMaker"""
        from PySide6.QtWidgets import QFileDialog

        video_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择源视频",
            "",
            "视频文件 (*.mp4 *.mov *.avi *.mkv *.flv *.wmv);;所有文件 (*)",
        )
        if not video_path:
            return
        self._start_production_with_video(video_path)

    def _start_production_with_video(self, video_path: str):
        """使用指定视频路径启动生产流程（文件对话框与拖放共用）"""
        from PySide6.QtWidgets import QInputDialog

        # 解说主题/上下文（create_project 的必填参数）
        context, ok = QInputDialog.getText(
            self, "创作设置", "解说主题/上下文:", text="第一人称影视解说"
        )
        if not ok or not context.strip():
            return

        # 情感风格
        emotions = ["neutral", "惆怅", "忧郁", "开心", "平静", "温柔", "excited"]
        emotion, ok = QInputDialog.getItem(
            self, "创作设置", "情感风格:", emotions, 0, False
        )
        if not ok:
            return

        self.statusbar.set_status(f"正在处理: {video_path}")
        self.show_loading(True)
        if hasattr(self, "_production_page"):
            self._production_page.reset_steps()
            self._production_page.set_running(True)
            self._production_page.update_step_status(
                "素材审片", "进行中", _C.PRIMARY
            )

        # 后台线程运行 MonologueMaker
        from scenefab.core.base_worker import BaseWorker

        class ProductionWorker(BaseWorker):
            def _run(self):
                from pathlib import Path

                from scenefab.services.video.monologue_maker import MonologueMaker

                maker = MonologueMaker()
                project = maker.create_project(
                    source_video=video_path,
                    context=context,
                    emotion=emotion,
                )
                if project is None:
                    raise RuntimeError("项目创建失败")
                self.emit_progress(1, 5, "场景分析完成")
                if self.check_cancel_or_pause():
                    return

                maker.generate_script(project)
                self.emit_progress(2, 5, "脚本生成完成")
                if self.check_cancel_or_pause():
                    return

                maker.generate_voice(project)
                self.emit_progress(3, 5, "配音合成完成")
                if self.check_cancel_or_pause():
                    return

                maker.generate_captions(project)
                self.emit_progress(4, 5, "字幕生成完成")

                # 保存项目到 .scenefab 文件，避免生产结果丢失
                output_path = Path(project.output_dir) / f"{project.name}.scenefab"
                project_path = project.save(str(output_path))
                self.emit_progress(5, 5, "项目已保存")

                return {"project": project, "project_path": project_path}

        self._production_worker = ProductionWorker(
            name="ProductionWorker", cancellable=True
        )
        self._production_worker.progress.connect(self._on_production_progress)
        self._production_worker.finished.connect(self._on_production_finished)
        self._production_worker.error.connect(self._on_production_error)
        self._production_worker.cancelled.connect(self._on_production_cancelled)
        self._production_worker.start()

    def _on_production_progress(self, current, total, message):
        self.statusbar.set_status(f"[{current}/{total}] {message}")
        self.statusbar.show_progress(current, total)

        if not hasattr(self, "_production_page"):
            return
        page = self._production_page

        if current >= total:
            # 最终步骤（保存）：将全部 6 个步骤标记为已完成
            for step_name in _ALL_PRODUCTION_STEPS:
                page.update_step_status(step_name, "已完成", "#52c41a")
            return

        step_name = _PROGRESS_STEP_MAP.get(current)
        if step_name:
            page.update_step_status(step_name, "已完成", "#52c41a")
        next_step = _NEXT_ACTIVE_STEP.get(current)
        if next_step:
            page.update_step_status(next_step, "进行中", _C.PRIMARY)

    def _on_production_finished(self, result):

        self.show_loading(False)
        self.statusbar.hide_progress()
        if hasattr(self, "_production_page"):
            self._production_page.set_running(False)

        if not (result and result.success):
            self.statusbar.set_status("生产流程完成（有警告）")
            return

        # 保存最近一次生产的项目，供导出/另存使用
        data = result.data or {}
        self._last_project = data.get("project")
        project_path = data.get("project_path", "")
        self.statusbar.set_status("✅ 生产流程完成")

        # Refresh HomePage dashboard stats after production
        if hasattr(self, "_home_page"):
            self._home_page.refresh_stats()

        msg = "第一人称解说视频生产完成！"
        if project_path:
            msg += f"\n项目已保存到:\n{project_path}"

        box = QMessageBox(self)
        box.setWindowTitle("生产完成")
        box.setText(msg)
        export_btn = box.addButton("导出成片", QMessageBox.ButtonRole.ActionRole)
        save_btn = box.addButton("保存项目", QMessageBox.ButtonRole.ActionRole)
        box.addButton("关闭", QMessageBox.ButtonRole.RejectRole)
        box.exec()

        clicked = box.clickedButton()
        if clicked == export_btn:
            self._on_export()
        elif clicked == save_btn:
            self._on_save_project()

    def _on_production_error(self, error_msg):
        self.show_loading(False)
        self.statusbar.hide_progress()
        if hasattr(self, "_production_page"):
            self._production_page.set_running(False)
        self.statusbar.set_status(f"❌ 生产失败: {error_msg}")
        self.show_message(f"生产流程出错:\n{error_msg}", level="error")

    def _on_cancel_production(self):
        """请求取消正在运行的生产流程（取消按钮 / Escape 快捷键）"""
        worker = getattr(self, "_production_worker", None)
        if worker is not None and worker.isRunning():
            worker.cancel()
            self.statusbar.set_status("正在取消生产流程...")

    def _on_production_cancelled(self):
        """Worker 确认取消后恢复界面状态"""
        self.show_loading(False)
        self.statusbar.hide_progress()
        if hasattr(self, "_production_page"):
            self._production_page.set_running(False)
        self.statusbar.set_status("生产流程已取消")

    # ══════════════════════════════════════════════════════════════
    # 拖放支持
    # ══════════════════════════════════════════════════════════════

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                if url.toLocalFile().endswith(_VIDEO_EXTENSIONS):
                    event.acceptProposedAction()
                    return
        event.ignore()

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if path.endswith(_VIDEO_EXTENSIONS):
                self._start_production_with_video(path)
                break

    def _on_open_project(self, path: str = ""):
        """打开已有的 .scenefab 项目文件"""
        from PySide6.QtWidgets import QFileDialog

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "打开项目",
            path or "",
            "SceneFab 项目 (*.scenefab);;所有文件 (*)",
        )
        if not file_path:
            return

        try:
            from scenefab.services.video.monologue_maker import MonologueProject

            project = MonologueProject.load(file_path)
        except Exception as e:
            QMessageBox.critical(self, "打开失败", f"无法加载项目:\n{e}")
            return

        self._last_project = project
        self.statusbar.set_status(f"已打开项目: {project.name}")
        QMessageBox.information(
            self,
            "项目已打开",
            f"项目: {project.name}\n"
            f"源视频: {project.source_video}\n"
            f"时长: {project.video_duration:.1f}s\n"
            f"片段数: {len(project.segments)}\n"
            f"上下文: {project.context}",
        )

    def _on_save_project(self):
        """将当前项目另存为 .scenefab 文件"""
        from PySide6.QtWidgets import QFileDialog

        if self._last_project is None:
            QMessageBox.warning(self, "无法保存", "请先完成生产流程")
            return

        default_name = f"{self._last_project.name}.scenefab"
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "保存项目",
            default_name,
            "SceneFab 项目 (*.scenefab)",
        )
        if not file_path:
            return

        try:
            saved = self._last_project.save(file_path)
        except Exception as e:
            QMessageBox.critical(self, "保存失败", f"保存项目出错:\n{e}")
            return

        self.statusbar.set_status(f"项目已保存: {saved}")
        QMessageBox.information(self, "保存成功", f"项目已保存到:\n{saved}")

    def _on_import_assets(self):
        """导入素材：打开文件选择对话框，将素材添加到 AssetsPage 列表"""
        from PySide6.QtWidgets import QFileDialog

        files, _ = QFileDialog.getOpenFileNames(
            self,
            "导入素材",
            "",
            "媒体文件 (*.mp4 *.mov *.avi *.mkv *.mp3 *.wav *.jpg *.png);;所有文件 (*)",
        )
        if not files:
            return

        self.statusbar.set_status(f"已选择 {len(files)} 个素材文件")

        # Show imported files in the AssetsPage list
        if hasattr(self, "_assets_page"):
            self._assets_page.add_imported_files(files)

        # Register media files with the current project if one is open
        pm = getattr(self, "_project_manager", None)
        if pm is not None:
            current = pm.get_current_project()
            if current is not None:
                import shutil
                from pathlib import Path

                from scenefab.models.project_models import ProjectMedia

                media_dir = Path(current.path) / "media"
                media_dir.mkdir(parents=True, exist_ok=True)
                for fp in files:
                    src = Path(fp)
                    dst = media_dir / src.name
                    if not dst.exists():
                        shutil.copy2(src, dst)
                    media = ProjectMedia(
                        id=f"{src.stem}_{src.suffix.lstrip('.')}",
                        name=src.name,
                        type=src.suffix.lstrip(".").lower(),
                        path=str(dst),
                    )
                    current.add_media_file(media)
                pm.save_project(current.id)

    def build_global_stylesheet(self) -> str:
        """Return the QApplication-level stylesheet using current _C values."""
        prefix = f"""
            QMainWindow {{
                background: {_C.BG_BASE};
                outline: none;
            }}
            QToolButton#topbar_action_btn {{
                background: {_C.BG_SURFACE};
                border: 1px solid {_C.BORDER_DEFAULT};
                border-radius: {Radii.base};
                color: {_C.TEXT_SECONDARY};
                font-size: {FontSizes.xs}px;
                font-weight: 600;
            }}
            QToolButton#topbar_action_btn:hover {{
                background: {_C.PRIMARY_LIGHTEST};
                color: {_C.PRIMARY_DARKER};
                border-color: {_C.PRIMARY};
            }}
            QTooltip {{
                background: {_C.BG_OVERLAY};
                color: {_C.TEXT_PRIMARY};
                border: 1px solid {_C.BORDER_DEFAULT};
                border-radius: {Radii.sm};
                padding: 6px 10px;
                font-size: {FontSizes.xs}px;
            }}
        """
        suffix = f"""
            * {{
                selection-background-color: {_C.PRIMARY};
                selection-color: {_C.TEXT_INVERSE};
            }}
        """
        return prefix + QSSComponents.scrollbar() + suffix

    # ThemeAwareMixin hook: route _build_stylesheet to the live builder above
    def _build_stylesheet(self) -> str:
        return self.build_global_stylesheet()

    # ──────────────────────────────────────────────────────────
    # 路由 + 动作
    # ──────────────────────────────────────────────────────────

    def _on_navigate(self, page_id: str) -> None:
        self.router.navigate(page_id)

    def navigate_to(self, page_id: str, **_kwargs: object) -> None:
        """公共导航接口(供其他模块从外部跳转)。"""
        self._on_navigate(page_id)

    def _on_action(self, action_id: str) -> None:
        if action_id == "export":
            self._on_navigate("create")
            self.statusbar.set_status("请在创作流程完成后导出成片")

    # ──────────────────────────────────────────────────────────
    # 托盘 / 关闭
    # ──────────────────────────────────────────────────────────

    def _restore_from_tray(self) -> None:
        self.tray.restore_from_tray(self)

    def _open_settings_from_tray(self) -> None:
        self._restore_from_tray()
        self._on_navigate("settings")

    def _quit_application(self) -> None:
        app = QApplication.instance()
        if app is not None:
            app.quit()

    def set_minimize_to_tray(self, enabled: bool) -> None:
        """供 SettingsPage 调用的关闭行为开关。"""
        self.tray.set_minimize_to_tray(enabled)

    def closeEvent(self, event) -> None:
        self.tray.handle_close_event(self, event)

    # ──────────────────────────────────────────────────────────
    # 公共便利方法
    # ──────────────────────────────────────────────────────────

    @property
    def app(self) -> QApplication:
        return QApplication.instance()

    @property
    def application(self) -> Application | None:
        return self._application

    def _apply_saved_theme(self):
        """Read the persisted theme mode from QSettings and apply it."""
        from scenefab.ui.theme.theme_manager import ThemeManager

        qsettings = QSettings("SceneFab", "Application")
        mode = qsettings.value("appearance/theme_mode", "light", type=str)
        self._theme_manager = ThemeManager()
        if mode != "light":
            self._theme_manager.set_theme_mode(mode)


__all__ = ["SceneFabMainWindow"]
