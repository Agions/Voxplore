import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESOURCES = ROOT / "resources"
SRC_THEME = ROOT / "src" / "scenefab" / "ui" / "theme"
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def _png_size(path: Path) -> tuple[int, int]:
    data = path.read_bytes()
    assert data[:8] == PNG_SIGNATURE
    return struct.unpack(">II", data[16:24])


def test_app_icon_sizes() -> None:
    expected = {
        "app_icon.png": (512, 512),
        "app_icon_32.png": (32, 32),
        "app_icon_64.png": (64, 64),
        "app_icon_128.png": (128, 128),
        "app_icon_256.png": (256, 256),
        "app_icon_512.png": (512, 512),
    }

    for name, size in expected.items():
        assert _png_size(RESOURCES / "icons" / name) == size


def test_platform_icons_exist() -> None:
    assert (RESOURCES / "icon.ico").read_bytes()[:4] == b"\x00\x00\x01\x00"
    assert (RESOURCES / "icon.icns").read_bytes()[:4] == b"icns"


def test_resource_styles_do_not_use_legacy_tokens() -> None:
    banned = ("oklch", "voxplore", "ai video narrator", "clipflowcut")

    for path in (RESOURCES / "styles").glob("*.qss"):
        text = path.read_text(encoding="utf-8").lower()
        assert not any(token in text for token in banned), path


def test_qss_uses_qt_compatible_syntax() -> None:
    banned = (
        "var(--",
        "linear-gradient(",
        "box-shadow",
        "backdrop-filter",
        "text-transform",
        "transform:",
    )

    for path in [*(RESOURCES / "styles").glob("*.qss"), *SRC_THEME.glob("*.qss")]:
        text = path.read_text(encoding="utf-8").lower()
        assert not any(token in text for token in banned), path

    base_styles = (SRC_THEME / "base_styles.py").read_text(encoding="utf-8").lower()
    assert not any(token in base_styles for token in banned)
