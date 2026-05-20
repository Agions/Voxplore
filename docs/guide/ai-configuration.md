---
title: AI 配置指南
description: 配置 DeepSeek Qwen VL Edge TTS 等 AI 服务
---

# AI 配置指南

## 支持的 AI 服务

Voxplore 采用多模型协作架构，每个环节使用最适合的服务。

## DeepSeek（解说稿生成）

**必填** | 生成电影感第一人称解说稿

| 参数 | 值 |
|------|----|
| 模型 | `deepseek-chat` |
| 上下文 | 32K tokens |
| 成本 | ¥0.1 / 1M tokens（缓存后 ¥0.01） |

### 获取 API Key

1. 访问 [platform.deepseek.com/api_keys](https://platform.deepseek.com/api_keys)
2. 创建新 Key，设置限额
3. 妥善保存，勿泄露

### 费用估算

| 视频时长 | 解说字数 | 成本 |
|---------|---------|------|
| 5 分钟 | ~300 字 | ¥0.0003 |
| 30 分钟 | ~2000 字 | ¥0.002 |
| 60 分钟 | ~4000 字 | ¥0.004 |

## Qwen VL（视频帧分析）

**必填** | 逐帧分析判断第一人称视角

| 参数 | 值 |
|------|----|
| 模型 | `qwen-vl-plus` |
| 输入 | 视频关键帧截图 |
| 成本 | ¥0.05 / 次 |

### 配置方式

```bash
# .env 文件
QWEN_API_KEY=your_qwen_api_key
```

## Edge TTS（文字转语音）

**推荐** | 微软文字转语音，免费低延迟

```bash
# Edge TTS 自带，无需配置
# 可在设置中选择音色：
# - 女声：zh-CN-XiaoxiaoNeural
# - 男声：zh-CN-YunxiNeural
# - 其他角色音
```

## F5-TTS（音色克隆）

**可选** | 零样本音色克隆，需本地部署

```bash
# 安装
pip install f5-tts

# 在设置中启用
# 支持自定义音色参考音频
```

## 模型对比

| 配音方案 | 质量 | 延迟 | 成本 | 部署 |
|---------|------|------|------|------|
| Edge TTS | ⭐⭐⭐⭐ | <500ms | 免费 | 云端 |
| F5-TTS | ⭐⭐⭐⭐⭐ | 1-3s | 仅 GPU | 本地 |
| GPT-SoVITS | ⭐⭐⭐⭐⭐ | 2-5s | 仅 GPU | 本地 |

## 常见问题

:::warning
**API Key 泄露怎么办？**
立即在平台控制台删除该 Key，重新生成并替换。
:::

:::tip
**如何降低费用？**
- 开启 DeepSeek 上下文缓存（命中后降 90%）
- 减少视频分析采样帧数
- 使用 Edge TTS 代替 F5-TTS
:::
