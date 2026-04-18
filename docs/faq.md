---
title: 常见问题
description: Voxplore 使用中的常见问题解答。
---

# 常见问题

---

## 安装与启动

### 下载速度很慢怎么办？

GitHub Releases 国内访问较慢，可使用代理：
```bash
# 使用 ghproxy
wget https://ghproxy.com/https://github.com/Agions/Voxplore/releases/download/v3.4.0/Voxplore-x.x.x.AppImage
```

或使用 Gitee 镜像（如有同步）。

### macOS 提示"无法打开，因为无法验证开发者"？

这是 Gatekeeper 安全限制，解决方法：
1. 右键点击应用 → **打开**
2. 弹出提示时点击 **打开**

或在终端执行：
```bash
xattr -d com.apple.quarantine /Applications/Voxplore.app
```

### Linux AppImage 无法运行？

```bash
chmod +x Voxplore-x.x.x.AppImage
sudo apt install fuse libfuse2  # 如缺少依赖
```

部分精简系统需要安装额外库：`libegl1 libgl1 libxkbcommon0 libdbus-1-3`

### 无头环境（SSH / 服务器）能运行吗？

能。Linux 服务器或 Docker 容器中，应用会自动使用 `QT_QPA_PLATFORM=offscreen` 模式，完整运行所有 AI 处理流程，只是无法使用图形界面。

```bash
export QT_QPA_PLATFORM=offscreen
python3 app/main.py
```

### Docker 中运行

```dockerfile
FROM python:3.10-slim

RUN apt-get update && apt-get install -y \
    ffmpeg libegl1 libgl1 libxkbcommon0 libdbus-1-3 libgtk-3-0

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
CMD ["python3", "app/main.py"]
```

---

## API 与账户

### DeepSeek API Key 多少钱？

DeepSeek-V3 价格极低（约 $0.1 / 1M tokens），处理一个 5 分钟视频约消耗 50K–100K tokens，成本不到 **1 分钱**。普通使用一个月 $1 足够。

### API Key 泄露了怎么办？

立即在 [platform.deepseek.com](https://platform.deepseek.com) 删除该 Key，并创建新 Key 替换。同时检查账户是否有异常调用记录。

### 账户余额还有，但报 401 错误？

可能是触发了 API 的速率限制（Rate Limit）。等待 1 分钟重试，或在 [DeepSeek 控制台](https://platform.deepseek.com) 查看当前配额状态。

### 支持其他 AI 提供商吗？

目前 Voxplore 主推 DeepSeek-V3（性价比最优）。理论上支持 OpenAI GPT-4.1 和 Anthropic Claude 系列，但需要自行修改代码中的 API 端点。视频理解模型（Qwen2.5-VL）目前仅支持阿里云百炼 API。

---

## 功能与效果

### 解说稿可以手动修改吗？

可以。生成后点击解说稿区域进入编辑模式，直接修改文字。修改后的稿子会保留，重新合成配音和字幕即可。

### 生成的配音听起来不够自然？

- 尝试切换不同音色（XiaoXiao / Yunxi / Yunyang）
- 调整语速至 0.9x–1.1x 区间
- 解说稿越自然、配音效果越好（避免长难句和生僻词）
- 进阶用户可使用 F5-TTS 克隆真实人声

### 字幕和配音不同步怎么办？

字幕同步依赖 TTS word-level timing 数据，Edge-TTS 同步精度通常在 50ms 以内。如遇明显不同步：
1. 确认使用的是 Edge-TTS（非第三方 TTS）
2. 检查解说稿是否有异常字符或特殊符号
3. 在设置中开启 **强制重新对齐** 选项

### 视频很长（1 小时+）能处理吗？

能，但需要注意：
- 超长视频建议分段处理（每段 10–15 分钟效果最佳）
- 视频理解阶段显存消耗较大，有 GPU 时会自动分段
- API 调用量增加，处理时间和成本相应上升

### 不支持哪些视频？

- **无明确主角** 的纯风景、延时摄影、监控录像（AI 无法判断"我是谁"）
- **画面严重模糊或遮挡** 的视频
- **竖屏视频**（当前版本对竖屏支持有限，9:16 比例可能产生构图问题）
- **音频严重损坏或无音轨**（对配音无影响，但会影响场景理解辅助参考）

### 如何让 AI 更准确地识别主角？

- 主角在画面中占比越大、出现时间越长，识别越准确
- 多主角场景，可在生成后手动指定哪个是"我"
- 避免主角长期处于画面边缘或被大面积遮挡

---

## 输出与格式

### 导出失败怎么办？

1. 确认磁盘空间充足（导出需要原片 2–3 倍空间）
2. 检查输出目录是否有写入权限
3. 临时关闭杀毒软件（部分杀软会拦截 FFmpeg）
4. 尝试更换导出格式（H.265 换成 H.264）

### 导出后没有声音？

检查导出设置中 **"保留配音音轨"** 是否勾选。默认仅导出 AI 配音，原片音频需手动开启。

### 剪映草稿无法导入？

- 确认剪映版本为最新（较老版本可能不兼容新格式）
- 草稿 JSON 文件不可直接双击打开，需在剪映内通过"导入草稿"加载
- 部分 CapCut 国际版不支持中文路径，草稿保存路径避免中文字符

---

## 性能与硬件

### 没有 NVIDIA 显卡能用吗？

能。Voxplore 在无 GPU 时自动回退到 CPU 模式。视频理解会变慢（3x 实时 vs 10x 实时），其他步骤（配音合成、字幕、导出）几乎不受影响。

### 显存不足（OOM）怎么办？

- 关闭 GPU 加速（设置 → AI 配置 → 启用 GPU 加速 → 关闭）
- 减少抽帧密度（设置 → 场景理解 → 抽帧间隔，改为 2 秒）
- 降低视频分辨率（1080p → 720p）
- 使用更小的模型切片（目前仅支持 Qwen2.5-VL 72B）

### 处理速度参考

以一段 **5 分钟 1080p 视频** 为例：

| 阶段 | CPU 模式 | GPU 模式 (RTX 3060) |
|------|----------|---------------------|
| 场景理解 | 约 15–20 分钟 | 约 3–5 分钟 |
| 解说生成 | 约 30 秒 | 约 30 秒 |
| 配音合成 | 约 2 分钟 | 约 2 分钟 |
| 字幕制作 | 约 1 分钟 | 约 1 分钟 |
| 视频导出 | 约 5–10 分钟 | 约 2–3 分钟 |
| **总计** | **约 25–35 分钟** | **约 8–15 分钟** |

---

## 其他

### 如何贡献代码？

见 [贡献指南](../contributing)。

### 商业使用需要授权吗？

不需要。Voxplore 采用 MIT 协议，商用和个人使用均无需授权。但需注意：
- 使用的 AI 模型（DeepSeek / Qwen / Edge-TTS）各有其服务条款，商业场景请自行确认合规
- 生成内容的版权由使用者自行负责，Voxplore 不对输出内容主张任何权利

### 如何获取更新？

- **GitHub Releases**：关注 [Releases 页面](https://github.com/Agions/Voxplore/releases)
- **Watch 仓库**：在 GitHub 页面点击 Watch → Releases only
- **Homebrew**：`brew upgrade narrafiilm`
