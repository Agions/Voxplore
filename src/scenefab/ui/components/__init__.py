# SceneFab UI Components
# REDESIGNED: frontend-design-pro compliant

# containers
# buttons
from scenefab.ui.common.macos_components import MacIconButton

from .buttons import MacButton, MacDangerButton, MacPrimaryButton, MacSecondaryButton
from .containers import MacCard, MacElevatedCard, MacSection
from .labels import MacBadge, MacLabel, MacTitleLabel

# narration editor (SceneFab architecture upgrade)
from .narration import NarrationEditor, NarrationSegmentItem

# timeline shuttle (SceneFab architecture upgrade)
from .timeline import TimelineRuler, TimelineShuttle, TimelineTrack

__all__ = [
 # containers
 "MacCard",
 "MacElevatedCard",
 "MacSection",
 # buttons
 "MacIconButton",
 "MacButton",
 "MacPrimaryButton",
 "MacSecondaryButton",
 "MacDangerButton",
 # labels
 "MacBadge",
 "MacLabel",
 "MacTitleLabel",
 # narration
 "NarrationEditor",
 "NarrationSegmentItem",
 # timeline
 "TimelineShuttle",
 "TimelineRuler",
 "TimelineTrack",
]  # noqa: F401 (re-exported for public API: from scenefab.ui.components import MacIconButton)
