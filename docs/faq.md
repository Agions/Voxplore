---
title: 常见问题
description: SceneFab 使用中的常见问题解答。
---

# 常见问题

---

## 安装与启动

### 下载速度很慢怎么办？

GitHub Releases 国内访问较慢，可使用代理：

```bash
wget https://ghproxy.com/https://github.com/Agions/scene-fab/releases/download/v3.0.0/SceneFab-x.x.x.AppImage
```

### macOS 提示"无法打开，因为无法验证开发者"？

这是 Gatekeeper 安全限制。右键点击应用 → **打开**，或在终端执行：

```bash
xattr -d com.apple.quarantine /Applications/SceneFab.app
```

### Linux AppImage 无法运行？

```bash
chmod +x SceneFab-x.x.x.AppImage
sudo apt install fuse libfuse2
```

部分精简系统还需安装：`libegl1 libgl1 libxkbcommon0 libdbus-1-3`

### 无头环境（SSH / 服务器）能运行吗？

能。Linux 服务器或 Docker 容器中自动使用 `QT_QPA_PLATFORM=offscreen` 模式：

```bash
export QT_QPA_PLATFORM=offscreen
python3 -m scenefab
```

---

## API 与账户

### DeepSeek API Key 多少钱？

DeepSeek-V4 价格极低（约 ¥0.1 / 1M tokens），处理一部 2 小时电影解说约消耗 500K tokens，成本不到 **5 分钱**。

### API Key 泄露了怎么办？

立即在 [platform.deepseek.com](https://platform.deepseek.com) 删除该 Key，并创建新 Key 替换。

### 账户余额还有，但报 401 错误？

可能是触发了 API 速率限制。等待 1 分钟重试。

### 支持其他 AI 提供商吗？

目前主推 DeepSeek-V4 + Qwen VL（性价比最优）。理论上支持 OpenAI GPT-4o / Claude Sonnet，但需自行修改 API 端点。

---

## 功能与效果

### 解说稿可以手动修改吗？

可以。生成后点击解说稿区域进入编辑模式，直接修改文字。修改后的稿子会保留，重新合成配音和字幕即可。

### 生成的配音听起来不够自然？

- 尝试切换不同音色（晓晓 / 云希 / 云扬）
- 调整语速至 0.9x–1.1x 区间
- 解说稿越自然、配音效果越好
- 进阶用户可使用 F5-TTS 克隆真实人声

### 字幕和配音不同步怎么办？

1. 确认使用的是 Edge-TTS（非第三方 TTS）
2. 检查解说稿是否有异常字符或特殊符号
3. 在设置中开启 **强制重新对齐** 选项

### 视频很长（1 小时+）能处理吗？

能。超长视频会自动分段处理，每段 10–15 分钟效果最佳。

### 不支持哪些视频？

- **无明确情节**的纯风景、延时摄影、监控录像
- **画面严重模糊或遮挡**的视频
- **竖屏视频**（当前版本对 9:16 比例支持有限）
- **音频严重损坏或无音轨**

---

## 输出与格式

### 导出失败怎么办？

1. 确认磁盘空间充足（导出需要原片 2–3 倍空间）
2. 检查输出目录是否有写入权限
3. 临时关闭杀毒软件（部分杀软会拦截 FFmpeg）
4. 尝试更换导出格式（H.265 → H.264）

### 导出后没有声音？

检查导出设置中 **"保留配音音轨"** 是否勾选。默认仅导出 AI 配音，原片音频需手动开启。

### 剪映草稿无法导入？

- 确认剪映版本为最新
- 草稿 JSON 文件需在剪映内通过"导入草稿"加载（不可直接双击）
- 部分 CapCut 国际版不支持中文路径

---

## 性能与硬件

### 没有 NVIDIA 显卡能用吗？

能。无 GPU 时自动回退到 CPU 模式，视频理解会变慢，其他步骤几乎不受影响。

### 显存不足（OOM）怎么办？

- 关闭 GPU 加速（设置 → AI 配置）
- 减少抽帧密度（设置 → 拆条配置 → 抽帧间隔，改为 2 秒）
- 降低视频分辨率（1080p → 720p）

---

## 其他

### 如何贡献代码？

见 [贡献指南](../../CONTRIBUTING.md)。

### 商业使用需要授权吗？

不需要。SceneFab 采用 MIT 协议，商用和个人使用均无需授权。生成内容的版权由使用者自行负责。

### 如何获取更新？

- **GitHub Releases**：[github.com/Agions/scene-fab/releases](https://github.com/Agions/scene-fab/releases)
- **Watch 仓库**：Watch → Releases only
- **Homebrew**：`brew upgrade scenefab`