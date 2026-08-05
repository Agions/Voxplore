---
title: 安装指南
description: 在 Windows、macOS 和 Linux 上完整安装 SceneFab v2.5.0 桌面应用（Tauri 2 + React 主线）。
---

# 安装指南

## 系统要求

| 要求           | 最低配置                                                         | 推荐配置                                                                      |
| -------------- | ---------------------------------------------------------------- | ----------------------------------------------------------------------------- |
| 操作系统       | Windows 10 / macOS 11 / Ubuntu 20.04                             | 最新稳定版                                                                    |
| Node.js        | 20.19+                                                           | 22 LTS                                                                        |
| pnpm           | 9.x                                                              | 最新版（`corepack prepare pnpm@latest --activate`）                           |
| Rust           | 1.85+                                                            | 1.96+（`rustup default stable`）                                              |
| 内存           | 8 GB                                                             | 16 GB+                                                                        |
| 磁盘           | 2 GB 可用空间                                                    | 5 GB 可用空间                                                                 |
| FFmpeg         | 6.0+                                                             | 最新版（系统级 `ffmpeg` 命令行）                                              |
| Tauri 系统依赖 | 见 [Tauri prerequisites](https://tauri.app/start/prerequisites/) | macOS: Xcode CLT · Windows: WebView2 + VS Build Tools · Linux: webkit2gtk-4.1 |

## Windows

### 方式一：安装包（推荐）

1. 从 [Releases](https://github.com/Agions/scene-fab/releases) 下载最新 `.msi` 或 `.exe`
2. 双击运行安装程序
3. 安装完成后，桌面会出现 **SceneFab** 图标，从开始菜单启动

### 方式二：从源码开发

```powershell
# 1. 安装 Node.js 22 LTS 与 Rust 1.85+
winget install OpenJS.NodeJS.LTS
winget install Rustlang.Rustup

# 2. 安装 pnpm
corepack enable
corepack prepare pnpm@latest --activate

# 3. 安装 Tauri 系统依赖
#    - Microsoft Visual Studio Build Tools (C++ workload)
#    - WebView2 Runtime
#    详见 https://tauri.app/start/prerequisites/windows

# 4. 克隆与启动
git clone https://github.com/Agions/scene-fab.git
cd scene-fab
pnpm install
cd apps/desktop
pnpm tauri:dev
```

## macOS

### 方式一：安装包（推荐）

1. 从 [Releases](https://github.com/Agions/scene-fab/releases) 下载最新 `.dmg`
2. 双击挂载，将 `SceneFab.app` 拖入「应用程序」文件夹
3. 启动台中搜索 **SceneFab** 启动

### 方式二：从源码开发

```bash
# 1. 安装 Xcode Command Line Tools
xcode-select --install

# 2. 安装 Rust
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh

# 3. 安装 Node.js 与 pnpm
brew install node@22
corepack enable
corepack prepare pnpm@latest --activate

# 4. 安装 FFmpeg（系统级，crate 内部调用）
brew install ffmpeg

# 5. 克隆与启动
git clone https://github.com/Agions/scene-fab.git
cd scene-fab
pnpm install
cd apps/desktop
pnpm tauri:dev
```

## Linux（Ubuntu 22.04+ / Debian 12+）

### 方式一：安装包（推荐）

1. 从 [Releases](https://github.com/Agions/scene-fab/releases) 下载最新 `.deb` 或 `.AppImage`
2. **deb**：`sudo dpkg -i scenefab_2.5.0_amd64.deb && sudo apt install -f`
3. **AppImage**：`chmod +x SceneFab_2.5.0_amd64.AppImage && ./SceneFab_2.5.0_amd64.AppImage`

### 方式二：从源码开发

```bash
# 1. 安装系统依赖（webkit2gtk-4.1 是 Tauri 必需）
sudo apt update
sudo apt install -y \
  libwebkit2gtk-4.1-dev \
  build-essential \
  curl wget file \
  libxdo-dev \
  libssl-dev \
  libayatana-appindicator3-dev \
  librsvg2-dev

# 2. 安装 Node.js 22 LTS 与 pnpm
curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -
sudo apt install -y nodejs
corepack enable
corepack prepare pnpm@latest --activate

# 3. 安装 Rust
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
source "$HOME/.cargo/env"

# 4. 安装 FFmpeg
sudo apt install -y ffmpeg

# 5. 克隆与启动
git clone https://github.com/Agions/scene-fab.git
cd scene-fab
pnpm install
cd apps/desktop
pnpm tauri:dev
```

## 验证安装

启动后验证 4 项关键状态：

```bash
# 1. 检查 Node.js
node --version        # 应输出 v20.19+ 或 v22.x

# 2. 检查 Rust
rustc --version       # 应输出 1.85+

# 3. 检查 pnpm
pnpm --version        # 应输出 9.x 或更新

# 4. 检查 FFmpeg
ffmpeg -version | head -1   # 应输出 6.0+

# 5. 启动应用
cd apps/desktop && pnpm tauri:dev
# 成功标志：弹出 Tauri 窗口 + 看到 SceneFab Home 页面
```

## 常见问题

### FFmpeg 未找到

```bash
# macOS
brew install ffmpeg

# Ubuntu
sudo apt install ffmpeg

# Windows
winget install ffmpeg
```

### WebView2 缺失（Windows）

```powershell
winget install Microsoft.EdgeWebView2Runtime
```

### 端口 1420 / 1421 占用

Tauri dev server 默认端口被占用时，编辑 `apps/desktop/vite.config.ts` 修改 `server.port` 字段。

### 编译失败：Rust 工具链版本不足

```bash
rustup update stable
rustup default stable
```

## 相关文档

- [快速开始](/guide/quick-start) — 3 步上手
- [界面介绍](/guide/interface) — 了解桌面界面
- [AI 模型配置](/guide/ai-configuration) — 11 个 LLM Provider
- [疑难排查](/guide/troubleshooting) — 常见问题解决
