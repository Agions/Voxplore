---
title: AI 配置与大模型矩阵
description: 配置 Monoloop 支持的 11 大 LLM 解说稿生成引擎与 3 大 TTS 人声克隆服务。
---

# 🧠 AI 配置与大模型矩阵

Monoloop 采用统一的 LLM & TTS Provider 架构。所有 API 密钥均通过应用内 **设置 → AI 服务** 进行本地加密存储，绝不上云或外传。

---

## ⚙️ 基本配置入口

打开桌面应用 **设置 → AI 服务**，可配置以下参数：

| 字段 | 说明 |
| :--- | :--- |
| **Provider** | 选择用于生成解说稿的 11 大 LLM 服务商 |
| **API Key** | 服务商密钥（本地加密存储） |
| **Base URL** | 可选 · 自定义代理或本地端点（如 Ollama / GPT-SoVITS） |
| **Model** | 可选 · 留空使用 Provider 推荐模型，也可自定义 |

---

## 🤖 11 大主流 LLM 独白引擎支持

Monoloop 原生支持 `README.md` 与底层核心代码指定的 11 大大语言模型引擎：

| 服务商 | 官方默认模型 (Default Model) | 推荐替代模型 | 特性与适用场景 |
| :--- | :--- | :--- | :--- |
| **🇨🇳 通义千问 (Qwen)** | `qwen3.8-max` | `qwen3.7-max`, `qwen-plus` | 阿里云百炼推荐，视频语义理解与 Hook 爆点抓取极佳 |
| **🇨🇳 DeepSeek** | `deepseek-v4-pro` | `deepseek-v4-flash`, `deepseek-r1` | 性价比极高，逻辑思维与反转打脸剧情推理能力强 |
| **🇺🇸 OpenAI** | `gpt-5.6-sol` | `gpt-4o`, `gpt-4o-mini` | 全球旗舰模型，第一人称内心独白与情感表达渲染力强 |
| **🇺🇸 Claude** | `claude-sonnet-5` | `claude-3-5-sonnet` | 叙事文采华丽，无机械感，适合电影感与纪录片腔调 |
| **🇺🇸 Gemini** | `gemini-3.6-flash` | `gemini-3.1-pro` | Google 超长上下文，支持长达 2 小时整季短剧批量分析 |
| **🇨🇳 Kimi (月之暗面)** | `kimi-k3` | `moonshot-v1` | 适合长篇小说改编剧本与多集角色设定集处理 |
| **🇨🇳 智谱 GLM** | `glm-5.2` | `glm-4-plus` | 智谱清言引擎，针对中文剧情递进与抑扬顿挫深度优化 |
| **🇨🇳 豆包 (Doubao)** | `doubao-seed-2-1-pro` | `doubao-pro-128k` | 字节火山引擎，天然契合抖音爆款节奏与短视频卡点 |
| **🇨🇳 腾讯混元 (Hunyuan)** | `hunyuan-pro` | `hunyuan-standard` | 腾讯云大模型，中文结构严密，适合影评解析与吐槽 |
| **🏠 本地模型 (Local)** | `llama3.2` | `qwen2.5` | 基于 Ollama / LMStudio 运行，100% 本地离线隐私保护 |

---

## 🎙️ 4 大 TTS 语音合成与人声克隆引擎

Monoloop 提供从免费内置配音到专业人声克隆的全套解决方案，支持单独为 TTS 引擎指定 **TTS API Key** 与 **TTS Base URL**：

| TTS 引擎 | 状态与费用 | 核心 Model / 音色 | 功能说明 |
| :--- | :--- | :--- | :--- |
| **Edge-TTS** | ✅ 免费内置 | `zh-CN-XiaoxiaoNeural` / `Yunxi` | 微软官方 50+ 黄金发音人，无需 API Key |
| **MiMo (小米 MiMo)** | ✅ 限时免费 | `mimo-v2.5-tts` | 小米 MiMo 开放平台限时免费大模型语音，支持自然语气与情感控音 |
| **OpenAI-TTS** | ✅ 需 API Key | `gpt-4o-mini-tts` / `tts-1-hd` | 影视级语音合成，支持富情感拟真人声 |
| **GPT-SoVITS** | ✅ 本地 / 零样本 | Zero-shot Sovits (`127.0.0.1:9880`) | 仅需 5 秒参考音频即可复刻主播或影视角色音色 |

> 💡 **Xiaomi MiMo API Key 配置说明**：使用 MiMo TTS (`mimo-v2.5-tts`) 前，请前往 [小米 MiMo 开放平台 (platform.xiaomimimo.com)](https://platform.xiaomimimo.com) 注册账号并在「API 管理」中生成专属 API Key。然后在 Monoloop **设置 → 语音合成 (TTS)** 中填入 `TTS API Key` 即可使用。若使用 OpenAI-TTS 或第三方代理，亦可在同处单独配置 `TTS API Key` 与 `TTS Base URL`。

### Edge-TTS 热门解说音色参考

| 音色 ID | 呈现名称 | 适用解说风格 |
| :--- | :--- | :--- |
| `zh-CN-XiaoxiaoNeural` | 晓晓 | 治愈、情感内心独白、浪漫故事 |
| `zh-CN-YunxiNeural` | 云希 | 悬疑反转、第一人称剧场、热血 |
| `zh-CN-YunyangNeural` | 云扬 | 电影解说、严肃纪录片、正式播音 |
| `zh-CN-XiaoyiNeural` | 小艺 | 轻松吐槽、搞笑影评、欢快短视频 |
| `zh-CN-YunjianNeural` | 云健 | 激情叙事、快节奏爽剧 |

---

## 💰 API 费用与 Token 消耗估算

以推荐模型 `deepseek-v4-pro` 或 `qwen3.8-max` 为例：

| 视频类型 | 估算 Token 消耗 | 预估费用 |
| :--- | :--- | :--- |
| **5 分钟短剧拆条解说** | ~50K Tokens | ~¥0.005 |
| **15 分钟影视单集解说** | ~200K Tokens | ~¥0.02 |
| **2 小时全季电影剧场** | ~600K Tokens | ~¥0.06 |

---

## 🛠️ 常见 AI 报错与排查

| 错误代码 / 现象 | 可能原因 | 解决办法 |
| :--- | :--- | :--- |
| `401 Unauthorized` | API Key 填写错误或额度用尽 | 检查设置页 Key 复制是否包含空格，或登录平台充值 |
| `429 Rate Limit` | 触发了服务商 QPS 频率限制 | 1 分钟后自动重试，或在设置中更换其他 Provider 备用 |
| `GPT-SoVITS Offline` | 本地克隆服务未在 9880 端口启动 | 检查本地 GPT-SoVITS 终端是否正常运行，点击「重新检测」 |
| `Edge-TTS Connect Error` | 网络无法连接微软 Azure 节点 | 检查本地网络连接或开启 HTTP 代理重试 |

---

## 📖 相关推荐文档

- [快速开始](/guide/quick-start) — 3 步完成配置上手
- [AI 工作流详解](/guide/ai-video-guide) — 7 步生产流程拆解
- [疑难排查](/guide/troubleshooting) — 常见故障排查
