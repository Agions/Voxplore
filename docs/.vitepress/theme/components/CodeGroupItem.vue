<template>
  <div v-show="active"><slot /></div>
</template>

<script setup lang="ts">
defineProps<{ title?: string; active?: boolean }>()
</script>
