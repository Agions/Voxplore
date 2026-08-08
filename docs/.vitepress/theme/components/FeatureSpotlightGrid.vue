<template>
  <div class="vynaro-spotlight-grid">
    <div class="spotlight-header">
      <div class="spotlight-kicker">核心技术亮点</div>
      <h3 class="spotlight-title">为专业短剧拆条与影视解说团队打造</h3>
      <p class="spotlight-sub">每一个模块均经过高完播率剪辑 SOP 调优，兼顾生成效率与爆款品质。</p>
    </div>

    <div class="cards-wrapper">
      <div
        v-for="(item, idx) in features"
        :key="item.title"
        class="spotlight-card"
        @mousemove="onMouseMove($event, idx)"
        :style="cardStyles[idx]"
      >
        <div class="card-inner">
          <div class="card-top-bar">
            <span class="card-icon">{{ item.icon }}</span>
            <span class="card-chip">{{ item.tag }}</span>
          </div>
          <h4 class="card-title">{{ item.title }}</h4>
          <p class="card-text">{{ item.text }}</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const features = [
  {
    icon: '✂️',
    tag: 'FFmpeg 智能切面',
    title: '智能语义切片与关键帧打点',
    text: '基于镜头突变与情绪峰值自动打点，生成 keyframe 缩略图索引，告别繁琐人工打点。'
  },
  {
    icon: '🤖',
    tag: '11 大 LLM 独白',
    title: '第一人称主角独白脚本',
    text: '通义千问 (qwen3.8-max)、DeepSeek (deepseek-v4-pro)、OpenAI (gpt-5.6-sol) 深度微调，黄金3秒 Hook 留存，大幅拉升完播率。'
  },
  {
    icon: '🎙️',
    tag: 'GPT-SoVITS 克隆',
    title: '声波人声克隆与黄金音色',
    text: '50+ 种 Azure 黄金说话人音色，以及 5 秒音频极速人声克隆，复刻专属品牌解说音色。'
  },
  {
    icon: '📝',
    tag: '50ms VAD 对齐',
    title: 'silencedetect 毫秒轴对齐',
    text: '自动探测人声自然停顿与静音区间，校准配音与 SRT/ASS 字幕时间戳，偏差 < 50ms。'
  },
  {
    icon: '🎬',
    tag: '9:16 多轨混流',
    title: '音画多轨混音与 BGM 避让',
    text: '毫秒级时间轴混流，解说人声自动压过 BGM 背景声 (-6dB)，9:16 竖屏高清实时渲染。'
  },
  {
    icon: '📤',
    tag: '.draft 原生导出',
    title: '剪映工程草稿一键导出',
    text: '原生导出剪映 PC 端工程草稿文件夹 (.draft)，保留多轨关系、字幕与材质，二次微调零门槛。'
  }
]

const cardStyles = ref(features.map(() => ({
  background: 'rgba(13, 15, 23, 0.6)'
})))

function onMouseMove(e: MouseEvent, idx: number) {
  const card = e.currentTarget as HTMLElement
  const rect = card.getBoundingClientRect()
  const x = e.clientX - rect.left
  const y = e.clientY - rect.top
  cardStyles.value[idx] = {
    background: `radial-gradient(400px circle at ${x}px ${y}px, rgba(245, 200, 66, 0.12), rgba(13, 15, 23, 0.6) 80%)`
  }
}
</script>

<style scoped>
.vynaro-spotlight-grid {
  margin: 48px 0;
  width: 100%;
}

.spotlight-header {
  text-align: center;
  margin-bottom: 32px;
}

.spotlight-kicker {
  font-size: 12px;
  font-weight: 700;
  color: #f5c842;
  letter-spacing: 1.5px;
  text-transform: uppercase;
  font-family: var(--vp-font-family-mono);
  margin-bottom: 8px;
}

.spotlight-title {
  font-family: 'Outfit', var(--vp-font-family-base);
  font-size: 2.2rem;
  font-weight: 800;
  color: var(--vp-c-text-1);
  margin: 0 0 10px 0;
}

.spotlight-sub {
  font-size: 1rem;
  color: var(--vp-c-text-3);
  margin: 0;
}

.cards-wrapper {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 20px;
}

.spotlight-card {
  position: relative;
  border-radius: 14px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  backdrop-filter: blur(16px);
  padding: 24px;
  transition: border-color 0.25s ease, transform 0.25s ease;
}

.spotlight-card:hover {
  border-color: rgba(245, 200, 66, 0.4);
  transform: translateY(-3px);
  box-shadow: 0 14px 35px rgba(0, 0, 0, 0.6), 0 0 20px rgba(245, 200, 66, 0.12);
}

.card-inner {
  display: flex;
  flex-direction: column;
}

.card-top-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.card-icon {
  font-size: 28px;
}

.card-chip {
  font-size: 11px;
  font-weight: 700;
  color: #f5c842;
  background: rgba(245, 200, 66, 0.12);
  padding: 3px 10px;
  border-radius: 12px;
  border: 1px solid rgba(245, 200, 66, 0.25);
  font-family: var(--vp-font-family-mono);
}

.card-title {
  font-family: 'Outfit', var(--vp-font-family-base);
  font-size: 1.2rem;
  font-weight: 700;
  color: var(--vp-c-text-1);
  margin: 0 0 8px 0;
}

.card-text {
  font-size: 13px;
  color: var(--vp-c-text-2);
  line-height: 1.6;
  margin: 0;
}
</style>
