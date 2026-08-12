---
layout: home
title: Monoloop 叙影 · AI 视频解说与短剧创作引擎
titleTemplate: false
---

<script setup>
import { withBase } from 'vitepress'
</script>

<div class="vp-doc container">

<!-- 1. Linear 级动态 Hero 视窗展示 -->
<HeroAppShowcase />

<!-- 2. 跟随鼠标微风聚光功能网格 -->
<FeatureSpotlightGrid />

<!-- 3. 7 步卡片交互式 DAG 生产流水线 -->
<InteractivePipeline />

<!-- 4. 11 大 LLM 与 TTS 引擎能力矩阵 -->
<ModelMatrixCard />

<!-- 5. 8 大主流短视频/长视频平台发布预设 -->
<PlatformPresetSelector />

<!-- 6. 顶奢 Call-to-Action 区域 -->
<section class="sf-section sf-cta">
  <div class="sf-cta-inner">
    <h2 class="sf-cta-title">准备好体验超凡的 AI 影视解说生产力了吗？</h2>
    <p class="sf-cta-text">只需 3 分钟即可完成桌面端安装与 API 密钥配置，立即开启标准化解说创作。</p>
    <div class="sf-cta-actions">
      <a class="sf-cta-btn sf-cta-btn-primary" :href="withBase('/guide/quick-start')">🚀 快速开始使用</a>
      <a class="sf-cta-btn sf-cta-btn-secondary" :href="withBase('/guide/interface')">🖥️ 界面与控制说明</a>
      <a class="sf-cta-btn sf-cta-btn-secondary" href="https://github.com/Agions/monoloop">⭐ GitHub 仓库</a>
    </div>
  </div>
</section>

</div>
