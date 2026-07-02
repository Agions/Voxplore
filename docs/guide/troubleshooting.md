---
title: 疑难排查
description: SceneFab 启动、AI 服务、视频处理和导出的常见问题与解决方案。
---

# 疑难排查

## 启动问题

### No module named 'scenefab'

```bash
pip install scenefab
```

如果已安装仍报错，检查 Python 环境：

```bash
which python3
pip3 show scenefab
```

### ffmpeg not found

| 系统 | 解决方法 |
|------|----------|
| Windows | 下载 [FFmpeg](https://ffmpeg.org/download.html)，添加到 PATH |
| macOS | `brew install ffmpeg` |
| Linux | `sudo apt install ffmpeg` |

### GUI 启动失败

```bash
### 检查 PySide6 是否安装
python3 -c "import PySide6; print(PySide6.__version__)"

### 无头环境使用 offscreen 模式
export QT_QPA_PLATFORM=offscreen
scenefab
```

## AI 服务问题

### API Key 无效（401）

1. 确认 Key 格式正确（`sk-` 开头）
2. 检查 Key 是否已过期或被删除
3. 确认 Key 已正确填入 `config/llm.yaml` 或环境变量

```bash
### 检查环境变量
echo $DEEPSEEK_API_KEY | head -c 3
### 应显示 sk-
```

### API 调用报 429 Rate Limit

- 降低并发请求数
- 等待 1 分钟后重试
- 在服务商控制台升级套餐

### 视频分析失败

- 检查 API Key 余额
- 确认视频格式受支持（mp4 / mov / avi / webm）
- 长视频建议分段处理

## 视频处理问题

### 视频导入后无响应

1. 确认视频文件未损坏
2. 尝试重新编码：`ffmpeg -i input.mp4 -c:v libx264 output.mp4`
3. 检查磁盘空间是否充足

### 分析时间过长

- 减少视频数量
- 在设置中降低分析帧率（抽帧间隔改为 2 秒）
- 确认网络连接正常（API 调用需联网）

### 显存不足（OOM）

```bash
### 关闭 GPU 加速
scenefab --no-gpu

### 减少抽帧密度
scenefab --frame-interval 2

### 降低视频分辨率
ffmpeg -i input.mp4 -vf scale=1280:720 output.mp4
```

## 导出问题

### 导出进度卡在 0%

- 检查临时目录空间
- 确认输出目录有写入权限

### 导出文件无声

- 确认原视频包含音频轨道
- 检查导出设置中"保留配音音轨"是否勾选
- 尝试切换导出编码器

### 剪映草稿无法导入

- 确认剪映版本为最新
- 草稿 JSON 文件需在剪映内通过"导入草稿"加载（不可直接双击）
- 部分 CapCut 国际版不支持中文路径

## 界面问题

### 窗口显示异常

```text
SceneFab > 设置 > 界面 > 重置窗口布局
```

### 侧边栏点击无反应

- 升级到最新版本
- 删除配置文件：`~/.scenefab/config.json`

## 获取帮助

如以上方案均无法解决问题：

- [GitHub Issues](https://github.com/Agions/scene-fab/issues/new?template=bug_report.md) — 提交 Bug 报告
- [GitHub Discussions](https://github.com/Agions/scene-fab/discussions) — 社区讨论
