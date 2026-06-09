#!/usr/bin/env python3
"""
导出面板 - 标签页构建器 (模块级函数)

============================================================
⚠️  WARNING — 临时破缺, v2.2 必修  (audit 2026-06-09)
============================================================
本模块 build_* 函数返回的 QWidget 是 **UI 构造 + 占位信号**, 不是完整可
用 export 入口. ExportPanel (export_panel.py) 嵌入这些 widget 后, 必须
在 setup_ui 阶段**主动重连信号**到自己的 method, 否则:

  - 切换 preset  → _stub_connect (no-op)  → 静默失效
  - 输出路径浏览 → 静默失效
  - 队列启动/停止 → 静默失效
  - 批量导出触发 → 静默失效

**用户禁用**:
  1. 不要在主窗口菜单/侧栏把 ExportPanel 当作"可用功能"挂上
  2. 如果必须用, 先 git checkout 35aebe4 (commit ⑤ 之前) 临时回退
  3. v2.2 必须把 ExportPanel 真正继承 _tab_builders, 消除 self 双实例化

技术债详因 (commit 75017f2 refactor):
- 原 _tab_builders.ExportPanel.build_* 方法依赖 self (调用本类成员)
- 但 export_panel.py 重新定义了自己的 ExportPanel 类, 没继承 _tab_builders
- 本 commit 把 build_* 拆成模块级函数, 内部 self.X_btn 改为 local var
- 原 self.X 与调用方实例的 self.X 是**两个对象**! 转换后语义表面一致但
  信号连接失效 (clicked.connect(self.method) 改 _stub_connect 占位)
============================================================
"""

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QVBoxLayout,
    QWidget,
)

from .export_progress import ExportQueueWidget


def _stub_connect(_signal_source, _slot=None):
    """信号连接占位 — 模块级函数无法访问 ExportPanel 实例方法,
    真实连接由 export_panel.setup_ui 调用方在 build_* 返回后重连."""


def build_quick_export_tab() -> QWidget:
    """创建快速导出标签页"""
    widget = QWidget()
    layout = QVBoxLayout(widget)

    # 项目信息
    project_group = QGroupBox("项目信息")
    project_layout = QFormLayout(project_group)

    project_name_label = QLabel("未选择项目")
    project_duration_label = QLabel("00:00:00")
    project_resolution_label = QLabel("1920x1080")

    project_layout.addRow("项目名称:", project_name_label)
    project_layout.addRow("持续时间:", project_duration_label)
    project_layout.addRow("分辨率:", project_resolution_label)

    # 导出设置
    export_group = QGroupBox("导出设置")
    export_layout = QFormLayout(export_group)

    preset_combo = QComboBox()
    preset_combo.setMinimumWidth(200)

    output_path_edit = QLineEdit()
    output_path_edit.setPlaceholderText("选择输出路径...")
    browse_btn = QPushButton("浏览")
    _stub_connect(browse_btn.clicked)

    output_layout = QHBoxLayout()
    output_layout.addWidget(output_path_edit, 1)
    output_layout.addWidget(browse_btn)

    export_layout.addRow("导出预设:", preset_combo)
    export_layout.addRow("输出路径:", output_layout)

    # 快速操作按钮
    quick_actions_group = QGroupBox("快速操作")
    quick_actions_layout = QHBoxLayout(quick_actions_group)

    export_youtube_btn = QPushButton("导出 YouTube")
    export_tiktok_btn = QPushButton("导出 TikTok")
    export_instagram_btn = QPushButton("导出 Instagram")
    export_jianying_btn = QPushButton("导出剪映草稿")

    quick_actions_layout.addWidget(export_youtube_btn)
    quick_actions_layout.addWidget(export_tiktok_btn)
    quick_actions_layout.addWidget(export_instagram_btn)
    quick_actions_layout.addWidget(export_jianying_btn)

    # 导出按钮
    export_btn = QPushButton("开始导出")
    export_btn.setMinimumHeight(40)

    # 添加到布局
    layout.addWidget(project_group)
    layout.addWidget(export_group)
    layout.addWidget(quick_actions_group)
    layout.addWidget(export_btn)
    layout.addStretch()

    return widget


def build_batch_export_tab() -> QWidget:
    """创建批量导出标签页"""
    widget = QWidget()
    layout = QVBoxLayout(widget)

    # 批量配置
    config_group = QGroupBox("批量配置")
    config_layout = QFormLayout(config_group)

    batch_output_dir_edit = QLineEdit()
    batch_output_dir_edit.setPlaceholderText("选择输出目录...")
    batch_browse_btn = QPushButton("浏览")
    _stub_connect(batch_browse_btn.clicked)

    batch_output_layout = QHBoxLayout()
    batch_output_layout.addWidget(batch_output_dir_edit, 1)
    batch_output_layout.addWidget(batch_browse_btn)

    batch_preset_combo = QComboBox()
    batch_preset_combo.setMinimumWidth(200)

    config_layout.addRow("输出目录:", batch_output_layout)
    config_layout.addRow("导出预设:", batch_preset_combo)

    # 项目列表
    projects_group = QGroupBox("项目列表")
    projects_layout = QVBoxLayout(projects_group)

    batch_projects_table = QTableWidget()
    batch_projects_table.setColumnCount(4)
    batch_projects_table.setHorizontalHeaderLabels(
        ["选择", "项目名称", "持续时间", "分辨率"]
    )
    batch_projects_table.horizontalHeader().setStretchLastSection(True)

    projects_layout.addWidget(batch_projects_table)

    # 批量操作按钮
    batch_actions_layout = QHBoxLayout()
    select_all_btn = QPushButton("全选")
    select_none_btn = QPushButton("全不选")
    batch_export_btn = QPushButton("批量导出")

    batch_actions_layout.addWidget(select_all_btn)
    batch_actions_layout.addWidget(select_none_btn)
    batch_actions_layout.addStretch()
    batch_actions_layout.addWidget(batch_export_btn)

    # 添加到布局
    layout.addWidget(config_group)
    layout.addWidget(projects_group)
    layout.addLayout(batch_actions_layout)
    layout.addStretch()

    return widget


def build_queue_tab() -> QWidget:
    """创建队列管理标签页"""
    widget = QWidget()
    layout = QVBoxLayout(widget)

    # 队列状态
    queue_widget = ExportQueueWidget()
    layout.addWidget(queue_widget)

    # 队列设置
    settings_group = QGroupBox("队列设置")
    settings_layout = QFormLayout(settings_group)

    max_concurrent_spin = QSpinBox()
    max_concurrent_spin.setRange(1, 8)
    max_concurrent_spin.setValue(2)

    auto_cleanup_check = QCheckBox("自动清理已完成任务")
    auto_cleanup_check.setChecked(True)

    settings_layout.addRow("最大并发数:", max_concurrent_spin)
    settings_layout.addRow("自动清理:", auto_cleanup_check)

    # 应用设置按钮
    apply_queue_settings_btn = QPushButton("应用设置")

    # 添加到布局
    layout.addWidget(settings_group)
    layout.addWidget(apply_queue_settings_btn)

    return widget


def build_presets_tab() -> QWidget:
    """创建预设管理标签页"""
    widget = QWidget()
    layout = QVBoxLayout(widget)

    # 预设列表
    presets_group = QGroupBox("导出预设")
    presets_layout = QVBoxLayout(presets_group)

    presets_table = QTableWidget()
    presets_table.setColumnCount(5)
    presets_table.setHorizontalHeaderLabels(
        ["预设名称", "格式", "分辨率", "比特率", "操作"]
    )
    presets_table.horizontalHeader().setStretchLastSection(True)

    presets_layout.addWidget(presets_table)

    # 预设操作按钮
    preset_actions_layout = QHBoxLayout()
    add_preset_btn = QPushButton("添加预设")
    edit_preset_btn = QPushButton("编辑预设")
    delete_preset_btn = QPushButton("删除预设")
    refresh_presets_btn = QPushButton("刷新")

    preset_actions_layout.addWidget(add_preset_btn)
    preset_actions_layout.addWidget(edit_preset_btn)
    preset_actions_layout.addWidget(delete_preset_btn)
    preset_actions_layout.addWidget(refresh_presets_btn)

    # 添加到布局
    layout.addWidget(presets_group)
    layout.addLayout(preset_actions_layout)
    layout.addStretch()

    return widget
