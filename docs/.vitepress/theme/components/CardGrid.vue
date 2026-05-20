<template>
  <div class="vp-card-grid" :style="`--cols: ${columns}`">
    <slot />
  </div>
</template>

<script setup lang="ts">
defineProps<{ columns?: number }>()
</script>

<style scoped>
.vp-card-grid {
  display: grid;
  grid-template-columns: repeat(var(--cols, 3), 1fr);
  gap: 16px;
}
@media (max-width: 768px) {
  .vp-card-grid { grid-template-columns: repeat(2, 1fr); }
}
@media (max-width: 480px) {
  .vp-card-grid { grid-template-columns: 1fr; }
}
</style>
