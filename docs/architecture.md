---
title: 架构概览
description: Voxplore 系统架构和技术设计的核心要点速查。
---

# 架构概览

本文档帮助你快速理解 Voxplore 的核心系统架构。

---

## 系统架构

Voxplore 采用 **三层模块化架构**：

```
┌──────────────────────────────────────────────────────────────┐
│                         UI 层 (PySide6)                      │
│     主窗口 · 素材面板 · 预览区域 · 时间线面板 · 状态栏         │
├──────────────────────────────────────────────────────────────┤
│                        服务层 (Services)                      │
│   AI 服务 · 视频处理服务 · 音频服务 · 导出服务                 │
├──────────────────────────────────────────────────────────────┤
│                         核心层 (Core)                         │
│   配置管理 · 事件总线 · 依赖注入 · 安全密钥管理               │
├──────────────────────────────────────────────────────────────┤
│                        外部依赖层                              │
│        FFmpeg · OpenCV · Qwen2.5-VL · DeepSeek-V3 · Edge-TTS │
└──────────────────────────────────────────────────────────────┘
```

**设计原则**：UI 层与业务逻辑完全解耦，可以独立替换 UI 框架而不影响核心功能。

---

## 目录结构

```
Voxplore/
├── app/
│   ├── core/                    # 核心模块
│   │   ├── application.py       # 应用生命周期
│   │   ├── config_manager.py    # 配置管理（YAML + .env）
│   │   ├── event_bus.py        # 事件总线（发布/订阅，解耦通信）
│   │   ├── service_container.py # 依赖注入容器（按需懒加载）
│   │   └── secure_key_manager.py # API 密钥安全管理
│   │
│   ├── services/                # 业务服务层
│   │   ├── ai/                  # AI 服务
│   │   │   ├── providers/       # LLM 提供商抽象（OpenAI 兼容接口）
│   │   │   ├── llm_manager.py   # LLM 统一管理器
│   │   │   ├── scene_analyzer.py # Qwen2.5-VL 场景理解
│   │   │   ├── script_generator.py # DeepSeek-V3 解说生成
│   │   │   └── voice_generator.py  # Edge-TTS / F5-TTS 语音合成
│   │   ├── video/               # 视频处理服务
│   │   │   └── monologue_maker.py  # AI 第一人称解说制作（核心）
│   │   └── export/              # 导出服务
│   │       └── jianying_exporter.py  # 剪映草稿 JSON 导出
│   │
│   ├── plugins/                 # 插件系统（Plugin Manifest v1）
│   └── ui/                      # 界面层 (PySide6)
│       ├── main_window.py         # 主窗口
│       ├── panels/                # 面板组件
│       ├── widgets/               # 通用组件
│       └── pages/                # 页面组件
│
├── tests/                       # 测试（pytest + pytest-asyncio）
├── docs/                        # VitePress 文档
└── resources/                   # 静态资源
```

---

## 核心模块

### Application（应用生命周期）

| 组件 | 职责 |
|------|------|
| `ApplicationLauncher` | 命令行参数处理、早期初始化 |
| `Application` | 管理应用状态、服务容器、事件总线 |
| `ServiceContainer` | 依赖注入容器，按需懒加载服务 |
| `EventBus` | 模块间解耦通信（发布/订阅模式） |

### LLMManager（AI 统一管理器）

| 方法 | 说明 |
|------|------|
| `complete(prompt, model?)` | 文本补全 |
| `analyze_video(video_path)` | Qwen2.5-VL 视频内容分析 |
| `generate_script(context, emotion)` | DeepSeek-V3 生成解说文案 |

### SecureKeyManager（密钥安全）

```
API Key 存储优先级:
1. OS Keychain (macOS Keychain / Windows Credential Manager / Linux Secret Service)
2. 加密文件 (Fernet + PBKDF2)
```

---

## 视频处理流程

```
视频 → 场景检测（PySceneDetect）
      → AI 内容分析（Qwen2.5-VL）
      → 解说生成（DeepSeek-V3）
      → 配音合成（Edge-TTS / F5-TTS）
      → 字幕生成（ASS + TTS word-level timing）
      → 视频合成（FFmpeg）
      → 导出（MP4 / 剪映草稿 JSON）
```

| 步骤 | 核心技术 |
|------|----------|
| 场景检测 | PySceneDetect |
| 内容分析 | Qwen2.5-VL（阿里云百炼 API） |
| 文案生成 | DeepSeek-V3.2（API） |
| 语音合成 | Edge-TTS（本地）/ F5-TTS（本地） |
| 字幕生成 | TTS word-level timing → ASS 格式 |
| 视频合成 | FFmpeg（H.264 / H.265） |

---

## 插件系统

```
Plugin Interface (抽象基类)
       │
       ├── VideoProcessorPlugin
       ├── ExportPlugin
       ├── AIGeneratorPlugin
       └── UIExtensionPlugin
```

插件加载流程：

```
扫描 plugins/ 目录 → 验证 manifest.json → 实例化 → 注册服务
```

详见 [插件开发指南](./guide/plugin-development)。

---

## 技术栈

| 层级 | 技术选型 |
|------|----------|
| GUI 框架 | **PySide6** (LGPL) |
| 视频处理 | FFmpeg、opencv-python |
| AI 分析 | Qwen2.5-VL（阿里云百炼 API） |
| AI 文案 | DeepSeek-V3.2（API） |
| 语音合成 | Edge-TTS（本地）、F5-TTS（本地） |
| 加密 | cryptography (Fernet / AES-128) |
| 配置 | YAML、python-dotenv |
| 测试 | pytest、pytest-asyncio |

---

## 相关文档

- [安全设计](./security) — API 密钥安全和文件操作安全
- [插件开发指南](./guide/plugin-development) — 如何编写插件
- [AI 配置指南](./guide/ai-configuration) — AI 服务配置
