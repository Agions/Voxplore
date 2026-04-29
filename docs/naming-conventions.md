# 文件命名规范分析

**分析日期：** 2026-04-29  
**检查范围：** 253 个 Python 文件

---

## ✅ 命名现状

### 已遵守的规范

| 类型 | 示例 | 数量 |
|------|------|------|
| snake_case | `video_exporter.py`, `subtitle_extractor.py` | ~120 |
| 短文件名 | `models.py`, `base.py`, `main.py` (合理) | ~15 |
| 模块化 | `providers/*.py` | ~15 |

---

## 🔴 发现的问题

### 1. macOS 驼峰命名（2个文件）

| 当前文件名 | 类名 | 位置 |
|------------|------|------|
| `macOS_theme_manager.py` | `macOS_ThemeManager` | `app/core/` |
| `macOS_components.py` | `macOS_Components` | `app/ui/common/` |

**建议修改：**
- `macOS_theme_manager.py` → `macos_theme_manager.py`
- `macOS_components.py` → `macos_components.py`

**影响分析：**
- 引用点仅在 `app/ui/main/quick_ai_config.py:25` 和 `app/ui/main/pages/projects_page.py:22`
- 修改需要同步更新导入语句

### 2. 类名不符合 Python PEP8

| 文件 | 类名 | 问题 |
|------|------|------|
| `macOS_theme_manager.py:18` | `class macOS_ThemeManager` | 应为 `class MacOSThemeManager` |

---

## 📋 建议操作

**执行结果（2026-04-29）：**

| 操作 | 状态 |
|------|------|
| 重命名 `macOS_theme_manager.py` | ✅ 完成 |
| 重命名 `macOS_components.py` | ✅ 完成 |
| 修复类名 `macOS_ThemeManager` → `MacOSThemeManager` | ✅ 完成 |
| 更新引用点 | ✅ 完成 |

**最终状态：**< 无违规文件 |
