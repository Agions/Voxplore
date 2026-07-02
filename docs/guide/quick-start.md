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
# 应输出：ffmpeg version 6.x ...
```

如果 FFmpeg 未安装：
- **macOS**：`brew install ffmpeg`
- **Ubuntu/Debian**：`sudo apt install ffmpeg`
- **Windows**：通过 winget 或 [ffmpeg.org](https://ffmpeg.org) 下载

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

### 可选：环境变量方式

在项目根目录创建 `.env` 文件：

```bash
DEEPSEEK_API_KEY=sk-your-deepseek-key
QWEN_API_KEY=sk-your-qwen-key
```

## 第三步：运行

启动 SceneFab：

```bash
scenefab
```

验证安装：

```bash
scenefab --version
# 应输出：scene-fab v2.2.3
```

### 常见卡点

| 问题 | 解决 |
|------|------|
| `No module named 'scenefab'` | 确认使用 `pip install scenefab`，而非 `python -m pip` |
| `ffmpeg not found` | 安装 FFmpeg 后重启终端 |
| GUI 启动失败 | 安装 PySide6：`pip install PySide6`，或使用命令行模式 |
| API Key 无效 | 检查 `config/llm.yaml` 中的 Key 是否正确，无多余空格 |

## 验证成功

运行以下命令确认一切正常：

```bash
# 1. 检查版本
scenefab --version

# 2. 检查配置
cat config/llm.yaml

# 3. 检查 FFmpeg
ffmpeg -version | head -1
```

## 下一步

- [安装指南](/guide/installation) — 各平台完整安装步骤
- [AI 配置](/guide/ai-configuration) — 多服务商配置详解
- [界面介绍](/guide/interface) — 了解桌面界面