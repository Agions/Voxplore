import { defineConfig } from "vitepress";

// 单一来源 sidebar：全站统一五大分类，nav 与之一一对应，避免重复与漂移。
const SIDEBAR = [
  {
    text: "开始使用",
    collapsed: false,
    items: [
      { text: "快速开始", link: "/guide/quick-start" },
      { text: "安装指南", link: "/guide/installation" },
      { text: "AI 配置", link: "/guide/ai-configuration" },
      { text: "界面说明", link: "/guide/interface" },
    ],
  },
  {
    text: "生产流程",
    collapsed: false,
    items: [
      { text: "第一人称生产规范", link: "/guide/narration-spec" },
      { text: "AI 工作流详解", link: "/guide/ai-video-guide" },
      { text: "导出发布", link: "/guide/exporting" },
    ],
  },
  {
    text: "帮助",
    collapsed: false,
    items: [{ text: "疑难排查", link: "/guide/troubleshooting" }],
  },
];

export default defineConfig({
  title: "Monoloop",
  description:
    "Monoloop 第一人称影视/短剧解说生产文档，覆盖素材、脚本、配音、字幕、导出和发布复盘。",
  base: "/monoloop/",
  lang: "zh-CN",
  cleanUrls: false,
  // 默认深色主题，保留手动切换。
  appearance: "dark",
  // 死链作为构建错误（此前被 true 掩盖）。新增页面/链接若拼错会在 CI 暴露。
  ignoreDeadLinks: false,
  lastUpdated: true,

  head: [
    // Google Fonts: Outfit, Inter, JetBrains Mono
    ["link", { rel: "preconnect", href: "https://fonts.googleapis.com" }],
    ["link", { rel: "preconnect", href: "https://fonts.gstatic.com", crossorigin: "" }],
    [
      "link",
      {
        rel: "stylesheet",
        href: "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&family=Outfit:wght@500;600;700;800;900&display=swap",
      },
    ],

    // Favicon (新品牌: SVG 主, PNG 备)
    ["link", { rel: "icon", type: "image/svg+xml", href: "/favicon.svg" }],
    [
      "link",
      { rel: "alternate icon", type: "image/png", href: "/favicon.png" },
    ],

    // SEO
    [
      "meta",
      {
        name: "keywords",
        content:
          "短剧解说,第一人称解说,影视解说,AI脚本,自动配音,AI字幕,竖屏导出,Monoloop",
      },
    ],
    ["meta", { name: "author", content: "Agions" }],
    ["meta", { name: "robots", content: "index, follow" }],

    // Open Graph
    ["meta", { property: "og:type", content: "website" }],
    [
      "meta",
      {
        property: "og:title",
        content: "Monoloop 文档中心 — 第一人称影视解说生产流程",
      },
    ],
    [
      "meta",
      {
        property: "og:description",
        content:
          "面向短剧和影视解说团队的标准化生产文档：素材、脚本、配音、字幕、导出和发布复盘。",
      },
    ],
    [
      "meta",
      {
        property: "og:image",
        content: "https://agions.github.io/monoloop/og-image.png",
      },
    ],
    [
      "meta",
      { property: "og:url", content: "https://agions.github.io/monoloop/" },
    ],
    ["meta", { property: "og:site_name", content: "Monoloop" }],

    // Twitter / X
    ["meta", { name: "twitter:card", content: "summary_large_image" }],
    ["meta", { name: "twitter:title", content: "Monoloop 文档中心" }],
    [
      "meta",
      {
        name: "twitter:description",
        content: "第一人称影视/短剧解说标准化生产流程。",
      },
    ],
    [
      "meta",
      {
        name: "twitter:image",
        content: "https://agions.github.io/monoloop/og-image.png",
      },
    ],

    // Theme
    ["meta", { name: "theme-color", content: "#111210" }],
    ["meta", { name: "color-scheme", content: "dark" }],
  ],

  markdown: {
    lineNumbers: false,
    theme: {
      light: "github-light",
      dark: "github-dark",
    },
    container: {
      tipLabel: "💡 提示",
      warningLabel: "⚠️ 注意",
      dangerLabel: "🚨 危险",
      infoLabel: "ℹ️ 信息",
      detailsLabel: "详情",
    },
  },

  themeConfig: {
    // ── Logo & Site Title ──────────────────────────────────
    // VitePress logo 字段类型 ThemeableImage，用 { light, dark } 平铺结构，
    // 让 logo 随主题自动切换。
    logo: {
      dark: "/logo.svg",
      light: "/logo-light.svg",
      alt: "Monoloop",
    },
    siteTitle: "Monoloop",

    // ── Last Updated ────────────────────────────────────────
    lastUpdated: {
      text: "最后更新",
      formatOptions: {
        dateStyle: "medium",
        timeStyle: "short",
      },
    },

    // ── Search ──────────────────────────────────────────────
    search: {
      provider: "local",
      options: {
        translations: {
          button: {
            buttonText: "搜索",
            buttonAriaLabel: "搜索文档",
          },
          modal: {
            noResultsText: "未找到结果",
            resetButtonTitle: "清除搜索",
          },
        },
      },
    },

    // ── Navigation（与 sidebar 一一对应，5 个一级分类）────────
    nav: [
      { text: "首页", link: "/" },
      {
        text: "开始使用",
        items: [
          { text: "快速开始", link: "/guide/quick-start" },
          { text: "安装指南", link: "/guide/installation" },
          { text: "AI 配置", link: "/guide/ai-configuration" },
          { text: "界面说明", link: "/guide/interface" },
        ],
      },
      {
        text: "生产流程",
        items: [
          { text: "第一人称生产规范", link: "/guide/narration-spec" },
          { text: "AI 工作流详解", link: "/guide/ai-video-guide" },
          { text: "导出发布", link: "/guide/exporting" },
        ],
      },
      {
        text: "帮助",
        items: [{ text: "疑难排查", link: "/guide/troubleshooting" }],
      },
    ],

    // ── Sidebar（单一来源，五大分类全站统一）──────────────────
    sidebar: SIDEBAR,

    // ── Table of Contents ──────────────────────────────────
    outline: {
      level: [2, 3],
      label: "目录",
    },

    // ── Doc Footer (prev/next) ──────────────────────────────
    docFooter: {
      prev: "上一篇",
      next: "下一篇",
    },

    // ── Footer ──────────────────────────────────────────────
    footer: {
      message: "Monoloop 文档中心 · 面向影视/短剧第一人称解说生产",
      copyright: "Copyright © 2025-2026 Agions · 隐私优先 · 本地处理",
    },

    // ── Return to Top ────────────────────────────────────────
    returnToTopLabel: "返回顶部",
    sidebarMenuLabel: "菜单",

    // ── Not Found (404) ────────────────────────────────────
    notFound: {
      title: "页面未找到",
      quote: "你来到了一片空白的领域。",
      linkText: "返回首页",
    },
  },

  // ── Sitemap ────────────────────────────────────────────────
  sitemap: {
    hostname: "https://agions.github.io/monoloop/",
    lastmodDateOnly: true,
  },
});
