---
title: 快速入门
description: Voxplore 完整安装与首次使用指南。
---

# 快速入门

本文档帮助你在 10 分钟内完成 Voxplore 安装配置，并生成第一个解说视频。

---

## 第一步：安装 Voxplore

### 下载安装包（推荐）

访问 [GitHub Releases](https://github.com/Agions/Voxplore/releases/latest)，下载对应平台版本：

| 平台 | 文件 | 安装方式 |
|------|------|----------|
| Windows | `Voxplore-Setup-x.x.x.exe` | 运行安装程序 |
| macOS | `Voxplore-x.x.x.dmg` | 拖入 Applications |
| Linux | `Voxplore-x.x.x.AppImage` | 添加执行权限后运行 |

### Homebrew（macOS / Linux）

```bash
brew install narrafiilm
```

### 源码运行

```bash
git clone https://github.com/Agions/Voxplore.git
cd narrafiilm
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python app/main.py
```

---

## 第二步：安装 FFmpeg

FFmpeg 是视频处理的核心依赖。

```bash
# macOS
brew install ffmpeg

# Ubuntu / Debian
sudo apt update && sudo apt install ffmpeg

# Windows
# 下载 https://ffmpeg.org/download.html，解压后将 bin 目录加入 PATH
```

验证安装：

```bash
ffmpeg -version
```

---

## 第三步：配置 DeepSeek API Key

Voxplore 使用 **DeepSeek-V3** 生成解说稿，性价比最高（约 $0.1 / 1M tokens）。

### 获取 Key

1. 打开 [platform.deepseek.com](https://platform.deepseek.com)
2. 注册并登录 → **API Keys** → **Create API Key**
3. 复制 Key（格式：`sk-...`）

### 配置方式

**方式一：应用内配置**

启动应用 → **设置** → **AI 配置** → 粘贴 Key → **保存**

**方式二：.env 文件**

在项目根目录创建 `.env`：

```env
DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxx
```

---

## 第四步：生成第一个解说视频

### Step 1 — 新建项目

启动 Voxplore → 点击 **新建项目** → 选择保存位置 → 输入项目名称

### Step 2 — 导入视频

- 点击 **导入素材** 或直接拖拽视频文件
- 支持格式：`MP4` / `MOV` / `AVI` / `MKV` / `WebM`

### Step 3 — 生成解说

1. 选择**情感风格**：治愈 / 悬疑 / 励志 / 怀旧 / 浪漫
2. 选择**配音音色**：默认 XiaoXiao（女声）
3. 点击 **开始创作**

等待 1–3 分钟（取决于视频长度），预览结果后点击 **导出**。

---

## 遇到问题？

- [5 分钟快速开始](./guide/quick-start) — 精简版上手指南
- [完整安装指南](./guide/installation) — 各平台详细步骤
- [疑难排查](./guide/troubleshooting) — 常见问题解决
- [常见问题](./faq) — FAQ 列表
