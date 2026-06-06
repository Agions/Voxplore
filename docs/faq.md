---
title: 常见问题
description: SceneFab 使用中的常见问题解答，涵盖安装、配置、功能与性能。
---

# 常见问题

---

## 安装与启动

### 下载速度很慢怎么办？

GitHub Releases 国内访问较慢，可使用代理或镜像：

```bash
# 使用 ghproxy 代理
wget https://ghproxy.com/https://github.com/Agions/scene-fab/releases/download/v3.0.0/SceneFab-x.x.x.AppImage

# 或使用 gitee 镜像（如有）
```

### macOS 提示"无法打开，因为无法验证开发者"？

这是 Gatekeeper 安全限制。解决方法：

```bash
# 方法 1：右键点击应用 → 打开
# 方法 2：终端执行
xattr -d com.apple.quarantine /Applications/SceneFab.app
```

### Linux AppImage 无法运行？

```bash
# 添加执行权限
chmod +x SceneFab-x.x.x.AppImage

# 安装 FUSE 依赖
sudo apt install fuse libfuse2

# 部分精简系统还需安装
sudo apt install libegl1 libgl1 libxkbcommon0 libdbus-1-3
```

### 无头环境（SSH / 服务器）能运行吗？

能。Linux 服务器或 Docker 容器中自动使用 `QT_QPA_PLATFORM=offscreen` 模式：

```bash
export QT_QPA_PLATFORM=offscreen
python3 -m scenefab
```

### Python 版本不兼容怎么办？

SceneFab 需要 Python 3.10+。检查版本：

```bash
python3 --version
# 应显示 3.10.x 或更高

# 如版本过低，使用 pyenv 安装
pyenv install 3.12.0
pyenv local 3.12.0
```

---

## API 与账户

### DeepSeek API Key 多少钱？

DeepSeek-V4 价格极低（约 ¥0.1 / 1M tokens），处理一部 2 小时电影解说约消耗 500K tokens，成本不到 **5 分钱**。

| 用途 | Token 消耗 | 成本 |
|------|------------|------|
| 1 分钟视频 | ~50K | ¥0.005 |
| 10 分钟视频 | ~200K | ¥0.02 |
| 2 小时电影 | ~500K | ¥0.05 |

### API Key 泄露了怎么办？

1. **立即撤销**：在 [platform.deepseek.com](https://platform.deepseek.com) 删除该 Key
2. **创建新 Key**：生成新的 API Key
3. **更新配置**：替换 `.env` 或 Keychain 中的旧 Key
4. **检查用量**：查看是否有异常调用

### 账户余额还有，但报 401 错误？

可能原因：

- API Key 格式错误（应以 `sk-` 开头）
- API Key 已过期或被删除
- 触发了 API 速率限制

解决方法：

```bash
# 检查 Key 格式
echo $DEEPSEEK_API_KEY | head -c 3
# 应显示 sk-

# 等待 1 分钟后重试
sleep 60 && scenefab --retry
```

### 支持其他 AI 提供商吗？

目前主推 DeepSeek-V4 + Qwen VL（性价比最优）。支持的提供商：

| 提供商 | 状态 | 说明 |
|--------|------|------|
| DeepSeek | ✅ 默认 | 性价比最高 |
| Qwen (阿里云) | ✅ 默认 | 视频理解 |
| OpenAI | ✅ 支持 | 需配置 API Key |
| Claude | ✅ 支持 | 需配置 API Key |
| Gemini | ✅ 支持 | 需配置 API Key |

---

## 功能与效果

### 解说稿可以手动修改吗？

可以。生成后点击解说稿区域进入编辑模式，直接修改文字。修改后的稿子会保留，重新合成配音和字幕即可。

### 生成的配音听起来不够自然？

优化建议：

| 方法 | 说明 |
|------|------|
| 切换音色 | 尝试晓晓 / 云希 / 云扬 |
| 调整语速 | 0.9x–1.1x 区间最自然 |
| 优化文案 | 解说稿越自然，配音效果越好 |
| 使用 F5-TTS | 克隆真实人声（进阶） |

### 字幕和配音不同步怎么办？

1. 确认使用的是 Edge-TTS（非第三方 TTS）
2. 检查解说稿是否有异常字符或特殊符号
3. 在设置中开启 **强制重新对齐** 选项
4. 尝试重新生成配音

### 视频很长（1 小时+）能处理吗？

能。超长视频会自动分段处理，每段 10–15 分钟效果最佳。

| 视频时长 | 处理时间 | 建议 |
|----------|----------|------|
| < 10 分钟 | 1-2 分钟 | 直接处理 |
| 10-30 分钟 | 3-5 分钟 | 直接处理 |
| 30-60 分钟 | 5-10 分钟 | 自动分段 |
| > 60 分钟 | 10-20 分钟 | 自动分段，建议先测试片段 |

### 不支持哪些视频？

| 类型 | 原因 | 替代方案 |
|------|------|----------|
| 无明确情节的纯风景 | AI 难以生成连贯解说 | 手动添加解说 |
| 延时摄影 | 画面变化过快 | 手动添加解说 |
| 监控录像 | 无叙事结构 | 不适用 |
| 竖屏视频 (9:16) | 当前版本支持有限 | 等待后续版本 |
| 音频严重损坏 | 无法提取有效信息 | 修复音频后重试 |

---

## 输出与格式

### 导出失败怎么办？

```bash
# 1. 检查磁盘空间
df -h .

# 2. 检查输出目录权限
ls -la ~/Videos/SceneFab

# 3. 尝试更换导出格式
scenefab --export-format h264

# 4. 查看详细日志
scenefab --debug --log-file export.log
```

### 导出后没有声音？

检查导出设置中 **"保留配音音轨"** 是否勾选。默认仅导出 AI 配音，原片音频需手动开启。

### 剪映草稿无法导入？

- 确认剪映版本为最新
- 草稿 JSON 文件需在剪映内通过"导入草稿"加载（不可直接双击）
- 部分 CapCut 国际版不支持中文路径

### 导出的视频质量如何？

| 格式 | 分辨率 | 码率 | 说明 |
|------|--------|------|------|
| H.264 MP4 | 原始分辨率 | 自适应 | 兼容性最好 |
| H.265 MP4 | 原始分辨率 | 自适应 | 体积小 40%，需设备支持 |
| 剪映草稿 | 原始分辨率 | 可在剪映调整 | 继续精剪 |

---

## 性能与硬件

### 没有 NVIDIA 显卡能用吗？

能。无 GPU 时自动回退到 CPU 模式，视频理解会变慢，其他步骤几乎不受影响。

| 组件 | GPU 影响 |
|------|----------|
| 语义拆条 | 有 GPU 快 5-10 倍 |
| 解说生成 | 无影响（纯 API） |
| 配音合成 | 无影响（CPU 足够） |
| 视频合成 | 有 GPU 快 2-3 倍 |

### 显存不足（OOM）怎么办？

```bash
# 方案 1：关闭 GPU 加速
scenefab --no-gpu

# 方案 2：减少抽帧密度
scenefab --frame-interval 2

# 方案 3：降低视频分辨率
ffmpeg -i input.mp4 -vf scale=1280:720 output.mp4
```

### 处理速度慢怎么办？

| 瓶颈 | 解决方案 |
|------|----------|
| 网络慢 | 使用代理或更换 API 提供商 |
| 磁盘慢 | 使用 SSD 存储 |
| 内存不足 | 关闭其他程序，增加 swap |
| CPU 满载 | 减少并发任务数 |

---

## 其他

### 如何贡献代码？

见 [贡献指南](./contributing)。

### 商业使用需要授权吗？

不需要。SceneFab 采用 MIT 协议，商用和个人使用均无需授权。生成内容的版权由使用者自行负责。

### 如何获取更新？

```bash
# GitHub Releases
https://github.com/Agions/scene-fab/releases

# Watch 仓库
Watch → Releases only

# pip 更新
pip install --upgrade scenefab
```

### 如何反馈问题？

- **Bug 报告**：[GitHub Issues](https://github.com/Agions/scene-fab/issues/new?template=bug_report.md)
- **功能建议**：[Feature Request](https://github.com/Agions/scene-fab/issues/new?template=feature_request.md)
- **讨论交流**：[GitHub Discussions](https://github.com/Agions/scene-fab/discussions)
