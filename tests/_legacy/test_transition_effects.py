#!/usr/bin/env python3
"""Test Transition Effects"""


from app.services.video.transition_effects import (
    TransitionType,
    TransitionConfig,
    TransitionEffects,
)


class TestTransitionType:
    """Test transition type enum"""

    def test_basic_transitions(self):
        """Test basic transitions"""
        assert TransitionType.CUT.value == "cut"
        assert TransitionType.FADE.value == "fade"
        assert TransitionType.FADE_BLACK.value == "fade_black"
        assert TransitionType.FADE_WHITE.value == "fade_white"

    def test_dissolve_transitions(self):
        """Test dissolve transitions"""
        assert TransitionType.DISSOLVE.value == "dissolve"

    def test_wipe_transitions(self):
        """Test wipe transitions"""
        assert TransitionType.WIPE_LEFT.value == "wipe_left"
        assert TransitionType.WIPE_RIGHT.value == "wipe_right"

    def test_slide_transitions(self):
        """Test slide transitions"""
        assert TransitionType.SLIDE_LEFT.value == "slide_left"
        assert TransitionType.SLIDE_RIGHT.value == "slide_right"

    def test_zoom_transitions(self):
        """Test zoom transitions"""
        assert TransitionType.ZOOM_IN.value == "zoom_in"
        assert TransitionType.ZOOM_OUT.value == "zoom_out"


class TestTransitionConfig:
    """Test transition config"""

    def test_default_creation(self):
        """Test default creation"""
        config = TransitionConfig()
        
        assert config.type == TransitionType.FADE
        assert config.duration == 0.5
        assert config.easing == "easeInOut"

    def test_custom_creation(self):
        """Test custom creation"""
        config = TransitionConfig(
            type=TransitionType.DISSOLVE,
            duration=1.0,
            easing="easeOut",
        )
        
        assert config.type == TransitionType.DISSOLVE
        assert config.duration == 1.0
        assert config.easing == "easeOut"


class TestTransitionEffects:
    """Test transition effects"""

    def test_init(self):
        """Test initialization"""
        effects = TransitionEffects()
        
        assert effects is not None

    def test_list_available_transitions(self):
        """Test list available transitions"""
        transitions = TransitionEffects.list_available_transitions()
        
        assert isinstance(transitions, list)

    def test_get_xfade_transitions(self):
        """Test get xfade transitions"""
        transitions = TransitionEffects.get_xfade_transitions()
        
        assert isinstance(transitions, list)
