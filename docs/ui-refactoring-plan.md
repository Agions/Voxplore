# UI 重构规划

**项目：** Voxplore UI 层  
**创建日期：** 2026-04-29  
**范围：** 101 个 Python 文件，约 5.5K 行代码

---

## 📊 UI 模块分析

| 文件 | 行数 | 状态 |
|------|------|------|
| `monitor_panel.py` | 657 | 🔴 需要拆分 |
| `export_monitor.py` | 662 | 🔴 需要拆分 |
| `design_system.py` | 617 | 🟡 可优化 |
| `onboarding_wizard.py` | 652 | 🟡 观察中 |
| `subsubtitles_widgets.py` | 650 | 🟡 观察中 |
| `theme_optimizer.py` | 586 | 🟢 OK |
| `monitor_models.py` | ~40 | ✅ 已提取 |

---

## ✅ 已完成

### 1. Monitor 数据模型提取
- `MonitorMode` 和 `AlertData` 已移至 `monitor_models.py`
- `monitor_panel.py` 现在从 `monitor_models` 导入

---

## 🔴 高优先级（需要拆分）

### 2.1 `export_monitor.py` (662 行)

**问题：**
- `ExportSpeedChart` 与 `monitor_widgets.py` 中的 `PerformanceChart` 重复
- `ExportMonitorWidget` 职责过多

**操作：**
- [ ] 用 `PerformanceChart` 替换 `ExportSpeedChart`
- [ ] 提取 `ExportStatisticsWidget` 到独立文件

### 2.2 `monitor_panel.py` (657 行)

**问题：**
- `AIMonitorPanel` 是 ~600 行的 god class
- 包含 5 种模式页面和 5 个更新循环

**操作：**
- [ ] 提取 Alert 生成逻辑到 `AlertManager`
- [ ] 将 5 个模式页面拆分为独立文件

---

## 🟡 中优先级

### 3. `design_system.py` (617 行)

**建议：**
- 将 `Colors`, `Radius`, `Fonts` 等常量移到独立文件
- `CF*` 组件类保持原样

---

## 🔄 观察中（暂不修改）

- `onboarding_wizard.py` (652 行) - 功能稳定
- `subsubtitles_widgets.py` (650 行) - 功能稳定
- `step_*.py` 页面 - 互相引用，拆分风险高

---

## 下一步行动

| 优先级 | 操作 | 工作量 | 风险 |
|--------|------|--------|------|
| 高 | 用 PerformanceChart 替换 ExportSpeedChart | 低 | 中 |
| 高 | 提取 ExportStatisticsWidget | 中 | 中 |
| 中 | 提取 AlertManager | 中 | 高 |
| 中 | 拆分 AIMonitorPanel 模式页面 | 高 | 高 |

---

*状态：分析阶段，待执行*
