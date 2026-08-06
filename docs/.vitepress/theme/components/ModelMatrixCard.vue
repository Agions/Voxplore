<template>
  <div class="vynaro-model-matrix">
    <div class="matrix-header">
      <div class="matrix-kicker">多模型协同能力矩阵</div>
      <h3 class="matrix-title">支持 11 大 LLM 独白引擎与 TTS 人声克隆</h3>
      <p class="matrix-sub">内置各大模型 SDK 驱动与备用节点，自动校验剧情独白一致性与逻辑完播率。</p>
    </div>

    <!-- 分类 Filter Buttons -->
    <div class="matrix-filter-bar">
      <button
        v-for="cat in categories"
        :key="cat.id"
        class="filter-btn"
        :class="{ active: selectedCat === cat.id }"
        @click="selectedCat = cat.id"
      >
        <span>{{ cat.icon }}</span>
        <span>{{ cat.name }}</span>
      </button>
    </div>

    <!-- 模型 Cards 网格 -->
    <div class="matrix-grid">
      <div
        v-for="model in filteredModels"
        :key="model.name"
        class="model-card"
      >
        <div class="card-top">
          <div class="model-badge" :style="{ color: model.brandColor, borderColor: model.brandColor + '40', background: model.brandColor + '12' }">
            {{ model.badge }}
          </div>
          <span class="type-tag">{{ model.type }}</span>
        </div>

        <h4 class="model-name">{{ model.name }}</h4>
        <p class="model-desc">{{ model.desc }}</p>

        <div class="card-specs">
          <div class="spec-item">
            <span class="spec-lbl">响应耗时</span>
            <span class="spec-val">{{ model.latency }}</span>
          </div>
          <div class="spec-item">
            <span class="spec-lbl">叙事完播预估</span>
            <span class="spec-val gold">{{ model.rating }}</span>
          </div>
        </div>

        <div class="card-tags">
          <span v-for="tag in model.tags" :key="tag" class="tag-chip"># {{ tag }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'

const selectedCat = ref('all')

const categories = [
  { id: 'all', name: '全部引擎 (11+)', icon: '⚡' },
  { id: 'llm', name: 'LLM 独白脚本', icon: '🧠' },
  { id: 'tts', name: 'TTS 与人声克隆', icon: '🎙️' },
  { id: 'local', name: '本地开源部署', icon: '🏠' }
]

const models = [
  {
    name: '通义千问 (Qwen 3.8 / Plus)',
    badge: '🇨🇳 Aliyun Bailian',
    type: 'LLM 脚本引擎',
    desc: '原生支持视频帧语义解析与人物情绪拟定，Hook 引子爆点抓取极佳。',
    latency: '~1.2s',
    rating: '98.5% 高完播率',
    tags: ['qwen3.8-max', '短剧桥段识别', '原生结构化输出'],
    cat: 'llm',
    brandColor: '#f5c842'
  },
  {
    name: 'DeepSeek (R1 / V3 Pro)',
    badge: '🇨🇳 DeepSeek AI',
    type: 'LLM 深度推理',
    desc: '深度思考推理引擎，擅长处理错综复杂的多人反转与悬疑短剧冲突。',
    latency: '~1.8s',
    rating: '99.1% 逻辑门禁',
    tags: ['deepseek-r1', '反转打脸链', '高密度情节'],
    cat: 'llm',
    brandColor: '#06b6d4'
  },
  {
    name: 'OpenAI (GPT-4o / GPT-5.6)',
    badge: '🇺🇸 OpenAI',
    type: 'LLM 旗舰模型',
    desc: '全球顶尖多模态模型，文笔流畅优美，角色第一人称内心独白渲染极强。',
    latency: '~1.4s',
    rating: '98.8% 情感表达',
    tags: ['gpt-4o', '多语种解说', '角色人设对齐'],
    cat: 'llm',
    brandColor: '#10b981'
  },
  {
    name: 'Claude (Claude 3.5 Sonnet)',
    badge: '🇺🇸 Anthropic',
    type: 'LLM 叙事大师',
    desc: '极具电影质感的文风输出，无机械感，适合治愈系、怀旧与纪录片腔调。',
    latency: '~1.5s',
    rating: '97.9% 电影质感',
    tags: ['claude-3.5', '高级修辞', '人称视角一致'],
    cat: 'llm',
    brandColor: '#a78bfa'
  },
  {
    name: 'Gemini (3.6 Flash / Pro)',
    badge: '🇺🇸 Google AI',
    type: 'LLM 极速推理',
    desc: '超长上下文窗口，支持长达 2 小时的全季短剧批量分析与连续集梗概。',
    latency: '~0.8s',
    rating: '96.5% 长剧梗概',
    tags: ['gemini-3.6-flash', '整季批量', '秒级响应'],
    cat: 'llm',
    brandColor: '#3b82f6'
  },
  {
    name: 'Kimi (月之暗面 Moonshot)',
    badge: '🇨🇳 Moonshot AI',
    type: 'LLM 长文本',
    desc: '擅长处理百万字级别小说改编剧本与短剧背景设定集。',
    latency: '~1.6s',
    rating: '97.2% 设定对齐',
    tags: ['kimi-k3', '小说改编', '人设卡片'],
    cat: 'llm',
    brandColor: '#ec4899'
  },
  {
    name: 'Edge-TTS 黄金配音',
    badge: '🎙️ Microsoft Azure',
    type: 'TTS 语音合成',
    desc: '内置 50+ 种多语种黄金发音人，涵盖云希、云扬、晓晓等解说界热门音色。',
    latency: '~0.5s',
    rating: '99.5% 播音质感',
    tags: ['50+ 音色', '语速/音调可调', '零延迟'],
    cat: 'tts',
    brandColor: '#f5c842'
  },
  {
    name: 'GPT-SoVITS 零样本克隆',
    badge: '🎙️ Local / Cloud',
    type: 'TTS 音色克隆',
    desc: '只需要 5 秒参考音频，即可复刻任意指定主播、博主或博主角色音色。',
    latency: '~2.5s',
    rating: '98.2% 音色相似度',
    tags: ['Zero-shot Clone', '5秒极速采样', '音色保真'],
    cat: 'tts',
    brandColor: '#8b5cf6'
  },
  {
    name: 'Ollama / LMStudio 本地大模型',
    badge: '🏠 Local GPU',
    type: '本地开源推理',
    desc: '支持本地离线运行 Qwen2.5 / Llama3.2，保护剧本隐私与数据安全。',
    latency: '取决于本地 GPU',
    rating: '100% 离线隐私',
    tags: ['qwen2.5-local', 'llama3.2', '完全本地化'],
    cat: 'local',
    brandColor: '#10b981'
  }
]

const filteredModels = computed(() => {
  if (selectedCat.value === 'all') return models
  return models.filter(m => m.cat === selectedCat.value || (selectedCat.value === 'local' && m.cat === 'local'))
})
</script>

<style scoped>
.vynaro-model-matrix {
  margin: 48px 0;
  width: 100%;
}

.matrix-header {
  text-align: center;
  margin-bottom: 28px;
}

.matrix-kicker {
  font-size: 12px;
  font-weight: 700;
  color: #f5c842;
  letter-spacing: 1.5px;
  text-transform: uppercase;
  font-family: var(--vp-font-family-mono);
  margin-bottom: 8px;
}

.matrix-title {
  font-family: 'Outfit', var(--vp-font-family-base);
  font-size: 2.2rem;
  font-weight: 800;
  color: var(--vp-c-text-1);
  margin: 0 0 10px 0;
}

.matrix-sub {
  font-size: 1rem;
  color: var(--vp-c-text-3);
  margin: 0;
}

/* Filter Bar */
.matrix-filter-bar {
  display: flex;
  justify-content: center;
  gap: 10px;
  margin-bottom: 28px;
  flex-wrap: wrap;
}

.filter-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 18px;
  border-radius: 20px;
  background: rgba(13, 15, 23, 0.6);
  border: 1px solid rgba(255, 255, 255, 0.1);
  color: var(--vp-c-text-2);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.25s ease;
}

.filter-btn:hover {
  color: #f5c842;
  border-color: rgba(245, 200, 66, 0.3);
}

.filter-btn.active {
  background: rgba(245, 200, 66, 0.15);
  border-color: #f5c842;
  color: #ffffff;
  box-shadow: 0 0 15px rgba(245, 200, 66, 0.2);
}

/* Matrix Grid */
.matrix-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 20px;
}

.model-card {
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  padding: 22px;
  background: rgba(13, 15, 23, 0.7);
  backdrop-filter: blur(16px);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 14px;
  transition: all 0.25s ease;
}

.model-card:hover {
  border-color: rgba(245, 200, 66, 0.4);
  transform: translateY(-3px);
  box-shadow: 0 12px 30px rgba(0, 0, 0, 0.6), 0 0 20px rgba(245, 200, 66, 0.1);
}

.card-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 14px;
}

.model-badge {
  font-size: 11px;
  font-weight: 700;
  padding: 3px 10px;
  border-radius: 12px;
  border: 1px solid;
  font-family: var(--vp-font-family-mono);
}

.type-tag {
  font-size: 11px;
  color: var(--vp-c-text-3);
  font-weight: 500;
}

.model-name {
  font-family: 'Outfit', var(--vp-font-family-base);
  font-size: 1.15rem;
  font-weight: 700;
  color: var(--vp-c-text-1);
  margin: 0 0 8px 0;
}

.model-desc {
  font-size: 13px;
  color: var(--vp-c-text-2);
  line-height: 1.5;
  margin: 0 0 16px 0;
}

.card-specs {
  display: flex;
  justify-content: space-between;
  padding: 10px 12px;
  background: rgba(7, 8, 13, 0.6);
  border-radius: 8px;
  border: 1px solid #1a1c2a;
  margin-bottom: 14px;
  font-size: 12px;
}

.spec-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.spec-lbl {
  color: var(--vp-c-text-3);
  font-size: 10px;
}

.spec-val {
  color: #e5e7eb;
  font-weight: 600;
  font-family: var(--vp-font-family-mono);
}

.spec-val.gold {
  color: #f5c842;
}

.card-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.tag-chip {
  font-size: 11px;
  color: var(--vp-c-text-3);
  background: rgba(255, 255, 255, 0.05);
  padding: 2px 8px;
  border-radius: 4px;
}
</style>
