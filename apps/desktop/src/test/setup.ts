/**
 * vitest 共享 setup — 全局注册 @testing-library/jest-dom matchers
 * (toBeInTheDocument / toHaveClass / toHaveAccessibleName 等)
 */
import "@testing-library/jest-dom/vitest";

// jsdom 不实现的浏览器 API 兜底 (Tauri convertFileSrc / sonner toast 不会触发,但保险起见)
if (typeof window !== "undefined" && !window.matchMedia) {
  window.matchMedia = () => ({
    matches: false,
    media: "",
    onchange: null,
    addListener: () => {},
    removeListener: () => {},
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => false,
  });
}
