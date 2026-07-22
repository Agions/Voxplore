from scenefab.services.export import (
    DEFAULT_VERTICAL_RESOLUTION,
    ExportPreset,
    bitrate_label,
    normalize_resolution,
    parse_bitrate_kbps,
)


def test_export_preset_defaults_target_vertical_short_video():
    preset = ExportPreset()

    assert preset.resolution == DEFAULT_VERTICAL_RESOLUTION
    assert preset.bitrate == "8000k"
    assert preset.audio_bitrate == "192k"
    assert preset.id == preset.name


def test_normalize_resolution_accepts_ui_labels_and_sequences():
    assert normalize_resolution("1080x1920 (竖屏 9:16)") == "1080x1920"
    assert normalize_resolution("1920 × 1080") == "1920x1080"
    assert normalize_resolution((720, 1280)) == "720x1280"
    assert normalize_resolution("自定义") == DEFAULT_VERTICAL_RESOLUTION


def test_parse_bitrate_kbps_accepts_common_units():
    assert parse_bitrate_kbps("8M") == 8000
    assert parse_bitrate_kbps("8 Mbps") == 8000
    assert parse_bitrate_kbps("5000k") == 5000
    assert parse_bitrate_kbps("192 kbps") == 192
    assert parse_bitrate_kbps(320) == 320


def test_bitrate_label_is_human_readable():
    assert bitrate_label("8000k") == "8 Mbps"
    assert bitrate_label("192k") == "192 kbps"


def test_export_preset_from_dict_canonicalizes_legacy_values():
    preset = ExportPreset.from_dict(
        {
            "name": "Shorts",
            "resolution": [1080, 1920],
            "bitrate": "8M",
            "audio_bitrate": 192,
        }
    )

    assert preset.id == "Shorts"
    assert preset.resolution == "1080x1920"
    assert preset.bitrate == "8000k"
    assert preset.audio_bitrate == "192k"
