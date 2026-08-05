/**
 * SceneFab v3.0 · 根路由 (M3.2 · 接 AppShell)
 *
 * 整个应用统一布局:AppShell 已经包含 TopBar + Sidebar + 自带 Outlet。
 */

import {
  HeadContent,
  Link,
  createRootRouteWithContext,
} from "@tanstack/react-router";
import type { QueryClient } from "@tanstack/react-query";
import { AppShell } from "@components/layout/AppShell";

interface RouterContext {
  queryClient: QueryClient;
}

export const Route = createRootRouteWithContext<RouterContext>()({
  component: RootLayout,
  notFoundComponent: () => (
    <div className="flex min-h-screen items-center justify-center bg-zinc-950 text-zinc-100">
      <div className="space-y-3 text-center">
        <h1 className="bg-gradient-to-br from-blue-400 to-fuchsia-500 bg-clip-text text-5xl font-black text-transparent">
          404
        </h1>
        <p className="text-zinc-400">页面不存在 · Page not found</p>
        <Link to="/" className="text-blue-400 hover:underline">
          返回首页
        </Link>
      </div>
    </div>
  ),
});

function RootLayout() {
  return (
    <>
      <HeadContent />
      <AppShell />
    </>
  );
}
