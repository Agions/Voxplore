# UI 重构规划

**项目：** Voxplore UI 层  
**创建日期：** 2026-04-29  
**范围：** 101 个 Python 文件，约 5.5K 行代码

---

## 📊 UI 模块分析

| 文件 | 行数 | 状态 |
|------|------|------|
| `monitor_panel.py` | 657 | 🔴 需要拆分 |
| `export_monitor.py` | 516 | 🟡 已优化（-146行） |
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

### 2. export_monitor.py 重构 ✅
- **删除 ExportSpeedChart**：用 `monitor_widgets.PerformanceChart` 替代 (71 行节省)
- **提取 ExportStatisticsWidget**：独立文件 (~97 行)

---

## 🔴 高优先级（需要拆分）

### 3.1 `export_monitor.py` (590 行 now)

**状态：** ✅ 大部分完成
- ExportSpeedChart 已删除
- ExportStatisticsWidget 已提取

### 3.2 `monitor_panel.py` (657 行)

**问题：**
- `AIMonitorPanel` 是 ~600 行的 god class
- 包含 5 种模式页面和多个更新循环
- `_generate_alerts`, `_add_alert`, `_update_alerts_list` 紧密耦合

**操作：**
- [ ] 提取 AlertManager 类 - 中等风险
- [ ] 拆分 AIMonitorPanel 模式页面 - 高风险

**结论：** 由于 AlertManager 与 AIMonitorPanel 高度耦合（共享 `self.alerts` 列表），提取风险较高。建议保持当前架构。

---

## 🟡 中优先级

### 4. `design_system.py` (617 行)

**建议：**
- 将 `Colors`, `Radius`, `Fonts` 等常量移到独立文件
- `CF*` 组件类保持原样

---

## 🔄 观察中（暂不修改）

- `onboarding_wizard.py` (652 行) - 功能稳定
- `subsubtitles_widgets.py` (650 行) - 功能稳定
- `step_*.py` 页面 - 互相引用，拆分风险高
- `AIMonitorPanel` 模式页面 - 与 AlertManager 紧耦合，拆分风险高

---

## 下一步行动

| 优先级 | 操作 | 工作量 | 风险 | 状态 |
|--------|------|--------|------|------|
| 高 | 用 PerformanceChart 替换 ExportSpeedChart | 低 | 中 | ✅ 已完成 |
| 高 | 提取 ExportStatisticsWidget | 中 | 中 | ✅ 已完成 |
| 中 | 提取 AlertManager | 中 | 高 | ❌ 不推荐 - 紧耦合 |
| 中 | 拆分 AIMonitorPanel 模式页面 | 高 | 高 | ❌ 不推荐 - 高风险 |
| 低 | design_system.py 常量分离 | 低 | 低 | 🔲 可选 |

---

*状态：已执行 2/5 个重构任务*
*建议：已完成的任务足够，减少进一步重构以避免破坏性变更*
