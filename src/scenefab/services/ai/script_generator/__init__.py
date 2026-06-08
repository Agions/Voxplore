"""
AI 文案生成器包

提供 ScriptGenerator 类和便捷函数 generate_script。
"""

from ..script_models import (
    GeneratedScript,
    ScriptConfig,
    ScriptSegment,
    ScriptStyle,
    VoiceTone,
)
from .script_generator import ScriptGenerator, generate_script

__all__ = ["ScriptGenerator", "generate_script"]
