/**
 * Vynaro v1.0.0 · App 根组件 (Gate 0)
 *
 * 阶段：M0 Gate 0 (最小可启动骨架) + TanStack Router 6 路由占位
 * 下一步 (M2)：
 *   - 拆分 LayoutShell (TopBar / Sidebar / StatusBar)
 *   - 接入 QueryClientProvider 全局数据层
 *   - 接入 ThemeProvider + i18n Provider
 */

import { RouterProvider, createRouter } from "@tanstack/react-router";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { routeTree } from "./routes/-routeTree.gen";

// ── TanStack Query 客户端（Gate 0 占位，无缓存策略）───────────────────
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000, // 30s 占位
      retry: 1,
    },
  },
});

// ── TanStack Router 实例 ────────────────────────────────────────────
const router = createRouter({
  routeTree,
  context: { queryClient },
  defaultPreload: "intent",
});

declare module "@tanstack/react-router" {
  interface Register {
    router: typeof router;
  }
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>
  );
}
