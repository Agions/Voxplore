# Voxplore UI Components
# REDESIGNED: frontend-design-pro compliant

# containers
from .containers import MacCard, MacElevatedCard, MacSection

# buttons
from .buttons import MacButton, MacPrimaryButton, MacSecondaryButton, MacDangerButton

# narration editor (Voxplore architecture upgrade)
from .narration import NarrationEditor, NarrationSegmentItem

# timeline shuttle (Voxplore architecture upgrade)
from .timeline import TimelineShuttle, TimelineRuler, TimelineTrack

__all__ = [
    # containers
    "MacCard",
    "MacElevatedCard",
    "MacSection",
    # buttons
    "MacButton",
    "MacPrimaryButton",
    "MacSecondaryButton",
    "MacDangerButton",
    # narration
    "NarrationEditor",
    "NarrationSegmentItem",
    # timeline
    "TimelineShuttle",
    "TimelineRuler",
    "TimelineTrack",
]
