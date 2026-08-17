/**
 * splicr VitePress Theme
 * Linear / Raycast 级顶奢暗黑主题 + 自定义 Vue 高奢组件库
 */

import type { Theme } from 'vitepress'
import DefaultTheme from 'vitepress/theme'

// Custom Layout
import HomeLayout from './layouts/HomeLayout.vue'

// Custom Components
import HeroAppShowcase from './components/HeroAppShowcase.vue'
import InteractivePipeline from './components/InteractivePipeline.vue'
import ModelMatrixCard from './components/ModelMatrixCard.vue'
import PlatformPresetSelector from './components/PlatformPresetSelector.vue'
import FeatureSpotlightGrid from './components/FeatureSpotlightGrid.vue'

// Styles
import './style.css'

export default {
  extends: DefaultTheme,
  Layout: HomeLayout,
  enhanceApp({ app }) {
    app.component('HeroAppShowcase', HeroAppShowcase)
    app.component('InteractivePipeline', InteractivePipeline)
    app.component('ModelMatrixCard', ModelMatrixCard)
    app.component('PlatformPresetSelector', PlatformPresetSelector)
    app.component('FeatureSpotlightGrid', FeatureSpotlightGrid)
  }
} satisfies Theme
