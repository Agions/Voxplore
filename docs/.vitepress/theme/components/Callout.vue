<template>
  <div class="vp-callout" :class="`vp-callout--${type}`">
    <div class="vp-callout__header">
      <span class="vp-callout__icon">{{ icons[type] }}</span>
      <span class="vp-callout__title">{{ title || defaultTitles[type] }}</span>
    </div>
    <div class="vp-callout__body">
      <slot />
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  type?:  'info' | 'tip' | 'warning' | 'danger' | 'success'
  title?: string
}>()

const icons: Record<string, string> = {
  info:    'ℹ️',
  tip:     '💡',
  warning: '⚠️',
  danger:  '🚨',
  success: '✅',
}

const defaultTitles: Record<string, string> = {
  info:    '信息',
  tip:     '提示',
  warning: '注意',
  danger:  '危险',
  success: '成功',
}
</script>

<style scoped>
.vp-callout {
  border-radius: 12px;
  border: 1px solid;
  padding: 16px 20px;
  margin: 20px 0;
}
.vp-callout__header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}
.vp-callout__icon { font-size: 1rem; }
.vp-callout__title {
  font-size: 12px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.06em;
}
.vp-callout__body {
  font-size: 13.5px;
  line-height: 1.7;
}
.vp-callout__body :deep(p) { margin: 0; }
.vp-callout__body :deep(p + p) { margin-top: 8px; }

.vp-callout--info    { background: rgba(99,102,241,0.08); border-color: rgba(99,102,241,0.3); }
.vp-callout--tip     { background: rgba(16,185,129,0.08); border-color: rgba(16,185,129,0.3); }
.vp-callout--success { background: rgba(16,185,129,0.08); border-color: rgba(16,185,129,0.3); }
.vp-callout--warning { background: rgba(245,158,11,0.08); border-color: rgba(245,158,11,0.3); }
.vp-callout--danger  { background: rgba(239,68,68,0.08);  border-color: rgba(239,68,68,0.3); }

.vp-callout--info    .vp-callout__title { color: #6366F1; }
.vp-callout--tip     .vp-callout__title { color: #10B981; }
.vp-callout--success .vp-callout__title { color: #10B981; }
.vp-callout--warning .vp-callout__title { color: #F59E0B; }
.vp-callout--danger  .vp-callout__title { color: #EF4444; }

.vp-callout--info    .vp-callout__body { color: var(--vp-text-2, #8BA3C0); }
.vp-callout--tip     .vp-callout__body { color: var(--vp-text-2, #8BA3C0); }
.vp-callout--success .vp-callout__body { color: var(--vp-text-2, #8BA3C0); }
.vp-callout--warning .vp-callout__body { color: var(--vp-text-2, #8BA3C0); }
.vp-callout--danger  .vp-callout__body { color: var(--vp-text-2, #8BA3C0); }
</style>
