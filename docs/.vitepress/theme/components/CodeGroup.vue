<template>
  <div class="vp-code-group">
    <div class="vp-code-group__header">
      <button
        v-for="(tab, i) in tabs"
        :key="i"
        class="vp-code-group__tab"
        :class="{ active: i === active }"
        @click="active = i"
      >
        {{ tab }}
      </button>
    </div>
    <div class="vp-code-group__body">
      <slot :active="active" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, useSlots } from 'vue'
const slots = useSlots()
const tabs = ref<string[]>(
  slots.default?.()
    .flatMap(n => n.children)
    .filter(Boolean)
    .map((c: any) => c.props?.title || c.props?.label || 'Tab')
    .slice(0, 10) || []
)
const active = ref(0)
</script>

<style scoped>
.vp-code-group {
  margin: 20px 0;
  border: 1px solid var(--vp-border, #1A2540);
  border-radius: 12px;
  overflow: hidden;
}
.vp-code-group__header {
  display: flex;
  background: var(--vp-bg-elevated, #111827);
  border-bottom: 1px solid var(--vp-border, #1A2540);
  overflow-x: auto;
}
.vp-code-group__tab {
  padding: 10px 18px;
  font-size: 12.5px;
  font-weight: 500;
  color: var(--vp-text-3, #4A6080);
  background: transparent;
  border: none;
  cursor: pointer;
  white-space: nowrap;
  transition: color 0.15s, background 0.15s;
  border-bottom: 2px solid transparent;
  font-family: inherit;
}
.vp-code-group__tab:hover { color: var(--vp-text-2, #8BA3C0); }
.vp-code-group__tab.active {
  color: var(--vp-brand, #0A84FF);
  border-bottom-color: var(--vp-brand, #0A84FF);
  background: var(--vp-bg-soft, #0D1525);
}
.vp-code-group__body :deep(div[class*='language-']) {
  border-radius: 0 !important;
  border: none !important;
  margin: 0 !important;
}
</style>
