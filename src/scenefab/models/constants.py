"""
SceneFab 项目常量

集中管理硬编码值、API URL、魔法数字。
"""

# ══════════════════════════════════════════════════════════════
# 网络/API 默认值
# ══════════════════════════════════════════════════════════════

DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 8000

# 平台数据 API
DOUYIN_API_BASE = "https://open.douyin.com/api"
BILIBILI_API_BASE = "https://api.bilibili.com"
YOUTUBE_API_BASE = "https://www.googleapis.com/youtube/v3"
KUAISHOU_API_BASE = "https://open.kuaishou.com"
XIAOHONGSHU_API_BASE = "https://open.xiaohongshu.com"

# AI 服务
DASHSCOPE_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
DEEPL_API_URL = "https://api-free.deepl.com/v2/translate"
GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"

# ══════════════════════════════════════════════════════════════
# 视频/媒体默认值
# ══════════════════════════════════════════════════════════════

DEFAULT_VIDEO_WIDTH = 1920
DEFAULT_VIDEO_HEIGHT = 1080
DEFAULT_FPS = 30
DEFAULT_AUDIO_SAMPLE_RATE = 48000
DEFAULT_AUDIO_BITRATE = 192_000

# Premiere 时间戳基数
PREMIERE_TICKS_PER_SECOND = 254_016_000_000

# ══════════════════════════════════════════════════════════════
# 缓存默认值
# ══════════════════════════════════════════════════════════════

DEFAULT_CACHE_MAX_ENTRIES = 1000
DEFAULT_CACHE_MAX_MEMORY_MB = 100
DEFAULT_CACHE_MAX_DISK_MB = 1000

# ══════════════════════════════════════════════════════════════
# 业务阈值
# ══════════════════════════════════════════════════════════════

VIRAL_VIEW_THRESHOLD = 1_000_000  # 病毒式传播阈值
