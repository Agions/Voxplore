# SceneFab v2.4 (Python) · DEPRECATED

> **状态**：⚠️ **DEPRECATED** — 自 v3.0 起冻结
> **上一稳定版本**：[v2.4.3](../../../../) (Python 3.10+ / PySide6 6.9 / FFmpeg 6.x)
> **对应 React/Rust 主线**：[README.md](./README.md)
> **迁移方案**：[docs/refactor/v3-migration/00-overview.md](../../docs/refactor/v3-migration/00-overview.md)

## 历史背景

SceneFab v2.x 是一个 Python + PySide6 (Qt) + FastAPI + Edge-TTS + 多 LLM Provider
的统一桌面应用。完整功能包括：

- 5 步流水线（导入 → 拆分 → 脚本 → 配音字幕 → 导出）
- 11 个 LLM Provider（OpenAI/Qwen/Kimi/GLM/DeepSeek/Doubao/Hunyuan/Claude/Gemini/Qwen3.7/Local）
- 4 种多视频策略（single/concat/batch/series）
- Edge-TTS、OpenAI-TTS、GPT-SoVITS 三种配音引擎
- FFmpeg 6.x 视频处理
- 6 段核心 UI（首页/制作/项目管理/设置/更新/帮助）
- pyproject.toml / uv 包管理 + pytest / pytest-qt 测试套件

## 冻结原因

| 维度        | v2.4 (Python)                                | v3.0 (Rust + React)                |
| ----------- | -------------------------------------------- | ---------------------------------- |
| 安装包体积  | ~80 MB (PyInstaller)                         | **< 8 MB** (Tauri 2.0)             |
| 冷启动时间  | ~1.5 s                                       | **< 500 ms**                       |
| 内存占用    | ~280 MB                                      | **< 90 MB**                        |
| 部署复杂度  | Python 解释器 + 系统 Qt + FFmpeg 链路长       | **单可执行二进制 + bundled webview** |
| 跨平台一致性 | macOS/Windows/Linux 行为偶发偏离             | **Tauri 提供统一 webview 抽象**     |

> 详细对比与决策依据：[01-architecture-audit.md](../../docs/refactor/v3-migration/01-architecture-audit.md)
> · [02-target-architecture.md](../../docs/refactor/v3-migration/02-target-architecture.md)

## 当前维护政策

- ⛔ **不再添加新功能**
- 🐛 **M10 之前**（v3.0 GA）：仅修关键阻塞性 bug（与 v3.0 并行存在）
- 🧊 **M10 之后**（v3.0 GA）：完全只读
- 🗑️ **v3.2 计划**：从仓库中彻底删除 `src/app/`、`tests/{services,ui,...}`、`docs_bundle/` 等
  Python 主线残留（参见 [08-implementation-roadmap.md §10.8](../../docs/refactor/v3-migration/08-implementation-roadmap.md)）

## 历史归档

| 文件/目录                  | 状态     | 用途                                     |
| -------------------------- | -------- | ---------------------------------------- |
| `README_v3_legacy_bk.md`   | ✅ 归档  | v2.4 主线 README 完整备份（已保留）       |
| `pyproject.toml.legacy`    | ✅ 归档  | v2.4 Python 项目配置（备份）              |
| `src/app/`                 | 🗑️ 待删 | v2.4 桌面应用代码（257 文件）            |
| `tests/{services,ui,...}/` | 🗑️ 待删 | v2.4 测试套件（pytest + pytest-qt）       |
| `docs_bundle/`             | 🗑️ 待删 | v2.4 用户文档构建中间产物                |

---

**本文件**：v3.0 迁移方案的"v2.4 主线退役"签字存档。M0 启动后由 RA+TL 共同维护。
