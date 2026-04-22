"""
项目列表窗口
接入真实 ProjectManager，支持项目 CRUD
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QScrollArea, QFrame, QGridLayout,
    QSizePolicy, QSpacerItem, QInputDialog, QMessageBox,
    QMenu, QApplication
)
from PySide6.QtCore import Qt, Signal, QSize, QTimer
from PySide6.QtGui import QFont, QAction, QCursor
from app.core.project_manager import ProjectManager, Project


class ProjectCard(QFrame):
    """
    项目卡片
    显示项目信息，支持双击打开、右键菜单
    """
    open_requested = Signal(str)  # 项目路径
    delete_requested = Signal(str, str)  # (project_id, project_path)

    def __init__(self, project: dict, parent=None):
        super().__init__(parent)
        self.project = project
        self._setup_ui()

    def _setup_ui(self):
        self.setObjectName("project_card")
        self.setMinimumSize(200, 160)
        self.setMaximumSize(280, 200)
        self.setCursor(Qt.PointingHandCursor)

        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(16, 16, 16, 16)

        # 缩略图区
        thumb_container = QFrame()
        thumb_container.setObjectName("thumb_container")
        thumb_layout = QVBoxLayout(thumb_container)
        thumb_layout.setContentsMargins(0, 0, 0, 0)

        self.thumb = QLabel(self.project.get("thumb", "🎬"))
        self.thumb.setAlignment(Qt.AlignCenter)
        self.thumb.setStyleSheet("font-size: 48px;")
        self.thumb.setFixedHeight(80)
        thumb_layout.addWidget(self.thumb)
        layout.addWidget(thumb_container)

        # 状态标签
        status = self.project.get("status", "draft")
        status_colors = {
            "draft": "#888",
            "processing": "#F59E0B",
            "done": "#10B981",
            "error": "#EF4444",
        }
        self.status_label = QLabel({"draft": "📝 草稿", "processing": "⚙️ 处理中", "done": "✅ 完成", "error": "❌ 错误"}.get(status, ""))
        self.status_label.setStyleSheet(f"color: {status_colors.get(status, '#888')}; font-size: 11px;")
        layout.addWidget(self.status_label)

        # 名称
        self.name = QLabel(self.project.get("name", "未命名项目"))
        self.name.setFont(QFont("Inter", 13, QFont.Bold))
        self.name.setWordWrap(True)
        layout.addWidget(self.name)

        # 日期
        self.date = QLabel(self.project.get("date", ""))
        self.date.setObjectName("project_date")
        self.date.setStyleSheet("color: #666; font-size: 12px;")
        layout.addWidget(self.date)

        layout.addStretch()

        # 鼠标事件
        self.mousePressEvent = lambda e: self._handle_click(e)

    def _handle_click(self, event):
        if event.button() == Qt.LeftButton:
            self.open_requested.emit(self.project.get("path", ""))
        elif event.button() == Qt.RightButton:
            self._show_context_menu()

    def _show_context_menu(self):
        menu = QMenu(self)
        open_act = QAction("打开项目", self)
        open_act.triggered.connect(lambda: self.open_requested.emit(self.project.get("path", "")))
        delete_act = QAction("删除项目", self)
        delete_act.triggered.connect(
            lambda: self.delete_requested.emit(
                self.project.get("id", ""),
                self.project.get("path", "")
            )
        )
        menu.addAction(open_act)
        menu.addSeparator()
        menu.addAction(delete_act)
        menu.exec(QCursor.pos())


class ProjectsWindow(QWidget):
    """
    项目列表窗口（独立窗口，非步骤流程）
    功能：
    - 显示所有项目（从 ProjectManager 加载）
    - 新建项目
    - 打开已有项目
    - 删除项目
    """
    project_selected = Signal(str)  # 项目路径，发给 MainWindow

    def __init__(self, parent=None):
        super().__init__(parent)
        self._pm = ProjectManager()
        self._projects = []
        self._setup_ui()
        self._load_projects()

    def _setup_ui(self):
        self.setWindowTitle("Voxplore — 项目列表")
        self.setMinimumSize(900, 650)

        layout = QVBoxLayout(self)
        layout.setSpacing(24)
        layout.setContentsMargins(32, 32, 32, 32)

        # 标题栏
        header = QHBoxLayout()

        title = QLabel("我的项目")
        title.setFont(QFont("Inter", 26, QFont.Bold))
        title.setStyleSheet("color: #f0f0f0;")

        self.btn_new = QPushButton("+ 新建项目")
        self.btn_new.setObjectName("primary")
        self.btn_new.setMinimumHeight(40)
        self.btn_new.setFont(QFont("Inter", 14))
        self.btn_new.clicked.connect(self._new_project)

        header.addWidget(title)
        header.addStretch()
        header.addWidget(self.btn_new)
        layout.addLayout(header)

        # 项目网格（ScrollArea）
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setObjectName("projects_scroll")
        scroll.setStyleSheet("""
            QScrollArea { border: none; background: transparent; }
            QScrollArea > QWidget > QWidget { background: transparent; }
        """)

        self.grid_widget = QWidget()
        self.grid_layout = QGridLayout(self.grid_widget)
        self.grid_layout.setSpacing(16)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)

        scroll.setWidget(self.grid_widget)
        layout.addWidget(scroll, stretch=1)

        # 底部信息栏
        footer = QHBoxLayout()
        self.footer_label = QLabel("")
        self.footer_label.setObjectName("footer_label")
        footer.addWidget(self.footer_label)
        footer.addStretch()
        layout.addLayout(footer)

    def _load_projects(self):
        """从 ProjectManager 加载真实项目"""
        self._projects = []
        try:
            for proj in self._pm.get_all_projects():
                self._projects.append({
                    "id": proj.id,
                    "name": proj.metadata.name,
                    "date": proj.metadata.modified_at.strftime("%Y-%m-%d") if proj.metadata.modified_at else "未知",
                    "status": proj.metadata.status.value if proj.metadata.status else "draft",
                    "path": proj.path,
                    "thumb": self._get_thumb_for_status(proj.metadata.status.value if proj.metadata.status else "draft"),
                })
        except Exception as e:
            print(f"[ProjectsWindow] 加载项目失败: {e}")
        self._render_projects()

    def _get_thumb_for_status(self, status: str) -> str:
        return {"draft": "📁", "processing": "⚙️", "done": "🎬", "error": "❌"}.get(status, "📁")

    def _render_projects(self):
        """渲染项目卡片网格"""
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        cols = 4
        if not self._projects:
            empty = QLabel("  还没有项目\n  点击右上角「新建项目」开始创作")
            empty.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            empty.setObjectName("empty_state")
            empty.setStyleSheet("color: #555; font-size: 15px; padding: 40px;")
            self.grid_layout.addWidget(empty, 0, 0, 1, cols)
        else:
            for i, proj in enumerate(self._projects):
                card = ProjectCard(proj)
                card.open_requested.connect(self._open_project)
                card.delete_requested.connect(self._delete_project)
                row, col = divmod(i, cols)
                self.grid_layout.addWidget(card, row, col)

        self.footer_label.setText(f"共 {len(self._projects)} 个项目")

    def _new_project(self):
        """新建项目"""
        name, ok = QInputDialog.getText(self, "新建项目", "项目名称:")
        if ok and name.strip():
            project_id, project_path = self._pm.create_project(name.strip())
            self._load_projects()
            # 自动打开新项目
            QTimer.singleShot(100, lambda: self._open_project(project_path))

    def _open_project(self, project_path: str):
        """打开项目"""
        result = self._pm.open_project(project_path)
        if result:
            self.project_selected.emit(project_path)
        else:
            QMessageBox.warning(self, "错误", f"无法打开项目：\n{project_path}")

    def _delete_project(self, project_id: str, project_path: str):
        """删除项目"""
        reply = QMessageBox.question(
            self, "确认删除", f"确定要删除项目「{project_path.split('/')[-1]}」吗？\n此操作不可恢复。",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            success = self._pm.delete_project(project_id)
            if success:
                self._load_projects()
            else:
                QMessageBox.warning(self, "错误", "删除失败")

    def refresh(self):
        """外部刷新接口"""
        self._load_projects()
