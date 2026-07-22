# Task 7 Report

## Commits Made

- `fed6e5f` — chore: 删除冗余脚本 build.py main.spec 和根目录 conftest.py

## Verification Results

All Step 3 checks passed:
- `OK: build.py deleted`
- `OK: main.spec deleted`
- `OK: root conftest.py deleted`

`tests/conftest.py` now contains both required sections:
1. **PySide6 GUI skip logic** — defines `_PYSIDE6_GUI_TESTS` and sets `collect_ignore` when PySide6 is unavailable.
2. **FFmpeg mock** — `mock_ffmpeg_check` fixture patches `scenefab.services.video.ffmpeg_tool.FFmpegTool.check_ffmpeg`.

## Concerns

None.
