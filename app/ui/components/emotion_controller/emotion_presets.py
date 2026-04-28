#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Emotion Presets Data
情感预设数据 - 预设的情感曲线模板

包含5种预设情感：
- 治愈 (healing): 温暖橙色，曲线平缓温和
- 悬疑 (mysterious): 冷蓝色，曲线有起伏和尖峰
- 励志 (inspirational): 明黄色，曲线逐渐上升
- 怀旧 (nostalgic): 棕褐色，曲线平缓但有深度
- 浪漫 (romantic): 粉红色，曲线柔和流畅
"""

from typing import Dict, List
from PySide6.QtWidgets import QPushButton
from PySide6.QtGui import QColor


# 情感预设数据结构
EMOTION_PRESET = {
    "name": str,           # 英文名
    "name_cn": str,        # 中文名
    "color_hex": str,      # 颜色 (hex)
    "curve_template": List[float],  # 曲线模板 (10个点, 0.0-1.0)
    "description": str,    # 描述
}

# 曲线模板说明：
# 10个浮点数代表在 0%, 10%, 20%, ... 90%, 100% 时间点上的情感强度
# 数值范围 0.0-1.0

EMOTION_PRESETS: Dict[str, EMOTION_PRESET] = {
    "healing": {
        "name": "healing",
        "name_cn": "治愈",
        "color_hex": "#FF9E64",      # 温暖橙色
        "curve_template": [
            0.3,  # 0%  - 开始时柔和
            0.4,  # 10% - 轻微上升
            0.5,  # 20% - 继续上升
            0.7,  # 30% - 达到舒适区
            0.85, # 40% - 情感峰值
            0.9,  # 50% - 高峰体验
            0.8,  # 60% - 开始平缓
            0.65, # 70% - 逐渐下降
            0.5,  # 80% - 回归平静
            0.35, # 90% - 结束前柔和
            0.3,  # 100% - 结束
        ],
        "description": "温暖、舒适的情感曲线，开始和结束都柔和，中间有持续的正向情感。适合疗愈、温暖、平静的内容。",
    },

    "mysterious": {
        "name": "mysterious",
        "name_cn": "悬疑",
        "color_hex": "#7AA2F7",      # 冷蓝色
        "curve_template": [
            0.2,  # 0%  - 开始时低沉
            0.25, # 10% - 轻微波动
            0.35, # 20% - 逐渐上升
            0.5,  # 30% - 达到一个小高峰
            0.3,  # 40% - 突然下降，制造悬念
            0.55, # 50% - 再次上升
            0.75, # 60% - 高潮来临
            0.6,  # 70% - 短暂释放
            0.8,  # 80% - 再次紧张
            0.95, # 100% - 结束在紧张点
        ],
        "description": "悬疑、紧张的情感曲线，有多个起伏和尖峰，适合制造紧张感和悬念。适合惊悚、探秘、推理内容。",
    },

    "inspirational": {
        "name": "inspirational",
        "name_cn": "励志",
        "color_hex": "#E0AF68",      # 明黄色
        "curve_template": [
            0.2,  # 0%  - 开始时较低（困境）
            0.3,  # 10% - 略有起色
            0.4,  # 20% - 努力中
            0.5,  # 30% - 持续上升
            0.6,  # 40% - 取得进展
            0.7,  # 50% - 中间点，持续向上
            0.75, # 60% - 接近高峰
            0.85, # 70% - 突破
            0.95, # 80% - 高潮
            1.0,  # 90% - 达到顶峰
            0.9,  # 100% - 完美收尾
        ],
        "description": "励志、奋进的情感曲线，从低到高逐渐上升，适合展现克服困难、取得成功的故事弧线。",
    },

    "nostalgic": {
        "name": "nostalgic",
        "name_cn": "怀旧",
        "color_hex": "#BB9A6A",      # 棕褐色/怀旧色
        "curve_template": [
            0.35, # 0%  - 开始于平静
            0.4,  # 10% - 轻微波动
            0.45, # 20% - 回忆开始
            0.5,  # 30% - 情感加深
            0.55, # 40% - 达到情感深度
            0.5,  # 50% - 保持深度
            0.45, # 60% - 轻微回落
            0.4,  # 70% - 持续怀想
            0.35, # 80% - 回归平静
            0.3,  # 90% - 结束前平和
            0.3,  # 100% - 温柔结束
        ],
        "description": "怀旧、沉思的情感曲线，情感深度在中间偏高，整体平缓有深度。适合回忆、思念、感慨类内容。",
    },

    "romantic": {
        "name": "romantic",
        "name_cn": "浪漫",
        "color_hex": "#F7768E",      # 粉红色
        "curve_template": [
            0.25, # 0%  - 开始时羞涩
            0.35, # 10% - 轻微升温
            0.45, # 20% - 情感流动
            0.55, # 30% - 逐渐加深
            0.65, # 40% - 情感升温
            0.75, # 50% - 高峰体验
            0.7,  # 60% - 持续浪漫
            0.6,  # 70% - 轻微回落
            0.55, # 80% - 温柔延续
            0.45, # 90% - 渐入尾声
            0.4,  # 100% - 浪漫收尾
        ],
        "description": "浪漫、甜蜜的情感曲线，从羞涩到高潮再到温柔结束。适合爱情、温馨、甜蜜类内容。",
    },
}


def get_preset_by_name(name: str) -> EMOTION_PRESET:
    """
    根据名称获取情感预设

    Args:
        name: 预设名称 (英文或中文)

    Returns:
        预设数据字典

    Raises:
        KeyError: 找不到预设
    """
    # 尝试英文名
    if name in EMOTION_PRESETS:
        return EMOTION_PRESETS[name]

    # 尝试中文名
    for preset in EMOTION_PRESETS.values():
        if preset["name_cn"] == name:
            return preset

    raise KeyError(f"未找到情感预设: {name}")


def get_all_preset_names() -> List[str]:
    """
    获取所有预设名称列表

    Returns:
        英文名称列表
    """
    return list(EMOTION_PRESETS.keys())


def interpolate_curve(curve: List[float], num_points: int) -> List[float]:
    """
    对曲线进行插值，获取更多采样点

    用于平滑动画或获取更高分辨率的曲线数据。

    Args:
        curve: 原始曲线 (10个点)
        num_points: 目标采样点数量

    Returns:
        插值后的曲线
    """
    if len(curve) < 2:
        return curve


    # 使用线性插值
    result = []
    for i in range(num_points):
        # 计算在原始曲线中的位置
        t = i / (num_points - 1) * (len(curve) - 1)
        idx = int(t)
        frac = t - idx

        if idx >= len(curve) - 1:
            result.append(curve[-1])
        else:
            # 线性插值
            val = curve[idx] * (1 - frac) + curve[idx + 1] * frac
            result.append(val)

    return result


def smooth_curve(curve: List[float], iterations: int = 1) -> List[float]:
    """
    平滑曲线

    使用简单移动平均进行平滑处理。

    Args:
        curve: 原始曲线
        iterations: 平滑迭代次数

    Returns:
        平滑后的曲线
    """
    if len(curve) < 3:
        return curve

    result = curve[:]

    for _ in range(iterations):
        smoothed = []
        for i in range(len(result)):
            if i == 0:
                smoothed.append(result[0])
            elif i == len(result) - 1:
                smoothed.append(result[-1])
            else:
                # 移动平均
                avg = (result[i - 1] + result[i] + result[i + 1]) / 3.0
                smoothed.append(avg)
        result = smoothed

    return result


class EmotionPresetButton(QPushButton):
    """
    情感预设按钮

    带有预设颜色和样式的按钮组件。
    """

    def __init__(self, preset_key: str, parent=None):
        """
        初始化情感预设按钮

        Args:
            preset_key: 预设键名 (如 "healing")
            parent: 父 widget
        """
        super().__init__(parent)
        self.preset_key = preset_key
        self.preset = EMOTION_PRESETS.get(preset_key)

        if self.preset:
            self.setText(self.preset["name_cn"])
            self._setup_style()

    def _setup_style(self):
        """设置按钮样式"""
        color = self.preset["color_hex"]
        name_cn = self.preset["name_cn"]

        # 使用内联样式
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {color}22;
                color: {color};
                border: 1px solid {color};
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 13px;
                font-weight: bold;
                min-width: 70px;
            }}
            QPushButton:hover {{
                background-color: {color}44;
            }}
            QPushButton:pressed {{
                background-color: {color}66;
            }}
            QPushButton:checked {{
                background-color: {color};
                color: #090D14;
            }}
        """)

    def get_color(self) -> QColor:
        """获取预设颜色"""
        if self.preset:
            return QColor(self.preset["color_hex"])
        return QColor("#FFFFFF")

    def get_curve_template(self) -> List[float]:
        """获取预设曲线模板"""
        if self.preset:
            return self.preset["curve_template"].copy()
        return [0.5] * 11


if __name__ == '__main__':
    # 演示和测试
    import sys
    from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout

    app = QApplication(sys.argv)

    window = QWidget()
    window.setWindowTitle("Emotion Presets Demo")
    window.setStyleSheet("background-color: #090D14;")

    layout = QVBoxLayout(window)

    # 展示所有预设
    for preset_key, preset in EMOTION_PRESETS.items():
        btn = EmotionPresetButton(preset_key)
        layout.addWidget(btn)

        # 打印曲线数据
        curve = preset["curve_template"]
        print(f"{preset['name_cn']}: {curve}")

    window.resize(300, 400)
    window.show()

    sys.exit(app.exec())
