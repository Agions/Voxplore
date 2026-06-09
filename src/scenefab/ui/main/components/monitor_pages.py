#!/usr/bin/env python3

"""
AI监控面板 - 页面创建
"""

from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QVBoxLayout,
    QWidget,
)

from .monitor_widgets import PerformanceChart


class MonitorPages:
    """AI监控面板页面创建助手"""

    def __init__(self, panel):
        self.panel = panel  # Reference to AIMonitorPanel

    # -------------------------------------------------------------------------
    # Page Factories
    # -------------------------------------------------------------------------

    def create_overview_page(self) -> QWidget:
        """创建概览页面"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # 统计卡片
        stats_layout, frames = self._create_overview_stats_cards()
        layout.addLayout(stats_layout)

        # 服务状态列表
        layout.addWidget(self._create_services_status_section())

        # 性能图表
        layout.addLayout(self._create_overview_charts())

        layout.addStretch()

        # 保存引用
        self._save_overview_stats_references(frames)

        return page

    # ── overview helpers ─────────────────────────────────────────

    def _create_overview_stats_cards(self) -> tuple[QGridLayout, dict[str, QFrame]]:
        """创建概览页面的统计卡片，返回 (layout, {title: frame})"""
        stats_layout = QGridLayout()
        stats_layout.setSpacing(10)

        card_specs: list[tuple[int, int, str, str, str]] = [
            (0, 0, "服务状态", "0/0", "正常运行/总数"),
            (0, 1, "总请求数", "0", "今日请求"),
            (0, 2, "成功率", "100%", "请求成功率"),
            (1, 0, "响应时间", "0ms", "平均响应时间"),
            (1, 1, "总成本", "¥0.00", "今日成本"),
            (1, 2, "告警", "0", "未解决告警"),
        ]

        frames: dict[str, QFrame] = {}
        for row, col, title, value, subtitle in card_specs:
            frame = self._create_stat_card(title, value, subtitle)
            stats_layout.addWidget(frame, row, col)
            frames[title] = frame

        return stats_layout, frames

    def _create_services_status_section(self) -> QGroupBox:
        """创建服务状态列表区域"""
        services_group = QGroupBox("服务状态")
        services_group.setProperty("class", "monitor-group")
        services_layout = QVBoxLayout(services_group)

        self.panel.services_status_list = QWidget()
        self.panel.services_status_layout = QVBoxLayout(self.panel.services_status_list)
        self.panel.services_status_layout.setContentsMargins(0, 0, 0, 0)
        self.panel.services_status_layout.setSpacing(5)

        scroll_area = QScrollArea()
        scroll_area.setWidget(self.panel.services_status_list)
        scroll_area.setWidgetResizable(True)
        scroll_area.setMaximumHeight(200)
        services_layout.addWidget(scroll_area)

        return services_group

    def _create_overview_charts(self) -> QHBoxLayout:
        """创建概览页面的性能图表"""
        charts_layout = QHBoxLayout()
        charts_layout.setSpacing(10)

        self.panel.response_time_chart = PerformanceChart("响应时间 (ms)", 1000)
        charts_layout.addWidget(self.panel.response_time_chart)

        self.panel.error_rate_chart = PerformanceChart("错误率 (%)", 100)
        charts_layout.addWidget(self.panel.error_rate_chart)

        self.panel.throughput_chart = PerformanceChart("吞吐量 (req/s)", 100)
        charts_layout.addWidget(self.panel.throughput_chart)

        return charts_layout

    def _save_overview_stats_references(self, frames: dict[str, QFrame]) -> None:
        """保存概览页面统计卡片的 QLabel 引用到 panel"""
        self.panel.service_stats_label = frames["服务状态"].findChild(QLabel, "value_label")
        self.panel.requests_stats_label = frames["总请求数"].findChild(QLabel, "value_label")
        self.panel.success_stats_label = frames["成功率"].findChild(QLabel, "value_label")
        self.panel.response_stats_label = frames["响应时间"].findChild(QLabel, "value_label")
        self.panel.cost_stats_label = frames["总成本"].findChild(QLabel, "value_label")
        self.panel.alerts_stats_label = frames["告警"].findChild(QLabel, "value_label")

    def create_services_page(self) -> QWidget:
        """创建服务页面"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # 服务列表
        self.panel.services_table = QTableWidget()
        self.panel.services_table.setColumnCount(6)
        self.panel.services_table.setHorizontalHeaderLabels(
            ["服务", "状态", "响应时间", "错误率", "成功率", "操作"]
        )
        self.panel.services_table.horizontalHeader().setStretchLastSection(True)
        self.panel.services_table.verticalHeader().setVisible(False)
        self.panel.services_table.setAlternatingRowColors(True)
        self.panel.services_table.setProperty("class", "monitor-services-table")

        layout.addWidget(self.panel.services_table)

        return page

    def create_performance_page(self) -> QWidget:
        """创建性能页面"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # 性能图表区域
        charts_group = QGroupBox("性能指标")
        charts_group.setProperty("class", "monitor-group")
        charts_layout = QGridLayout(charts_group)

        # 响应时间趋势
        self.panel.response_trend_chart = PerformanceChart("响应时间趋势 (ms)", 1000)
        charts_layout.addWidget(self.panel.response_trend_chart, 0, 0)

        # 错误率趋势
        self.panel.error_trend_chart = PerformanceChart("错误率趋势 (%)", 100)
        charts_layout.addWidget(self.panel.error_trend_chart, 0, 1)

        # 吞吐量趋势
        self.panel.throughput_trend_chart = PerformanceChart("吞吐量趋势 (req/s)", 100)
        charts_layout.addWidget(self.panel.throughput_trend_chart, 1, 0)

        # CPU使用率
        self.panel.cpu_usage_chart = PerformanceChart("CPU使用率 (%)", 100)
        charts_layout.addWidget(self.panel.cpu_usage_chart, 1, 1)

        layout.addWidget(charts_group)

        return page

    def create_usage_page(self) -> QWidget:
        """创建使用量页面"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # 使用量统计
        usage_group = QGroupBox("使用量统计")
        usage_group.setProperty("class", "monitor-group")
        usage_layout = QVBoxLayout(usage_group)

        self.panel.usage_table = QTableWidget()
        self.panel.usage_table.setColumnCount(5)
        self.panel.usage_table.setHorizontalHeaderLabels(
            ["服务", "请求数", "成功数", "失败数", "成本"]
        )
        self.panel.usage_table.horizontalHeader().setStretchLastSection(True)
        self.panel.usage_table.verticalHeader().setVisible(False)
        self.panel.usage_table.setAlternatingRowColors(True)
        self.panel.usage_table.setProperty("class", "monitor-usage-table")

        usage_layout.addWidget(self.panel.usage_table)

        layout.addWidget(usage_group)

        return page

    def create_alerts_page(self) -> QWidget:
        """创建告警页面"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # 告警过滤器
        filter_layout = QHBoxLayout()

        filter_label = QLabel("过滤:")
        filter_layout.addWidget(filter_label)

        self.panel.alert_filter_combo = QComboBox()
        self.panel.alert_filter_combo.addItems(["全部", "信息", "警告", "错误", "严重"])
        self.panel.alert_filter_combo.currentTextChanged.connect(
            self.panel._filter_alerts
        )
        filter_layout.addWidget(self.panel.alert_filter_combo)

        filter_layout.addStretch()

        # 清除告警按钮
        clear_btn = QPushButton("清除已解决")
        clear_btn.clicked.connect(self.panel._clear_resolved_alerts)
        filter_layout.addWidget(clear_btn)

        layout.addLayout(filter_layout)

        # 告警列表
        self.panel.alerts_list = QWidget()
        self.panel.alerts_layout = QVBoxLayout(self.panel.alerts_list)
        self.panel.alerts_layout.setContentsMargins(0, 0, 0, 0)
        self.panel.alerts_layout.setSpacing(5)

        alerts_scroll = QScrollArea()
        alerts_scroll.setWidget(self.panel.alerts_list)
        alerts_scroll.setWidgetResizable(True)
        layout.addWidget(alerts_scroll)

        return page

    # -------------------------------------------------------------------------
    # Stat Card Helper
    # -------------------------------------------------------------------------

    def _create_stat_card(self, title: str, value: str, subtitle: str) -> QFrame:
        """创建统计卡片"""
        frame = QFrame()
        frame.setFrameShape(QFrame.Shape.StyledPanel)
        frame.setProperty("class", "monitor-stat-card")
        frame.setFixedSize(200, 80)

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(5)

        # 标题
        title_label = QLabel(title)
        title_label.setProperty("class", "stat-card-title")
        layout.addWidget(title_label)

        # 数值
        value_label = QLabel(value)
        value_label.setProperty("class", "stat-card-value")
        value_label.setObjectName("value_label")
        layout.addWidget(value_label)

        # 副标题
        subtitle_label = QLabel(subtitle)
        subtitle_label.setProperty("class", "stat-card-subtitle")
        layout.addWidget(subtitle_label)

        return frame
