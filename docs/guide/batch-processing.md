---
title: 批量处理
description: Voxplore 批量处理功能说明（v3.4.0 已整合至单次工作流）。
---

# 批量处理

> ⚠️ **版本说明**：独立批量处理面板已于 **v3.4.0** 整合至单次工作流。通过创建多个项目并逐个处理，可实现等效的批量操作。详情见下方说明。

---

## v3.4.0 变更说明

v3.4.0 品牌聚焦重构中，移除了独立的批量处理界面。原批量处理能力通过以下方式保留：

**等效替代方案**：创建多个 Voxplore 项目，逐个处理视频。每个项目独立运行，互不干扰，适合多视频顺序处理场景。

> 💡 **未来版本**计划将批量队列功能重新引入，作为单次工作流的增强功能。如有此需求，请在 [GitHub Discussions](https://github.com/Agions/Voxplore/discussions) 反馈。

---

## 多视频处理建议工作流

### 方式一：逐个项目处理

1. 为每个视频创建独立项目（**项目 → 新建项目**）
2. 逐个导入视频并生成解说
3. 统一设置输出目录，按项目名自动分类

输出目录结构示例：

```
~/Videos/Voxplore/
├── keynote_presentation/
│   └── final.mp4
├── conference_session2/
│   └── final.mp4
└── travel_vlog_ep3/
    └── final.mp4
```

### 方式二：FFmpeg 批量合并（如需合并多个成品）

```bash
# 合并同目录所有 MP4（需安装 FFmpeg）
cd output_dir
ffmpeg -f concat -safe 0 -i <(for f in *.mp4; do echo "file '$f'"; done) -c copy merged.mp4
```

---

## 输出管理

### 自动命名规则

| 变量 | 效果 |
|------|------|
| `{filename}` | 原始文件名（无扩展名） |
| `{date}` | 处理日期（YYYY-MM-DD） |
| `{time}` | 处理时间（HH-MM-SS） |
| `{mode}` | 情感风格 |

### 批量导出配置

| 参数 | 说明 |
|------|------|
| 统一编码 | H.264 / H.265 |
| 统一分辨率 | 保持原片 / 1080p / 720p |
| 统一输出目录 | 所有项目输出到同一父目录 |

---

## 快捷键

| 操作 | Windows | macOS |
|------|---------|-------|
| 新建项目 | `Ctrl+N` | `⌘N` |
| 打开项目 | `Ctrl+O` | `⌘O` |
| 快速导出 | `Ctrl+E` | `⌘E` |

---

## 相关文档

- [快速开始](./quick-start) — 单视频 5 分钟上手
- [导出格式](./exporting) — 详细导出参数配置
- [疑难排查](./troubleshooting) — 处理过程中的问题解决
