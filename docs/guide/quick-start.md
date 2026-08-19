---
title: 快速开始
description: 3 步上手 splicr 桌面端，10分钟完成第一次 AI 视频解说创作。
---

# 🚀 快速开始

只要 3 步，即可完成 **splicr 桌面端** 的安装、大模型 API 密钥配置与环境准备，开启自动化的短剧解说与视频剪辑流程。

![splicr 主工作台预览](/assets/mockups/hero-app-main.jpg)

---

## 📦 第一步：下载与安装桌面端

从 [GitHub Releases](https://github.com/Agions/splicr/releases) 下载适合您操作系统的预编译安装包：

| 操作系统 | 安装包格式 | 安装与安装后权限说明 |
| :--- | :--- | :--- |
| **Windows** | `.msi` / `.exe` | 双击运行安装向导，自动关联 `.draft` 导出协议 |
| **macOS** | `.dmg` | 拖拽至 `Applications`。首次启动如提示开发者未验证，请前往「系统设置 → 隐私与安全性 → 仍要打开」 |
| **Linux** | `.AppImage` / `.deb` | 赋予可执行权限 `chmod +x` 后直接运行 |

> 💡 如果您是开发者并希望从源码构建，请参考 [安装指南](/guide/installation)。

---

## 🗝️ 第二步：配置 LLM 与 TTS 秘钥

启动 splicr，点击左侧导航栏的 **⚙️ 设置 (Settings) → AI 配置**，输入至少一个 AI 大模型与 TTS 服务的 API Key：

![AI 独白脚本生成与 API 选择](/assets/mockups/ai-script-generator.jpg)

1. **LLM 供应商**：支持通义千问 (qwen3.8-max)、DeepSeek (deepseek-v4-pro)、OpenAI (gpt-5.6-sol)、Claude (claude-sonnet-5)、Gemini (gemini-3.6-flash)、Kimi (kimi-k3)、GLM-5.2、豆包 (doubao-seed-2-1-pro)、腾讯混元 (hunyuan-pro) 与本地 Ollama 等 11 大服务商。
2. **API Key**：粘贴您的 API 秘钥（秘钥通过系统密钥链安全加密存储在本地）。
3. **测试连接**：点击「连通性测试」按钮，确认 API Key 响应正常。

### 常用 LLM 秘钥获取地址

* 🇨🇳 **DeepSeek (deepseek-v4-pro)** — [platform.deepseek.com](https://platform.deepseek.com)
* 🇨🇳 **通义千问 (qwen3.8-max)** — [bailian.console.aliyun.com](https://bailian.console.aliyun.com)
* 🇺🇸 **OpenAI (gpt-5.6-sol)** — [platform.openai.com](https://platform.openai.com)
* 🇨🇳 **Kimi (kimi-k3)** — [platform.moonshot.cn](https://platform.moonshot.cn)

---

## 🎞️ 第三步：确认本地 FFmpeg 探针可用

splicr 核心底层使用 FFmpeg 进行场景切片、情绪检测与音画混流。桌面端内置探针，也可识别系统级 FFmpeg：

```bash
# 在终端中验证 FFmpeg 版本：
ffmpeg -version
# 输出应当包含: ffmpeg version 6.0 或更高的版本信息
```

若您的系统尚未安装 FFmpeg：
* **macOS**：`brew install ffmpeg`
* **Windows**：`winget install ffmpeg` 或下载后添加到 PATH 环境变量
* **Linux**：`sudo apt update && sudo apt install ffmpeg`

---

## 🎬 创作您的第一条 AI 视频解说

环境准备就绪后，进入【Agent 创作工作台】开启影视级制作：

1. **📥 素材装载**：点击「➕ 选择上传视频」，选取一段短剧或电影视频片段 (`.mp4` / `.mov`)。
2. **🤖 启动 Multi-Agent 团队**：点击「启动 Multi-Agent 创作团队」，总控导演将自动调度画面分析、金牌编剧、声乐调音、混音剪辑与质量验收 6 大智能体。
3. **⏸️ 断点审批 (HITL)**：在编剧节点审查生成的 0~3s 黄金 Hook 悬疑独白，可一键批准或打回重写。
4. **🎙️ 声乐克隆与 5 轨对齐**：智能体自动合成 48kHz 高保真配音，并完成 5 轨磁性多轨时间轴毫秒级对齐（偏差 < 12ms）。
5. **📤 原生草稿导出**：点击「导出剪映工程草稿」，原生生成剪映 `.draft` 工程直接打开精剪！

---

## ❓ 常见问题快速排查

| 现象 / 报错 | 常见原因 | 解决方法 |
| :--- | :--- | :--- |
| **API Key 报 401 Unauthorized** | 秘钥复制不完整或包含首尾空格 | 重新从服务商控制台复制并点击「连通性测试」 |
| **拆条提示 `FFmpeg executable missing`** | 系统 PATH 未找到 ffmpeg 可执行文件 | 按照第三步安装 FFmpeg 并重启 splicr |
| **TTS 生成极慢或超时** | 网络波动或代理设置影响 | 在设置中开启【Edge-TTS 备用节点】或使用本地克隆 |

---

## 📖 下一步推荐

* 了解三栏工作台：查看 [三栏集成工作台操作指南](/guide/interface)
* 了解多智能体协同：查看 [AI 多智能体工作流详解](/guide/ai-video-guide)
* 了解剪映草稿导出：查看 [导出与发布指南](/guide/exporting)
