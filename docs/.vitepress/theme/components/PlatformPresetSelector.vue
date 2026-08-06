<template>
  <div class="vynaro-platform-selector">
    <div class="selector-header">
      <div class="selector-kicker">多平台一键出片预设</div>
      <h3 class="selector-title">8 大短视频与长视频平台发布预设</h3>
      <p class="selector-sub">自动匹配最严谨的分辨率、画面比例、音调响度与剪映工程草稿结构。</p>
    </div>

    <div class="platforms-grid">
      <div
        v-for="(p, index) in platforms"
        :key="p.name"
        class="platform-card"
        :class="{ active: activePlatform === index }"
        @click="activePlatform = index"
      >
        <div class="card-header">
          <span class="platform-icon">{{ p.icon }}</span>
          <span class="platform-name">{{ p.name }}</span>
        </div>
        <div class="platform-aspect">{{ p.aspect }}</div>
        <div class="platform-res">{{ p.res }}</div>
        <div class="preset-tag">剪映 .draft 同步</div>
      </div>
    </div>

    <!-- Active Platform Details Card -->
    <div class="active-detail-box">
      <div class="detail-left">
        <div class="detail-badge">
          <span>{{ platforms[activePlatform].icon }}</span>
          <span>{{ platforms[activePlatform].name }} — 预设详情</span>
        </div>
        <h4 class="preset-title">{{ platforms[activePlatform].desc }}</h4>
        <div class="preset-specs-grid">
          <div class="preset-spec">
            <span class="spec-label">分辨率 (Resolution)</span>
            <span class="spec-value">{{ platforms[activePlatform].res }}</span>
          </div>
          <div class="preset-spec">
            <span class="spec-label">画面比例 (Aspect Ratio)</span>
            <span class="spec-value">{{ platforms[activePlatform].aspect }}</span>
          </div>
          <div class="preset-spec">
            <span class="spec-label">视频编码 (Video Codec)</span>
            <span class="spec-value">{{ platforms[activePlatform].codec }}</span>
          </div>
          <div class="preset-spec">
            <span class="spec-label">BGM 降噪避让 (Amix Ducking)</span>
            <span class="spec-value gold">{{ platforms[activePlatform].ducking }}</span>
          </div>
        </div>
      </div>
      <div class="detail-right">
        <div class="draft-preview-badge">
          <span class="check-icon">✓</span>
          <span>剪映原生工程草稿 (.draft) 已自动应用此预设</span>
        </div>
        <p class="draft-sub">导出后可直接拖入剪映 PC 端，轨道、字幕与音效完全保留。</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const activePlatform = ref(0)

const platforms = [
  {
    name: '抖音 (Douyin)',
    icon: '🎵',
    aspect: '9:16 竖屏',
    res: '1080×1920',
    codec: 'H.264 High Profile / 30-60fps',
    ducking: '解说声压过 BGM -6dB',
    desc: '短剧解说与第一人称视频的高完播率黄金规格，字幕居中下三界位。'
  },
  {
    name: 'B站 (Bilibili)',
    icon: '📺',
    aspect: '16:9 横屏',
    res: '1920×1080',
    codec: 'H.264 / AV1 60fps',
    ducking: '双声道均衡混响',
    desc: '适合深度电影解说、影评吐槽与中长视频创作，字幕压制清晰。'
  },
  {
    name: '小红书',
    icon: '📕',
    aspect: '9:16 竖屏',
    res: '1080×1920',
    codec: 'H.264 / 30fps',
    ducking: '治愈系人声低音微增',
    desc: '悬疑、治愈与剧情片爆款样式，字幕与画框上下留白防遮挡。'
  },
  {
    name: 'YouTube Shorts',
    icon: '▶️',
    aspect: '9:16 竖屏',
    res: '1080×1920',
    codec: 'H.264 / 60fps',
    ducking: '国际标准 -14 LUFS',
    desc: '全球短剧与视频叙事算法优化预设，SRT 软字幕原生嵌入。'
  },
  {
    name: 'TikTok',
    icon: '🎶',
    aspect: '9:16 竖屏',
    res: '1080×1920',
    codec: 'H.264 / 60fps',
    ducking: '高密度快节奏混音',
    desc: '海外爆款短视频引流预设，画面顶部与侧边预留操作 UI 区域。'
  },
  {
    name: '快手',
    icon: '⚡',
    aspect: '9:16 竖屏',
    res: '1080×1920',
    codec: 'H.264 / 30fps',
    ducking: '主角语调中频提升',
    desc: '下沉市场高完播率解说预设，高能爽点字幕突出显示。'
  },
  {
    name: '西瓜视频',
    icon: '🍉',
    aspect: '16:9 横屏',
    res: '1920×1080',
    codec: 'H.264 / 30fps',
    ducking: '影院级长剧降噪',
    desc: '长视频剧场与多集拆条解说预设，带章节标记。'
  },
  {
    name: '微信视频号',
    icon: '💬',
    aspect: '9:16 竖屏',
    res: '1080×1920',
    codec: 'H.264 / 30fps',
    ducking: '清晰人声社交混响',
    desc: '朋友圈与微信生态社交裂变传播，视频前3秒Hook强留存。'
  }
]
</script>

<style scoped>
.vynaro-platform-selector {
  margin: 48px 0;
  width: 100%;
}

.selector-header {
  text-align: center;
  margin-bottom: 28px;
}

.selector-kicker {
  font-size: 12px;
  font-weight: 700;
  color: #f5c842;
  letter-spacing: 1.5px;
  text-transform: uppercase;
  font-family: var(--vp-font-family-mono);
  margin-bottom: 8px;
}

.selector-title {
  font-family: 'Outfit', var(--vp-font-family-base);
  font-size: 2.2rem;
  font-weight: 800;
  color: var(--vp-c-text-1);
  margin: 0 0 10px 0;
}

.selector-sub {
  font-size: 1rem;
  color: var(--vp-c-text-3);
  margin: 0;
}

/* Platforms Grid */
.platforms-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 16px;
  margin-bottom: 24px;
}

.platform-card {
  padding: 16px;
  background: rgba(13, 15, 23, 0.6);
  backdrop-filter: blur(12px);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.25s ease;
}

.platform-card:hover {
  border-color: rgba(245, 200, 66, 0.4);
  transform: translateY(-2px);
}

.platform-card.active {
  background: rgba(245, 200, 66, 0.12);
  border-color: #f5c842;
  box-shadow: 0 0 20px rgba(245, 200, 66, 0.18);
}

.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.platform-icon {
  font-size: 20px;
}

.platform-name {
  font-size: 14px;
  font-weight: 700;
  color: var(--vp-c-text-1);
}

.platform-aspect {
  font-size: 12px;
  color: #f5c842;
  font-weight: 600;
  margin-bottom: 2px;
}

.platform-res {
  font-size: 12px;
  color: var(--vp-c-text-3);
  font-family: var(--vp-font-family-mono);
  margin-bottom: 10px;
}

.preset-tag {
  font-size: 10px;
  color: #10b981;
  background: rgba(16, 185, 129, 0.1);
  padding: 2px 8px;
  border-radius: 8px;
  display: inline-block;
}

/* Detail Box */
.active-detail-box {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
  padding: 24px;
  background: #0d0f17;
  border: 1px solid rgba(245, 200, 66, 0.25);
  border-radius: 14px;
}

.detail-badge {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  font-weight: 700;
  color: #f5c842;
  margin-bottom: 10px;
}

.preset-title {
  font-size: 14px;
  color: var(--vp-c-text-2);
  line-height: 1.5;
  margin: 0 0 16px 0;
}

.preset-specs-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.preset-spec {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.spec-label {
  font-size: 11px;
  color: var(--vp-c-text-3);
}

.spec-value {
  font-size: 13px;
  font-weight: 600;
  color: var(--vp-c-text-1);
  font-family: var(--vp-font-family-mono);
}

.spec-value.gold {
  color: #f5c842;
}

.detail-right {
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding: 20px;
  background: rgba(245, 200, 66, 0.06);
  border: 1px dashed rgba(245, 200, 66, 0.3);
  border-radius: 10px;
}

.draft-preview-badge {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  font-weight: 700;
  color: #f5c842;
  margin-bottom: 8px;
}

.check-icon {
  background: #f5c842;
  color: #05060a;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 900;
}

.draft-sub {
  font-size: 12px;
  color: var(--vp-c-text-3);
  line-height: 1.5;
  margin: 0;
}

@media (max-width: 768px) {
  .active-detail-box {
    grid-template-columns: 1fr;
  }
}
</style>
