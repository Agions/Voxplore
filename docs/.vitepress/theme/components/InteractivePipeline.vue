<template>
  <div class="splicr-interactive-pipeline">
    <div class="pipeline-header">
      <div class="pipeline-kicker">DAG 状态机驱动</div>
      <h3 class="pipeline-title">7 步智能全自动化生产流水线</h3>
      <p class="pipeline-sub">点击下方任意节点，探索其核心技术实现、数据输入输出与可调节参数。</p>
    </div>

    <!-- 水平/响应式 7 步节点指示器 -->
    <div class="pipeline-stepper">
      <button
        v-for="(step, idx) in pipelineSteps"
        :key="step.no"
        class="step-node"
        :class="{ active: currentStep === idx }"
        @click="currentStep = idx"
      >
        <div class="node-badge">0{{ idx + 1 }}</div>
        <div class="node-icon">{{ step.icon }}</div>
        <div class="node-name">{{ step.shortTitle }}</div>
        <div v-if="idx < pipelineSteps.length - 1" class="node-connector"></div>
      </button>
    </div>

    <!-- 选中 Step 的详细高奢视窗面板 -->
    <div class="pipeline-detail-panel">
      <div class="panel-left">
        <div class="step-meta">
          <span class="step-tag">STEP 0{{ currentStep + 1 }} OF 07</span>
          <span class="step-status">● DAG Node Active</span>
        </div>
        <h4 class="detail-title">{{ pipelineSteps[currentStep].title }}</h4>
        <p class="detail-description">{{ pipelineSteps[currentStep].description }}</p>

        <!-- 输入与输出 Badge 规范 -->
        <div class="io-box">
          <div class="io-row">
            <span class="io-label">📥 输入数据:</span>
            <span class="io-badge input">{{ pipelineSteps[currentStep].input }}</span>
          </div>
          <div class="io-row">
            <span class="io-label">📤 产出结果:</span>
            <span class="io-badge output">{{ pipelineSteps[currentStep].output }}</span>
          </div>
        </div>

        <!-- 核心算法/代码 Snippet -->
        <div class="code-preview-box">
          <div class="code-header">
            <span class="code-lang">{{ pipelineSteps[currentStep].techLang }}</span>
            <span class="code-desc">{{ pipelineSteps[currentStep].techName }}</span>
          </div>
          <pre class="code-content"><code>{{ pipelineSteps[currentStep].codeSnippet }}</code></pre>
        </div>
      </div>

      <div class="panel-right">
        <div class="mockup-container">
          <div class="mockup-frame-header">
            <span class="frame-title">{{ pipelineSteps[currentStep].title }} — UI 视窗</span>
            <span class="frame-badge">Live Visual</span>
          </div>
          <img
            :src="withBase(pipelineSteps[currentStep].mockupImg)"
            :alt="pipelineSteps[currentStep].title"
            class="mockup-img"
          />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { withBase } from 'vitepress'

const currentStep = ref(0)

const pipelineSteps = [
  {
    no: '01',
    shortTitle: '素材导入',
    icon: '📥',
    title: 'Step 1: 本地音视频素材解析与预处理',
    description: '自动解析本地 4K/1080P 音视频元数据（Resolution, FPS, Video Codec, Audio Bitrate），生成毫秒级关键帧快照缩略图，并对音频轨进行标准化重采样。',
    input: 'MP4 / MOV / AVI / WebM 本地视频源',
    output: 'AppContext 元数据 JSON + 帧缩略图序列',
    techLang: 'Rust / splicr-detect',
    techName: 'FFmpeg Probe Inspector',
    codeSnippet: `let probe = FfmpegProbe::analyze("input_episode_01.mp4")?;
println!("Resolution: {}x{}, FPS: {:.2}", probe.width, probe.height, probe.fps);
let thumbnails = probe.extract_keyframes(Interval::Sec(2))?;`,
    mockupImg: '/assets/mockups/hero-app-main.jpg'
  },
  {
    no: '02',
    shortTitle: '智能拆条',
    icon: '✂️',
    title: 'Step 2: FFmpeg 场景切片与关键帧识别',
    description: '基于 FFmpeg 切面探测 (select=gt(scene,0.3)) 与音频情绪峰值吸附，精准索引镜头边界，按剧情高潮与角色对峙自动切分短剧片段。',
    input: '视频流与 Keyframe Index',
    output: 'Scene Cut Timeline JSON + 情绪高光边界',
    techLang: 'Rust / splicr-detect',
    techName: 'Scene Boundary State Machine',
    codeSnippet: `let scene_cuts = detect_scene_boundaries(&video_path, 0.35)?;
let emotion_peaks = audio_analyzer.detect_volume_peaks(-12.0)?;
let final_segments = merge_cut_points(scene_cuts, emotion_peaks);`,
    mockupImg: '/assets/mockups/scene-split-ui.jpg'
  },
  {
    no: '03',
    shortTitle: '独白脚本',
    icon: '🤖',
    title: 'Step 3: 11 大 LLM 视角剧情独白创作',
    description: '集成通义千问 (qwen3.8-max)、DeepSeek (deepseek-v4-pro)、OpenAI (gpt-5.6-sol)、Claude (claude-sonnet-5)、Gemini (gemini-3.6-flash)、GLM-5.2、豆包 (doubao-seed-2-1-pro)、混元-pro、Kimi-k3 与本地 Ollama。基于主角第一人称视角构建 Hook 爆点与递进剧情。',
    input: '剧情理解上下文与角色人设 Pre-prompt',
    output: '第一人称独白稿 + 多模型一致性校验分',
    techLang: 'TypeScript / splicr-script',
    techName: 'LLM Multi-Model Provider Engine',
    codeSnippet: `const script = await llmClient.generateScript({
  provider: 'DeepSeek',
  model: 'deepseek-v4-pro',
  style: 'FirstPerson_Immersive',
  structure: ['Hook_3s', 'Character_Conflict', 'Climax_Turnaround', 'Next_Hook']
});`,
    mockupImg: '/assets/mockups/ai-script-generator.jpg'
  },
  {
    no: '04',
    shortTitle: 'TTS 配音',
    icon: '🎙️',
    title: 'Step 4: Edge-TTS / OpenAI-TTS 与 GPT-SoVITS 零样本克隆',
    description: '支持 Edge-TTS 50+ 黄金音色、OpenAI-TTS (gpt-4o-mini-tts) 以及基于 GPT-SoVITS 的 5秒零样本人声克隆 (127.0.0.1:9880)。集成黄金波形与本地服务探针。',
    input: '独白文本 + 目标克隆语音采样',
    output: '48kHz 广播级 WAV 解说配音轨',
    techLang: 'Rust / splicr-voice',
    techName: 'Zero-shot Voice Clone Probe',
    codeSnippet: `let voice_model = SovitsCloneEngine::load_sample("character_sample.wav")?;
let narration_wav = voice_model.synthesize(&script_text, Speed::Rate(1.1))?;
narration_wav.apply_golden_waveform_norm()?;`,
    mockupImg: '/assets/mockups/tts-voice-waveform.jpg'
  },
  {
    no: '05',
    shortTitle: 'VAD 对齐',
    icon: '📝',
    title: 'Step 5: 50ms 级别 VAD 端点字幕毫秒轴',
    description: '利用 FFmpeg silencedetect 探测人声自然停顿与静音区间，自动对齐配音音频与字幕时间戳，实现偏差低于 50ms 的极致声字同步。',
    input: 'narration.wav + script.txt',
    output: 'SRT / ASS / VTT 毫秒对齐字幕文件',
    techLang: 'Rust / splicr-subtitle',
    techName: 'Silencedetect VAD Timestamp Sync',
    codeSnippet: `let silences = ffmpeg::silencedetect(&audio_path, -35.0, 0.15)?;
let subtitles = VadAligner::sync_timestamps(script_sentences, silences)?;
subtitles.export_ass("output/narration.ass")?;`,
    mockupImg: '/assets/mockups/tts-voice-waveform.jpg'
  },
  {
    no: '06',
    shortTitle: '音画混流',
    icon: '🎬',
    title: 'Step 6: 多轨混音与 9:16 竖屏实时渲染',
    description: '多轨时间轴毫秒级混流，BGM 背景音乐自动降噪避让 (amix filter -6dB)，实时渲染 9:16 / 16:9 竖屏/横屏多平台成片预览。',
    input: 'Video Stream + Voice Audio + BGM + ASS Subtitle',
    output: '1080P 60fps MP4 竖屏成片',
    techLang: 'Rust / splicr-compose',
    techName: 'Multi-track Amix Muxer Engine',
    codeSnippet: `let mut composer = MultitrackComposer::new(Aspect::Vertical9x16);
composer.add_video_track(&video_cuts);
composer.add_audio_ducking(&voice_track, &bgm_track, -6.0);
composer.render_mp4("output/final_video.mp4")?;`,
    mockupImg: '/assets/mockups/hero-app-main.jpg'
  },
  {
    no: '07',
    shortTitle: '草稿导出',
    icon: '📤',
    title: 'Step 7: 剪映草稿 (.draft) 原生工程导出',
    description: '原生构建剪映 PC 端工程草稿文件夹 (`.draft`)，保留轨道、媒体关系与字幕样式，方便在剪映中进行二次精细化调效果与字幕微调。',
    input: 'Composer Project Context',
    output: 'CapCut Project (.draft) + 8 平台预设',
    techLang: 'Rust / splicr-export',
    techName: 'CapCut Native Draft Generator',
    codeSnippet: `let draft = CapCutDraftBuilder::new("splicr_Project_01")
  .add_video_lane(segment_files)
  .add_audio_lane(voice_file)
  .add_subtitle_lane(ass_file)
  .build()?;
draft.save_to_capcut_dir()?;`,
    mockupImg: '/assets/mockups/capcut-export-modal.jpg'
  }
]
</script>

<style scoped>
.splicr-interactive-pipeline {
  margin: 48px 0;
  width: 100%;
}

.pipeline-header {
  text-align: center;
  margin-bottom: 32px;
}

.pipeline-kicker {
  font-size: 12px;
  font-weight: 700;
  color: #f5c842;
  letter-spacing: 1.5px;
  text-transform: uppercase;
  font-family: var(--vp-font-family-mono);
  margin-bottom: 8px;
}

.pipeline-title {
  font-family: 'Outfit', var(--vp-font-family-base);
  font-size: 2.2rem;
  font-weight: 800;
  color: var(--vp-c-text-1);
  margin: 0 0 10px 0;
}

.pipeline-sub {
  font-size: 1rem;
  color: var(--vp-c-text-3);
  margin: 0;
}

/* Stepper Indicator */
.pipeline-stepper {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  overflow-x: auto;
  padding: 16px 8px;
  margin-bottom: 24px;
}

.step-node {
  position: relative;
  flex: 1;
  min-width: 120px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding: 14px 10px;
  background: rgba(13, 15, 23, 0.6);
  backdrop-filter: blur(12px);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.25s ease;
}

.step-node:hover {
  border-color: rgba(245, 200, 66, 0.4);
  transform: translateY(-2px);
  background: rgba(245, 200, 66, 0.05);
}

.step-node.active {
  background: rgba(245, 200, 66, 0.12);
  border-color: #f5c842;
  box-shadow: 0 0 20px rgba(245, 200, 66, 0.2);
}

.node-badge {
  font-size: 11px;
  font-weight: 800;
  color: #f5c842;
  font-family: var(--vp-font-family-mono);
}

.node-icon {
  font-size: 22px;
}

.node-name {
  font-size: 13px;
  font-weight: 700;
  color: var(--vp-c-text-1);
}

/* Detail Panel */
.pipeline-detail-panel {
  display: grid;
  grid-template-columns: 1fr 1.1fr;
  gap: 24px;
  padding: 28px;
  background: #0d0f17;
  border: 1px solid rgba(245, 200, 66, 0.25);
  border-radius: 18px;
  box-shadow: 0 20px 50px rgba(0, 0, 0, 0.7);
}

.panel-left {
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}

.step-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.step-tag {
  font-size: 11px;
  font-weight: 800;
  color: #f5c842;
  letter-spacing: 1px;
  font-family: var(--vp-font-family-mono);
}

.step-status {
  font-size: 11px;
  color: #10b981;
  font-family: var(--vp-font-family-mono);
}

.detail-title {
  font-family: 'Outfit', var(--vp-font-family-base);
  font-size: 1.4rem;
  font-weight: 800;
  color: var(--vp-c-text-1);
  margin: 0 0 12px 0;
  line-height: 1.3;
}

.detail-description {
  font-size: 14px;
  color: var(--vp-c-text-2);
  line-height: 1.6;
  margin-bottom: 20px;
}

/* IO Box */
.io-box {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 20px;
  padding: 12px 16px;
  background: rgba(18, 20, 30, 0.7);
  border-radius: 10px;
  border: 1px solid #1f212e;
}

.io-row {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 13px;
}

.io-label {
  color: var(--vp-c-text-3);
  font-weight: 600;
  width: 80px;
}

.io-badge {
  font-size: 12px;
  font-weight: 600;
  padding: 2px 10px;
  border-radius: 6px;
  font-family: var(--vp-font-family-mono);
}

.io-badge.input {
  background: rgba(6, 182, 212, 0.12);
  color: #06b6d4;
  border: 1px solid rgba(6, 182, 212, 0.25);
}

.io-badge.output {
  background: rgba(245, 200, 66, 0.12);
  color: #f5c842;
  border: 1px solid rgba(245, 200, 66, 0.25);
}

/* Code Snippet */
.code-preview-box {
  background: #07080d;
  border: 1px solid #1f212e;
  border-radius: 10px;
  overflow: hidden;
}

.code-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 14px;
  background: #11131c;
  border-bottom: 1px solid #1c1e2d;
  font-size: 12px;
}

.code-lang {
  color: #f5c842;
  font-weight: 700;
  font-family: var(--vp-font-family-mono);
}

.code-desc {
  color: var(--vp-c-text-3);
}

.code-content {
  padding: 14px;
  margin: 0;
  font-family: var(--vp-font-family-mono);
  font-size: 12px;
  color: #e5e7eb;
  line-height: 1.5;
  overflow-x: auto;
}

/* Panel Right Mockup */
.panel-right {
  display: flex;
  align-items: center;
}

.mockup-container {
  width: 100%;
  background: #11131c;
  border: 1px solid rgba(245, 200, 66, 0.2);
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);
}

.mockup-frame-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 14px;
  background: #08090e;
  border-bottom: 1px solid #1c1e2d;
}

.frame-title {
  font-size: 12px;
  font-weight: 600;
  color: var(--vp-c-text-2);
}

.frame-badge {
  font-size: 10px;
  font-weight: 700;
  color: #10b981;
  background: rgba(16, 185, 129, 0.12);
  padding: 2px 8px;
  border-radius: 10px;
  font-family: var(--vp-font-family-mono);
}

.mockup-img {
  width: 100%;
  height: auto;
  display: block;
}

@media (max-width: 900px) {
  .pipeline-detail-panel {
    grid-template-columns: 1fr;
  }
}
</style>
