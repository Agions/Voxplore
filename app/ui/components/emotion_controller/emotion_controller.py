#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Emotion Controller Component
情感控制器组件 - 主 widget，整合情感曲线和预设管理

功能:
- 5个情感预设按钮 (治愈/悬疑/励志/怀旧/浪漫)
- EmotionCurveWidget 显示情感曲线
- 强度调节滑块
- 信号发射: emotion_changed, curve_confirmed

使用示例:
    from app.ui.components.emotion_controller import EmotionController

    controller = EmotionController()
    controller.emotion_changed.connect(on_emotion_changed)
    controller.curve_confirmed.connect(on_curve_confirmed)
"""

from typing import List, Optional, Dict

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QSlider, QFrame, QSizePolicy
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

from .emotion_curve_widget import EmotionCurveWidget
from .emotion_presets import EMOTION_PRESETS, EmotionPresetButton


class EmotionController(QWidget):
    """
    情感控制器主组件

    整合情感预设、曲线显示和强度调节。

    Signals:
        emotion_changed(str emotion, float intensity):
            当情感类型或强度改变时发射
        curve_confirmed(List[float] curve):
            当用户确认曲线时发射
    """

    emotion_changed = Signal(str, float)  # emotion_name, intensity
    curve_confirmed = Signal(list)         # curve_data (11 floats)

    def __init__(self, parent: Optional[QWidget] = None):
        """
        初始化情感控制器

        Args:
            parent: 父 widget
        """
        super().__init__(parent)

        # 状态
        self._current_emotion: str = "healing"
        self._current_intensity: float = 0.5
        self._current_curve: List[float] = EMOTION_PRESETS["healing"]["curve_template"].copy()

        # 预设按钮
        self._preset_buttons: Dict[str, EmotionPresetButton] = {}

        # UI 组件
        self._title_label: Optional[QLabel] = None
        self._state_label: Optional[QLabel] = None
        self._curve_widget: Optional[EmotionCurveWidget] = None
        self._intensity_slider: Optional[QSlider] = None
        self._confirm_button: Optional[QPushButton] = None

        self._setup_ui()
        self._setup_styles()
        self._connect_signals()

        # 初始化显示
        self._apply_preset("healing")

    def _setup_ui(self):
        """设置 UI 布局"""
        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)

        # 标题
        self._title_label = QLabel("情感控制器")
        self._title_label.setObjectName("emotionControllerTitle")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        self._title_label.setFont(title_font)
        main_layout.addWidget(self._title_label)

        # 当前状态标签
        self._state_label = QLabel("当前情感: 治愈 | 强度: 50%")
        self._state_label.setObjectName("emotionStateLabel")
        main_layout.addWidget(self._state_label)

        # 预设按钮区域
        preset_label = QLabel("情感预设")
        preset_label.setObjectName("presetLabel")
        main_layout.addWidget(preset_label)

        preset_container = QFrame()
        preset_container.setObjectName("presetContainer")
        preset_layout = QHBoxLayout(preset_container)
        preset_layout.setContentsMargins(0, 8, 0, 8)
        preset_layout.setSpacing(12)

        # 创建预设按钮
        preset_keys = ["healing", "mysterious", "inspirational", "nostalgic", "romantic"]
        for key in preset_keys:
            btn = EmotionPresetButton(key)
            btn.setCheckable(True)
            btn.setObjectName(f"presetButton_{key}")
            self._preset_buttons[key] = btn
            preset_layout.addWidget(btn)

        # 添加弹性空间
        preset_layout.addStretch()

        main_layout.addWidget(preset_container)

        # 情感曲线 widget
        curve_label = QLabel("情感曲线")
        curve_label.setObjectName("curveLabel")
        main_layout.addWidget(curve_label)

        self._curve_widget = EmotionCurveWidget(
            curve_color=EMOTION_PRESETS["healing"]["color_hex"]
        )
        self._curve_widget.setObjectName("emotionCurveWidget")
        self._curve_widget.set_curve(self._current_curve)
        main_layout.addWidget(self._curve_widget)

        # 强度调节区域
        intensity_container = QFrame()
        intensity_container.setObjectName("intensityContainer")
        intensity_layout = QHBoxLayout(intensity_container)
        intensity_layout.setContentsMargins(0, 8, 0, 8)
        intensity_layout.setSpacing(12)

        intensity_title = QLabel("情感强度")
        intensity_title.setObjectName("intensityTitle")
        intensity_layout.addWidget(intensity_title)

        # 强度滑块 (0-100)
        self._intensity_slider = QSlider(Qt.Horizontal)
        self._intensity_slider.setObjectName("intensitySlider")
        self._intensity_slider.setMinimum(0)
        self._intensity_slider.setMaximum(100)
        self._intensity_slider.setValue(50)
        self._intensity_slider.setTickPosition(QSlider.TicksBelow)
        self._intensity_slider.setTickInterval(25)
        intensity_layout.addWidget(self._intensity_slider, 1)

        # 强度值标签
        self._intensity_value_label = QLabel("50%")
        self._intensity_value_label.setObjectName("intensityValueLabel")
        self._intensity_value_label.setMinimumWidth(40)
        intensity_layout.addWidget(self._intensity_value_label)

        main_layout.addWidget(intensity_container)

        # 确认按钮
        self._confirm_button = QPushButton("应用情感曲线")
        self._confirm_button.setObjectName("confirmButton")
        self._confirm_button.setCursor(Qt.PointingHandCursor)
        main_layout.addWidget(self._confirm_button)

        # 设置大小策略
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)

    def _setup_styles(self):
        """设置样式"""
        self.setStyleSheet("""
            /* 主容器 */
            QWidget {
                background-color: #0D1117;
            }

            /* 标题 */
            QLabel#emotionControllerTitle {
                color: #F1F5F9;
                font-size: 16px;
                font-weight: bold;
                padding: 4px 0;
            }

            /* 状态标签 */
            QLabel#emotionStateLabel {
                color: #94A3B8;
                font-size: 12px;
                padding: 4px 8px;
                background-color: #1E293B;
                border-radius: 4px;
            }

            /* 预设标签 */
            QLabel#presetLabel,
            QLabel#curveLabel {
                color: #94A3B8;
                font-size: 12px;
                font-weight: bold;
                padding: 4px 0;
            }

            /* 预设容器 */
            QFrame#presetContainer {
                background-color: #1E293B;
                border-radius: 8px;
                padding: 4px;
            }

            /* 强度容器 */
            QFrame#intensityContainer {
                background-color: #1E293B;
                border-radius: 8px;
                padding: 4px;
            }

            /* 强度标题 */
            QLabel#intensityTitle {
                color: #94A3B8;
                font-size: 12px;
                font-weight: bold;
                padding: 0 8px;
            }

            /* 强度值标签 */
            QLabel#intensityValueLabel {
                color: #22D3EE;
                font-size: 12px;
                font-weight: bold;
                padding: 0 8px;
            }

            /* 强度滑块 */
            QSlider#intensitySlider {
                background: transparent;
            }
            QSlider#intensitySlider::groove:horizontal {
                border: 1px solid #334155;
                height: 6px;
                border-radius: 3px;
                background: #0D1117;
            }
            QSlider#intensitySlider::handle:horizontal {
                background: #22D3EE;
                border: none;
                width: 16px;
                height: 16px;
                margin: -5px 0;
                border-radius: 8px;
            }
            QSlider#intensitySlider::handle:horizontal:hover {
                background: #67E8F9;
            }
            QSlider#intensitySlider::sub-page:horizontal {
                background: #22D3EE;
                border-radius: 3px;
            }

            /* 确认按钮 */
            QPushButton#confirmButton {
                background-color: #6366F1;
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                padding: 12px 24px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton#confirmButton:hover {
                background-color: #818CF8;
            }
            QPushButton#confirmButton:pressed {
                background-color: #4F46E5;
            }
        """)

    def _connect_signals(self):
        """连接信号和槽"""
        # 预设按钮点击
        for key, btn in self._preset_buttons.items():
            btn.clicked.connect(lambda checked, k=key: self._on_preset_clicked(k))

        # 强度滑块
        if self._intensity_slider:
            self._intensity_slider.valueChanged.connect(self._on_intensity_changed)

        # 确认按钮
        if self._confirm_button:
            self._confirm_button.clicked.connect(self._on_confirm_clicked)

        # 曲线 widget 位置变化
        if self._curve_widget:
            self._curve_widget.position_changed.connect(self._on_curve_position_changed)

    def _on_preset_clicked(self, preset_key: str):
        """
        预设按钮点击处理

        Args:
            preset_key: 预设键名
        """
        # 更新选中状态
        for key, btn in self._preset_buttons.items():
            btn.setChecked(key == preset_key)

        # 应用预设
        self._apply_preset(preset_key)

    def _apply_preset(self, preset_key: str):
        """
        应用情感预设

        Args:
            preset_key: 预设键名
        """
        if preset_key not in EMOTION_PRESETS:
            return

        preset = EMOTION_PRESETS[preset_key]

        # 更新状态
        self._current_emotion = preset_key
        self._current_curve = preset["curve_template"].copy()

        # 更新曲线 widget
        if self._curve_widget:
            self._curve_widget.set_curve_from_preset(
                preset["curve_template"],
                preset["color_hex"]
            )

        # 更新状态标签
        self._update_state_label()

        # 发射信号
        self.emotion_changed.emit(preset_key, self._current_intensity)

    def _on_intensity_changed(self, value: int):
        """
        强度滑块改变处理

        Args:
            value: 滑块值 (0-100)
        """
        self._current_intensity = value / 100.0

        # 更新值标签
        if self._intensity_value_label:
            self._intensity_value_label.setText(f"{value}%")

        # 应用强度到曲线
        self._apply_intensity_to_curve()

        # 更新状态标签
        self._update_state_label()

        # 发射信号
        self.emotion_changed.emit(self._current_emotion, self._current_intensity)

    def _apply_intensity_to_curve(self):
        """
        将强度值应用到曲线

        将基础曲线的振幅按强度调整。
        """
        if not self._curve_widget:
            return

        # 获取基础曲线
        preset = EMOTION_PRESETS.get(self._current_emotion)
        if not preset:
            return

        base_curve = preset["curve_template"]

        # 调整曲线强度
        # 强度为 0.5 时保持原样，>0.5 增强，<0.5 减弱
        adjusted_curve = []
        for i, value in enumerate(base_curve):
            # 以 0.5 为中性点
            if self._current_intensity >= 0.5:
                # 增强：向两端扩展
                factor = 1.0 + (self._current_intensity - 0.5) * 0.8
                adjusted = 0.5 + (value - 0.5) * factor
            else:
                # 减弱：向 0.5 收缩
                factor = self._current_intensity / 0.5
                adjusted = 0.5 + (value - 0.5) * factor

            adjusted_curve.append(max(0.0, min(1.0, adjusted)))

        self._current_curve = adjusted_curve
        self._curve_widget.curve = adjusted_curve

    def _on_curve_position_changed(self, position: float):
        """
        曲线位置改变处理

        Args:
            position: 位置 (0.0-1.0)
        """
        # 可以用于实时预览或其他功能
        pass

    def _on_confirm_clicked(self):
        """确认按钮点击处理"""
        # 发射最终曲线数据
        self.curve_confirmed.emit(self._current_curve.copy())

    def _update_state_label(self):
        """更新状态标签"""
        if self._state_label:
            emotion_cn = EMOTION_PRESETS.get(self._current_emotion, {}).get("name_cn", "未知")
            intensity_percent = int(self._current_intensity * 100)
            self._state_label.setText(f"当前情感: {emotion_cn} | 强度: {intensity_percent}%")

    def get_current_emotion(self) -> str:
        """
        获取当前情感类型

        Returns:
            情感类型键名
        """
        return self._current_emotion

    def get_current_intensity(self) -> float:
        """
        获取当前强度

        Returns:
            强度值 (0.0-1.0)
        """
        return self._current_intensity

    def get_current_curve(self) -> List[float]:
        """
        获取当前曲线数据

        Returns:
            11个 float 的列表
        """
        return self._current_curve.copy()

    def set_emotion(self, emotion: str):
        """
        设置情感类型

        Args:
            emotion: 情感类型键名
        """
        if emotion in EMOTION_PRESETS:
            self._apply_preset(emotion)
            for key, btn in self._preset_buttons.items():
                btn.setChecked(key == emotion)

    def set_intensity(self, intensity: float):
        """
        设置强度

        Args:
            intensity: 强度值 (0.0-1.0)
        """
        self._current_intensity = max(0.0, min(1.0, intensity))

        if self._intensity_slider:
            self._intensity_slider.setValue(int(self._current_intensity * 100))

        self._apply_intensity_to_curve()
        self._update_state_label()

    def reset(self):
        """重置为默认状态"""
        self._apply_preset("healing")
        self.set_intensity(0.5)


# ============================================================
# 便捷函数
# ============================================================

def create_emotion_controller(parent: Optional[QWidget] = None) -> EmotionController:
    """
    创建情感控制器的便捷函数

    Args:
        parent: 父 widget

    Returns:
        EmotionController 实例
    """
    return EmotionController(parent)


if __name__ == '__main__':
    # 演示用法
    import sys
    from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget

    app = QApplication(sys.argv)
    app.setStyleSheet("""
        QMainWindow {
            background-color: #090D14;
        }
    """)

    window = QMainWindow()
    window.setWindowTitle("Emotion Controller Demo")
    window.setMinimumSize(700, 500)

    central = QWidget()
    window.setCentralWidget(central)

    layout = QVBoxLayout(central)
    layout.setContentsMargins(20, 20, 20, 20)

    # 创建情感控制器
    controller = EmotionController()
    layout.addWidget(controller)

    # 连接信号
    def on_emotion_changed(emotion: str, intensity: float):
        print(f"Emotion changed: {emotion}, intensity: {intensity:.2f}")

    def on_curve_confirmed(curve: List[float]):
        print(f"Curve confirmed: {curve}")

    controller.emotion_changed.connect(on_emotion_changed)
    controller.curve_confirmed.connect(on_curve_confirmed)

    window.show()
    sys.exit(app.exec())
