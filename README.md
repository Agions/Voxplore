<!-- markdownlint-disable MD060 MD040 MD041 MD047 -->

<div align="center">

<img src="assets/logo-horizontal.png" width="640" alt="splicr 叙影 AI 视频解说创作工具" style="border-radius: 16px; box-shadow: 0 0 32px rgba(245,200,66,0.2);" />

[![Version](https://img.shields.io/badge/Version-v1.0.1-F5C842?style=flat-square&logo=git&logoColor=1A1A20)](https://github.com/Agions/splicr/releases) [![Tauri](https://img.shields.io/badge/Tauri-v2.0-7C3AED?style=flat-square&logo=tauri&logoColor=white)](https://tauri.app) [![Rust](https://img.shields.io/badge/Rust-1.85%2B-F97316?style=flat-square&logo=rust&logoColor=white)](https://www.rust-lang.org) [![React](https://img.shields.io/badge/React-19.0-06B6D4?style=flat-square&logo=react&logoColor=white)](https://react.dev) [![TypeScript](https://img.shields.io/badge/TypeScript-5.8-3178C6?style=flat-square&logo=typescript&logoColor=white)](https://www.typescriptlang.org) [![License](https://img.shields.io/badge/License-MIT-10B981?style=flat-square&logo=open-source-initiative&logoColor=white)](LICENSE)  
[![Multi-Agent](https://img.shields.io/badge/Multi--Agent-6%20Specialists-D97706?style=flat-square&logo=openai)](https://github.com/Agions/splicr) [![LLM](https://img.shields.io/badge/LLM-11%20Providers-F5C842?style=flat-square&logo=openai&logoColor=1A1A20)](https://github.com/Agions/splicr) [![TTS](https://img.shields.io/badge/TTS-Zero--shot%20Clone-22C55E?style=flat-square&logo=microphone)](https://github.com/Agions/splicr) [![Export](https://img.shields.io/badge/Export-CapCut%20Draft-EC4899?style=flat-square&logo=video)](https://github.com/Agions/splicr)

</div>

---

## 🎬 核心定位与设计理念

**splicr（叙影）** 是一款基于 **Rust Native 多智能体架构 + Tauri 2 + React 19** 深度研发的电影级桌面端 AI 视频叙事与解说生成引擎。

专为短剧拆条、影视解说、自媒体故事化创作者打造。通过 **三栏一体化专业集成工作台 (Integrated Cinema Studio)** 与 **6 大多智能体团队协作体系 (Multi-Agent Team)**，一键完成素材多模态抽帧、第一人称高潮独白撰写、人声克隆合成、5 轨毫秒级对齐与剪映工程草稿（`.draft`）原生交付。

---

## 🖥️ 桌面端真实运行界面展示

<div align="center">

| 首页 Dashboard 工程概览 | 三栏一体化 Multi-Agent 解说工作台 |
| :---: | :---: |
| <img src="assets/splicr_dashboard_cover.png" width="460" alt="splicr 首页 Dashboard 界面截图" style="border-radius: 8px; border: 1px solid #27272A;" /> | <img src="assets/splicr_production_cover.png" width="460" alt="splicr 三栏多智能体工作台截图" style="border-radius: 8px; border: 1px solid #27272A;" /> |

| 素材资产管理中心 | 11 大模型与 TTS 探针设置 |
| :---: | :---: |
| <img src="assets/splicr_assets_cover.png" width="460" alt="splicr 素材资产管理界面截图" style="border-radius: 8px; border: 1px solid #27272A;" /> | <img src="assets/splicr_settings_cover.png" width="460" alt="splicr 模型设置表单界面截图" style="border-radius: 8px; border: 1px solid #27272A;" /> |

</div>

---

## 🎭 Rust Native 多智能体协作架构 (Multi-Agent Team)

```mermaid
graph TD
    User["人类创作者 (Human-in-the-Loop)"] -->|导入素材 + 风格偏好| Director["🎬 总控导演 Agent (DirectorAgent)"]
    
    subgraph MultiAgentTeam ["splicr 智能体工作群 (crates/agent)"]
        Director -->|分配拆条与关键帧分析| VisualCritic["👁️ 视觉分析师 (VisualCriticAgent)"]
        VisualCritic -->|输出镜头切片 + 画面情绪特征| Screenwriter["✍️ 金牌编剧 (ScreenwriterAgent)"]
        
        Screenwriter -->|自反思评估: 0~3s 黄金Hook完播率评分| Screenwriter
        Screenwriter -->|输出第一人称台词剧本| VoiceArtist["🎙️ 声乐调音师 (VoiceArtistAgent)"]
        
        VoiceArtist -->|音色选型 + 情绪克隆 + 语速控制| SoundEngineer["🎛️ 混音剪辑师 (SoundEngineerAgent)"]
        SoundEngineer -->|FFmpeg毫秒级声画吸附 + BGM智能闪避| QC["🔍 质量验收员 (QualityReviewerAgent)"]
        
        QC -->|打回修正 / 评分合格| Director
    end
    
    Director -->|断点审核/最终产物交付| User
    Director -->|原生导出| CapCut[".draft 剪映工程草稿"]
```

| 智能体角色 | 专业职责与能力底座 |
| :--- | :--- |
| **🎬 总控导演 (DirectorAgent)** | 全局任务规划、状态机流转调度、管理 `AgentContext` 与创作者断点交互 (HITL) |
| **👁️ 视觉分析师 (VisualCriticAgent)** | FFmpeg 场景切面探测、多模态关键帧提取、画面情绪峰值与张力打点 |
| **✍️ 金牌编剧 (ScreenwriterAgent)** | 生成 0~3s 黄金 Hook 与第一人称独白，内置 **完播率自反思评分回路 (Reflection Loop)** |
| **🎙️ 声乐调音师 (VoiceArtistAgent)** | 角色音色匹配、Edge-TTS / GPT-SoVITS 深度克隆与 48kHz 音频生成 |
| **🎛️ 混音剪辑师 (SoundEngineerAgent)** | 5 轨磁性时间轴毫秒级对齐（偏差 <18ms）与 BGM 智能闪避混流 (-18%) |
| **🔍 质量验收员 (QualityReviewerAgent)** | 审查多轨时间轴结构、违禁词扫描、草稿完整性与最终交付核验 (Score: 98/100) |

---

## 🧠 11 大主流大模型与人声克隆矩阵

### 11 大主流 LLM 引擎支持
* 🇨🇳 **通义千问 (Qwen)**: `qwen3.8-max` (首选推荐)
* 🇨🇳 **DeepSeek**: `deepseek-v4-pro` / `deepseek-v4-flash`
* 🇺🇸 **OpenAI**: `gpt-5.6-sol` / `gpt-4o`
* 🇺🇸 **Claude**: `claude-sonnet-5`
* 🇺🇸 **Gemini**: `gemini-3.6-flash` / `gemini-3.1-pro`
* 🇨🇳 **Kimi (月之暗面)**: `kimi-k3`
* 🇨🇳 **智谱 GLM**: `glm-5.2`
* 🇨🇳 **豆包 (Doubao)**: `doubao-seed-2-1-pro`
* 🇨🇳 **腾讯混元 (Hunyuan)**: `hunyuan-pro`
* 🏠 **本地离线模型 (Local)**: Ollama / LMStudio (`llama3.2` / `qwen2.5`)

---

## 🏛️ 项目结构与模块划分

```
splicr/
├── src/                  # React 19 + TypeScript 三栏专业工作台
├── src-tauri/            # Tauri 2.0 桌面端入口 (Rust IPC 注册与生命周期)
├── crates/
│   ├── agent             # Rust Native 多智能体协作与自反思调度引擎 (Director/Screenwriter...)
│   ├── core              # 核心基础设施 (AppContext / SplicrError / Translator)
│   ├── domain            # 核心领域模型 (Project / Timeline / MediaFile / Track)
│   ├── detect            # FFmpeg 智能探针 / 场景切片 / 多模态抽帧
│   ├── script            # 11 大主流 LLM 客户端与独白脚本引擎
│   ├── voice             # Edge-TTS / OpenAI-TTS / GPT-SoVITS 人声克隆
│   ├── subtitle          # FFmpeg silencedetect VAD 语音端点检测与字幕生成
│   ├── compose           # 7 步流水线状态机与 DAG 执行器
│   ├── export            # 剪映草稿 (.draft) 原生工程导出与防重矩阵
│   ├── storage           # 本地 SQLite / JSON 持久化存储
│   └── update            # 跨平台自动热更新引擎
└── docs/                 # VitePress 在线官方生产与开发文档中心
```

---

## 🛠️ 本地极速开发

```bash
# 1. 克隆代码仓库
git clone https://github.com/Agions/splicr.git
cd splicr

# 2. 安装前端依赖
pnpm install

# 3. 启动桌面端开发环境
pnpm tauri dev

# 4. 运行全套自动化测试
cargo test --all
pnpm test
```

---

## 📜 许可证

基于 **[MIT License](LICENSE)** 许可协议开源。

© 2026 Agions · Powered by Tauri 2, Rust & React 19
