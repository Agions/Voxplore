#!/bin/bash
# SceneFab CLI 使用示例

# ============================================
# 1. 基础命令
# ============================================

# 查看版本
scenefab --version

# 查看帮助
scenefab --help

# 启动 GUI
scenefab

# ============================================
# 2. 解说生成
# ============================================

# 单视频解说生成
scenefab commentary create-movie ./movie.mp4 \
  --style 纪录片 \
  --output ./output/

# 短剧解说生成
scenefab commentary create-drama ./episode01.mp4 \
  --style 悬疑 \
  --platform douyin \
  --output ./output/

# ============================================
# 3. 批量处理
# ============================================

# 批量处理短剧整季
scenefab batch /path/to/series/ \
  --preset short_drama_suspense \
  --parallel 2

# 批量处理指定集数
scenefab batch /path/to/series/ \
  --episodes 1-10 \
  --style 甜宠

# ============================================
# 4. 导出
# ============================================

# 导出到多平台
scenefab export master.mp4 \
  --platforms douyin,bilibili,xiaohongshu

# 导出剪映草稿
scenefab export master.mp4 \
  --format jianying \
  --output ./drafts/

# ============================================
# 5. 配置管理
# ============================================

# 查看当前配置
scenefab --show-config

# 查看可用模型
scenefab --list-models

# ============================================
# 6. 环境变量配置
# ============================================

# 设置 API Key
export DEEPSEEK_API_KEY="sk-your-deepseek-key"
export QWEN_API_KEY="sk-your-qwen-key"

# 或使用 .env 文件
cat > .env << EOF
DEEPSEEK_API_KEY=sk-your-deepseek-key
QWEN_API_KEY=sk-your-qwen-key
EOF
