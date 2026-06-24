"""
Smoke tests for the main SceneFab pipeline.

Exercises the end-to-end flow in sequence using mocks (no real API calls):
  1. VisionService    - video frame understanding
  2. ScriptGenerator  - AI script generation
  3. SubtitleTranslator - subtitle translation
  4. DirectVideoExporter - draft export via FFmpeg

Each component is tested for:
  - Instantiation with config
  - Expected output format
  - Error handling / fallback behaviour
"""

from __future__ import annotations

import shutil
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from scenefab.services.ai.base_llm_provider import LLMRequest, LLMResponse
from scenefab.services.ai.script_models import (
    GeneratedScript,
    ScriptConfig,
    ScriptStyle,
)
from scenefab.services.ai.subtitle_types import (
    SubtitleExtractionResult,
    SubtitleSegment,
)
from scenefab.services.export.direct_video_exporter import (
    DirectVideoExporter,
    Resolution,
    VideoExportConfig,
    VideoFormat,
)

# ---------------------------------------------------------------------------
# anyio backend restriction (only asyncio, no trio)
# ---------------------------------------------------------------------------


@pytest.fixture(params=["asyncio"])
def anyio_backend(request):
    return request.param


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def vision_config() -> dict:
    """Minimal VisionService config (enabled=False so it falls back to mock)."""
    return {
        "name": "qwen",
        "enabled": False,
        "api_key": "",
        "base_url": "",
    }


@pytest.fixture
def llm_config() -> dict:
    """LLMManager config with a single provider for deterministic tests."""
    return {
        "LLM": {
            "qwen": {
                "enabled": True,
                "api_key": "test-qwen-key",
                "model": "qwen3.7-max",
            },
        },
        "default_provider": "qwen",
    }


@pytest.fixture
def sample_frame_bytes() -> bytes:
    """Fake JPEG frame bytes (just enough to hash)."""
    return b"\xff\xd8\xff\xe0" + b"\x00" * 200


@pytest.fixture
def sample_subtitle_result() -> SubtitleExtractionResult:
    """A small subtitle extraction result for translation tests."""
    return SubtitleExtractionResult(
        video_path="/tmp/test.mp4",
        duration=10.0,
        language="zh",
        method="ocr",
        segments=[
            SubtitleSegment(start=0.0, end=2.0, text="你好世界", confidence=0.9, source="ocr"),
            SubtitleSegment(start=2.0, end=4.0, text="这是一个测试", confidence=0.85, source="ocr"),
            SubtitleSegment(start=4.0, end=6.0, text="字幕翻译", confidence=0.8, source="ocr"),
        ],
        full_text="你好世界 这是一个测试 字幕翻译",
    )


def _make_llm_response(content: str = "mock", model: str = "qwen3.7-max") -> LLMResponse:
    return LLMResponse(
        content=content,
        model=model,
        tokens_used=50,
        finish_reason="stop",
    )


def _make_vision_mock_session(mock_response: MagicMock) -> MagicMock:
    """Build a mock requests.Session whose .post() returns *mock_response*."""
    mock_session = MagicMock()
    mock_session.post.return_value = mock_response
    mock_session.mount = MagicMock()
    return mock_session


# =========================================================================
# 2. ScriptGenerator
# =========================================================================


class _StubLLMManager:
    """A minimal async-capable stand-in for LLMManager."""

    def __init__(self, response_content: str = "生成的文案内容"):
        self._content = response_content

    async def generate(
        self, request: LLMRequest, provider=None
    ) -> LLMResponse:
        return _make_llm_response(content=self._content, model="qwen3.7-max")

    async def close_all(self):
        pass

    def get_available_providers(self):
        return []


class TestScriptGeneratorSmoke:
    """Smoke tests for ScriptGenerator (script generation)."""

    def test_instantiation_no_args_raises(self):
        """ScriptGenerator with no api_key and no use_llm_manager raises ValueError."""
        from scenefab.services.ai.script_generator import ScriptGenerator

        with pytest.raises(ValueError, match="请提供 api_key"):
            ScriptGenerator()

    def test_instantiation_with_api_key_ok(self):
        """ScriptGenerator can be constructed with an explicit API key."""
        from scenefab.services.ai.script_generator import ScriptGenerator

        gen = ScriptGenerator(api_key="test-key")
        assert gen.use_llm_manager is False

    @pytest.mark.anyio
    async def test_generate_returns_generated_script(self, llm_config):
        """generate() returns a GeneratedScript with non-empty content."""
        from scenefab.services.ai.script_generator import ScriptGenerator

        stub_manager = _StubLLMManager(response_content="这是一段测试文案，用于验证脚本生成功能。")

        with patch(
            "scenefab.services.ai.script_generator.script_generator.LLMManager",
            return_value=stub_manager,
        ), patch(
            "scenefab.services.ai.script_generator.script_generator.load_llm_config",
            return_value=llm_config,
        ):
            gen = ScriptGenerator(use_llm_manager=True)
            gen.llm_manager = stub_manager

            config = ScriptConfig(style=ScriptStyle.COMMENTARY, target_duration=30)
            script = gen.generate("测试主题", config=config)

        assert script is not None
        assert isinstance(script, GeneratedScript)
        assert len(script.content) > 0
        assert script.provider_used != ""

    @pytest.mark.anyio
    async def test_generate_commentary_shortcut(self, llm_config):
        """generate_commentary() convenience method works."""
        from scenefab.services.ai.script_generator import ScriptGenerator

        stub_manager = _StubLLMManager("解说风格的文案内容。")

        with patch(
            "scenefab.services.ai.script_generator.script_generator.LLMManager",
            return_value=stub_manager,
        ), patch(
            "scenefab.services.ai.script_generator.script_generator.load_llm_config",
            return_value=llm_config,
        ):
            gen = ScriptGenerator(use_llm_manager=True)
            gen.llm_manager = stub_manager
            script = gen.generate_commentary("科幻电影分析", duration=60)

        assert script.content is not None
        assert script.style == ScriptStyle.COMMENTARY

    @pytest.mark.anyio
    async def test_generate_handles_llm_failure(self, llm_config):
        """When the LLM call fails, the generator propagates the error."""
        from scenefab.exceptions import ProviderError
        from scenefab.services.ai.script_generator import ScriptGenerator

        failing_manager = MagicMock()
        failing_manager.generate = AsyncMock(side_effect=ProviderError("所有 Provider 都失败"))
        failing_manager.close_all = AsyncMock()
        failing_manager.get_available_providers = MagicMock(return_value=[])

        with patch(
            "scenefab.services.ai.script_generator.script_generator.LLMManager",
            return_value=failing_manager,
        ), patch(
            "scenefab.services.ai.script_generator.script_generator.load_llm_config",
            return_value=llm_config,
        ):
            gen = ScriptGenerator(use_llm_manager=True)
            gen.llm_manager = failing_manager

            with pytest.raises(ProviderError):
                gen.generate("失败测试")

    def test_script_config_target_words(self):
        """ScriptConfig.target_words is derived from duration and words_per_second."""
        cfg = ScriptConfig(target_duration=60, words_per_second=3.0)
        assert cfg.target_words == 180

    def test_generated_script_word_count_auto(self):
        """GeneratedScript auto-computes word_count from content."""
        script = GeneratedScript(content="一二三四五")
        assert script.word_count == 5

    def test_split_to_captions(self):
        """split_to_captions returns a list of dicts with text/start/end."""
        from scenefab.services.ai.script_generator import ScriptGenerator

        gen = ScriptGenerator(api_key="k")
        script = GeneratedScript(content="你好世界，这是一个测试。")
        captions = gen.split_to_captions(script, _max_chars=10)
        assert isinstance(captions, list)
        if captions:
            assert "text" in captions[0]


# =========================================================================
# 3. SubtitleTranslator
# =========================================================================


def _make_openai_mock_client(content: str) -> MagicMock:
    """Build a mock OpenAI client whose chat completion returns *content*."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content=content))]
    mock_client.chat.completions.create.return_value = mock_response
    return mock_client


class TestSubtitleTranslatorSmoke:
    """Smoke tests for SubtitleTranslator (subtitle translation)."""

    def test_instantiation(self):
        """SubtitleTranslator can be constructed with default provider."""
        from scenefab.services.ai.subtitle_translator import SubtitleTranslator

        t = SubtitleTranslator(api_key="test-key", provider="openai")
        assert t._provider == "openai"

    def test_translate_returns_subtitle_result(self, sample_subtitle_result):
        """translate() returns a SubtitleExtractionResult with translated text."""
        from scenefab.services.ai.subtitle_translator import SubtitleTranslator

        mock_client = _make_openai_mock_client(
            "1. Hello World\n2. This is a test\n3. Subtitle translation"
        )

        with patch("openai.OpenAI", return_value=mock_client):
            translator = SubtitleTranslator(api_key="test-key", provider="openai")
            result = translator.translate(sample_subtitle_result, target_lang="en")

        assert result is not None
        assert isinstance(result, SubtitleExtractionResult)
        assert len(result.segments) == len(sample_subtitle_result.segments)
        assert result.language == "en"
        assert "translated_ocr" in result.method

    def test_translate_empty_segments_passthrough(self):
        """Translating an empty result returns it unchanged."""
        from scenefab.services.ai.subtitle_translator import SubtitleTranslator

        empty = SubtitleExtractionResult(video_path="/tmp/x.mp4", duration=0.0, segments=[])
        translator = SubtitleTranslator(api_key="k", provider="openai")
        result = translator.translate(empty, target_lang="en")
        assert result.segments == []

    def test_translate_unsupported_provider_raises(self, sample_subtitle_result):
        """Using an unsupported provider raises ValueError."""
        from scenefab.services.ai.subtitle_translator import SubtitleTranslator

        translator = SubtitleTranslator(api_key="k", provider="bing_translate")
        with pytest.raises(ValueError, match="不支持的翻译引擎"):
            translator.translate(sample_subtitle_result, target_lang="en")

    def test_translate_preserves_timing(self, sample_subtitle_result):
        """Translated segments retain the original start/end timestamps."""
        from scenefab.services.ai.subtitle_translator import SubtitleTranslator

        mock_client = _make_openai_mock_client("1. Hello\n2. Testing\n3. Subtitles")

        with patch("openai.OpenAI", return_value=mock_client):
            translator = SubtitleTranslator(api_key="test-key", provider="openai")
            result = translator.translate(sample_subtitle_result, target_lang="en")

        for orig, translated in zip(sample_subtitle_result.segments, result.segments, strict=True):
            assert translated.start == orig.start
            assert translated.end == orig.end

    def test_translate_openai_failure_falls_back_to_original(self, sample_subtitle_result):
        """When OpenAI translation fails, original text is preserved as fallback."""
        from scenefab.services.ai.subtitle_translator import SubtitleTranslator

        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = ConnectionError("network error")

        with patch("openai.OpenAI", return_value=mock_client):
            translator = SubtitleTranslator(api_key="test-key", provider="openai")
            result = translator.translate(sample_subtitle_result, target_lang="en")

        # On failure, the batch returns original text
        for seg in result.segments:
            assert seg.text  # not empty

    @pytest.mark.anyio
    async def test_translate_async_returns_result(self, sample_subtitle_result):
        """translate_async() also returns a valid SubtitleExtractionResult."""
        from scenefab.services.ai.subtitle_translator import SubtitleTranslator

        mock_client = _make_openai_mock_client("1. Hi\n2. Test\n3. Sub")

        with patch("openai.OpenAI", return_value=mock_client):
            translator = SubtitleTranslator(api_key="test-key", provider="openai")
            result = await translator.translate_async(sample_subtitle_result, target_lang="en")

        assert result is not None
        assert len(result.segments) == 3

    def test_supported_languages(self):
        """get_supported_languages returns a non-empty dict."""
        from scenefab.services.ai.subtitle_translator import SubtitleTranslator

        translator = SubtitleTranslator(api_key="k")
        langs = translator.get_supported_languages()
        assert isinstance(langs, dict)
        assert "zh" in langs
        assert "en" in langs


# =========================================================================
# 4. DirectVideoExporter
# =========================================================================


def _create_exporter(config: VideoExportConfig | None = None) -> DirectVideoExporter:
    """Helper: construct a DirectVideoExporter with mocked ffmpeg executor."""
    mock_executor = MagicMock()
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_executor.run.return_value = mock_result
    with patch(
        "scenefab.services.export.direct_video_exporter.get_ffmpeg_executor",
        return_value=mock_executor,
    ):
        return DirectVideoExporter(config=config)


def _run_export(
    exporter: DirectVideoExporter,
    project: SimpleNamespace,
    output_path: str,
    mock_executor: MagicMock,
) -> str:
    """
    Run export_commentary with mocked file I/O.

    The exporter creates real temp files (concat list, segment placeholders).
    We mock shutil.copy/shutil.copy2 so the final copy does not require the
    merged video to exist on disk.
    """
    with patch.object(shutil, "copy"), patch.object(shutil, "copy2"):
        return exporter.export_commentary(project, output_path)


class TestDirectVideoExporterSmoke:
    """Smoke tests for DirectVideoExporter (export draft)."""

    def test_instantiation_default_config(self):
        """DirectVideoExporter can be constructed with default config."""
        exporter = _create_exporter()
        assert exporter.config.resolution == Resolution.FHD_1080P
        assert exporter.config.fps == 30.0
        assert exporter.config.format == VideoFormat.MP4

    def test_instantiation_custom_config(self):
        """DirectVideoExporter accepts a custom VideoExportConfig."""
        cfg = VideoExportConfig(
            resolution=Resolution.VERTICAL_1080P,
            fps=60.0,
            format=VideoFormat.MOV,
        )
        exporter = _create_exporter(config=cfg)
        assert exporter.config.resolution == Resolution.VERTICAL_1080P
        assert exporter.config.resolution.width == 1080
        assert exporter.config.resolution.height == 1920
        assert exporter.config.fps == 60.0

    def test_resolution_enum_values(self):
        """Resolution enum provides correct width/height pairs."""
        assert Resolution.FHD_1080P.width == 1920
        assert Resolution.FHD_1080P.height == 1080
        assert Resolution.UHD_4K.width == 3840
        assert Resolution.VERTICAL_1080P.width == 1080
        assert Resolution.VERTICAL_1080P.height == 1920

    def test_export_config_defaults(self):
        """VideoExportConfig has sensible defaults."""
        cfg = VideoExportConfig()
        assert cfg.crf == 23
        assert cfg.preset == "medium"
        assert cfg.video_bitrate == "5M"
        assert cfg.audio_bitrate == "192k"
        assert cfg.include_subtitles is True
        assert cfg.audio_normalize is True

    def test_export_commentary_builds_correct_ffmpeg_calls(self):
        """export_commentary constructs ffmpeg commands with expected parameters."""
        mock_executor = MagicMock()
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_executor.run.return_value = mock_result

        segment = SimpleNamespace(
            video_start=0.0,
            video_end=5.0,
            audio_path=None,
            captions=[],
        )
        project = SimpleNamespace(source_video="/tmp/source.mp4", segments=[segment])

        cfg = VideoExportConfig(
            resolution=Resolution.HD_720P,
            crf=28,
            preset="fast",
            include_subtitles=False,
        )

        with patch(
            "scenefab.services.export.direct_video_exporter.get_ffmpeg_executor",
            return_value=mock_executor,
        ):
            exporter = DirectVideoExporter(config=cfg)
            output = _run_export(exporter, project, "/tmp/output.mp4", mock_executor)

        assert output == "/tmp/output.mp4"
        # Verify ffmpeg was called at least twice (extract + concat)
        assert mock_executor.run.call_count >= 2

        # Verify the extract command contains our resolution and quality settings
        first_call_args = mock_executor.run.call_args_list[0][0][0]
        assert "ffmpeg" in first_call_args
        # Resolution appears inside the -vf scale string
        vf_idx = first_call_args.index("-vf")
        vf_value = first_call_args[vf_idx + 1]
        assert "1280" in vf_value   # HD_720P width
        assert "720" in vf_value    # HD_720P height
        assert "28" in first_call_args    # crf
        assert "fast" in first_call_args  # preset

    def test_export_commentary_with_subtitles(self):
        """When include_subtitles=True and captions exist, subtitle burn-in is attempted."""
        mock_executor = MagicMock()
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_executor.run.return_value = mock_result

        cap = SimpleNamespace(text="Hello", start_time=0.0, end_time=2.0)
        segment = SimpleNamespace(
            video_start=0.0, video_end=5.0, audio_path=None, captions=[cap],
        )
        project = SimpleNamespace(source_video="/tmp/source.mp4", segments=[segment])

        cfg = VideoExportConfig(include_subtitles=True)

        with patch(
            "scenefab.services.export.direct_video_exporter.get_ffmpeg_executor",
            return_value=mock_executor,
        ), patch(
            "scenefab.services.export.subtitle_exporter.SubtitleExporter.export_srt",
        ), patch.object(shutil, "copy"), patch.object(shutil, "copy2"):
            exporter = DirectVideoExporter(config=cfg)
            exporter.export_commentary(project, "/tmp/output_subs.mp4")

        # At least: extract + concat + subtitle burn-in
        assert mock_executor.run.call_count >= 3

    def test_export_commentary_ffmpeg_failure_raises(self):
        """When ffmpeg returns non-zero, the error propagates."""
        mock_executor = MagicMock()
        mock_executor.run.side_effect = RuntimeError("ffmpeg failed: exit 1")

        segment = SimpleNamespace(
            video_start=0.0, video_end=5.0, audio_path=None, captions=[],
        )
        project = SimpleNamespace(source_video="/tmp/source.mp4", segments=[segment])

        with patch(
            "scenefab.services.export.direct_video_exporter.get_ffmpeg_executor",
            return_value=mock_executor,
        ):
            exporter = DirectVideoExporter()
            with pytest.raises(RuntimeError, match="ffmpeg failed"):
                with patch.object(shutil, "copy"), patch.object(shutil, "copy2"):
                    exporter.export_commentary(project, "/tmp/output.mp4")

    def test_progress_callback_invoked(self):
        """set_progress_callback registers a callback that receives stage/progress tuples."""
        mock_executor = MagicMock()
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_executor.run.return_value = mock_result

        segment = SimpleNamespace(
            video_start=0.0, video_end=5.0, audio_path=None, captions=[],
        )
        project = SimpleNamespace(source_video="/tmp/source.mp4", segments=[segment])

        progress_calls: list[tuple[str, float]] = []

        with patch(
            "scenefab.services.export.direct_video_exporter.get_ffmpeg_executor",
            return_value=mock_executor,
        ):
            exporter = DirectVideoExporter()
            exporter.set_progress_callback(lambda stage, pct: progress_calls.append((stage, pct)))
            _run_export(exporter, project, "/tmp/output.mp4", mock_executor)

        assert len(progress_calls) >= 3
        # First call should be "准备导出" at 0.0
        assert progress_calls[0] == ("准备导出", 0.0)
        # Last call should be "导出完成" at 1.0
        assert progress_calls[-1] == ("导出完成", 1.0)

    def test_get_video_codec_default(self):
        """_get_video_codec returns the enum value for default (no hw accel)."""
        exporter = _create_exporter()
        codec = exporter._get_video_codec(exporter.config)
        assert codec == "libx264"

    def test_hw_accel_apple_codec_mapping(self):
        """On macOS, hardware-accelerated codec mapping works."""
        from scenefab.services.export.direct_video_exporter import HWAccel, VideoCodec

        cfg = VideoExportConfig(hw_accel=HWAccel.APPLE, video_codec=VideoCodec.H264)
        exporter = _create_exporter(config=cfg)
        codec = exporter._get_video_codec(cfg)
        assert codec == "h264_videotoolbox"


# =========================================================================
# 5. Pipeline Integration (end-to-end sequence)
# =========================================================================


class TestPipelineSmokeIntegration:
    """
    End-to-end smoke test: script -> subtitles -> export.

    Exercises the pipeline stages in sequence with mocks at every boundary,
    verifying that outputs from one stage can feed into the next.
    """

    @pytest.mark.anyio
    async def test_full_pipeline_sequence(
        self,
        llm_config,
        sample_subtitle_result,
    ):
        """
        Run the pipeline stages in order, verifying each produces
        output that the next stage can consume.
        """
        # ------------------------------------------------------------------
        # Stage 1: Script Generation - generate a script from a description
        # ------------------------------------------------------------------
        from scenefab.services.ai.script_generator import ScriptGenerator

        scene_description = "城市街头场景，第一人称视角漫步"
        script_content = "在这段视频中，我们看到一个城市街头的场景。第一人称视角带领观众漫步其中。"
        stub_manager = _StubLLMManager(response_content=script_content)

        with patch(
            "scenefab.services.ai.script_generator.script_generator.LLMManager",
            return_value=stub_manager,
        ), patch(
            "scenefab.services.ai.script_generator.script_generator.load_llm_config",
            return_value=llm_config,
        ):
            generator = ScriptGenerator(use_llm_manager=True)
            generator.llm_manager = stub_manager

            config = ScriptConfig(style=ScriptStyle.COMMENTARY, target_duration=30)
            script = generator.generate(scene_description, config=config)

        assert script.content is not None
        assert len(script.content) > 0

        # ------------------------------------------------------------------
        # Stage 3: Subtitle Translation - translate subtitles to English
        # ------------------------------------------------------------------
        from scenefab.services.ai.subtitle_translator import SubtitleTranslator

        mock_client = _make_openai_mock_client(
            "1. Hello World\n2. This is a test\n3. Subtitle translation"
        )

        with patch("openai.OpenAI", return_value=mock_client):
            translator = SubtitleTranslator(api_key="test-key", provider="openai")
            translated = translator.translate(sample_subtitle_result, target_lang="en")

        assert translated is not None
        assert translated.language == "en"
        assert len(translated.segments) == 3

        # ------------------------------------------------------------------
        # Stage 4: Export - build an export config and verify ffmpeg calls
        # ------------------------------------------------------------------
        mock_executor = MagicMock()
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_executor.run.return_value = mock_result

        cap = SimpleNamespace(
            text=translated.segments[0].text,
            start_time=translated.segments[0].start,
            end_time=translated.segments[0].end,
        )
        segment = SimpleNamespace(
            video_start=0.0, video_end=6.0, audio_path=None, captions=[cap],
        )
        project = SimpleNamespace(source_video="/tmp/source.mp4", segments=[segment])

        export_cfg = VideoExportConfig(
            resolution=Resolution.FHD_1080P,
            include_subtitles=True,
        )

        with patch(
            "scenefab.services.export.direct_video_exporter.get_ffmpeg_executor",
            return_value=mock_executor,
        ), patch(
            "scenefab.services.export.subtitle_exporter.SubtitleExporter.export_srt",
        ), patch.object(shutil, "copy"), patch.object(shutil, "copy2"):
            exporter = DirectVideoExporter(config=export_cfg)
            output_path = exporter.export_commentary(project, "/tmp/final.mp4")

        assert output_path == "/tmp/final.mp4"
        assert mock_executor.run.call_count >= 3  # extract + concat + subtitle
