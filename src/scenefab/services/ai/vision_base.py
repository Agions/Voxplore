"""
视觉分析基类和通用定义

从 vision_providers.py 提取，解决循环导入问题。
所有 vision provider（包括 providers/ 子目录下的）都从这里导入基类。
"""

import base64
import json
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from scenefab.exceptions import ProviderError


@dataclass
class VisionAnalysisResult:
    """视觉分析结果

    同时支持属性访问（result.description）和字典风格访问（result["description"]），
    以保持与 ``dict[str, Any]`` 调用方的兼容性。
    """

    description: str = ""
    content_type: str = "unknown"
    objects: list[str] = field(default_factory=list)
    text_content: str = ""
    emotion: str = "neutral"
    color_tone: str = "neutral"
    confidence: float = 0.0
    raw_response: str = ""
    # 第一人称解说专用字段
    scene_narrative: str = ""  # 场景叙事（"我"看到什么）
    protagonist_action: str = ""  # 主角动作
    environment_mood: str = ""  # 环境氛围
    first_person_hook: str = ""  # 适合第一人称的开场钩子

    # ---- dict-like protocol for backward compatibility ----

    def __getitem__(self, key: str) -> Any:
        """Allow ``result["description"]`` style access."""
        try:
            return getattr(self, key)
        except AttributeError:
            raise KeyError(key)

    def __contains__(self, key: object) -> bool:
        """Allow ``"description" in result`` style checks."""
        if not isinstance(key, str):
            return False
        return hasattr(self, key)

    def get(self, key: str, default: Any = None) -> Any:
        """Dict-style ``.get()`` method."""
        return getattr(self, key, default)

    def keys(self):
        """Return field names (dict-like)."""
        return [f.name for f in self.__dataclass_fields__.values()]

    def to_dict(self) -> dict[str, Any]:
        """Explicit conversion to a plain dict."""
        return asdict(self)


# ============================================================================
# 默认提示词（通用场景理解）
# ============================================================================
VISION_ANALYSIS_PROMPT = """分析这张视频截图，返回JSON格式：
{
    "description": "详细描述画面内容（50-100字）",
    "content_type": "person/landscape/indoor/outdoor/text/product/animal/food/action",
    "objects": ["检测到的主要物体列表"],
    "text": "画面中出现的文字（如果有）",
    "emotion": "neutral/happy/sad/excited/calm/tense/romantic",
    "color_tone": "warm/cold/neutral",
    "suitable_for": {
        "commentary": 0-100,
        "monologue": 0-100,
        "mashup": 0-100
    }
}
只返回JSON，不要其他内容。"""


# ============================================================================
# 第一人称解说专用提示词
# ============================================================================
FIRST_PERSON_ANALYSIS_PROMPT = """你是一位专业的电影分镜师和第一人称叙事导演。

分析这段视频截图，用"我"（画面中主角）的视角描述所见所行。

返回JSON格式：
{
    "description": "客观描述画面内容（30-60字）",
    "content_type": "person/landscape/indoor/outdoor/product/action/scenery",
    "objects": ["画面中主要物体"],
    "emotion": "neutral/happy/sad/calm/excited/tense/wonder/awe",
    "color_tone": "warm/cold/muted/vibrant",
    "protagonist_action": "主角正在做什么（用动词，简洁）",
    "environment_mood": "环境氛围关键词（3-5个）",
    "first_person_hook": "一句适合第一人称的开场叙述（10-20字，要有画面感）",
    "narrative_angle": "这个场景适合从哪个角度切入叙事（旁观/内心独白/现场解说）"
}

注意：
- protagist_action 站在主角立场描述，而非旁观者
- first_person_hook 要有沉浸感，像主角在说话
- 只返回JSON，不要解释"""


# ============================================================================
# Provider 基类
# ============================================================================
class VisionProvider(ABC):
    """视觉分析提供者基类"""

    @abstractmethod
    def analyze_image(
        self, image_base64: str, prompt: str = VISION_ANALYSIS_PROMPT
    ) -> dict[str, Any] | VisionAnalysisResult:
        """分析图片，返回解析后的字典或结构化结果"""
        pass

    @abstractmethod
    def get_name(self) -> str:
        pass

    @staticmethod
    def _parse_json_response(content: str) -> dict[str, Any]:
        """从可能包含 markdown 的响应中提取 JSON"""
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]
        try:
            return json.loads(content.strip())  # type: ignore[no-any-return]
        except json.JSONDecodeError:
            return {"description": content.strip()}

    @staticmethod
    def read_image_as_base64(image_path: str | Path) -> str:
        """Read ``image_path`` and return base64-encoded UTF-8 string.

        Raises ``ProviderError`` if the file does not exist. Shared by
        every vision-capable provider (Claude / Gemini / OpenAI-Compat)
        to avoid re-implementing the same ``open(path, "rb").read()``
        dance in each subclass.
        """
        p = Path(image_path)
        if not p.exists():
            raise ProviderError(f"图片不存在: {p}")
        with open(p, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")

    # MIME map shared by all vision providers. ``.jpeg`` is normalised to
    # ``image/jpeg`` (Anthropic / OpenAI both accept this canonical form).
    _IMAGE_MIME_MAP: dict[str, str] = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
        ".gif": "image/gif",
    }

    @classmethod
    def detect_image_mime(cls, image_path: str | Path) -> str:
        """Infer MIME type from file suffix. Falls back to ``image/jpeg``."""
        suffix = Path(image_path).suffix.lower()
        return cls._IMAGE_MIME_MAP.get(suffix, "image/jpeg")
