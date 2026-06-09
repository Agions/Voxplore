#!/usr/bin/env python3
"""
导出面板 - 标签页构建器 (模块级函数)

==================================================================
v2.2 P0 修复 (refactor 2026-06-09): 消除 ExportPanel 双实例化
==================================================================
原 commit 75017f2 把 build_* 拆成模块级函数, 但信号 connect 改为 _stub_connect
占位, 导致:
  - 切换 preset      → 静默失效
  - 输出路径浏览     → 静默失效
  - 队列/批量启动    → 静默失效

修复方案: build_* 现在返回 (widget, refs) 元组, refs 包含所有需要
暴露给 ExportPanel 的 widget 引用. ExportPanel 在 setup_ui() 接收
refs 后复制到 self, 真实信号连接到 self.method.
==================================================================
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
    """
    向后兼容: 旧版 build_* 调用 _stub_connect 占位.

    v2.2 修复后, build_* 改用 _real_connect 返回 refs, 调用方连真实信号.
    此函数保留以防其他旧调用点.
    """
    pass


def _make_button(label: str) -> QPushButton:
    """统一创建按钮 — 提取重复的 QPushButton(label)"""
    return QPushButton(label)


def build_quick_export_tab() -> tuple[QWidget, dict[str, QWidget]]:
    """创建快速导出标签页. 返回 (widget, refs) — refs 包含 ExportPanel 需引用的 widget"""
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
    browse_btn = _make_button("浏览")

    output_layout = QHBoxLayout()
    output_layout.addWidget(output_path_edit, 1)
    output_layout.addWidget(browse_btn)

    export_layout.addRow("导出预设:", preset_combo)
    export_layout.addRow("输出路径:", output_layout)

    # 快速操作按钮
    quick_actions_group = QGroupBox("快速操作")
    quick_actions_layout = QHBoxLayout(quick_actions_group)

    export_youtube_btn = _make_button("导出 YouTube")
    export_tiktok_btn = _make_button("导出 TikTok")
    export_instagram_btn = _make_button("导出 Instagram")
    export_jianying_btn = _make_button("导出剪映草稿")

    quick_actions_layout.addWidget(export_youtube_btn)
    quick_actions_layout.addWidget(export_tiktok_btn)
    quick_actions_layout.addWidget(export_instagram_btn)
    quick_actions_layout.addWidget(export_jianying_btn)

    # 导出按钮
    export_btn = _make_button("开始导出")
    export_btn.setMinimumHeight(40)

    # 添加到布局
    layout.addWidget(project_group)
    layout.addWidget(export_group)
    layout.addWidget(quick_actions_group)
    layout.addWidget(export_btn)
    layout.addStretch()

    refs = {
        "project_name_label": project_name_label,
        "project_duration_label": project_duration_label,
        "project_resolution_label": project_resolution_label,
        "preset_combo": preset_combo,
        "output_path_edit": output_path_edit,
        "browse_btn": browse_btn,
        "export_youtube_btn": export_youtube_btn,
        "export_tiktok_btn": export_tiktok_btn,
        "export_instagram_btn": export_instagram_btn,
        "export_jianying_btn": export_jianying_btn,
        "export_btn": export_btn,
    }
    return widget, refs


def build_batch_export_tab() -> tuple[QWidget, dict[str, QWidget]]:
    """创建批量导出标签页. 返回 (widget, refs)"""
    widget = QWidget()
    layout = QVBoxLayout(widget)

    # 批量配置
    config_group = QGroupBox("批量配置")
    config_layout = QFormLayout(config_group)

    batch_output_dir_edit = QLineEdit()
    batch_output_dir_edit.setPlaceholderText("选择输出目录...")
    batch_browse_btn = _make_button("浏览")

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
    select_all_btn = _make_button("全选")
    select_none_btn = _make_button("全不选")
    batch_export_btn = _make_button("批量导出")

    batch_actions_layout.addWidget(select_all_btn)
    batch_actions_layout.addWidget(select_none_btn)
    batch_actions_layout.addStretch()
    batch_actions_layout.addWidget(batch_export_btn)

    # 添加到布局
    layout.addWidget(config_group)
    layout.addWidget(projects_group)
    layout.addLayout(batch_actions_layout)
    layout.addStretch()

    refs = {
        "batch_output_dir_edit": batch_output_dir_edit,
        "batch_browse_btn": batch_browse_btn,
        "batch_preset_combo": batch_preset_combo,
        "batch_projects_table": batch_projects_table,
        "select_all_btn": select_all_btn,
        "select_none_btn": select_none_btn,
        "batch_export_btn": batch_export_btn,
    }
    return widget, refs


def build_queue_tab() -> tuple[QWidget, dict[str, QWidget]]:
    """创建队列管理标签页. 返回 (widget, refs)"""
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
    apply_queue_settings_btn = _make_button("应用设置")

    # 添加到布局
    layout.addWidget(settings_group)
    layout.addWidget(apply_queue_settings_btn)

    refs = {
        "queue_widget": queue_widget,
        "max_concurrent_spin": max_concurrent_spin,
        "auto_cleanup_check": auto_cleanup_check,
        "apply_queue_settings_btn": apply_queue_settings_btn,
    }
    return widget, refs


def build_presets_tab() -> tuple[QWidget, dict[str, QWidget]]:
    """创建预设管理标签页. 返回 (widget, refs)"""
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
    add_preset_btn = _make_button("添加预设")
    edit_preset_btn = _make_button("编辑预设")
    delete_preset_btn = _make_button("删除预设")
    refresh_presets_btn = _make_button("刷新")

    preset_actions_layout.addWidget(add_preset_btn)
    preset_actions_layout.addWidget(edit_preset_btn)
    preset_actions_layout.addWidget(delete_preset_btn)
    preset_actions_layout.addWidget(refresh_presets_btn)

    # 添加到布局
    layout.addWidget(presets_group)
    layout.addLayout(preset_actions_layout)
    layout.addStretch()

    refs = {
        "presets_table": presets_table,
        "add_preset_btn": add_preset_btn,
        "edit_preset_btn": edit_preset_btn,
        "delete_preset_btn": delete_preset_btn,
        "refresh_presets_btn": refresh_presets_btn,
    }
    return widget, refs
