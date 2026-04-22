# Voxplore UI 重新设计实施计划

## 项目概述

- **目标**：全新简约科技风设计系统 + 多窗口流程架构
- **UI 框架**：PySide6
- **布局**：多窗口（每步一个窗口，完成后进入下一步）
- **主题**：纯暗色，OKLCH 色系

---

## Phase 1: 设计系统基础

### Task 1.1: 重新设计 tokens.py（全新 OKLCH 色系）
- 文件：`app/ui/theme/tokens.py`
- 纯暗色配色方案（推翻原 tokens.py）
- 定义所有 design tokens：颜色、间距、字体、圆角、阴影
- 无渐变、无多余阴影，纯扁平科技风

### Task 1.2: 创建主题管理器
- 文件：`app/ui/theme/theme_manager.py`（重构）
- 应用 tokens 到 QSS 样式表
- 支持动态主题切换（未来扩展）

### Task 1.3: 创建基础样式系统
- 文件：`app/ui/theme/base_styles.py`（新建）
- 按钮、输入框、卡片、面板基础样式
- 所有样式基于 tokens，不硬编码颜色

---

## Phase 2: 多窗口架构

### Task 2.1: 创建主窗口（MainWindow）
- 文件：`app/ui/windows/main_window.py`（新建）
- 步骤指示器（StepIndicator）
- 顶部导航栏
- 窗口管理（打开/关闭子窗口）

### Task 2.2: 创建步骤指示器组件（StepIndicator）
- 文件：`app/ui/components/step_indicator.py`（新建）
- 4 步：上传 → 场景理解 → 配音编辑 → 导出
- 当前步骤高亮，完成步骤打勾

### Task 2.3: 创建子窗口基类（BaseStepWindow）
- 文件：`app/ui/windows/base_step_window.py`（新建）
- 统一的"上一步/下一步"按钮区
- 统一的进度提示区
- 窗口关闭确认

### Task 2.4: 创建项目列表窗口（ProjectsWindow）
- 文件：`app/ui/windows/projects_window.py`（新建）
- 项目卡片网格
- 新建项目按钮
- 项目删除/重命名

---

## Phase 3: Step 1 - 上传窗口

### Task 3.1: 创建上传窗口（UploadWindow）
- 文件：`app/ui/windows/upload_window.py`（新建）
- 拖拽上传区（支持多文件）
- 文件列表（名称、时长、分辨率）
- 移除文件按钮

### Task 3.2: 创建视频预览卡片组件
- 文件：`app/ui/components/upload/video_preview_card.py`（新建）
- 缩略图 + 视频信息
- 删除按钮

### Task 3.3: 创建文件选择器
- 文件：`app/ui/components/upload/file_drop_zone.py`（新建）
- 拖拽区域样式
- 点击选择文件

---

## Phase 4: Step 2 - 场景理解窗口

### Task 4.1: 创建场景理解窗口（SceneWindow）
- 文件：`app/ui/windows/scene_window.py`（新建）
- AI 分析进度显示
- 场景卡片列表
- 场景描述编辑

### Task 4.2: 创建场景卡片组件
- 文件：`app/ui/components/scene/scene_card.py`（新建）
- 时间范围
- 场景描述文本
- 缩略图

---

## Phase 5: Step 3 - 配音编辑窗口

### Task 5.1: 创建配音编辑窗口（NarrationWindow）
- 文件：`app/ui/windows/narration_window.py`（新建）
- 文本编辑区
- 情感控制器
- 预览播放按钮

### Task 5.2: 重构情感控制器
- 文件：`app/ui/components/emotion_controller/emotion_controller.py`
- 简化界面（使用新设计系统）
- 预设情感选择（平静/兴奋/悬疑/温暖）

### Task 5.3: 创建字幕编辑器组件
- 文件：`app/ui/components/subtitle/subtitle_editor.py`（重构）
- 时间轴编辑
- 字幕样式预览

---

## Phase 6: Step 4 - 导出窗口

### Task 6.1: 创建导出窗口（ExportWindow）
- 文件：`app/ui/windows/export_window.py`（新建）
- 格式选择（MP4 / 剪映草稿）
- 分辨率选择
- 导出进度条

### Task 6.2: 创建导出进度面板
- 文件：`app/ui/components/export/export_progress.py`（新建）
- 进度条
- 预计时间
- 取消按钮

---

## Phase 7: 主窗口集成

### Task 7.1: 创建主窗口布局
- 文件：`app/ui/windows/main_window.py`
- 集成步骤指示器
- 集成项目列表
- 集成新建项目流程

### Task 7.2: 创建创建项目向导
- 文件：`app/ui/windows/creation_wizard.py`（新建）
- 引导用户完成 4 步
- 每步验证通过后进入下一步

---

## Phase 8: 页面路由与窗口管理

### Task 8.1: 创建窗口管理器
- 文件：`app/ui/windows/window_manager.py`（新建）
- 管理所有窗口实例
- 窗口间数据传递
- 统一的窗口创建/销毁

### Task 8.2: 更新主程序入口
- 文件：`app/main.py`
- 替换旧的 PySide6 初始化
- 使用新窗口管理器

---

## Phase 9: 样式与动效

### Task 9.1: 添加微交互动画
- 文件：`app/ui/theme/animations.py`（重构）
- 窗口淡入淡出
- 按钮悬停效果
- 进度条动画

### Task 9.2: 应用统一样式
- 全局 QSS 样式表
- 确保所有组件使用 tokens

---

## Phase 10: 清理与测试

### Task 10.1: 删除旧 UI 文件
- 备份后删除 `app/ui/main/pages/` 中的旧页面文件
- 删除 `app/ui/main/components/` 中的旧组件

### Task 10.2: 运行测试
- 执行 `pytest tests/`
- 修复任何导入错误

---

## 文件变更总览

### 新建文件
```
app/ui/windows/
├── __init__.py
├── base_step_window.py
├── creation_wizard.py
├── export_window.py
├── main_window.py
├── narration_window.py
├── projects_window.py
├── scene_window.py
└── upload_window.py

app/ui/theme/
├── base_styles.py       # 新建
└── tokens.py             # 重写

app/ui/components/
├── scene/
│   ├── __init__.py
│   └── scene_card.py
├── upload/
│   ├── __init__.py
│   ├── file_drop_zone.py
│   └── video_preview_card.py
├── export/
│   ├── __init__.py
│   └── export_progress.py
├── step_indicator.py
└── subtitle/
    └── subtitle_editor.py
```

### 修改文件
```
app/ui/theme/
├── theme_manager.py     # 重构
└── animations.py        # 重构

app/main.py              # 更新入口
```

### 删除文件（旧文件，备份后删除）
```
app/ui/main/             # 整个目录备份后删除
app/ui/components/       # 清理旧组件
```
