<template>
  <div class="vynaro-model-matrix">
    <div class="matrix-header">
      <div class="matrix-kicker">多模型协同能力矩阵</div>
      <h3 class="matrix-title">支持 11 大 LLM 独白引擎与 3 大 TTS 人声克隆</h3>
      <p class="matrix-sub">严格对应 Vynaro 核心代码与 README 规范，自动校验剧情独白一致性与完播率。</p>
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
            <span class="spec-lbl">官方默认模型</span>
            <span class="spec-val gold">{{ model.defaultModel }}</span>
          </div>
          <div class="spec-item">
            <span class="spec-lbl">响应耗时</span>
            <span class="spec-val">{{ model.latency }}</span>
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
  { id: 'all', name: '全部 11 大引擎 + TTS', icon: '⚡' },
  { id: 'llm', name: 'LLM 独白脚本 (10大)', icon: '🧠' },
  { id: 'tts', name: 'TTS 与人声克隆 (3大)', icon: '🎙️' },
  { id: 'local', name: '本地开源引擎', icon: '🏠' }
]

const models = [
  {
    name: '通义千问 (Qwen)',
    badge: '🇨🇳 Aliyun DashScope',
    type: 'LLM 脚本引擎',
    defaultModel: 'qwen3.8-max',
    desc: '阿里云百炼官方推荐，原生支持视频帧语义解析与人物情绪拟定，Hook 爆点抓取极佳。',
    latency: '~1.1s',
    tags: ['qwen3.8-max', 'qwen-plus', '短剧桥段识别'],
    cat: 'llm',
    brandColor: '#f5c842'
  },
  {
    name: 'DeepSeek',
    badge: '🇨🇳 DeepSeek AI',
    type: 'LLM 深度推理',
    defaultModel: 'deepseek-v4-pro',
    desc: '深度思考推理引擎，擅长处理错综复杂的多人反转与悬疑短剧冲突逻辑链。',
    latency: '~1.5s',
    tags: ['deepseek-v4-pro', 'deepseek-v4-flash', '高密度情节'],
    cat: 'llm',
    brandColor: '#06b6d4'
  },
  {
    name: 'OpenAI',
    badge: '🇺🇸 OpenAI',
    type: 'LLM 旗舰模型',
    defaultModel: 'gpt-5.6-sol',
    desc: '全球顶尖多模态模型，文笔流畅优美，角色第一人称内心独白渲染极强。',
    latency: '~1.2s',
    tags: ['gpt-5.6-sol', 'gpt-4o-mini', '多语种解说'],
    cat: 'llm',
    brandColor: '#10b981'
  },
  {
    name: 'Claude',
    badge: '🇺🇸 Anthropic',
    type: 'LLM 叙事大师',
    defaultModel: 'claude-sonnet-5',
    desc: '极具电影质感的文风输出，无机械感，适合治愈系、怀旧与纪录片腔调。',
    latency: '~1.4s',
    tags: ['claude-sonnet-5', '电影感修辞'],
    cat: 'llm',
    brandColor: '#a78bfa'
  },
  {
    name: 'Gemini',
    badge: '🇺🇸 Google AI',
    type: 'LLM 极速推理',
    defaultModel: 'gemini-3.6-flash',
    desc: '超长上下文窗口，支持长达 2 小时的全季短剧批量分析与连续集梗概。',
    latency: '~0.8s',
    tags: ['gemini-3.6-flash', 'gemini-3.1-pro', '整季批量'],
    cat: 'llm',
    brandColor: '#3b82f6'
  },
  {
    name: 'Kimi (月之暗面)',
    badge: '🇨🇳 Moonshot AI',
    type: 'LLM 长文本',
    defaultModel: 'kimi-k3',
    desc: '擅长处理百万字级别小说改编剧本与短剧背景设定集。',
    latency: '~1.5s',
    tags: ['kimi-k3', 'moonshot-v1', '小说改编'],
    cat: 'llm',
    brandColor: '#ec4899'
  },
  {
    name: '智谱 GLM',
    badge: '🇨🇳 Zhipu AI',
    type: 'LLM 国产强核',
    defaultModel: 'glm-5.2',
    desc: '智谱清言大模型引擎，针对中文影视剧本与情感递进深度调优。',
    latency: '~1.3s',
    tags: ['glm-5.2', 'glm-4-plus', '中文剧本拟真'],
    cat: 'llm',
    brandColor: '#f97316'
  },
  {
    name: '豆包 (Doubao)',
    badge: '🇨🇳 火山引擎',
    type: 'LLM 字节短视频',
    defaultModel: 'doubao-seed-2-1-pro',
    desc: '火山引擎抖音生态大模型，天然契合短视频高完播率节奏与热梗解说。',
    latency: '~0.9s',
    tags: ['doubao-seed-2-1-pro', 'doubao-pro-128k', '抖音爆款'],
    cat: 'llm',
    brandColor: '#00aeec'
  },
  {
    name: '腾讯混元 (Hunyuan)',
    badge: '🇨🇳 腾讯云',
    type: 'LLM 腾讯生态',
    defaultModel: 'hunyuan-pro',
    desc: '腾讯混元大模型旗舰版，中文逻辑严密，适合影视剧情梗概与影评分析。',
    latency: '~1.2s',
    tags: ['hunyuan-pro', '影视解析', '结构化剧情'],
    cat: 'llm',
    brandColor: '#07c160'
  },
  {
    name: '本地模型 (Local Engine)',
    badge: '🏠 Ollama / LMStudio',
    type: '本地开源推理',
    defaultModel: 'llama3.2 / qwen2.5',
    desc: '支持本地离线运行 Qwen2.5 / Llama3.2，保护剧本隐私与数据安全，0 费用。',
    latency: '取决于本地 GPU',
    tags: ['llama3.2', 'qwen2.5', '100% 离线隐私'],
    cat: 'local',
    brandColor: '#10b981'
  },
  {
    name: 'Edge-TTS 黄金配音',
    badge: '🎙️ Microsoft Azure',
    type: 'TTS 语音合成',
    defaultModel: 'zh-CN-XiaoxiaoNeural / Yunxi',
    desc: '微软官方 TTS 引擎，内置 50+ 种多语种黄金发音人，免费极速无需 API Key。',
    latency: '~0.4s',
    tags: ['50+ 音色', '语速/音调可调', '免费极速'],
    cat: 'tts',
    brandColor: '#f5c842'
  },
  {
    name: 'OpenAI-TTS',
    badge: '🎙️ OpenAI Voice',
    type: 'TTS 影视配音',
    defaultModel: 'gpt-4o-mini-tts / tts-1-hd',
    desc: 'OpenAI 影视级语音合成引擎，音质极其逼真，呼吸感与情感抑扬顿挫丰富。',
    latency: '~1.2s',
    tags: ['gpt-4o-mini-tts', 'tts-1-hd', '影视高清配音'],
    cat: 'tts',
    brandColor: '#10b981'
  },
  {
    name: 'GPT-SoVITS 零样本克隆',
    badge: '🎙️ Local Engine',
    type: 'TTS 音色克隆',
    defaultModel: 'Zero-shot Sovits (127.0.0.1:9880)',
    desc: '只需要 5 秒参考音频，即可极速克隆指定主播或影视主角音色，带黄金波形探针。',
    latency: '~2.0s',
    tags: ['Zero-shot 5秒克隆', '黄金波形探针', '音色保真'],
    cat: 'tts',
    brandColor: '#8b5cf6'
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
