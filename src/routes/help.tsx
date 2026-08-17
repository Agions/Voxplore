/**
 * splicr v1.0.0 · /help 路由入口
 *
 * 实际组件在 components/help/HelpPage.tsx,
 * 此处只导出 Route 供 TanStack Router 做 code-split。
 */

import { createFileRoute } from "@tanstack/react-router";
import { HelpPage } from "@components/help/HelpPage";

export const Route = createFileRoute("/help")({
  component: HelpPage,
});
