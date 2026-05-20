---
title: 5 分钟快速开始
description: 最快 5 分钟上手 Voxplore，开始你的 AI 视频解说创作。
---

# 5 分钟快速开始

本指南帮助你最快的体验 Voxplore。

## 环境要求

| 项目 | 要求 |
|------|------|
| 操作系统 | Windows 10+ / macOS 12+ / Ubuntu 20.04+ |
| 内存 | ≥ 8 GB（推荐 16 GB） |
| 显存 | ≥ 4 GB（用于 Qwen2.5-VL OCR） |
| 磁盘 | ≥ 5 GB 可用空间 |

## 安装方式

:::code-group

```bash [Homebrew (macOS/Linux)]
brew install voxplore
voxplore
```

```bash [pip]
pip install voxplore
voxplore
```

```bash [源码]
git clone https://github.com/Agions/Voxplore.git
cd Voxplore
pip install -e .
voxplore
```

:::

## 配置 API Key

Voxplore 需要以下 API Key：

| 服务 | 用途 | 必填 | 费用 |
|------|------|------|------|
| DeepSeek | 解说稿生成 | ✅ | ~¥7/月 |
| Qwen VL | 视频帧分析 | ✅ | ¥0.1/千次 |
| Edge TTS | 配音生成 | ✅ | 免费 |

> 💡 **提示**：处理一个 5 分钟视频，DeepSeek 成本约 **0.3 分钱**。

### 获取 DeepSeek API Key

1. 访问 [platform.deepseek.com](https://platform.deepseek.com)
2. 注册/登录后进入 **API Keys** 页面
3. 点击 **Create API Key**
4. 复制 Key 并填入 Voxplore 设置页

### 配置方式

启动 Voxplore 后，进入 **设置 → AI 服务**，填入对应 Key。

## 创建第一个项目

```
1. 启动 Voxplore
2. 点击「新建项目」
3. 选择包含视频的文件夹
4. 等待 AI 分析完成（约 2-5 分钟）
5. 选择解说风格
6. 点击「生成解说」
7. 导出 MP4 或剪映草稿
```

## 快速配置

在项目根目录创建 `.env` 文件（可选）：

```bash
DEEPSEEK_API_KEY=your_key_here
QWEN_API_KEY=your_key_here
```

## 下一步

- [完整安装指南 →](/guide/installation)
- [配置 AI Key →](/guide/ai-configuration)
- [功能介绍 →](/features)
