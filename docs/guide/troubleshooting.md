---
title: 疑难排查
description: SceneFab 启动、AI 服务、视频处理和导出的常见问题与解决方案。
---

# 疑难排查

## 启动问题

### No module named 'scenefab'

**现象**：运行 `scenefab` 报错 `ModuleNotFoundError`

**解决**：

```bash
# 确认使用正确 Python
python -c "import scenefab; print(scenefab.__version__)"

# 如果报错，重新安装
pip install --upgrade --force-reinstall scenefab
```

### ffmpeg not found

**现象**：视频处理时提示 `ffmpeg: command not found`

**解决**：

```bash
# macOS
brew install ffmpeg

# Ubuntu/Debian
sudo apt install ffmpeg

# Windows
winget install ffmpeg

# 验证
ffmpeg -version
```

### GUI 启动失败

**现象**：PySide6 相关错误，无法打开界面

**解决**：

```bash
# 检查 PySide6 是否安装
python -c "from PySide6.QtCore import qVersion; print('Qt', qVersion())"

# 安装 PySide6
pip install PySide6

# 无头环境使用 offscreen 模式
QT_QPA_PLATFORM=offscreen scenefab
```

### 内存不足

**现象**：处理大视频时崩溃或卡顿

**解决**：

- 降低导出分辨率（720p 替代 1080p）
- 关闭其他应用释放内存
- 使用分段处理：将长视频拆分为多个片段

## AI 服务问题

### API Key 无效（401）

**现象**：调用 AI 服务时返回 401 Unauthorized

**解决**：

```bash
# 检查环境变量
echo $DEEPSEEK_API_KEY
echo $QWEN_API_KEY

# 检查配置文件
cat config/llm.yaml

# 确认 Key 格式正确（无多余空格、换行）
```

### API 限流（429）

**现象**：频繁调用后返回 429 Rate Limit

**解决**：

- 等待 1 分钟后重试
- 升级 API 套餐
- 降低并发请求数量

### 视频分析超时

**现象**：长视频分析卡住或超时

**解决**：

- 分段处理：将长视频拆分为多个片段
- 降低抽帧频率
- 使用更快的模型（如 qwen3.7-plus）

### 配音合成失败

**现象**：Edge-TTS 合成失败

**解决**：

- 检查网络连接（Edge-TTS 需要联网）
- 更换音色（某些音色可能暂时不可用）
- 使用 F5-TTS 本地合成

## 导出问题

### 导出失败

**现象**：导出时崩溃或输出文件损坏

**解决**：

```bash
# 检查 FFmpeg
ffmpeg -version

# 检查磁盘空间
df -h

# 降低分辨率重试
# 在界面中选择 720p 而非 1080p
```

### 字幕不同步

**现象**：字幕与配音/画面不同步

**解决**：

- 检查音频采样率（建议 44100Hz）
- 重新生成字幕，避免手动编辑
- 使用 ASS 格式保留样式信息

### 剪映草稿导入失败

**现象**：`.draft.json` 无法导入剪映

**解决**：

- 确认剪映版本为最新版
- 检查草稿路径是否含中文字符
- 使用英文路径重新导出

## 性能问题

### 处理速度慢

**优化建议**：

| 场景 | 优化方案 |
|------|----------|
| 长视频分析 | 分段处理，每段 < 10min |
| 配音合成 | 使用 Edge-TTS 而非 F5-TTS |
| 导出速度 | 使用 H.264 + 720p |
| 内存不足 | 关闭其他应用，升级内存 |

### GPU 加速未生效

**检查**：

```bash
# NVIDIA GPU
nvidia-smi

# Apple Silicon
system_profiler SPDisplaysDataType
```

## 联系支持

如果以上方法都无法解决问题：

- [GitHub Issues](https://github.com/Agions/scene-fab/issues)
- 提供日志文件：`~/.cache/scenefab/logs/`

## 相关文档

- [安装指南](/guide/installation) — 完整安装步骤
- [AI 配置](/guide/ai-configuration) — 服务商配置
- [CLI 参考](/guide/cli-reference) — 命令行参数
