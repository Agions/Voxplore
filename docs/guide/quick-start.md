---
title: 快速开始
description: 3 步上手 Vynaro，开始 AI 影视解说创作。
---

# 快速开始

3 步完成安装、配置和首次运行。

## 第一步：安装

从 [GitHub Releases](https://github.com/Agions/vynaro/releases) 下载对应平台的安装包：

| 平台    | 安装包                                                  |
| ------- | ------------------------------------------------------- |
| Windows | `.msi` 或 `.exe`                                        |
| macOS   | `.dmg`（首次打开需在「系统设置 → 隐私与安全性」中允许） |
| Linux   | `.AppImage` 或 `.deb`                                   |

安装完成后从开始菜单 / 启动台打开 **Vynaro**。

> 从源码运行开发版请见 [安装指南](/guide/installation)。

## 第二步：配置 AI 服务

打开应用内 **设置** 页面，填入至少一个 AI 服务商的 API Key：

1. **Provider**：选择解说稿生成所使用的服务商（如 Kimi / DeepSeek / Qwen）
2. **API Key**：粘贴你的密钥
3. **Model**（可选）：默认使用所选 Provider 的推荐模型

API Key 获取方式：

- **Kimi (月之暗面)** — [platform.moonshot.cn](https://platform.moonshot.cn)
- **DeepSeek** — [platform.deepseek.com](https://platform.deepseek.com)
- **Qwen (阿里云百炼)** — [bailian.console.aliyun.com](https://bailian.console.aliyun.com)

所有配置仅保存在本地，绝不外传。完整的多服务商配置说明见 [AI 配置](/guide/ai-configuration)。

## 第三步：确认 FFmpeg 可用

Vynaro 依赖系统级 FFmpeg 进行视频合成：

```bash
ffmpeg -version
# 应输出：ffmpeg version 6.x 或更高 ...
```

如果未安装：

- **macOS**：`brew install ffmpeg`
- **Ubuntu/Debian**：`sudo apt install ffmpeg`
- **Windows**：`winget install ffmpeg` 或从 [ffmpeg.org](https://ffmpeg.org) 下载并加入 PATH

## 验证成功

- 应用正常启动，进入项目首页
- 设置页面中 Provider 显示为已选择的服务商
- `ffmpeg -version` 输出正常

## 常见卡点

| 问题                       | 解决                               |
| -------------------------- | ---------------------------------- |
| macOS 提示"无法验证开发者" | 系统设置 → 隐私与安全性 → 仍要打开 |
| `ffmpeg not found`         | 安装 FFmpeg 后重启应用             |
| API Key 无效（401）        | 检查 Key 是否复制完整，无多余空格  |
| 调用限流（429）            | 稍后重试或切换其他 Provider        |

## 下一步

- [安装指南](/guide/installation) — 各平台完整安装与源码构建步骤
- [AI 配置](/guide/ai-configuration) — 多服务商配置详解
- [界面介绍](/guide/interface) — 了解桌面界面
