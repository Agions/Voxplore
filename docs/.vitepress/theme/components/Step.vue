<template>
  <div class="vp-step">
    <div class="vp-step__marker">
      <span class="vp-step__num">{{ num || '' }}</span>
      <div class="vp-step__dot" />
    </div>
    <div class="vp-step__body">
      <div v-if="title" class="vp-step__title">{{ title }}</div>
      <div v-if="$slots.default" class="vp-step__content">
        <slot />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  num?:    string | number
  title?:  string
}>()
</script>

<style scoped>
.vp-step {
  display: flex;
  align-items: flex-start;
  gap: 16px;
  position: relative;
}
.vp-step__marker {
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  width: 24px;
}
.vp-step__num {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: var(--vp-brand-soft, rgba(10,132,255,0.1));
  border: 1px solid rgba(10,132,255,0.3);
  color: var(--vp-brand, #0A84FF);
  font-size: 11px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: 'JetBrains Mono', monospace;
}
.vp-step__dot {
  width: 2px;
  flex: 1;
  min-height: 24px;
  background: var(--vp-border, #1A2540);
  margin: 4px 0;
}
.vp-step:last-child .vp-step__dot { display: none; }
.vp-step__body {
  padding-bottom: 24px;
  flex: 1;
}
.vp-step__title {
  font-size: 14px;
  font-weight: 700;
  color: var(--vp-text-1, #F1F5F9);
  margin-bottom: 6px;
  letter-spacing: -0.01em;
}
.vp-step__content {
  font-size: 13px;
  color: var(--vp-text-2, #8BA3C0);
  line-height: 1.65;
}
.vp-step__content :deep(p) { margin: 0; }
.vp-step__content :deep(p + p) { margin-top: 8px; }
</style>
