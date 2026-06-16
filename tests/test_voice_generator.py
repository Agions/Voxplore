#!/usr/bin/env python3
"""Voice generator unit tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from scenefab.services.ai import voice_generator as voice_module
from scenefab.services.ai.voice_generator import VoiceGenerator, generate_voice
from scenefab.services.ai.voice_models import (
    GeneratedVoice,
    VoiceConfig,
    VoiceGender,
    VoiceInfo,
)


class FakeProvider:
    """In-memory provider used to keep tests offline."""

    last_instance: FakeProvider | None = None

    def __init__(self) -> None:
        FakeProvider.last_instance = self
        self.calls: list[tuple[str, str, VoiceConfig]] = []

    def generate(
        self,
        text: str,
        output_path: str,
        config: VoiceConfig,
    ) -> GeneratedVoice:
        self.calls.append((text, output_path, config))
        Path(output_path).write_bytes(b"fake-audio")
        return GeneratedVoice(
            audio_path=output_path,
            duration=1.2,
            text=text,
            voice_id=config.voice_id or "fake-voice",
            format=config.output_format,
        )

    def list_voices(self, language: str = "zh-CN") -> list[VoiceInfo]:
        return [
            VoiceInfo(
                id="fake-voice",
                name="Fake Voice",
                gender=VoiceGender.FEMALE,
                language=language,
            )
        ]


@pytest.fixture
def fake_edge_provider(monkeypatch: pytest.MonkeyPatch) -> type[FakeProvider]:
    FakeProvider.last_instance = None
    monkeypatch.setattr(voice_module, "EdgeTTSProvider", FakeProvider)
    return FakeProvider


def test_edge_provider_generates_audio_file(
    tmp_path: Path,
    fake_edge_provider: type[FakeProvider],
) -> None:
    output = tmp_path / "voice.mp3"
    generator = VoiceGenerator(provider="edge")

    result = generator.generate("第一人称解说", str(output))

    assert output.read_bytes() == b"fake-audio"
    assert result.audio_path == str(output)
    assert result.voice_id == "fake-voice"
    assert isinstance(generator._provider, fake_edge_provider)


def test_generate_segments_skips_empty_text(
    tmp_path: Path,
    fake_edge_provider: type[FakeProvider],
) -> None:
    generator = VoiceGenerator(provider="edge")

    results = generator.generate_segments(
        [
            {"text": "开场冲突", "start": 0.0},
            {"text": "", "start": 1.0},
            {"text": "反转推进", "start": 2.5},
        ],
        str(tmp_path),
    )

    assert [item.text for item in results] == ["开场冲突", "反转推进"]
    assert [item.start_time for item in results] == [0.0, 2.5]
    assert (tmp_path / "segment_000.mp3").exists()
    assert (tmp_path / "segment_002.mp3").exists()
    assert isinstance(generator._provider, fake_edge_provider)


def test_list_voices_delegates_to_provider(
    fake_edge_provider: type[FakeProvider],
) -> None:
    generator = VoiceGenerator(provider="edge")

    voices = generator.list_voices("zh-CN")

    assert voices[0].id == "fake-voice"
    assert voices[0].language == "zh-CN"
    assert isinstance(generator._provider, fake_edge_provider)


def test_generate_voice_helper_passes_voice_and_rate(
    tmp_path: Path,
    fake_edge_provider: type[FakeProvider],
) -> None:
    output = tmp_path / "helper.mp3"

    result = generate_voice(
        "旁白",
        str(output),
        provider="edge",
        voice="custom-voice",
        rate=1.25,
    )

    assert result.voice_id == "custom-voice"
    assert output.exists()
    assert isinstance(FakeProvider.last_instance, fake_edge_provider)
    assert FakeProvider.last_instance.calls[0][2].voice_id == "custom-voice"
    assert FakeProvider.last_instance.calls[0][2].rate == 1.25


def test_openai_provider_requires_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    with pytest.raises(ValueError, match="OpenAI TTS"):
        VoiceGenerator(provider="openai")


def test_unknown_provider_is_rejected() -> None:
    with pytest.raises(ValueError, match="不支持的提供者"):
        VoiceGenerator(provider="unknown")
