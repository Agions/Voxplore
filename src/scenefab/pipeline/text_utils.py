"""Pipeline 文本处理工具函数。"""

import re

from scenefab.pipeline.narration.context import ProductionStyle


def split_sentences(text: str) -> list[str]:
    """按中文句末标点分割文本，保留标点附着在前句末尾。

    >>> split_sentences("你好。世界！再见？")
    ['你好。', '世界！', '再见？']
    """
    parts = re.split(r"([。！？])", text)
    sentences: list[str] = []
    i = 0
    while i < len(parts):
        s = parts[i]
        if i + 1 < len(parts) and parts[i + 1] in ("。", "！", "？"):
            s += parts[i + 1]
            i += 2
        else:
            i += 1
        if s.strip():
            sentences.append(s)
    return sentences


# ProductionStyle → ScriptStyle 映射（唯一权威定义）
PRODUCTION_TO_SCRIPT_STYLE: dict[ProductionStyle, str] = {
    ProductionStyle.SUSPENSE: "monologue",
    ProductionStyle.ROMANCE: "monologue",
    ProductionStyle.REVENGE: "commentary",
    ProductionStyle.UNDERDOG: "commentary",
    ProductionStyle.COMEDY: "viral",
    ProductionStyle.LITERARY: "narration",
    ProductionStyle.NEUTRAL: "commentary",
}
