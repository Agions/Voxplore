<template>
  <DefaultTheme.Layout>
    <template #home-hero-after>
      <div class="vp-proof-bar">
        <span class="vp-proof-item">
          <svg class="vp-proof-dot" viewBox="0 0 8 8"><circle cx="4" cy="4" r="3.5" fill="#10B981"/></svg>
          第一人称脚本
        </span>
        <span class="vp-proof-sep">·</span>
        <span class="vp-proof-item">
          <svg class="vp-proof-dot" viewBox="0 0 8 8"><circle cx="4" cy="4" r="3.5" fill="#0A84FF"/></svg>
          短剧内容标签
        </span>
        <span class="vp-proof-sep">·</span>
        <span class="vp-proof-item">
          <svg class="vp-proof-dot" viewBox="0 0 8 8"><circle cx="4" cy="4" r="3.5" fill="#8B5CF6"/></svg>
          配音字幕对齐
        </span>
        <span class="vp-proof-sep">·</span>
        <span class="vp-proof-item">
          <svg class="vp-proof-dot" viewBox="0 0 8 8"><circle cx="4" cy="4" r="3.5" fill="#F59E0B"/></svg>
          1080x1920 竖屏
        </span>
        <span class="vp-proof-sep">·</span>
        <span class="vp-proof-item">
          <svg class="vp-proof-dot" viewBox="0 0 8 8"><circle cx="4" cy="4" r="3.5" fill="#EF4444"/></svg>
          本地处理
        </span>
      </div>
    </template>
  </DefaultTheme.Layout>
</template>

<script setup lang="ts">
import DefaultTheme from 'vitepress/theme'
</script>
