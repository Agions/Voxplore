---
title: 疑难排查
description: splicr 启动、AI 服务、视频处理和导出的常见问题与解决方案。
---

# 疑难排查

## 启动问题

### macOS 提示"应用已损坏，无法打开。您应该将它移到废纸篓" (Gatekeeper 拦截)

**现象**：从 GitHub 下载 `.dmg` 或 `.app` 后打开，macOS 弹窗提示 `“splicr.app”已损坏，无法打开。您应该将它移到废纸篓。`

**原因**：macOS Gatekeeper 安全机制对未签名或自签名开源软件会自动标记 `com.apple.quarantine` 隔离扩展属性。

**解决**：
打开终端（Terminal），执行以下命令移除隔离属性即可立即正常打开：

```bash
sudo xattr -rd com.apple.quarantine /Applications/splicr.app
```

> 若之前下载的是旧版命名应用，可执行：`sudo xattr -rd com.apple.quarantine /Applications/vynaro.app`

### macOS 提示"无法验证开发者"

**现象**：首次打开应用被系统拦截。

**解决**：

1. 打开「系统设置 → 隐私与安全性」
2. 在底部找到被拦截的 splicr，点击「仍要打开」
3. 或右键应用图标 → 打开 → 在弹窗中确认

### Windows 提示 SmartScreen 拦截

**现象**：运行安装包时提示"Windows 已保护你的电脑"。

**解决**：点击「更多信息」→「仍要运行」。应用经过签名校验，该提示源于安装包尚未积累信誉。

### 窗口白屏或无法打开

**现象**：进程存在但界面空白。

**解决**：

- **Windows**：确认已安装 WebView2 Runtime（Win10 需手动安装，Win11 内置）
- **Linux**：确认已安装 `webkit2gtk-4.1`
- 重启应用；仍无法解决时从终端启动以查看日志：

```bash
# macOS
/Applications/splicr.app/Contents/MacOS/splicr

# Windows（PowerShell）
& "C:\Program Files\Agions\splicr\splicr.exe"
```

### ffmpeg not found

**现象**：视频处理时提示找不到 FFmpeg。

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

安装后需**重启应用**，使其重新探测 PATH。

## AI 服务问题

### API Key 无效（401）

**现象**：调用 AI 服务时返回 401 Unauthorized。

**解决**：

- 打开应用内「设置」页面，重新粘贴 API Key
- 确认 Key 无多余空格或换行
- 确认所选 Provider 与 Key 的归属服务商一致

### API 限流（429）

**现象**：频繁调用后返回 429 Rate Limit。

**解决**：

- 等待 1 分钟后重试
- 在「设置」中切换其他 Provider
- 升级 API 套餐

### 视频分析超时

**现象**：长视频分析卡住或超时。

**解决**：

- 分段处理：将长视频拆分为多个片段
- 降低抽帧频率
- 换用更快的模型档位

### 配音合成失败

**现象**：Edge-TTS 合成失败。

**解决**：

- 检查网络连接（Edge-TTS 需要联网）
- 更换音色（某些音色可能暂时不可用）
- 在「设置 → TTS 引擎」中切换备用引擎

## 导出问题

### 导出失败

**现象**：导出时崩溃或输出文件损坏。

**解决**：

```bash
# 检查 FFmpeg
ffmpeg -version

# 检查磁盘空间
df -h
```

- 降低导出分辨率（720p 替代 1080p）后重试
- 确认输出目录可写且路径不含特殊字符

### 字幕不同步

**现象**：字幕与配音/画面不同步。

**解决**：

- 重新生成字幕，避免手动编辑
- 检查音频采样率（建议 44100Hz）
- 使用 ASS 格式保留样式信息

### 剪映草稿导入失败

**现象**：`.draft.json` 无法导入剪映。

**解决**：

- 确认剪映版本为最新版
- 检查草稿路径是否含中文字符
- 使用英文路径重新导出

## 性能问题

### 处理速度慢

**优化建议**：

| 场景       | 优化方案                     |
| ---------- | ---------------------------- |
| 长视频分析 | 分段处理，每段 < 10min       |
| 导出速度   | 使用 H.264 + 720p            |
| 内存不足   | 关闭其他应用，降低导出分辨率 |

## 联系支持

如果以上方法都无法解决问题：

- [GitHub Issues](https://github.com/Agions/splicr/issues) — 提交时请附上操作系统、应用版本与复现步骤
- 从终端启动应用（见上文）收集日志输出，一并粘贴到 Issue 中

## 相关文档

- [安装指南](/guide/installation) — 完整安装步骤
- [AI 配置](/guide/ai-configuration) — 服务商配置
- [导出发布](/guide/exporting) — 导出与发布流程
