#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
AI状态监控面板
实时监控AI服务的运行状态、性能指标和使用情况
"""

import time as time_module
from typing import Dict, Any, List, Optional
from datetime import datetime

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QStackedWidget,
    QPushButton, QLabel, QGroupBox, QMessageBox, QTableWidgetItem
)
from PySide6.QtCore import QTimer, Signal
from PySide6.QtGui import QColor

from ....core.logger import Logger
from ....core.icon_manager import get_icon
from ....core.application import Application
from ....services import ServiceStatus

from .monitor_models import MonitorMode, AlertData
from .monitor_widgets import ServiceStatusWidget, PerformanceChart, AlertWidget
from .monitor_pages import MonitorPages


class AIMonitorPanel(QWidget):
    """AI状态监控面板"""

    # 信号定义
    service_selected = Signal(str)
    alert_selected = Signal(AlertData)
    refresh_requested = Signal()

    def __init__(self, application: Application):
        super().__init__()
        self.application = application
        self.logger = application.get_service(Logger)
        self.ai_service_manager = None
        self.current_mode = MonitorMode.OVERVIEW
        self.alerts: List[AlertData] = []
        self.performance_data: Dict[str, List[float]] = {}

        # 获取AI服务管理器
        self._get_ai_service_manager()

        # 定时器
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._update_monitor_data)
        self.update_timer.start(5000)  # 5秒更新一次

        # 页面创建助手
        self.pages = MonitorPages(self)

        self._init_ui()
        self._setup_connections()

    def _get_ai_service_manager(self):
        """获取AI服务管理器"""
        try:
            self.ai_service_manager = self.application.get_service_by_name("ai_service_manager")
            if not self.ai_service_manager:
                self.logger.warning("AI服务管理器未注册")
        except Exception as e:
            self.logger.error(f"获取AI服务管理器失败: {e}")

    def _init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # 模式切换栏
        mode_bar = QFrame()
        mode_bar.setFrameShape(QFrame.Shape.StyledPanel)
        mode_bar.setProperty("class", "monitor-mode-bar")
        mode_layout = QHBoxLayout(mode_bar)
        mode_layout.setContentsMargins(10, 10, 10, 10)

        # 模式按钮
        mode_buttons = []
        mode_list = [
            (MonitorMode.OVERVIEW, "概览"),
            (MonitorMode.SERVICES, "服务"),
            (MonitorMode.PERFORMANCE, "性能"),
            (MonitorMode.USAGE, "使用量"),
            (MonitorMode.ALERTS, "告警"),
        ]
        for mode_key, mode_text in mode_list:
            btn = QPushButton(mode_text)
            btn.setFixedSize(80, 30)
            btn.setCheckable(True)
            btn.setProperty("class", "monitor-mode-button")
            btn.clicked.connect(lambda checked, m=mode_key: self._switch_mode(m))
            mode_layout.addWidget(btn)
            mode_buttons.append(btn)

        # 设置默认按钮
        mode_buttons[0].setChecked(True)
        mode_buttons[0].setProperty("class", "monitor-mode-button active")
        self.mode_buttons = mode_buttons

        mode_layout.addStretch()

        # 刷新按钮
        refresh_btn = QPushButton(get_icon("refresh", 16), "刷新")
        refresh_btn.setFixedSize(80, 30)
        refresh_btn.setProperty("class", "monitor-refresh-button")
        refresh_btn.clicked.connect(self._refresh_data)
        mode_layout.addWidget(refresh_btn)

        layout.addWidget(mode_bar)

        # 内容区域
        self.content_stack = QStackedWidget()
        self.content_stack.setProperty("class", "monitor-content-stack")

        # 创建各个模式的内容页面
        self.overview_page = self.pages.create_overview_page()
        self.services_page = self.pages.create_services_page()
        self.performance_page = self.pages.create_performance_page()
        self.usage_page = self.pages.create_usage_page()
        self.alerts_page = self.pages.create_alerts_page()

        self.content_stack.addWidget(self.overview_page)
        self.content_stack.addWidget(self.services_page)
        self.content_stack.addWidget(self.performance_page)
        self.content_stack.addWidget(self.usage_page)
        self.content_stack.addWidget(self.alerts_page)

        layout.addWidget(self.content_stack)

    def _get_mode_text(self, mode) -> str:
        """获取模式文本"""
        mode_texts = {
            MonitorMode.OVERVIEW: "概览",
            MonitorMode.SERVICES: "服务",
            MonitorMode.PERFORMANCE: "性能",
            MonitorMode.USAGE: "使用量",
            MonitorMode.ALERTS: "告警"
        }
        return mode_texts.get(mode, "未知")

    def _switch_mode(self, mode):
        """切换模式"""
        self.current_mode = mode

        # 更新按钮状态
        for btn in self.mode_buttons:
            btn.setChecked(btn.text() == self._get_mode_text(mode))

        # 切换页面
        page_index = {
            MonitorMode.OVERVIEW: 0,
            MonitorMode.SERVICES: 1,
            MonitorMode.PERFORMANCE: 2,
            MonitorMode.USAGE: 3,
            MonitorMode.ALERTS: 4
        }.get(mode, 0)

        self.content_stack.setCurrentIndex(page_index)

    def _setup_connections(self):
        """设置信号连接"""
        # 连接AI服务管理器信号
        if self.ai_service_manager:
            self.ai_service_manager.service_health_updated.connect(self._on_service_health_updated)
            self.ai_service_manager.stats_updated.connect(self._on_stats_updated)

    # -------------------------------------------------------------------------
    # Data Update Methods
    # -------------------------------------------------------------------------

    def _update_monitor_data(self):
        """更新监控数据"""
        try:
            if not self.ai_service_manager:
                return

            # 更新服务状态
            self._update_services_status()

            # 更新统计数据
            self._update_stats()

            # 更新性能数据
            self._update_performance_data()

            # 更新告警
            self._update_alerts()

        except Exception as e:
            self.logger.error(f"更新监控数据失败: {e}")

    def _update_services_status(self):
        """更新服务状态"""
        try:
            if not self.ai_service_manager:
                return

            # 更新概览页面的服务状态
            self._update_services_status_list()

            # 更新服务页面的表格
            self._update_services_table()

        except Exception as e:
            self.logger.error(f"更新服务状态失败: {e}")

    def _update_services_status_list(self):
        """更新服务状态列表"""
        try:
            # 清除现有部件
            while self.services_status_layout.count():
                item = self.services_status_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()

            # 添加新的服务状态部件
            if self.ai_service_manager:
                for service_name, health in self.ai_service_manager.service_health.items():
                    status_widget = ServiceStatusWidget(service_name, health.status, health.__dict__)
                    self.services_status_layout.addWidget(status_widget)

        except Exception as e:
            self.logger.error(f"更新服务状态列表失败: {e}")

    def _update_services_table(self):
        """更新服务表格"""
        try:
            if not self.ai_service_manager:
                return

            services = self.ai_service_manager.get_all_services()
            self.services_table.setRowCount(len(services))

            for row, (service_name, service) in enumerate(services.items()):
                health = self.ai_service_manager.get_service_health(service_name)
                stats = self.ai_service_manager.get_usage_stats(service_name)

                # 服务名称
                self.services_table.setItem(row, 0, QTableWidgetItem(service_name))

                # 状态
                status_item = QTableWidgetItem(health.status.value if health else "未知")
                status_color = {
                    ServiceStatus.ACTIVE: "#52c41a",
                    ServiceStatus.INACTIVE: "#888888",
                    ServiceStatus.ERROR: "#ff4d4f",
                    ServiceStatus.MAINTENANCE: "#faad14"
                }.get(health.status, "#888888")
                status_item.setBackground(QColor(status_color))
                self.services_table.setItem(row, 1, status_item)

                # 响应时间
                response_time = health.response_time if health else 0
                self.services_table.setItem(row, 2, QTableWidgetItem(f"{response_time:.1f}ms"))

                # 错误率
                error_rate = health.error_rate if health else 0
                self.services_table.setItem(row, 3, QTableWidgetItem(f"{error_rate:.1%}"))

                # 成功率
                success_rate = (stats.successful_requests / stats.total_requests * 100) if stats and stats.total_requests > 0 else 100
                self.services_table.setItem(row, 4, QTableWidgetItem(f"{success_rate:.1f}%"))

                # 操作按钮
                actions_widget = QWidget()
                actions_layout = QHBoxLayout(actions_widget)
                actions_layout.setContentsMargins(0, 0, 0, 0)

                test_btn = QPushButton("测试")
                test_btn.setFixedSize(60, 24)
                test_btn.clicked.connect(lambda checked, sn=service_name: self._test_service(sn))
                actions_layout.addWidget(test_btn)

                details_btn = QPushButton("详情")
                details_btn.setFixedSize(60, 24)
                details_btn.clicked.connect(lambda checked, sn=service_name: self._show_service_details(sn))
                actions_layout.addWidget(details_btn)

                self.services_table.setCellWidget(row, 5, actions_widget)

        except Exception as e:
            self.logger.error(f"更新服务表格失败: {e}")

    def _update_stats(self):
        """更新统计数据"""
        try:
            if not self.ai_service_manager:
                return

            summary = self.ai_service_manager.get_summary()

            # 更新概览页面统计
            if hasattr(self, 'service_stats_label'):
                self.service_stats_label.setText(f"{summary['active_services']}/{summary['total_services']}")
                self.requests_stats_label.setText(str(summary['total_requests']))

                # 计算成功率
                total_requests = summary.get('total_requests', 0)
                successful_requests = summary.get('successful_requests', 0)
                success_rate = (successful_requests / total_requests * 100) if total_requests > 0 else 100
                self.success_stats_label.setText(f"{success_rate:.1f}%")

                # 计算平均响应时间
                avg_response_time = self._calculate_avg_response_time()
                self.response_stats_label.setText(f"{avg_response_time:.1f}ms")

                self.cost_stats_label.setText(f"¥{summary['total_cost']:.2f}")
                self.alerts_stats_label.setText(str(len([a for a in self.alerts if not a.resolved])))

            # 更新使用量表格
            self._update_usage_table()

        except Exception as e:
            self.logger.error(f"更新统计数据失败: {e}")

    def _calculate_avg_response_time(self) -> float:
        """计算平均响应时间"""
        try:
            if not self.ai_service_manager:
                return 0.0

            total_time = 0
            count = 0

            for health in self.ai_service_manager.service_health.values():
                if health.response_time > 0:
                    total_time += health.response_time
                    count += 1

            return total_time / count if count > 0 else 0.0

        except Exception as e:
            self.logger.error(f"计算平均响应时间失败: {e}")
            return 0.0

    def _update_usage_table(self):
        """更新使用量表格"""
        try:
            if not self.ai_service_manager:
                return

            stats = self.ai_service_manager.usage_stats
            self.usage_table.setRowCount(len(stats))

            for row, (service_name, stat) in enumerate(stats.items()):
                self.usage_table.setItem(row, 0, QTableWidgetItem(service_name))
                self.usage_table.setItem(row, 1, QTableWidgetItem(str(stat.total_requests)))
                self.usage_table.setItem(row, 2, QTableWidgetItem(str(stat.successful_requests)))
                self.usage_table.setItem(row, 3, QTableWidgetItem(str(stat.failed_requests)))
                self.usage_table.setItem(row, 4, QTableWidgetItem(f"¥{stat.total_cost:.2f}"))

        except Exception as e:
            self.logger.error(f"更新使用量表格失败: {e}")

    def _update_performance_data(self):
        """更新性能数据"""
        try:
            if not self.ai_service_manager:
                return

            # 生成模拟性能数据
            response_time = self._calculate_avg_response_time()
            error_rate = self._calculate_error_rate()
            throughput = self._calculate_throughput()

            # 更新图表
            self.response_time_chart.add_data_point(response_time)
            self.error_rate_chart.add_data_point(error_rate * 100)
            self.throughput_chart.add_data_point(throughput)

            self.response_trend_chart.add_data_point(response_time)
            self.error_trend_chart.add_data_point(error_rate * 100)
            self.throughput_trend_chart.add_data_point(throughput)

            # 模拟CPU使用率
            import random
            cpu_usage = random.uniform(10, 80)
            self.cpu_usage_chart.add_data_point(cpu_usage)

        except Exception as e:
            self.logger.error(f"更新性能数据失败: {e}")

    def _calculate_error_rate(self) -> float:
        """计算错误率"""
        try:
            if not self.ai_service_manager:
                return 0.0

            total_errors = 0
            total_requests = 0

            for health in self.ai_service_manager.service_health.values():
                total_errors += health.error_count
                total_requests += health.success_count + health.error_count

            return total_errors / total_requests if total_requests > 0 else 0.0

        except Exception as e:
            self.logger.error(f"计算错误率失败: {e}")
            return 0.0

    def _calculate_throughput(self) -> float:
        """计算吞吐量"""
        try:
            if not self.ai_service_manager:
                return 0.0

            # 简单计算每秒请求数
            total_requests = sum(stat.total_requests for stat in self.ai_service_manager.usage_stats.values())
            return total_requests / 3600  # 假设统计的是1小时的数据

        except Exception as e:
            self.logger.error(f"计算吞吐量失败: {e}")
            return 0.0

    # -------------------------------------------------------------------------
    # Alert Methods
    # -------------------------------------------------------------------------

    def _update_alerts(self):
        """更新告警"""
        try:
            if not self.ai_service_manager:
                return

            # 生成告警
            self._generate_alerts()

            # 更新告警列表
            self._update_alerts_list()

        except Exception as e:
            self.logger.error(f"更新告警失败: {e}")

    def _generate_alerts(self):
        """生成告警"""
        try:
            if not self.ai_service_manager:
                return

            current_time = time_module.time()

            # 检查服务健康状态
            for service_name, health in self.ai_service_manager.service_health.items():
                if health.status == ServiceStatus.ERROR:
                    alert = AlertData(
                        id=f"{service_name}_error_{int(current_time)}",
                        service_name=service_name,
                        level="error",
                        message="服务出现错误，请检查配置",
                        timestamp=current_time,
                        details={"error_rate": health.error_rate, "last_check": health.last_check}
                    )
                    self._add_alert(alert)

                elif health.error_rate > 0.1:
                    alert = AlertData(
                        id=f"{service_name}_high_error_rate_{int(current_time)}",
                        service_name=service_name,
                        level="warning",
                        message=f"错误率过高: {health.error_rate:.1%}",
                        timestamp=current_time,
                        details={"error_rate": health.error_rate}
                    )
                    self._add_alert(alert)

                elif health.response_time > 5000:  # 5秒
                    alert = AlertData(
                        id=f"{service_name}_slow_response_{int(current_time)}",
                        service_name=service_name,
                        level="warning",
                        message=f"响应时间过长: {health.response_time:.1f}ms",
                        timestamp=current_time,
                        details={"response_time": health.response_time}
                    )
                    self._add_alert(alert)

        except Exception as e:
            self.logger.error(f"生成告警失败: {e}")

    def _add_alert(self, alert: AlertData):
        """添加告警"""
        now = time_module.time()
        # 检查是否已存在相似的告警（5分钟内不重复告警）
        for existing_alert in self.alerts:
            if (existing_alert.service_name == alert.service_name and
                existing_alert.level == alert.level and
                existing_alert.message == alert.message and
                not existing_alert.resolved and
                now - existing_alert.timestamp < 300):
                return

        self.alerts.append(alert)

        # 保持告警数量在合理范围内
        if len(self.alerts) > 100:
            self.alerts = self.alerts[-100:]

    def _update_alerts_list(self):
        """更新告警列表"""
        try:
            # 清除现有部件
            while self.alerts_layout.count():
                item = self.alerts_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()

            # 获取过滤器
            filter_text = self.alert_filter_combo.currentText()
            if filter_text == "全部":
                filtered_alerts = self.alerts
            else:
                level_map = {
                    "信息": "info",
                    "警告": "warning",
                    "错误": "error",
                    "严重": "critical"
                }
                filter_level = level_map.get(filter_text)
                filtered_alerts = [a for a in self.alerts if a.level == filter_level]

            # 按时间排序
            filtered_alerts.sort(key=lambda x: x.timestamp, reverse=True)

            # 添加告警部件
            for alert in filtered_alerts[:20]:  # 只显示最近20个
                alert_widget = AlertWidget(alert)
                alert_widget.alert_clicked.connect(self.alert_selected)
                self.alerts_layout.addWidget(alert_widget)

            if not filtered_alerts:
                no_alerts_label = QLabel("暂无告警")
                no_alerts_label.setProperty("class", "no-alerts-label")
                no_alerts_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                self.alerts_layout.addWidget(no_alerts_label)

        except Exception as e:
            self.logger.error(f"更新告警列表失败: {e}")

    def _filter_alerts(self, filter_text: str):
        """过滤告警"""
        self._update_alerts_list()

    def _clear_resolved_alerts(self):
        """清除已解决的告警"""
        self.alerts = [a for a in self.alerts if not a.resolved]
        self._update_alerts_list()

    # -------------------------------------------------------------------------
    # Service Actions
    # -------------------------------------------------------------------------

    def _test_service(self, service_name: str):
        """测试服务"""
        try:
            if self.ai_service_manager:
                # 测试第一个配置的模型
                configured_models = self.ai_service_manager.get_configured_models()
                if service_name in configured_models and configured_models[service_name]:
                    model_id = configured_models[service_name][0]
                    success = self.ai_service_manager.test_connection(service_name, model_id)

                    if success:
                        QMessageBox.information(self, "测试成功", f"{service_name} 连接测试成功")
                    else:
                        QMessageBox.warning(self, "测试失败", f"{service_name} 连接测试失败")
                else:
                    QMessageBox.warning(self, "未配置", f"{service_name} 未配置模型")
        except Exception as e:
            QMessageBox.critical(self, "测试错误", f"测试服务失败: {e}")

    def _show_service_details(self, service_name: str):
        """显示服务详情"""
        try:
            if not self.ai_service_manager:
                return

            health = self.ai_service_manager.get_service_health(service_name)
            stats = self.ai_service_manager.get_usage_stats(service_name)

            rt = f"{health.response_time:.1f}ms" if health else "N/A"
            er = f"{health.error_rate:.1%}" if health else "N/A"
            last_check = datetime.fromtimestamp(health.last_check).strftime('%Y-%m-%d %H:%M:%S') if health else "N/A"
            success_count = stats.successful_requests if stats else 0
            total_count = stats.total_requests if stats else 0
            cost = f"¥{stats.total_cost:.2f}" if stats else "N/A"

            details = (
                f"服务名称: {service_name}\n"
                f"状态: {(health.status.value if health else '未知')}\n"
                f"响应时间: {rt}\n"
                f"错误率: {er}\n"
                f"成功率: {success_count}/{total_count}\n"
                f"总成本: {cost}\n"
                f"最后检查: {last_check}"
            )

            QMessageBox.information(self, "服务详情", details)

        except Exception as e:
            QMessageBox.critical(self, "详情错误", f"获取服务详情失败: {e}")

    # -------------------------------------------------------------------------
    # Signal Handlers & Lifecycle
    # -------------------------------------------------------------------------

    def _refresh_data(self):
        """刷新数据"""
        self._update_monitor_data()

    def _on_service_health_updated(self, service_name: str, health_data: object):
        """服务健康状态更新处理"""
        self._update_services_status()

    def _on_stats_updated(self, stats: object):
        """统计数据更新处理"""
        self._update_stats()

    def refresh(self):
        """刷新面板"""
        self._update_monitor_data()

    def cleanup(self):
        """清理资源"""
        if hasattr(self, 'update_timer'):
            self.update_timer.stop()

    def __del__(self):
        """析构函数"""
        self.cleanup()
