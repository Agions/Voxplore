---
title: 导出发布指南
description: Vynaro 支持的剪映工程草稿 (.draft) 导出、8 平台发布预设与 MP4 导出配置。
---

# 📤 导出与发布指南

Vynaro 核心优势之一是原生支持 **剪映工程草稿 (`.draft`)** 导出与 **8 大主流视频平台预设**。无论是直接导出成片还是导入剪映二次精剪，均可一键完成。

---

## 🎬 剪映工程草稿 (.draft) 原生导出

点击 Step 7 导出视窗中的 **【导出剪映草稿】**，Vynaro 会直接构建剪映 PC 端原生的工程草稿文件夹结构：

```text
Vynaro_Export/
└── Vynaro_Promo_Vertical_9x16.draft/
    ├── draft_content.json       # 剪映原生轨道、视频/音频/字幕数据结构
    ├── draft_meta_info.json     # 剪映版本与时间轴元信息
    ├── media/                   # 切片视频片段与背景音乐
    │   ├── scene_01.mp4
    │   └── bgm_cinematic.mp3
    └── subtitles/               # VAD 毫秒级对齐字幕
        └── narration.srt
```

### 使用方法

1. 打开剪映 PC 端（CapCut PC），点击「导入工程草稿」。
2. 浏览并选中导出的 `.draft` 文件夹。
3. 剪映将自动加载多轨时间轴（视频轨、人声配音轨、BGM 背景声轨与双语字幕轨），您可以随时添加特效、贴纸或转场。

---

## 📱 8 大平台发布预设交互选择器

<PlatformPresetSelector />

---

## 🎞️ MP4 成片渲染选项

如果您不需要在剪映中修改，可以直接勾选 **【渲染 1080P/4K MP4 成片】**：

* **编码格式**：默认 H.264 (High Profile)，可选 H.265 (HEVC 体积减少 ~40%)。
* **混音算法 (`amix`)**：解说人声高亮，BGM 背景音乐自动降噪 `-6dB` 避让。
* **字幕压制**：支持硬字幕压制 (Hardsub) 或 封装软字幕轨 (Softsub)。

---

## 📖 相关推荐文档

* [第一人称生产规范](/guide/narration-spec) — 导出门禁与质量验收
* [界面与功能指南](/guide/interface) — 界面操作说明
* [疑难排查](/guide/troubleshooting) — 导出失败快速排查
