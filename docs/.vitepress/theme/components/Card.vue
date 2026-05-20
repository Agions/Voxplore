<template>
  <div class="vp-card" :class="{ 'vp-card--clickable': clickable }">
    <div v-if="icon || title" class="vp-card__header">
      <span v-if="icon" class="vp-card__icon">{{ icon }}</span>
      <span v-if="title" class="vp-card__title">{{ title }}</span>
      <slot name="action" />
    </div>
    <div class="vp-card__body">
      <slot />
    </div>
    <div v-if="$slots.footer" class="vp-card__footer">
      <slot name="footer" />
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  title?: string
  icon?:  string
  clickable?: boolean
}>()
</script>

<style scoped>
.vp-card {
  background: var(--vp-bg-soft, #0D1525);
  border: 1px solid var(--vp-border, #1A2540);
  border-radius: 12px;
  padding: 20px;
  transition: border-color 0.2s, transform 0.2s;
}
.vp-card--clickable {
  cursor: pointer;
}
.vp-card--clickable:hover {
  border-color: rgba(10,132,255,0.4);
  transform: translateY(-2px);
}
.vp-card__header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
}
.vp-card__icon {
  font-size: 1.4rem;
}
.vp-card__title {
  font-size: 14px;
  font-weight: 700;
  color: var(--vp-text-1, #F1F5F9);
  letter-spacing: -0.01em;
}
.vp-card__body {
  font-size: 13px;
  color: var(--vp-text-2, #8BA3C0);
  line-height: 1.65;
}
.vp-card__footer {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid var(--vp-border, #1A2540);
  font-size: 12px;
  color: var(--vp-text-3, #4A6080);
}
</style>
