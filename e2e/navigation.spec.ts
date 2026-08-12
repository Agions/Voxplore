import { expect, test } from "@playwright/test";

test.describe("Monoloop 页面导航", () => {
  test("首页可以加载并显示应用壳层", async ({ page }) => {
    await page.goto("/");
    await expect(page).toHaveTitle(/Monoloop/i);
    await expect(page.getByRole("navigation")).toBeVisible();
  });

  test("帮助页显示快捷键面板", async ({ page }) => {
    // M4.5 重写后:
    // - 帮助页用 help_topics IPC 拉取主题(需 Tauri 后端,e2e 无后端 → 列表为空)
    // - SHORTCUTS 静态面板始终可见 → 验证快捷键 heading
    // - 文档资源 / 快速上手 → 改由 IPC 动态渲染,e2e 跳过
    await page.goto("/help");
    await expect(page.getByRole("heading", { name: "帮助" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "快捷键" })).toBeVisible();
    await expect(page.getByText("命令面板")).toBeVisible();
  });

  test("侧边栏可以导航到设置页", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("link", { name: /设置/ }).click();
    await expect(page).toHaveURL(/\/settings$/);
    await expect(page.getByRole("heading", { name: "设置" })).toBeVisible();
  });

  test("未知路径显示 404 页面", async ({ page }) => {
    await page.goto("/not-found-e2e");
    await expect(page.getByText("页面不存在")).toBeVisible();
    await expect(page.getByRole("link", { name: "返回首页" })).toBeVisible();
  });
});
