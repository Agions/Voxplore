---
title: 快速开始
description: 3 步上手 SceneFab，开始 AI 影视解说创作。
---

# 快速开始

3 步完成安装、配置和首次运行。

## 第一步：安装

安装 SceneFab 并确认 FFmpeg 可用：

```bash
pip install scenefab
```

验证 FFmpeg：

```bash
ffmpeg -version
```

如果 FFmpeg 未安装，macOS 使用 `brew install ffmpeg`，Ubuntu 使用 `sudo apt install ffmpeg`。

## 第二步：配置

编辑 `config/llm.yaml`，填入至少一个 API Key：

```yaml
LLM:
  default_provider: "qwen"

  qwen:
    enabled: true
    api_key: "sk-your-qwen-key"
    model: "qwen3.7-max"

  deepseek:
    enabled: true
    api_key: "sk-your-deepseek-key"
    model: "deepseek-v4-pro"
```

API Key 获取方式：

- **Qwen (阿里云百炼)** — [bailian.console.aliyun.com](https://bailian.console.aliyun.com)
- **DeepSeek** — [platform.deepseek.com](https://platform.deepseek.com)

## 第三步：运行

启动 SceneFab：

```bash
scenefab
```

验证安装：

```bash
scenefab --version
```

## 下一步

- [安装指南](/guide/installation) — 各平台完整安装步骤
- [AI 配置](/guide/ai-configuration) — 多服务商配置详解
