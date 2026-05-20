<template>
  <div class="vp-timeline-item">
    <div class="vp-timeline-item__marker" />
    <div class="vp-timeline-item__body">
      <div class="vp-timeline-item__meta">
        <span v-if="date" class="vp-timeline-item__date">{{ date }}</span>
        <span v-if="tag" class="vp-timeline-item__tag">{{ tag }}</span>
      </div>
      <div v-if="title" class="vp-timeline-item__title">{{ title }}</div>
      <div v-if="$slots.default" class="vp-timeline-item__content">
        <slot />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  date?: string
  tag?:  string
  title?: string
}>()
</script>

<style scoped>
.vp-timeline-item {
  position: relative;
  margin-bottom: 20px;
}
.vp-timeline-item__marker {
  position: absolute;
  left: -24px;
  top: 6px;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: var(--vp-brand, #0A84FF);
  border: 2px solid var(--vp-bg, #070B12);
  box-shadow: 0 0 0 2px rgba(10,132,255,0.3);
}
.vp-timeline-item__body { padding-bottom: 4px; }
.vp-timeline-item__meta {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}
.vp-timeline-item__date {
  font-size: 11px;
  font-weight: 600;
  color: var(--vp-text-4, #2D4060);
  font-family: 'JetBrains Mono', monospace;
}
.vp-timeline-item__tag {
  font-size: 10px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  padding: 1px 6px;
  border-radius: 4px;
  background: var(--vp-brand-soft, rgba(10,132,255,0.1));
  color: var(--vp-brand, #0A84FF);
  border: 1px solid rgba(10,132,255,0.25);
}
.vp-timeline-item__title {
  font-size: 14px;
  font-weight: 700;
  color: var(--vp-text-1, #F1F5F9);
  margin-bottom: 4px;
}
.vp-timeline-item__content {
  font-size: 13px;
  color: var(--vp-text-2, #8BA3C0);
  line-height: 1.65;
}
.vp-timeline-item__content :deep(p) { margin: 0; }
.vp-timeline-item__content :deep(p + p) { margin-top: 6px; }
</style>
