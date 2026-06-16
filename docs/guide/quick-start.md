---
title: 5 分钟快速开始
description: 最快 5 分钟上手 SceneFab，开始你的 AI 影视解说创作。
---

# 5 分钟快速开始

## 环境要求

| 项目 | 要求 |
|------|------|
| 操作系统 | Windows 10+ / macOS 12+ / Ubuntu 20.04+ |
| 内存 | ≥ 8 GB（推荐 16 GB） |
| 显存 | ≥ 4 GB（用于视觉理解加速，无则自动用 CPU） |
| 磁盘 | ≥ 5 GB 可用空间 |

## 安装

::: code-group

```bash [Homebrew (macOS/Linux)]
brew install scenefab
scenefab
```

```bash [pip]
pip install scenefab
scenefab
```

:::

## 配置 API Key

SceneFab 需要以下 API Key：

| 服务 | 用途 | 费用 |
|------|------|------|
| DeepSeek | 解说稿生成 | ~¥0.1/百万 tokens |
| Qwen VL | 视频帧语义分析 | ¥0.1/千次 |
| Edge TTS | 配音生成 | 免费 |

> 处理一部 2 小时电影解说，成本不足 **1 元**。

### 获取 API Key

**DeepSeek**：
1. 访问 [platform.deepseek.com](https://platform.deepseek.com) → API Keys → Create
2. 复制 Key 并填入 SceneFab 设置页

**阿里云百炼（Qwen VL）**：
1. 访问 [bailian.console.aliyun.com](https://bailian.console.aliyun.com) → API Keys → 创建
2. 选择 `qwen-vl-max` 模型

### 环境变量配置

```bash
DEEPSEEK_API_KEY=sk-xxx...xxxx
DASHSCOPE_API_KEY=sk-xxx...xxxx
TTS_ENGINE=edge-tts
DEFAULT_EMOTION=heal
```

## 快速验证

```bash
scenefab --version
# 输出: scenefab 2.2.0
```

## 下一步

- [完整安装指南](./installation) — 各平台详细步骤
- [配置 API Key](./ai-configuration) — DeepSeek / Qwen VL 详细配置
- [AI 工作流详解](./ai-video-guide) — 深入理解 AI 处理流程
