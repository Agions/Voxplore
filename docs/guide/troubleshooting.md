---
title: 疑难排查
description: SceneFab 常见问题与解决方案。
---

# 疑难排查

## 启动问题

### "No module named 'scenefab'"

```bash
pip install scenefab
```

### "ffmpeg not found"

| 系统 | 解决方法 |
|------|----------|
| Windows | 下载 [FFmpeg](https://ffmpeg.org/download.html)，添加到 PATH |
| macOS | `brew install ffmpeg` |
| Linux | `sudo apt install ffmpeg` |

---

## AI 服务问题

### DeepSeek API Key 无效（401）

1. 确认 Key 格式正确（`sk-` 开头）
2. 检查 Key 是否已过期或被删除
3. 确认 Key 已正确填入设置页

### API 调用报 429 Rate Limit

- 降低并发请求数
- 开启上下文缓存降低 token 消耗
- 升级 DeepSeek 账号套餐

### Qwen VL 分析失败

- 检查 Qwen API Key 余额
- 确认视频格式受支持（mp4/mov/avi/webm）

---

## 视频处理问题

### 视频导入后无响应

- 确认视频文件未损坏
- 尝试重新编码：`ffmpeg -i input.mp4 -c:v libx264 output.mp4`
- 检查磁盘空间是否充足

### 分析时间过长

- 减少视频数量
- 在设置中降低分析帧率（抽帧间隔改为 2 秒）
- 确认网络连接正常（API 调用需联网）

---

## 导出问题

### 导出进度卡在 0%

- 检查临时目录空间
- 确认输出目录有写入权限

### 导出文件无声

- 确认原视频包含音频轨道
- 尝试切换导出编码器

---

## 界面问题

### 窗口显示异常

```
SceneFab > 设置 > 界面 > 重置窗口布局
```

### 侧边栏点击无反应

- 升级到最新版本
- 删除配置文件：`~/.scenefab/config.json`

::: tip
找不到解决方案？ → [提交 Issue](https://github.com/Agions/scene-fab/issues)
:::