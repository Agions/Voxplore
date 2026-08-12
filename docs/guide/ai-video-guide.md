---
title: AI 工作流详解
description: Monoloop 从视频素材到第一人称解说成片的 7 步 AI 工作流详解。
---

# 🤖 AI 工作流详解

Monoloop 的 AI 生产流程围绕 **“剧情理解 ➔ 独白脚本 ➔ 黄金声波合成 ➔ 剪映草稿交付”** 闭环设计。每个阶段都有明确的数据产出与质量评估，确保视频解说的完播率与观感。

---

## ⚡ 7 步卡片流水线架构

<InteractivePipeline />

---

## 🧠 11 大大模型与人声克隆能力矩阵

<ModelMatrixCard />

---

## 👁️ 多模态视觉关键帧分析 (Multimodal Vision Analysis)

Monoloop 引入了原生的**多模态视觉关键帧感知架构**：
- **智能抽帧**：在 Step 2 智能切片后，系统自动通过 FFmpeg 从每个镜头中提取高清 JPG 关键帧。
- **视觉联想与剧本生成**：在 Step 3 独白剧本生成时，将视觉关键帧直接编码为 Base64/Image 格式灌入 `gpt-5.6-sol` / `gemini-3.6-flash` / `qwen3.8-max` 等多模态大模型，使 AI 能够真正“看懂”画面中的角色动作、情绪变化与场景氛围，生成画面契合度高达 99% 的第一人称独白剧本。

---

## 🎙️ Web Audio Canvas 实时频域波形图 (Real-Time Audio Spectrum Visualizer)

Voice Studio 配音工坊内置了基于 HTML5 **Web Audio API** (`AudioContext` + `AnalyserNode`) 的 2D Canvas 实时波形渲染器：
- **实时频域分析**：在试听与合成配音播放时，实时采集 56 频段 FFT 频谱与时域信号。
- **赛博黑曜石美学**：呈现金黄香槟发光柱 (`#F5C842`) 与光滑贝塞尔曲线包络线，并带有动态粒子跳动与平滑息屏待机呼吸动画。

---

## 📖 相关推荐文档

* [界面与功能指南](/guide/interface) — 桌面端软件操作详解
* [第一人称生产规范](/guide/narration-spec) — 生产标准与完播率 SOP
* [导出与发布](/guide/exporting) — 多平台规格与预设参数
