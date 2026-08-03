---
layout: home
title: SceneFab · AI 影视解说一站式生产平台
titleTemplate: false

hero:
  name: SceneFab
  text: 影视解说，从素材到成片
  tagline: 用 AI 把"理解剧情 → 写脚本 → 配语音 → 对字幕 → 多平台导出"串成标准化流水线。<br/>第一人称视角 · 短剧桥段识别 · 多模型交叉审核 · 本地优先处理。
  actions:
    - theme: brand
      text: 🚀 快速开始
      link: /guide/quick-start
    - theme: alt
      text: 📖 完整文档
      link: /guide/first-person-narration-production
    - theme: alt
      text: ⭐ GitHub
      link: https://github.com/Agions/scene-fab

features:
  - icon: 🎬
    title: AI 智能语义拆条
    details: Qwen2.5-VL 深度理解视频语义，按情节/场景/情绪峰值自动切分，告别手工打点。
  - icon: 📝
    title: 第一人称脚本生成
    details: Hook → 主体 → 反击 → 收束 → 钩子。7 种风格预设，多模型交叉审核，确保质量稳定。
  - icon: 🎙️
    title: 智能配音 + 字幕对齐
    details: Edge-TTS 50+ 音色 + F5-TTS 音色克隆。50ms 精度时间戳对齐，字幕偏差 < 50ms 验收。
  - icon: 📐
    title: 7 种情感风格
    details: 治愈 · 悬疑 · 励志 · 怀旧 · 浪漫 · 幽默 · 纪录片 + 自定义角色人设。
  - icon: 📱
    title: 多平台一键导出
    details: 抖音 / B站 / 小红书 / YouTube / TikTok / 快手 / 西瓜视频 / 微信视频号，8 平台预设。
  - icon: 🔄
    title: 整季批量生产
    details: 短剧整季批量生成 + 断点续传 + 并行 worker + 实时进度追踪，规模化生产不掉链。
---

<script setup>
import { withBase } from 'vitepress'

const roleCards = [
  {
    label: '新用户',
    title: '3 步上手',
    text: '安装 SceneFab → 配置 API Key → 启动 GUI，10 分钟完成第一次解说创作。',
    link: '/guide/quick-start',
    icon: '🚀'
  },
  {
    label: '内容团队',
    title: '标准化生产',
    text: '从素材来源到脚本、配音、字幕、导出和复盘的完整第一人称解说生产规范。',
    link: '/guide/first-person-narration-production',
    icon: '🎬'
  },
]

const workflowSteps = [
  { no: '01', title: '素材导入', desc: 'mp4 / mov / avi / webm', color: 'cyan' },
  { no: '02', title: '场景拆分', desc: 'AI 视频语义分析', color: 'cyan' },
  { no: '03', title: '脚本生成', desc: '第一人称 Hook→主体→钩子', color: 'violet' },
  { no: '04', title: '配音合成', desc: 'Edge-TTS / F5-TTS', color: 'cyan' },
  { no: '05', title: '字幕对齐', desc: '50ms 精度时间戳', color: 'cyan' },
  { no: '06', title: '导出发布', desc: '8 平台预设 · 剪映草稿', color: 'violet' }
]

const platforms = [
  { name: '抖音', res: '1080×1920', ratio: '9:16', color: '#000000' },
  { name: 'B站', res: '1920×1080', ratio: '16:9', color: '#fb7299' },
  { name: '小红书', res: '1080×1920', ratio: '9:16', color: '#ff2442' },
  { name: 'YouTube', res: '1920×1080', ratio: '16:9', color: '#ff0000' },
  { name: 'TikTok', res: '1080×1920', ratio: '9:16', color: '#fe2c55' },
  { name: '快手', res: '1080×1920', ratio: '9:16', color: '#ff4906' },
  { name: '西瓜视频', res: '1920×1080', ratio: '16:9', color: '#ff6633' },
  { name: '视频号', res: '1080×1920', ratio: '9:16', color: '#07c160' }
]

const techStack = [
  { layer: '桌面端', items: ['PySide6 6.9+', 'Qt 跨平台'], icon: '🖥️' },
  { layer: '视频处理', items: ['FFmpeg 6.x', 'OpenCV · MoviePy'], icon: '🎞️' },
  { layer: 'AI 推理', items: ['DeepSeek · Qwen', 'Gemini · GPT · Claude'], icon: '🧠' },
  { layer: '语音合成', items: ['Edge-TTS', 'F5-TTS 本地克隆'], icon: '🎙️' },
  { layer: '数据层', items: ['Pydantic 2.5+', 'YAML 配置 + 环境变量'], icon: '📦' },
  { layer: 'HTTP API', items: ['FastAPI · uvicorn', 'REST API 可选'], icon: '🌐' }
]
</script>

<div class="vp-doc container">

<!-- ════════════════ 按角色进入 ════════════════ -->
<section class="sf-section">
  <div class="sf-section-head">
    <div>
      <div class="sf-section-kicker">文档地图</div>
      <h2 class="sf-section-title">按角色进入文档</h2>
    </div>
    <p class="sf-section-copy">新用户、内容团队、架构师各有对应入口，无需通读全部内容。</p>
  </div>

  <div class="sf-grid cols-3 sf-role-grid">
    <a
      v-for="card in roleCards"
      :key="card.link"
      class="sf-link-card sf-role-card"
      :href="withBase(card.link)"
    >
      <div class="sf-role-icon">{{ card.icon }}</div>
      <div class="sf-card-label">{{ card.label }}</div>
      <div class="sf-card-title">{{ card.title }}</div>
      <p class="sf-card-text">{{ card.text }}</p>
      <div class="sf-card-arrow">→</div>
    </a>
  </div>
</section>

<!-- ════════════════ 完整工作流 ════════════════ -->
<section class="sf-section">
  <div class="sf-section-head">
    <div>
      <div class="sf-section-kicker">生产流程</div>
      <h2 class="sf-section-title">6 步从素材到成片</h2>
    </div>
    <p class="sf-section-copy">每个阶段都有质量门禁，失败自动重试或人工干预。</p>
  </div>

  <div class="sf-workflow">
    <div
      v-for="(step, idx) in workflowSteps"
      :key="step.no"
      class="sf-workflow-step"
      :class="'sf-step-' + step.color"
    >
      <div class="sf-step-no">{{ step.no }}</div>
      <div class="sf-step-title">{{ step.title }}</div>
      <div class="sf-step-desc">{{ step.desc }}</div>
      <div v-if="idx < workflowSteps.length - 1" class="sf-step-arrow">→</div>
    </div>
  </div>
</section>

<!-- ════════════════ 平台支持 ════════════════ -->
<section class="sf-section">
  <div class="sf-section-head">
    <div>
      <div class="sf-section-kicker">导出发布</div>
      <h2 class="sf-section-title">8 平台一键导出</h2>
    </div>
    <p class="sf-section-copy">预设分辨率 + 编码 + 字幕样式，无需手动调参。</p>
  </div>

  <div class="sf-platform-grid">
    <div
      v-for="p in platforms"
      :key="p.name"
      class="sf-platform-card"
      :style="{ '--brand-color': p.color }"
    >
      <div class="sf-platform-name">{{ p.name }}</div>
      <div class="sf-platform-res">{{ p.res }}</div>
      <div class="sf-platform-ratio">{{ p.ratio }}</div>
    </div>
  </div>
</section>

<!-- ════════════════ 技术架构 ════════════════ -->
<section class="sf-section">
  <div class="sf-section-head">
    <div>
      <div class="sf-section-kicker">技术栈</div>
      <h2 class="sf-section-title">精心选型的每一层</h2>
    </div>
    <p class="sf-section-copy">开源生态主流方案，每个组件都有成熟替代，方便扩展。</p>
  </div>

  <div class="sf-tech-grid">
    <div
      v-for="t in techStack"
      :key="t.layer"
      class="sf-tech-card"
    >
      <div class="sf-tech-icon">{{ t.icon }}</div>
      <div class="sf-tech-layer">{{ t.layer }}</div>
      <div class="sf-tech-items">
        <div v-for="item in t.items" :key="item" class="sf-tech-item">{{ item }}</div>
      </div>
    </div>
  </div>
</section>

<!-- ════════════════ CTA ════════════════ -->
<section class="sf-section sf-cta">
  <div class="sf-cta-inner">
    <h2 class="sf-cta-title">准备好开始你的第一次 AI 解说创作了吗？</h2>
    <p class="sf-cta-text">3 步安装、配置和首次运行，10 分钟完成从素材到成片。</p>
    <div class="sf-cta-actions">
      <a class="sf-cta-btn sf-cta-btn-primary" :href="withBase('/guide/quick-start')">🚀 快速开始</a>
      <a class="sf-cta-btn sf-cta-btn-secondary" href="https://github.com/Agions/scene-fab/releases">📥 下载安装</a>
      <a class="sf-cta-btn sf-cta-btn-secondary" href="https://github.com/Agions/scene-fab">⭐ GitHub 仓库</a>
    </div>
  </div>
</section>

</div>
