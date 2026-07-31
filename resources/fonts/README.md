# SceneFab 字体包目录 (Font Assets)

本目录用于存放 SceneFab 桌面客户端集成的苹果 macOS 原生视觉字体包：

- `SF-Pro-Text-Regular.otf` / `SF-Pro-Text-Bold.otf` (SF Pro Text 界面字体)
- `SF-Pro-Display-Regular.otf` / `SF-Pro-Display-Bold.otf` (SF Pro Display 标题字体)
- `PingFang-SC-Regular.ttf` / `PingFang-SC-Medium.ttf` (苹方中文标准字体)

> 应用启动时，`app.ui.theme.font_loader` 模块会自动通过 `QFontDatabase.addApplicationFont` 动态加载挂载本目录下的全部字体资源。在 macOS 原生系统上将自动优先映射系统内置的高清 SF Pro 与 PingFang SC 苹方字族。
