<template>
  <span class="vp-badge" :class="`vp-badge--${type}`">
    <slot />
  </span>
</template>

<script setup lang="ts">
defineProps<{
  type?: 'brand' | 'success' | 'warning' | 'danger' | 'info' | 'purple'
}>()
</script>

<style scoped>
.vp-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 10.5px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.07em;
  font-family: 'JetBrains Mono', monospace;
  border-radius: 4px;
  padding: 2px 8px;
  border: 1px solid;
  line-height: 1.6;
}
.vp-badge--brand  { color: #2196FF; background: rgba(10,132,255,0.1); border-color: rgba(10,132,255,0.3); }
.vp-badge--success{ color: #10B981; background: rgba(16,185,129,0.1);  border-color: rgba(16,185,129,0.3); }
.vp-badge--warning{ color: #F59E0B; background: rgba(245,158,11,0.1);  border-color: rgba(245,158,11,0.3); }
.vp-badge--danger { color: #EF4444; background: rgba(239,68,68,0.1);   border-color: rgba(239,68,68,0.3); }
.vp-badge--info   { color: #6366F1; background: rgba(99,102,241,0.1);  border-color: rgba(99,102,241,0.3); }
.vp-badge--purple { color: #A78BFA; background: rgba(139,92,246,0.1);  border-color: rgba(139,92,246,0.3); }
</style>
