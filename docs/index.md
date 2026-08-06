---
layout: home
title: Vynaro 叙影 · AI 视频解说与短剧创作平台
titleTemplate: false

hero:
  name: Vynaro
  text: 影视解说，从素材到成片
  tagline: 基于 Tauri 2 + Rust + React 19 打造的桌面端 AI 视频叙事编辑器。<br/>7 步卡片流水线 · 11 大大模型矩阵 · 声波零样本克隆 · 剪映原生工程草稿导出。
  actions:
    - theme: brand
      text: 🚀 快速开始
      link: /guide/quick-start
    - theme: alt
      text: 📖 界面与流程说明
      link: /guide/interface
    - theme: alt
      text: ⭐ GitHub 仓库
      link: https://github.com/Agions/vynaro

features:
  - icon: ✂️
    title: FFmpeg 智能场景拆条
    details: 基于切面探测与情绪峰值吸附，精准索引视频关键帧与场景边界，自动分离音视频流。
  - icon: 🤖
    title: 11 大 LLM 独白脚本引擎
    details: 通义千问、DeepSeek R1、GPT-4o、Claude 3.5、Gemini 3.6，支持 Hook → 主体 → 钩子 4 大叙事结构。
  - icon: 🎙️
    title: Edge-TTS 与 GPT-SoVITS 克隆
    details: 50+ 黄金音色预设 + 零样本人声克隆，配合 50ms 级别 VAD 端点检测与 SRT/ASS 字幕精准对齐。
  - icon: 🎬
    title: 9:16 竖屏多轨音画混流
    details: 毫秒级时间轴混音，背景音乐 (BGM) 自动降噪避让 (`amix`)，实时高清预览成片效果。
  - icon: 📤
    title: 剪映工程草稿 (.draft) 导出
    details: 原生导出剪映二次剪辑工程草稿 (`.draft`)，支持抖音、B站、小红书等 8 大平台发布预设。
  - icon: ⚡
    title: Tauri 2 + Rust 极速内核
    details: 本地硬件加速与极低内存占用，数据本地化优先处理，AI 生成任务断点续传与并行 DAG 执行。
---

<script setup>
import { withBase } from 'vitepress'

const roleCards = [
  {
    label: '新手入门',
    title: '快速开始指南',
    text: '安装 Vynaro 桌面端 → 配置大模型与 TTS 密钥 → 10 分钟创作第一条精彩短剧解说。',
    link: '/guide/quick-start',
    icon: '🚀'
  },
  {
    label: '界面操作',
    title: '主界面与工具说明',
    text: '详细了解 7 步卡片流水线、时间轴轨道、AI 独白编辑器与预览播放器的控制按键。',
    link: '/guide/interface',
    icon: '🖥️'
  },
  {
    label: '标准生产',
    title: '第一人称解说规范',
    text: '涵盖剧本黄金三秒 Hook、情绪起伏调配、音质混响与高完播率剪辑复盘的标准 SOP。',
    link: '/guide/narration-spec',
    icon: '🎬'
  }
]

const workflowSteps = [
  { no: 'Step 1', title: '素材导入', desc: '4K/1080P 元数据解析与快照缩略图', icon: '📥' },
  { no: 'Step 2', title: '智能拆条', desc: 'FFmpeg 场景切片与关键帧索引', icon: '✂️' },
  { no: 'Step 3', title: '独白脚本', desc: '11 大 LLM 主角视点剧情创作', icon: '🤖' },
  { no: 'Step 4', title: 'TTS 克隆', desc: 'Edge-TTS 与 GPT-SoVITS 语音合成', icon: '🎙️' },
  { no: 'Step 5', title: 'VAD 对齐', desc: '50ms silencedetect 字幕毫秒级轴', icon: '📝' },
  { no: 'Step 6', title: '音画混流', desc: '多轨混音与 9:16 竖屏实时渲染', icon: '🎬' },
  { no: 'Step 7', title: '草稿导出', desc: '剪映 .draft 工程与 8 平台预设', icon: '📤' }
]

const platforms = [
  { name: '抖音', res: '1080×1920', ratio: '9:16 (竖屏)', color: '#F5C842' },
  { name: 'B站', res: '1920×1080', ratio: '16:9 (横屏)', color: '#00AEEC' },
  { name: '小红书', res: '1080×1920', ratio: '9:16 (竖屏)', color: '#FF2442' },
  { name: 'YouTube Shorts', res: '1080×1920', ratio: '9:16 (竖屏)', color: '#FF0000' },
  { name: 'TikTok', res: '1080×1920', ratio: '9:16 (竖屏)', color: '#FE2C55' },
  { name: '快手', res: '1080×1920', ratio: '9:16 (竖屏)', color: '#FF4906' },
  { name: '西瓜视频', res: '1920×1080', ratio: '16:9 (横屏)', color: '#FF6633' },
  { name: '微信视频号', res: '1080×1920', ratio: '9:16 (竖屏)', color: '#07C160' }
]

const techStack = [
  { layer: '桌面端应用', items: ['Tauri 2.0 (Rust)', 'React 19', 'TypeScript 5.8'], icon: '⚡' },
  { layer: '视频探针与编解码', items: ['FFmpeg 6.x', 'Keyframe Inspector', 'MoviePy / OpenCV'], icon: '🎞️' },
  { layer: 'LLM 脚本大模型', items: ['通义千问 · DeepSeek R1', 'GPT-4o · Claude 3.5 · Gemini'], icon: '🧠' },
  { layer: 'TTS 与人声克隆', items: ['Edge-TTS (50+音色)', 'GPT-SoVITS (Zero-shot)'], icon: '🎙️' },
  { layer: '字幕与语音对齐', items: ['FFmpeg silencedetect VAD', 'SRT / VTT / ASS 毫秒轴'], icon: '📝' },
  { layer: '剪辑工程导出', items: ['CapCut Draft (.draft)', '原生 JSON 结构化描述'], icon: '📦' }
]
</script>

<div class="vp-doc container">

<section class="vynaro-hero-showcase">
  <div class="vynaro-mockup-wrapper">
    <div class="vynaro-mockup-badge">✨ Vynaro v2.5.0 旗舰版桌面端</div>
    <div class="vynaro-mockup-frame">
      <div class="vynaro-frame-header">
        <div class="vynaro-window-controls">
          <span class="dot red"></span>
          <span class="dot yellow"></span>
          <span class="dot green"></span>
        </div>
        <div class="vynaro-window-title">Vynaro Desktop - AI 视频解说与短剧创作工作台</div>
        <div class="vynaro-window-tag">Tauri 2.0 + Rust</div>
      </div>
      <img :src="withBase('/assets/mockups/hero-app-main.jpg')" alt="Vynaro 桌面端 UI 全景工作台" class="vynaro-mockup-img" />
    </div>
  </div>
</section>

<section class="sf-section">
  <div class="sf-section-head">
    <div>
      <div class="sf-section-kicker">文档导航</div>
      <h2 class="sf-section-title">快速探索文档</h2>
    </div>
    <p class="sf-section-copy">根据您的使用需求快速跳转对应模块，开启智能化影视解说创作。</p>
  </div>
  <div class="sf-grid cols-3 sf-role-grid">
    <a v-for="card in roleCards" :key="card.link" class="sf-link-card sf-role-card" :href="withBase(card.link)">
      <div class="sf-role-icon">{{ card.icon }}</div>
      <div class="sf-card-label">{{ card.label }}</div>
      <div class="sf-card-title">{{ card.title }}</div>
      <p class="sf-card-text">{{ card.text }}</p>
      <div class="sf-card-arrow">→</div>
    </a>
  </div>
</section>

<section class="sf-section">
  <div class="sf-section-head">
    <div>
      <div class="sf-section-kicker">全流水线</div>
      <h2 class="sf-section-title">7 步智能卡片生产流水线</h2>
    </div>
    <p class="sf-section-copy">基于 DAG 状态机驱动，每一步均支持实时参数微调、重试与工程断点续传。</p>
  </div>
  <div class="vynaro-pipeline-cards">
    <div v-for="step in workflowSteps" :key="step.no" class="vynaro-pipeline-card">
      <div class="vynaro-step-header">
        <span class="vynaro-step-icon">{{ step.icon }}</span>
        <span class="vynaro-step-badge">{{ step.no }}</span>
      </div>
      <div class="vynaro-step-title">{{ step.title }}</div>
      <p class="vynaro-step-desc">{{ step.desc }}</p>
    </div>
  </div>
</section>

<section class="sf-section">
  <div class="sf-section-head">
    <div>
      <div class="sf-section-kicker">界面特写</div>
      <h2 class="sf-section-title">模块化极简交互视角</h2>
    </div>
    <p class="sf-section-copy">结合前沿深度学习与自动化剪辑引擎，让高品质解说触手可及。</p>
  </div>
  <div class="vynaro-feature-mockups">
    <div class="vynaro-grid-2">
      <div class="vynaro-submockup-card">
        <div class="vynaro-submockup-title">✂️ Step 2: FFmpeg 智能拆条与场景检测</div>
        <img :src="withBase('/assets/mockups/scene-split-ui.jpg')" alt="智能场景拆条界面" class="vynaro-submockup-img" />
        <p class="vynaro-submockup-text">基于镜头突变与情绪峰值自动打点，生成关键帧快照序列，支持合并/微调切片边界。</p>
      </div>
      <div class="vynaro-submockup-card">
        <div class="vynaro-submockup-title">🤖 Step 3: AI 独白脚本生成器</div>
        <img :src="withBase('/assets/mockups/ai-script-generator.jpg')" alt="AI 独白脚本生成器界面" class="vynaro-submockup-img" />
        <p class="vynaro-submockup-text">支持 Qwen、DeepSeek R1、GPT-4o 等 11 大大模型，一键拟定主角视角 Hook、反击与高潮剧情。</p>
      </div>
    </div>
    <div class="vynaro-grid-2" style="margin-top: 24px;">
      <div class="vynaro-submockup-card">
        <div class="vynaro-submockup-title">🎙️ Step 4 & 5: TTS 人声克隆与 VAD 字幕对齐</div>
        <img :src="withBase('/assets/mockups/tts-voice-waveform.jpg')" alt="TTS与字幕对齐界面" class="vynaro-submockup-img" />
        <p class="vynaro-submockup-text">实时黄金声波显示与人声克隆探针，配合 silencedetect 端点检测，实现 50ms 级别字幕毫秒级轴。</p>
      </div>
      <div class="vynaro-submockup-card">
        <div class="vynaro-submockup-title">📤 Step 7: 剪映草稿 (.draft) 与 8 平台预设导出</div>
        <img :src="withBase('/assets/mockups/capcut-export-modal.jpg')" alt="剪映草稿导出界面" class="vynaro-submockup-img" />
        <p class="vynaro-submockup-text">原生生成剪映二次剪辑工程草稿 (`.draft`)，内置抖音、B站、小红书、TikTok 等 8 大平台预设。</p>
      </div>
    </div>
  </div>
</section>

<section class="sf-section">
  <div class="sf-section-head">
    <div>
      <div class="sf-section-kicker">多平台导出</div>
      <h2 class="sf-section-title">8 大主流短视频/长视频平台预设</h2>
    </div>
    <p class="sf-section-copy">预设分辨率、宽高比与码率，导出直接发布，省去参数适配繁琐步骤。</p>
  </div>
  <div class="sf-platform-grid">
    <div v-for="p in platforms" :key="p.name" class="sf-platform-card" :style="{ '--brand-color': p.color }">
      <div class="sf-platform-name">{{ p.name }}</div>
      <div class="sf-platform-res">{{ p.res }}</div>
      <div class="sf-platform-ratio">{{ p.ratio }}</div>
    </div>
  </div>
</section>

<section class="sf-section">
  <div class="sf-section-head">
    <div>
      <div class="sf-section-kicker">技术矩阵</div>
      <h2 class="sf-section-title">Tauri 2 + Rust 现代技术栈</h2>
    </div>
    <p class="sf-section-copy">高性能、低资源消耗与极速响应的现代化工程架构。</p>
  </div>
  <div class="sf-tech-grid">
    <div v-for="t in techStack" :key="t.layer" class="sf-tech-card">
      <div class="sf-tech-icon">{{ t.icon }}</div>
      <div class="sf-tech-layer">{{ t.layer }}</div>
      <div class="sf-tech-items">
        <div v-for="item in t.items" :key="item" class="sf-tech-item">{{ item }}</div>
      </div>
    </div>
  </div>
</section>

<section class="sf-section sf-cta">
  <div class="sf-cta-inner">
    <h2 class="sf-cta-title">准备好体验高效的 AI 第一人称视频解说创作了吗？</h2>
    <p class="sf-cta-text">只需几分钟即可完成桌面端安装与 API 密钥配置，立即开启标准化解说生产。</p>
    <div class="sf-cta-actions">
      <a class="sf-cta-btn sf-cta-btn-primary" :href="withBase('/guide/quick-start')">🚀 快速开始使用</a>
      <a class="sf-cta-btn sf-cta-btn-secondary" :href="withBase('/guide/interface')">🖥️ 界面操作说明</a>
      <a class="sf-cta-btn sf-cta-btn-secondary" href="https://github.com/Agions/vynaro">⭐ GitHub 仓库</a>
    </div>
  </div>
</section>

</div>
