"""text_utils 模块测试 — 句子分割与风格映射。"""


from scenefab.pipeline.narration_context import ProductionStyle
from scenefab.pipeline.text_utils import (
    PRODUCTION_TO_SCRIPT_STYLE,
    split_sentences,
)


class TestSplitSentences:
    """split_sentences 函数测试。"""

    def test_basic_split(self) -> None:
        result = split_sentences("你好。世界！再见？")
        assert result == ["你好。", "世界！", "再见？"]

    def test_single_sentence(self) -> None:
        assert split_sentences("你好。") == ["你好。"]

    def test_no_punctuation(self) -> None:
        assert split_sentences("你好世界") == ["你好世界"]

    def test_empty_string(self) -> None:
        assert split_sentences("") == []

    def test_punctuation_attached_to_preceding(self) -> None:
        result = split_sentences("他说。她笑了。")
        assert all(s.endswith("。") for s in result)

    def test_mixed_punctuation(self) -> None:
        result = split_sentences("真的吗？太好了！走吧。")
        assert len(result) == 3
        assert result[0].endswith("？")
        assert result[1].endswith("！")
        assert result[2].endswith("。")

    def test_whitespace_between_sentences_preserved(self) -> None:
        result = split_sentences("  。  。  ")
        assert result == ["  。", "  。"]


class TestProductionToScriptStyle:
    """PRODUCTION_TO_SCRIPT_STYLE 映射测试。"""

    def test_all_production_styles_mapped(self) -> None:
        for style in ProductionStyle:
            assert style in PRODUCTION_TO_SCRIPT_STYLE

    def test_mapping_values(self) -> None:
        assert PRODUCTION_TO_SCRIPT_STYLE[ProductionStyle.SUSPENSE] == "monologue"
        assert PRODUCTION_TO_SCRIPT_STYLE[ProductionStyle.ROMANCE] == "monologue"
        assert PRODUCTION_TO_SCRIPT_STYLE[ProductionStyle.REVENGE] == "commentary"
        assert PRODUCTION_TO_SCRIPT_STYLE[ProductionStyle.COMEDY] == "viral"
        assert PRODUCTION_TO_SCRIPT_STYLE[ProductionStyle.LITERARY] == "narration"
        assert PRODUCTION_TO_SCRIPT_STYLE[ProductionStyle.NEUTRAL] == "commentary"

    def test_mapping_is_dict(self) -> None:
        assert isinstance(PRODUCTION_TO_SCRIPT_STYLE, dict)
