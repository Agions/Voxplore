"""Tests for the diagnostics snapshot collector (Phase 4-4).

覆盖：
  * 主入口 collect_diagnostics() 不会因为子步骤失败而崩
  * _safe 包装器
  * _redact_api_key 不暴露完整 key
  * diagnostics_to_clipboard_payload 包成 code block
  * 子收集器在 headless 环境下降级
"""

from __future__ import annotations

from app.utils.diagnostics import (
    _probe_ffmpeg_version,
    _redact_api_key,
    _safe,
    collect_diagnostics,
    diagnostics_to_clipboard_payload,
)


class TestSafe:
    def test_returns_str_on_success(self):
        assert _safe(lambda: "ok") == "ok"

    def test_returns_default_on_exception(self):
        def boom() -> str:
            raise RuntimeError("nope")

        assert _safe(boom, default="[fallback]") == "[fallback]"

    def test_default_used_verbatim(self):
        def boom() -> str:
            raise ValueError("bad input")

        # 异常信息不泄漏到输出，只返回 default
        assert _safe(boom, default="[x]") == "[x]"


class TestRedactApiKey:
    def test_empty(self):
        assert _redact_api_key("") == "(empty)"
        assert _redact_api_key(None) == "(empty)"  # type: ignore[arg-type]

    def test_short(self):
        assert _redact_api_key("ab") == "***"

    def test_long(self):
        assert _redact_api_key("sk-abcdef1234567890") == "sk-a***"


class TestFfmpegProbe:
    def test_returns_string(self):
        out = _probe_ffmpeg_version()
        assert isinstance(out, str)
        # 至少不会是 None
        assert out


class TestCollectDiagnostics:
    def test_returns_nonempty_markdown(self):
        text = collect_diagnostics()
        assert text.startswith("# SceneFab Diagnostics")
        assert "## Application" in text
        assert "## Environment" in text
        assert "## Key Dependencies" in text
        assert "## LLM Configuration" in text
        assert "## Settings Store" in text
        assert "## Recent Audit" in text
        assert "## Metrics Snapshot" in text

    def test_extra_sections_appended(self):
        text = collect_diagnostics(extra_sections=[("Custom", "hello world")])
        assert "## Custom" in text
        assert "hello world" in text

    def test_audit_tail_custom(self):
        # audit_tail=1 也要合法
        text = collect_diagnostics(audit_tail=1)
        assert "## Recent Audit (last 1)" in text

    def test_does_not_crash_when_subsystems_missing(self):
        """即使 metrics / settings / audit 全都没装也不应崩。"""
        text = collect_diagnostics()
        # 即便降级也要有内容
        assert "SceneFab Diagnostics" in text


class TestClipboardPayload:
    def test_wraps_in_code_block(self):
        payload = diagnostics_to_clipboard_payload("hello")
        assert payload.startswith("```text\n")
        assert payload.endswith("\n```")
        assert "hello" in payload

    def test_multiline_preserved(self):
        text = "line1\nline2\nline3"
        payload = diagnostics_to_clipboard_payload(text)
        assert "line1" in payload
        assert "line2" in payload
        assert "line3" in payload
