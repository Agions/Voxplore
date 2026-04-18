#!/usr/bin/env python3
"""Test Beat Detector"""

import pytest
from dataclasses import asdict

from app.services.audio.beat_detector import (
    BeatStrength,
    MusicSection,
    BeatInfo,
    SectionInfo,
    AudioAnalysisResult,
    BeatDetector,
)


class TestBeatStrength:
    """Test beat strength enum"""

    def test_enum_values(self):
        """Test enum values"""
        assert BeatStrength.STRONG.value == "strong"
        assert BeatStrength.MEDIUM.value == "medium"
        assert BeatStrength.WEAK.value == "weak"


class TestMusicSection:
    """Test music section enum"""

    def test_all_sections(self):
        """Test all sections"""
        sections = [
            MusicSection.INTRO,
            MusicSection.VERSE,
            MusicSection.CHORUS,
            MusicSection.BRIDGE,
            MusicSection.OUTRO,
        ]
        
        assert len(sections) == 5


class TestBeatInfo:
    """Test beat info"""

    def test_creation(self):
        """Test creation"""
        beat = BeatInfo(
            timestamp=1.5,
            strength=BeatStrength.STRONG,
            bar_position=1,
        )
        
        assert beat.timestamp == 1.5
        assert beat.strength == BeatStrength.STRONG
        assert beat.bar_position == 1


class TestSectionInfo:
    """Test section info"""

    def test_creation(self):
        """Test creation"""
        section = SectionInfo(
            start=0.0,
            end=10.0,
            section_type=MusicSection.INTRO,
            energy=0.8,
        )
        
        assert section.start == 0.0
        assert section.end == 10.0
        assert section.section_type == MusicSection.INTRO
        assert section.energy == 0.8


class TestAudioAnalysisResult:
    """Test audio analysis result"""

    def test_creation(self):
        """Test creation"""
        result = AudioAnalysisResult(
            file_path="/test.mp3",
            duration=180.0,
            sample_rate=44100,
            bpm=120.0,
        )
        
        assert result.file_path == "/test.mp3"
        assert result.duration == 180.0
        assert result.sample_rate == 44100
        assert result.bpm == 120.0


class TestBeatDetector:
    """Test beat detector"""

    def test_init(self):
        """Test initialization"""
        detector = BeatDetector()
        
        assert detector._hop_length == 512

    def test_init_custom_hop_length(self):
        """Test custom hop length"""
        detector = BeatDetector(hop_length=1024)
        
        assert detector._hop_length == 1024
