# ADR-001: PySide6 vs Electron 作为桌面端 GUI 框架

- **状态**: ✅ Accepted
- **日期**: 2026-06-04
- **作者**: 架构团队
- **关联版本**: v1.0.0 ~ v2.0.0

## 背景

SceneFab 作为 AI 影视解说创作工具，需要选择桌面端 GUI 框架。两个候选方案：

1. **PySide6**（Qt for Python）
2. **Electron**（Chromium + Node.js）

## 决策

采用 **PySide6** 作为 SceneFab 桌面端 GUI 框架。

## 权衡

| 维度 | PySide6 | Electron |
|------|:---:|:---:|
| **Python 生态集成** | ✅ 原生 | ⚠️ 需 IPC 桥接 |
| **本地文件 I/O 性能** | ✅ 同步 | ⚠️ 异步 Promise |
| **FFmpeg 进程调用** | ✅ subprocess | ⚠️ child_process |
| **启动时间** | ✅ ~1s | ⚠️ ~3-5s |
| **打包体积** | ✅ ~150MB | ⚠️ ~200MB+ |
| **视觉风格统一** | ✅ Qt Style Sheets | ✅ CSS |
| **跨平台** | ✅ Win/Mac/Linux | ✅ Win/Mac/Linux |
| **AI 模型本地运行** | ✅ 直接调用 Python | ❌ 需 Python sidecar |
| **开发迭代速度** | ⚠️ 需重启 | ✅ 热重载 |
| **社区生态** | ⚠️ 较小 | ✅ 巨大 |

## 关键理由

1. **核心业务是 Python 生态**：FFmpeg 进程、视频帧处理、LLM API 调用等全部在 Python 侧，使用 PySide6 避免 IPC 开销和序列化成本
2. **本地优先架构**：视频/音频/帧数据全部在本地处理，PySide6 与 OpenCV/NumPy/PyTorch 等本地库无缝集成
3. **打包优势**：PyInstaller + PySide6 单文件 ~150MB，Electron + Chromium ~200MB+
4. **FFmpeg 集成**：subprocess 同步调用更稳定，错误信息更易捕获

## 后果

- ✅ 享受 Python 生态的快速迭代
- ✅ FFmpeg/OpenCV/LLM 本地化零障碍
- ⚠️ UI 视觉风格需手动调 QSS（用 VitePress 文档站作参考）
- ⚠️ PySide6 学习曲线较陡（Signal/Slot、QThread、Model/View）

## 替代方案探索

- **Webview (pywebview)**: 保留 Python 后端 + Web 前端，但生态碎片化
- **Tauri (Rust + WebView)**: 体积更小但 Rust 生态不熟，且与 Python AI 库集成需 IPC

## 评审

- 决策已稳定 2+ 个大版本（v1.0.0 ~ v1.1.0），无回退计划
