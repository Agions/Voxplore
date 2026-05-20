<template>
  <div class="vp-timeline">
    <slot />
  </div>
</template>

<style scoped>
.vp-timeline {
  position: relative;
  padding-left: 28px;
}
.vp-timeline::before {
  content: '';
  position: absolute;
  left: 9px;
  top: 4px;
  bottom: 4px;
  width: 2px;
  background: var(--vp-border, #1A2540);
}
</style>
