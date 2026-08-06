---
title: AI 工作流详解
description: Vynaro 从视频素材到第一人称解说成片的 7 步 AI 工作流详解。
---

# 🤖 AI 工作流详解

Vynaro 的 AI 生产流程围绕 **“剧情理解 ➔ 独白脚本 ➔ 黄金声波合成 ➔ 剪映草稿交付”** 闭环设计。每个阶段都有明确的数据产出与质量评估，确保视频解说的完播率与观感。

![Vynaro 全流程 UI 工作台](/assets/mockups/hero-app-main.jpg)

---

## ⚡ 7 步卡片流水线架构

```text
 📥 1. 素材导入    ➔    ✂️ 2. 场景拆条    ➔    🤖 3. 独白脚本    ➔    🎙️ 4. TTS克隆
 MP4 / MOV解析           FFmpeg镜头检测           11大LLM主角视点          Edge/GPT-SoVITS
                                                                               │
 📤 7. 草稿导出        🎬 6. 音画混流        📝 5. VAD字幕               │
 剪映.draft/MP4          9:16竖屏/amix           50ms silencedetect ◄──────────┘
```

---

## 1. 🎬 智能拆条与镜头理解

![FFmpeg 智能拆条 UI](/assets/mockups/scene-split-ui.jpg)

* **FFmpeg 场景探测**：基于场景切面算法 `silencedetect` 与镜头突变点识别，将连续视频拆解为若干独立片段。
* **情绪峰值识别**：提取高光冲突瞬间，自动标注黄金 3 秒 Hook 候选帧与冲突转折点。

---

## 2. 🤖 第一人称独白脚本引擎

![AI 独白脚本生成 UI](/assets/mockups/ai-script-generator.jpg)

Vynaro 合成了 11 大 LLM 模型的剧情理解与独白输出能力：

| 阶段 | 核心作用 | 典型文案示例 |
| :--- | :--- | :--- |
| **Hook (引子)** | 3 秒留存危险/悬念 | *"我死也没想到，陪伴了我三年的闺蜜，居然偷偷拿走了我的救命钱..."* |
| **Body (主体)** | 第一人称叙事推进 | *"她眼神里的慌乱出卖了她，但我没有当场拆穿，而是默默打开了监控..."* |
| **Counter-attack (反转)** | 爽点爆发与反击 | *"第二天发布会上，当她以为自己胜券在握时，屏幕上播放的却是我准备好的证据..."* |
| **Conclusion (钩子)** | 下集留存与点赞 | *"关注我，下一集看她如何为自己的所作所为付出代价！"* |

---

## 3. 🎙️ TTS 人声克隆与 VAD 对齐

![TTS 与 VAD 对齐 UI](/assets/mockups/tts-voice-waveform.jpg)

* **Edge-TTS 50+ 黄金音色**：涵盖情感叙述、悬疑解说、幽默吐槽与纪录片腔调。
* **GPT-SoVITS 零样本克隆**：上传 5 秒目标音色，生成具有极高相似度的角色原声配音。
* **50ms VAD 轴对齐**：精准校准字幕与声音停顿，无重叠、无突兀停顿。

---

## 4. 📤 剪映工程草稿 (.draft) 导出

![剪映草稿导出 UI](/assets/mockups/capcut-export-modal.jpg)

* 导出标准的剪映 `.draft` 工程文件包，保留视频轨道、音频轨、BGM 轨与字幕层。
* 在剪映中随时调整特效、贴纸与字幕动画，实现 AI 自动化与人工精细化二次创作的无缝衔接。

---

## 📖 相关推荐文档

* [界面与功能指南](/guide/interface) — 桌面端软件操作详解
* [第一人称生产规范](/guide/narration-spec) — 生产标准与完播率 SOP
* [导出与发布](/guide/exporting) — 多平台规格与预设参数
