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
      { text: "CLI 参考", link: "/guide/cli-reference" },
      { text: "Python API", link: "/guide/python-api" },
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
  title: "SceneFab",
  description:
    "SceneFab 第一人称影视/短剧解说生产文档，覆盖素材、脚本、配音、字幕、导出和发布复盘。",
  base: "/scene-fab/",
  lang: "zh-CN",
  cleanUrls: false,
  // 死链作为构建错误（此前被 true 掩盖）。新增页面/链接若拼错会在 CI 暴露。
  ignoreDeadLinks: false,
  lastUpdated: true,

  head: [
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
          "短剧解说,第一人称解说,影视解说,AI脚本,自动配音,AI字幕,竖屏导出,SceneFab",
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
        content: "SceneFab 文档中心 — 第一人称影视解说生产流程",
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
        content: "https://agions.github.io/scene-fab/og-image.png",
      },
    ],
    [
      "meta",
      { property: "og:url", content: "https://agions.github.io/scene-fab/" },
    ],
    ["meta", { property: "og:site_name", content: "SceneFab" }],

    // Twitter / X
    ["meta", { name: "twitter:card", content: "summary_large_image" }],
    ["meta", { name: "twitter:title", content: "SceneFab 文档中心" }],
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
        content: "https://agions.github.io/scene-fab/og-image.png",
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
    // 升级到新品牌资产 (v2.4.0 重设计):
    //   - /logo.svg        → 新 logo-mark.svg (256², dark bg + cyan/violet gradient)
    //   - /logo-horizontal.svg → 新横版 logo (README/docs 头部)
    //   - /favicon.svg     → 浏览器标签 (32²)
    //
    // VitePress logo 字段类型 ThemeableImage,支持:
    //   string | { src, alt } | { light, dark, alt }
    // 用第三种 { light, dark } 平铺结构 (不是 { src: { light, dark } }!),
    // 让 logo 随主题自动切换 (用户切到 light 模式不会出现黑底白字问题)。
    logo: {
      dark: "/logo.svg",
      light: "/logo-light.svg",
      alt: "SceneFab",
    },
    siteTitle: "SceneFab",
    appearance: "dark",

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
        placeholder: "搜索文档...",
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
          { text: "CLI 参考", link: "/guide/cli-reference" },
          { text: "Python API", link: "/guide/python-api" },
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
      {
        text: "重构档案",
        items: [
          { text: "总览与 ADR", link: "/refactor/00-overview" },
          { text: "架构审计", link: "/refactor/01-architecture-audit" },
          { text: "多文件上传方案", link: "/refactor/02-multi-video-upload" },
          {
            text: "第一人称解说规范",
            link: "/refactor/03-first-person-narration",
          },
          { text: "代码精简", link: "/refactor/04-code-cleanup" },
          { text: "过时内容清理", link: "/refactor/05-legacy-removal" },
          { text: "文档清理", link: "/refactor/06-doc-cleanup" },
          { text: "UI 重设计", link: "/refactor/07-ui-redesign" },
          { text: "实施路线图", link: "/refactor/08-implementation-roadmap" },
          { text: "风险矩阵", link: "/refactor/09-risk-matrix" },
        ],
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
      message: "SceneFab 文档中心 · 面向影视/短剧第一人称解说生产",
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
    hostname: "https://agions.github.io/scene-fab/",
    lastmodDateOnly: true,
  },
});
