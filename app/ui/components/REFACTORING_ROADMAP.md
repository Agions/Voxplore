# UI Component Refactoring Roadmap

## P3-4: UI Disaster Zones Analysis

---

## 1. export_monitor.py

### Purpose
实时导出进度监控组件，提供导出任务进度跟踪、统计展示和速度图表功能。

### Stats
- **Lines**: 662
- **Classes**: 5 (ExportProgressWidget, ExportStatisticsWidget, ExportSpeedChart, ExportMonitorWidget, ExportProgressDialog)
- **Methods**: ~62

### Issues Found

1. **God Widget Pattern**: `ExportMonitorWidget` (lines 339-533) handles too many responsibilities:
   - Task list management
   - Statistics display
   - Speed chart updates
   - Theme updates
   - Timer management

2. **Code Duplication**: 
   - `ExportSpeedChart` (lines 270-337) duplicates `PerformanceChart` in `monitor_widgets.py` (lines 114-183)
   - Both implement similar line chart drawing logic

3. **Tight Coupling**: `ExportProgressWidget` is tightly coupled to `ExportTask` model

4. **Theme Hardcoding**: CSS colors hardcoded in multiple places

### Extraction Targets (Priority Order)

| Target | Lines | Estimated Effort | Reason |
|--------|-------|------------------|--------|
| `ExportSpeedChart` | ~67 | Low | Duplicates `PerformanceChart`; pure drawing widget |
| `ExportStatisticsWidget` | ~76 | Medium | Simple stat display; needs refactoring of stat update logic |
| `ExportProgressWidget` | ~166 | High | Core widget; depends on ExportTask |

### Recommended Next Steps
1. **LOW priority**: Delete `ExportSpeedChart` and use `PerformanceChart` from `monitor_widgets.py` instead
2. **MEDIUM priority**: Extract `ExportStatisticsWidget` to separate file
3. **HIGH priority**: Split `ExportMonitorWidget` into smaller focused widgets

---

## 2. monitor_panel.py

### Purpose
AI状态监控面板，实时监控AI服务的运行状态、性能指标和使用情况。

### Stats
- **Lines**: 657
- **Classes**: 3 (MonitorMode, AlertData, AIMonitorPanel)
- **Methods**: ~40

### Issues Found

1. **Massive Monolithic Widget**: `AIMonitorPanel` (lines 51-657) is a ~600-line god class with:
   - 5 different "mode" pages (overview, services, performance, usage, alerts)
   - 5 update loops (one per mode)
   - Mixed data update and UI code
   - Alert generation, filtering, and display logic

2. **Mode Switching Logic**: `_switch_mode` (lines 168-185) creates pages but doesn't properly clean up

3. **Alert Logic Overload**: `_update_alerts`, `_generate_alerts`, `_add_alert`, `_update_alerts_list` are intermingled

4. **Data Model Leakage**: `AlertData` dataclass is defined in this file but used across multiple modules

### Extraction Targets (Priority Order)

| Target | Lines | Estimated Effort | Reason |
|--------|-------|------------------|--------|
| `AlertData` | ~10 | Low | Simple dataclass; no Qt dependencies; should be in models |
| `MonitorMode` | ~7 | Low | Simple constants enum; could be separate file |
| `_update_performance_data` logic | ~25 | Medium | Could be a separate PerformanceAnalyzer class |
| `AIMonitorPanel` page creation | ~40 | High | Pages are created via MonitorPages helper but still embedded |

### Recommended Next Steps
1. **LOW priority**: Move `AlertData` to `app/ui/main/components/monitor_models.py`
2. **LOW priority**: Move `MonitorMode` to same file
3. **MEDIUM priority**: Create `AlertManager` class to handle alert generation/filtering
4. **HIGH priority**: Break `AIMonitorPanel` into separate page widgets

---

## 3. monitor_widgets.py (Existing Helper File)

### Purpose
共享的监控面板组件库。

### Stats
- **Lines**: 273
- **Classes**: 3 (ServiceStatusWidget, PerformanceChart, AlertWidget)
- **Methods**: ~15

### Notes
- This file already exists and contains good separable widgets
- `PerformanceChart` duplicates `ExportSpeedChart` in export_monitor.py

---

## 4. Quick Wins Summary

### Immediate Actions (Low Effort, High Impact)

1. **Delete `ExportSpeedChart`** (export_monitor.py lines 270-337)
   - Reason: Duplicates `PerformanceChart` in monitor_widgets.py
   - Risk: Low (pure drawing widget)
   - Savings: ~67 lines of duplication

2. **Move `AlertData` to monitor_models.py** (monitor_panel.py lines 39-48)
   - Reason: Data model should be separate from UI code
   - Risk: Low (simple dataclass)
   - Savings: Clarifies architecture

---

## 5. Executed Extractions

### Extraction 1: (Pending execution)
**Source**: export_monitor.py  
**Target**: monitor_widgets.py (merge with existing PerformanceChart)  
**Content**: ExportSpeedChart class (~67 lines)  
**Status**: RECOMMENDED but NOT YET EXECUTED (requires replacing usages in ExportMonitorWidget)

---

*Generated: 2026-04-19*
*Context: P3-4 quality analysis flagged these as disaster zones*
