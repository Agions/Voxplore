/**
 * Vynaro VitePress Theme
 * 使用默认主题 + 自定义CSS
 */

import type { Theme } from 'vitepress'
import DefaultTheme from 'vitepress/theme'

// Custom Layout
import HomeLayout from './layouts/HomeLayout.vue'

// Styles
import './style.css'

export default {
  extends: DefaultTheme,
  Layout: HomeLayout,
} satisfies Theme
