// defineConfig 从 vitest/config 导入:带 test 字段扩展的 UserConfig (vite 原生类型不含 test)
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import { tanstackRouter } from "@tanstack/router-vite-plugin";
import tailwindcss from "@tailwindcss/vite";
import path from "node:path";
import process from "node:process";

// __dirname 在 ESM 下不可用,改用 import.meta.dirname (Node 20.11+)
const host = process.env.TAURI_DEV_HOST;
const root = import.meta.dirname;

// apps/desktop 平铺结构: 前端代码位于 src/, 与 src-tauri/ 同级共置
export default defineConfig({
  test: {
    globals: true,
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
    include: ["src/**/*.test.{ts,tsx}", "src/**/*.spec.{ts,tsx}"],
    exclude: ["node_modules", "dist", "src-tauri", ".tanstack"],
    css: false,
  },

  plugins: [
    // TanStack Router 必须在 React 之前 (v1.168+ 新约束)
    tanstackRouter({
      routesDirectory: "./src/routes",
      generatedRouteTree: "./src/routes/-routeTree.gen.ts",
      autoCodeSplitting: true,
    }),
    react(),
    tailwindcss(),
  ],

  resolve: {
    alias: {
      "@": path.resolve(root, "./src"),
      "@ui": path.resolve(root, "./src/components/ui"),
      "@components": path.resolve(root, "./src/components"),
      "@hooks": path.resolve(root, "./src/hooks"),
      "@stores": path.resolve(root, "./src/stores"),
      "@ipc": path.resolve(root, "./src/ipc"),
      "@lib": path.resolve(root, "./src/lib"),
      "@pages": path.resolve(root, "./src/pages"),
      "@styles": path.resolve(root, "./src/styles"),
      "@workers": path.resolve(root, "./src/workers"),
    },
  },

  clearScreen: false,
  server: {
    port: 1420,
    strictPort: true,
    host: host || false,
    hmr: host ? { protocol: "ws", host, port: 1421 } : undefined,
    watch: {
      ignored: [
        "**/src-tauri/**",
        "**/src/app.legacy/**",
        "**/tests.legacy/**",
      ],
    },
  },

  envPrefix: ["VITE_", "TAURI_"],

  build: {
    target: ["es2022", "chrome105", "safari14"],
    minify: process.env.TAURI_DEBUG ? false : "esbuild",
    sourcemap: !!process.env.TAURI_DEBUG,
    rollupOptions: {
      output: {
        manualChunks: {
          "react-vendor": ["react", "react-dom"],
          tanstack: ["@tanstack/react-query", "@tanstack/react-router"],
          i18n: ["i18next", "react-i18next"],
        },
      },
    },
  },

  optimizeDeps: {
    exclude: ["@tauri-apps/api"],
  },
});
