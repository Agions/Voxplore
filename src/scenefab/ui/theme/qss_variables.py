"""Compatibility hook for the older token-to-QSS pipeline."""


def register_qss_variables() -> str:
    """Return a harmless marker; Qt QSS does not support CSS variables."""
    return "/* SceneFab tokens are resolved before QSS is applied. */"
