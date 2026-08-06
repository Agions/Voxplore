<template>
  <section class="vynaro-hero-app-showcase">
    <!-- 顶部分浪 Pill Badge & Title -->
    <div class="vynaro-showcase-header">
      <div class="vynaro-gradient-badge">
        <span class="pulse-dot"></span>
        <span class="badge-text">Vynaro v1.0.0 · Tauri 2.0 + Rust 旗舰版桌面端</span>
      </div>
      <h2 class="vynaro-showcase-title">
        为短剧拆条与影视解说而生的
        <span class="gold-gradient-text">全自动 AI 工厂</span>
      </h2>
      <p class="vynaro-showcase-subtitle">
        从视频切片拆条、剧情独白生成、人声声波克隆到剪映草稿原生导出，一站式极致流畅体验。
      </p>
    </div>

    <!-- 交互式 Tab 选项卡 -->
    <div class="vynaro-tab-bar">
      <button
        v-for="(tab, index) in tabs"
        :key="tab.id"
        class="vynaro-tab-btn"
        :class="{ active: activeTab === index }"
        @click="activeTab = index"
      >
        <span class="tab-icon">{{ tab.icon }}</span>
        <span class="tab-label">{{ tab.name }}</span>
        <span v-if="activeTab === index" class="active-indicator"></span>
      </button>
    </div>

    <!-- 3D 拟态 Mac 桌面视窗 -->
    <div class="vynaro-window-box">
      <!-- 窗口 Ambient 柔黄背景发光圈 -->
      <div class="vynaro-ambient-glow"></div>

      <div class="vynaro-mac-window">
        <div class="window-bar">
          <div class="window-dots">
            <span class="dot close"></span>
            <span class="dot minimize"></span>
            <span class="dot zoom"></span>
          </div>
          <div class="window-title">
            <span class="app-name">Vynaro Desktop</span>
            <span class="sep">—</span>
            <span class="current-step">{{ tabs[activeTab].tagline }}</span>
          </div>
          <div class="window-status">
            <span class="status-dot"></span>
            <span class="status-text">Tauri 2 Core Active</span>
          </div>
        </div>

        <!-- 屏幕主图展示 (支持切换与淡入动画) -->
        <div class="window-viewport" @click="openZoom">
          <transition name="vynaro-fade" mode="out-in">
            <img
              :key="tabs[activeTab].img"
              :src="withBase(tabs[activeTab].img)"
              :alt="tabs[activeTab].name"
              class="viewport-img"
            />
          </transition>
          <div class="viewport-zoom-hint">
            <svg class="zoom-icon" viewBox="0 0 24 24" width="16" height="16" stroke="currentColor" stroke-width="2" fill="none">
              <circle cx="11" cy="11" r="8"></circle>
              <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
              <line x1="11" y1="8" x2="11" y2="14"></line>
              <line x1="8" y1="11" x2="14" y2="11"></line>
            </svg>
            点击放大高清 UI 视窗
          </div>
        </div>
      </div>
    </div>

    <!-- 底部极简核心指标卡 -->
    <div class="vynaro-metric-strip">
      <div class="metric-item">
        <span class="metric-val">7 步</span>
        <span class="metric-lbl">DAG 状态机流水线</span>
      </div>
      <div class="metric-divider"></div>
      <div class="metric-item">
        <span class="metric-val">11 大</span>
        <span class="metric-lbl">LLM 独白脚本模型</span>
      </div>
      <div class="metric-divider"></div>
      <div class="metric-item">
        <span class="metric-val">&lt; 50ms</span>
        <span class="metric-lbl">VAD 字幕对齐精度</span>
      </div>
      <div class="metric-divider"></div>
      <div class="metric-item">
        <span class="metric-val">.draft</span>
        <span class="metric-lbl">剪映草稿原生工程</span>
      </div>
    </div>

    <!-- 大图 Lightbox 浮层 Modal -->
    <teleport to="body">
      <div v-if="isZoomed" class="vynaro-lightbox-overlay" @click="isZoomed = false">
        <div class="vynaro-lightbox-content" @click.stop>
          <button class="lightbox-close" @click="isZoomed = false">✕</button>
          <img :src="withBase(tabs[activeTab].img)" :alt="tabs[activeTab].name" class="lightbox-img" />
          <div class="lightbox-caption">{{ tabs[activeTab].name }} — {{ tabs[activeTab].tagline }}</div>
        </div>
      </div>
    </teleport>
  </section>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { withBase } from 'vitepress'

const activeTab = ref(0)
const isZoomed = ref(false)

const tabs = [
  {
    id: 'main',
    name: '全景工作台',
    icon: '🖥️',
    img: '/assets/mockups/hero-app-main.jpg',
    tagline: 'Tauri 2 极速桌面端，7步卡片 DAG 状态机一览'
  },
  {
    id: 'split',
    name: '智能拆条',
    icon: '✂️',
    img: '/assets/mockups/scene-split-ui.jpg',
    tagline: 'FFmpeg 场景切片与关键帧情绪峰值吸附'
  },
  {
    id: 'script',
    name: 'AI 独白脚本',
    icon: '🤖',
    img: '/assets/mockups/ai-script-generator.jpg',
    tagline: '11 大 LLM 引擎生成第一人称 Hook 与剧情'
  },
  {
    id: 'voice',
    name: '声波与字幕对齐',
    icon: '🎙️',
    img: '/assets/mockups/tts-voice-waveform.jpg',
    tagline: 'GPT-SoVITS 零样本克隆与 50ms VAD 毫秒级轴'
  },
  {
    id: 'export',
    name: '剪映草稿与导出',
    icon: '📤',
    img: '/assets/mockups/capcut-export-modal.jpg',
    tagline: '原生导出剪映工程草稿 (.draft) 与 8 平台预设'
  }
]

function openZoom() {
  isZoomed.value = true
}
</script>

<style scoped>
.vynaro-hero-app-showcase {
  margin: 40px 0 60px 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  width: 100%;
}

.vynaro-showcase-header {
  text-align: center;
  max-width: 800px;
  margin-bottom: 32px;
}

.vynaro-gradient-badge {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 6px 18px;
  border-radius: 30px;
  background: rgba(245, 200, 66, 0.08);
  border: 1px solid rgba(245, 200, 66, 0.25);
  box-shadow: 0 0 20px rgba(245, 200, 66, 0.12);
  margin-bottom: 16px;
}

.pulse-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #f5c842;
  box-shadow: 0 0 10px #f5c842;
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0% { opacity: 0.4; transform: scale(0.9); }
  50% { opacity: 1; transform: scale(1.2); }
  100% { opacity: 0.4; transform: scale(0.9); }
}

.badge-text {
  font-size: 13px;
  font-weight: 600;
  color: #f5c842;
  letter-spacing: 0.3px;
  font-family: var(--vp-font-family-mono);
}

.vynaro-showcase-title {
  font-family: 'Outfit', var(--vp-font-family-base);
  font-size: 2.6rem;
  font-weight: 800;
  line-height: 1.25;
  color: var(--vp-c-text-1);
  margin: 0 0 12px 0;
  letter-spacing: -0.5px;
}

.gold-gradient-text {
  background: linear-gradient(135deg, #fff099 0%, #f5c842 50%, #d97706 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  filter: drop-shadow(0 0 16px rgba(245, 200, 66, 0.3));
}

.vynaro-showcase-subtitle {
  font-size: 1.05rem;
  color: var(--vp-c-text-3);
  line-height: 1.6;
  margin: 0;
}

/* Tab 选项卡 */
.vynaro-tab-bar {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 8px;
  padding: 6px;
  background: rgba(18, 20, 30, 0.7);
  backdrop-filter: blur(16px);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 14px;
  margin-bottom: 24px;
}

.vynaro-tab-btn {
  position: relative;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 18px;
  border-radius: 10px;
  background: transparent;
  border: none;
  color: var(--vp-c-text-2);
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.25s ease;
}

.vynaro-tab-btn:hover {
  color: #f5c842;
  background: rgba(245, 200, 66, 0.06);
}

.vynaro-tab-btn.active {
  color: #ffffff;
  background: rgba(245, 200, 66, 0.15);
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3);
}

.active-indicator {
  position: absolute;
  bottom: 0;
  left: 20%;
  right: 20%;
  height: 2px;
  background: #f5c842;
  border-radius: 2px;
  box-shadow: 0 0 8px #f5c842;
}

/* 视窗 Mockup */
.vynaro-window-box {
  position: relative;
  width: 100%;
  max-width: 1100px;
}

.vynaro-ambient-glow {
  position: absolute;
  top: -20px;
  left: 5%;
  right: 5%;
  height: 300px;
  background: radial-gradient(ellipse at top, rgba(245, 200, 66, 0.2) 0%, rgba(124, 58, 237, 0.1) 45%, transparent 70%);
  filter: blur(40px);
  pointer-events: none;
  z-index: 0;
}

.vynaro-mac-window {
  position: relative;
  z-index: 1;
  background: #0d0f17;
  border-radius: 16px;
  border: 1px solid rgba(245, 200, 66, 0.3);
  box-shadow: 0 25px 60px rgba(0, 0, 0, 0.8), 0 0 40px rgba(245, 200, 66, 0.15);
  overflow: hidden;
  transition: border-color 0.3s ease, box-shadow 0.3s ease;
}

.vynaro-mac-window:hover {
  border-color: rgba(245, 200, 66, 0.5);
  box-shadow: 0 30px 70px rgba(0, 0, 0, 0.9), 0 0 50px rgba(245, 200, 66, 0.25);
}

.window-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 18px;
  background: #07080d;
  border-bottom: 1px solid #1c1e2e;
}

.window-dots {
  display: flex;
  gap: 8px;
}

.window-dots .dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
}
.window-dots .dot.close { background: #ff5f56; }
.window-dots .dot.minimize { background: #ffbd2e; }
.window-dots .dot.zoom { background: #27c93f; }

.window-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: var(--vp-c-text-2);
}

.app-name {
  font-weight: 700;
  color: #f5c842;
}

.sep {
  opacity: 0.4;
}

.current-step {
  font-weight: 500;
  color: var(--vp-c-text-3);
}

.window-status {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  color: #10b981;
  font-family: var(--vp-font-family-mono);
  background: rgba(16, 185, 129, 0.1);
  padding: 2px 10px;
  border-radius: 12px;
  border: 1px solid rgba(16, 185, 129, 0.2);
}

.status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #10b981;
  box-shadow: 0 0 6px #10b981;
}

.window-viewport {
  position: relative;
  width: 100%;
  cursor: pointer;
  overflow: hidden;
}

.viewport-img {
  width: 100%;
  height: auto;
  display: block;
  transition: transform 0.4s ease;
}

.window-viewport:hover .viewport-img {
  transform: scale(1.015);
}

.viewport-zoom-hint {
  position: absolute;
  bottom: 16px;
  right: 16px;
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  border-radius: 20px;
  background: rgba(13, 15, 23, 0.85);
  backdrop-filter: blur(8px);
  border: 1px solid rgba(255, 255, 255, 0.15);
  color: #ffffff;
  font-size: 12px;
  font-weight: 600;
  opacity: 0;
  transform: translateY(6px);
  transition: all 0.25s ease;
}

.window-viewport:hover .viewport-zoom-hint {
  opacity: 1;
  transform: translateY(0);
}

/* 核心指标 Strip */
.vynaro-metric-strip {
  display: flex;
  align-items: center;
  justify-content: space-around;
  width: 100%;
  max-width: 900px;
  margin-top: 36px;
  padding: 20px 24px;
  background: rgba(13, 15, 23, 0.6);
  backdrop-filter: blur(16px);
  border: 1px solid rgba(245, 200, 66, 0.15);
  border-radius: 16px;
}

.metric-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}

.metric-val {
  font-family: 'Outfit', var(--vp-font-family-mono);
  font-size: 1.5rem;
  font-weight: 800;
  color: #f5c842;
  text-shadow: 0 0 12px rgba(245, 200, 66, 0.3);
}

.metric-lbl {
  font-size: 12px;
  color: var(--vp-c-text-3);
  font-weight: 500;
}

.metric-divider {
  width: 1px;
  height: 32px;
  background: rgba(255, 255, 255, 0.1);
}

/* Lightbox Modal */
.vynaro-lightbox-overlay {
  position: fixed;
  inset: 0;
  z-index: 9999;
  background: rgba(5, 6, 10, 0.92);
  backdrop-filter: blur(20px);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 32px;
  animation: fadeIn 0.25s ease;
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

.vynaro-lightbox-content {
  position: relative;
  max-width: 92vw;
  max-height: 92vh;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.lightbox-close {
  position: absolute;
  top: -44px;
  right: 0;
  background: rgba(255, 255, 255, 0.15);
  border: 1px solid rgba(255, 255, 255, 0.2);
  color: #ffffff;
  width: 36px;
  height: 36px;
  border-radius: 50%;
  font-size: 18px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.2s;
}

.lightbox-close:hover {
  background: rgba(255, 255, 255, 0.3);
}

.lightbox-img {
  max-width: 100%;
  max-height: 80vh;
  border-radius: 12px;
  border: 1px solid rgba(245, 200, 66, 0.3);
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.9);
}

.lightbox-caption {
  margin-top: 14px;
  color: #f5c842;
  font-size: 14px;
  font-weight: 600;
  font-family: var(--vp-font-family-mono);
}

/* Animations */
.vynaro-fade-enter-active,
.vynaro-fade-leave-active {
  transition: opacity 0.25s ease, transform 0.25s ease;
}

.vynaro-fade-enter-from {
  opacity: 0;
  transform: scale(0.98);
}

.vynaro-fade-leave-to {
  opacity: 0;
  transform: scale(1.02);
}

@media (max-width: 768px) {
  .vynaro-showcase-title {
    font-size: 1.8rem;
  }
  .vynaro-metric-strip {
    flex-wrap: wrap;
    gap: 16px;
  }
  .metric-divider {
    display: none;
  }
}
</style>
