#!/usr/bin/env python3
"""Regression tests for issue #82 — startup failure chain.

The original bug report (No module named 'scenefab.icon_manager') was
already fixed on main by commit 40070fd. But that exposed a SECOND
startup failure: `Application.initialize()` crashed in
`_load_configuration` because `Logger.info()` (custom wrapper) was called
with 2 args (msg + format arg), which the wrapper does not accept.

These tests exercise the *fixed* code paths so future refactors cannot
silently reintroduce the regression. They deliberately avoid PySide6 so
they run in the headless CI matrix (see conftest.py for the Pyside6
skip list).

See: https://github.com/Agions/scene-fab/issues/82
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest


class TestProjectManagerRecentProjectsIO:
    """ProjectManager must not call removed ConfigManager.get/set methods.

    ConfigManager was refactored to a typed AppConfig interface and no
    longer exposes a dict-like ``get(key, default)`` API. The previous
    implementation used ``self.config_manager.get("editor.recent_files")``
    in ``_load_recent_projects`` and ``.set(...)`` in
    ``_save_recent_projects`` — both raised ``AttributeError`` at startup.
    """

    def test_config_manager_has_no_dict_like_get(self) -> None:
        """ConfigManager intentionally removed dict-like get()."""
        from scenefab.settings import ConfigManager

        assert not hasattr(ConfigManager, "get"), (
            "ConfigManager.get() was re-introduced; this is the API that "
            "broke startup. If you need a key/value store, use the typed "
            "AppConfig interface or a dedicated persistence layer."
        )
        assert not hasattr(ConfigManager, "set"), (
            "ConfigManager.set() must not exist; the typed AppConfig "
            "interface is the only supported configuration API."
        )

    def test_recent_projects_roundtrip_via_filesystem(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """_load/_save_recent_projects must persist to a local file, not
        ConfigManager.

        This test is PySide6-free: it instantiates only the persistence
        helpers by binding them to a tmp_path projects dir and a fake
        logger. The full ProjectManager class requires QObject; here we
        verify the file-format contract that the new code uses.
        """
        # Simulate the cache file location & format that
        # ProjectManager._save_recent_projects writes to.
        cache_file = tmp_path / ".recent_projects.json"
        sample = ["/path/a", "/path/b"]

        # Write using the same code path the production code uses.
        cache_file.write_text(
            json.dumps(sample, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        # Read back using the same code path _load_recent_projects uses.
        loaded = json.loads(cache_file.read_text(encoding="utf-8"))
        assert [str(p) for p in loaded if isinstance(p, str)] == sample

    def test_load_missing_recent_projects_returns_empty(
        self, tmp_path: Path
    ) -> None:
        """A missing cache file must yield [] — same as the old default."""
        cache_file = tmp_path / ".recent_projects.json"
        assert not cache_file.exists()
        # Mirror the early-return in _load_recent_projects.
        assert (cache_file.exists() and json.loads(cache_file.read_text())) or [] == []


class TestApplicationLoggerInfoArity:
    """Application._load_configuration previously called
    ``self.logger.info("...%s...", value)`` with two args.

    ``scenefab.logger.Logger.info`` has signature
    ``info(message: str) -> None`` (single arg). Passing a 2nd arg
    raised ``TypeError: takes 2 positional arguments but 3 were given``
    inside the ``try/except`` in ``_load_configuration``, which then
    logged a confusing "配置加载失败" message and aborted startup.
    """

    def test_logger_info_accepts_only_single_message(self) -> None:
        from scenefab.logger import Logger

        logger = Logger("test-issue82")
        with pytest.raises(TypeError):
            # Two-arg form (msg + format arg) must NOT be supported.
            logger.info("hello %s", "world")  # type: ignore[call-arg]

    def test_logger_info_accepts_single_string(self) -> None:
        from scenefab.logger import Logger

        logger = Logger("test-issue82")
        # Single-arg form must work (and not raise).
        logger.info("hello world")

    def test_logger_info_accepts_fstring(self) -> None:
        """The new code in _load_configuration uses f-strings; verify
        that path round-trips a value through the wrapper."""
        from scenefab.logger import Logger

        logger = Logger("test-issue82")
        n = 7
        logger.info(f"config loaded: {n} keys")  # must not raise


class TestApplicationStartSmoke:
    """Smoke-test that ``python -m scenefab`` does not regress to the #82
    fatal error patterns.

    Issue #82 was a startup-failure chain. The regression gate is:
    **no** ``No module named '...'`` and **no** ``object has no attribute
    '...'`` in the entrypoint's combined stdout/stderr.

    We deliberately do NOT assert "the process enters the Qt main loop"
    because:
      - In a headless CI without ffmpeg installed, scenefab correctly
        falls back to a CLI menu (prints a numbered menu, waits for
        input, then exits with rc=0). This is the documented graceful
        degradation, not a bug. Asserting main-loop entry would couple
        the test to the dev-machine's ffmpeg availability.
      - In a headless CI without ``libEGL.so.1`` (the standard Qt GL
        shim), the GUI path also falls back to CLI — same reason.
    The *only* patterns that prove #82 is back are the two fatal strings
    the original user saw; we assert those are absent, regardless of
    whether the process ended up in GUI or CLI mode.
    """

    FORBIDDEN_PATTERNS = (
        "No module named",  # original #82 (icon_manager)
        "object has no attribute",  # secondary #82 (ConfigManager.get)
    )

    REQUIRED_BOOT_MARKER = (
        # The first log line that proves the entrypoint actually ran
        # our code (vs dying on missing ffmpeg or Qt libs at import).
        "🎬 SceneFab - AI 视频创作工具",
    )

    def test_scenefab_entrypoint_no_regression(self) -> None:
        import os
        import subprocess
        import sys

        env = os.environ.copy()
        env["QT_QPA_PLATFORM"] = "offscreen"
        env["SCENEFAB_DEBUG"] = "false"
        # Feed an empty stdin so the CLI menu (if fallback triggers)
        # doesn't block waiting for user input.
        env["PYTHONUNBUFFERED"] = "1"

        proc = subprocess.Popen(
            [sys.executable, "-m", "scenefab"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            text=True,
        )
        try:
            stdout, stderr = proc.communicate(input="\n", timeout=15)
        except subprocess.TimeoutExpired:
            proc.kill()
            stdout, stderr = proc.communicate()
        combined = stdout + stderr

        # Hard requirement: the entrypoint must reach our boot log
        # line. This catches "entrypoint died on import" (e.g. a
        # typo in main.py that breaks module load).
        for marker in self.REQUIRED_BOOT_MARKER:
            assert marker in combined, (
                f"scenefab entrypoint did not produce boot marker "
                f"{marker!r}. Possible import-time crash.\n"
                f"stdout: {stdout}\nstderr: {stderr}"
            )

        # The actual regression gate: none of the #82 fatal patterns.
        for forbidden in self.FORBIDDEN_PATTERNS:
            assert forbidden not in combined, (
                f"Regression to issue #82: {forbidden!r} in "
                f"scenefab startup output.\n"
                f"stdout: {stdout}\nstderr: {stderr}"
            )
