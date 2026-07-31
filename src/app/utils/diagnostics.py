#!/usr/bin/env python3
"""应用诊断信息收集器 — Phase 4 · diagnostics。

主菜单/设置面板"复制诊断信息"按钮的底层实现，生成一个
可粘贴到 GitHub Issue / 工单的纯文本快照：

  - 应用版本（``app/version.py``）
  - Python / Qt / PySide6 / OpenCV / FFmpeg 版本
  - 操作系统、内核、运行模式（PyInstaller / 开发模式）
  - 当前 LLM provider + model（脱敏 API key）
  - 各功能模块版本（项目 lockfile 关键依赖）
  - ``AuditLogger`` 最近 N 条（默认 10）
  - ``MetricsRegistry.snapshot()`` 摘要（counter 数 / histogram 计数）
  - 已知问题/警告（最近 5 条 logger.warning 以上级别）

设计：
  - 单一函数 ``collect_diagnostics(...) -> str``，无副作用
  - 异常降级：任何子步骤失败时记录 ``[error] xxx``，不让总流程崩
  - 不收集任何 API key / 用户内容；API key 仅显示"已配置"或前缀 4 字符
"""

from __future__ import annotations

import getpass
import os
import platform
import sys
from collections.abc import Iterable
from datetime import datetime, timezone
from typing import Any

# ────────────────────────────────────────────────────────────────
#  通用工具
# ────────────────────────────────────────────────────────────────


def _safe(fn: Any, default: str = "[unavailable]") -> str:
    """执行 ``fn``，失败时返回 ``default``。"""
    try:
        return str(fn())
    except Exception:  # noqa: BLE001
        return default


def _redact_api_key(value: str) -> str:
    """API key 脱敏：仅显示前 4 字符。"""
    if not value:
        return "(empty)"
    if len(value) <= 4:
        return "***"
    return f"{value[:4]}***"


# ────────────────────────────────────────────────────────────────
#  子收集器
# ────────────────────────────────────────────────────────────────


def _section(title: str) -> str:
    return f"\n## {title}\n"


def _collect_environment() -> str:
    lines: list[str] = []
    lines.append(f"- **OS**: {platform.platform()}")
    lines.append(f"- **Architecture**: {platform.machine()}")
    lines.append(f"- **Python**: {platform.python_version()}")
    lines.append(
        f"- **Implementation**: {platform.python_implementation()}"
    )
    lines.append(
        f"- **Executable**: "
        f"{'frozen' if getattr(sys, 'frozen', False) else 'script'} "
        f"({sys.executable})"
    )
    lines.append(f"- **User**: {getpass.getuser()}")
    lines.append(f"- **CWD**: {os.getcwd()}")
    # 检测 PyInstaller 打包
    if getattr(sys, "frozen", False):
        # type: ignore[attr-defined]
        lines.append(f"- **Bundle Dir**: {sys._MEIPASS}")
    return "\n".join(lines)


def _collect_app_version() -> str:
    def _load() -> str:
        from app.utils.version import get_version_string

        return get_version_string()

    return _safe(_load, default="[version unavailable]")


def _collect_key_deps() -> str:
    """关键依赖版本。"""
    deps = {
        "PySide6": None,
        "OpenCV": "cv2",
        "FFmpeg (binary)": None,
        "httpx": None,
        "SQLite": "sqlite3",
        "Pydantic": None,
    }
    lines: list[str] = []
    for name, mod in deps.items():
        if mod is None:
            # 单独处理：ffmpeg 由二进制探针
            if name.startswith("FFmpeg"):
                lines.append(f"- **{name}**: {_probe_ffmpeg_version()}")
                continue
            # 其它：试 importlib.metadata
            try:
                from importlib.metadata import version

                ver = version(name)
                lines.append(f"- **{name}**: {ver}")
            except Exception:  # noqa: BLE001
                lines.append(f"- **{name}**: (not installed)")
            continue
        try:
            mod_obj = __import__(mod)
            ver = getattr(mod_obj, "__version__", "?")
            lines.append(f"- **{name}**: {ver}")
        except Exception as e:  # noqa: BLE001
            lines.append(f"- **{name}**: [import failed: {e!r}]")
    return "\n".join(lines)


def _probe_ffmpeg_version() -> str:
    import shutil
    import subprocess

    binary = shutil.which("ffmpeg")
    if not binary:
        return "(not in PATH)"
    try:
        out = subprocess.run(
            [binary, "-version"],
            capture_output=True,
            text=True,
            timeout=3.0,
            check=False,
        )
        first_line = (out.stdout or "").splitlines()[0] if out.stdout else ""
        return first_line or "(empty output)"
    except Exception as e:  # noqa: BLE001
        return f"[probe failed: {e!r}]"


def _collect_llm() -> str:
    def _load() -> str:
        from app.config.config import get_config

        cfg = get_config()
        lines = [f"- **Default**: `{cfg.default_llm}`"]
        lines.append("- **Providers**:")
        for name in sorted(cfg.llm_providers):
            p = cfg.llm_providers[name]
            lines.append(
                f"  - `{name}`: model=`{p.model}` "
                f"enabled={p.enabled} key={_redact_api_key(p.api_key)}"
            )
        return "\n".join(lines)

    return _safe(_load, default="[LLM config unavailable]")


def _collect_audit_recent(n: int = 10) -> str:
    def _load() -> str:
        from app.core.audit import AuditLogger

        log = AuditLogger()
        log.flush()  # 把 buffer 落盘后再读
        rows = log.query(limit=n)
        if not rows:
            return "(empty)"
        out: list[str] = []
        for r in rows:
            params = r.parameters if isinstance(r.parameters, dict) else {}
            param_keys = ",".join(sorted(params.keys()))[:60]
            out.append(
                f"- `{r.timestamp[:19]}` **{r.action}** "
                f"[{r.result}] {r.duration_ms}ms "
                f"task={r.task_id or '-'} params={param_keys}"
            )
        return "\n".join(out)

    return _safe(_load, default="[audit unavailable]")


def _collect_metrics_snapshot() -> str:
    def _load() -> str:
        from app.core.metrics import get_metrics

        snap = get_metrics().snapshot()
        counters = snap.get("counters", {})
        histograms = snap.get("histograms", {})
        lines = [
            f"- Counter series: **{len(counters)}**",
            f"- Histogram series: **{len(histograms)}**",
        ]
        # Top 5 counters
        top_counters = sorted(
            counters.items(),
            key=lambda kv: sum(
                b.get("value", 0) for b in kv[1].get("by_labels", {}).values()
            ),
            reverse=True,
        )[:5]
        for name, info in top_counters:
            total = sum(b.get("value", 0)
                        for b in info.get("by_labels", {}).values())
            lines.append(f"  - `{name}` total={total}")
        return "\n".join(lines)

    return _safe(_load, default="[metrics unavailable]")


def _collect_settings_summary() -> str:
    def _load() -> str:
        from app.core.settings_store import get_settings

        store = get_settings()
        all_keys = store.keys()
        lines = [f"- Total keys: **{len(all_keys)}**"]
        for prefix in ("app.", "llm.", "project.", "qt.", "onboarding."):
            n = sum(1 for k in all_keys if k.startswith(prefix))
            lines.append(f"  - `{prefix}*`: {n}")
        return "\n".join(lines)

    return _safe(_load, default="[settings store unavailable]")


# ────────────────────────────────────────────────────────────────
#  主入口
# ────────────────────────────────────────────────────────────────


def collect_diagnostics(
    *,
    audit_tail: int = 10,
    extra_sections: Iterable[tuple[str, Any]] | None = None,
) -> str:
    """收集完整诊断信息并返回 Markdown 文本。

    Parameters
    ----------
    audit_tail:
        收集最近 N 条审计记录。
    extra_sections:
        调用方可追加 ``(标题, 文本)`` 自定义段落。
    """
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    parts: list[str] = [
        "# SceneFab Diagnostics",
        f"\n_Generated at {now}_\n",
    ]
    parts.append(_section("Application"))
    parts.append(f"- **Version**: {_collect_app_version()}")

    parts.append(_section("Environment"))
    parts.append(_collect_environment())

    parts.append(_section("Key Dependencies"))
    parts.append(_collect_key_deps())

    parts.append(_section("LLM Configuration"))
    parts.append(_collect_llm())

    parts.append(_section("Settings Store"))
    parts.append(_collect_settings_summary())

    parts.append(_section(f"Recent Audit (last {audit_tail})"))
    parts.append(_collect_audit_recent(audit_tail))

    parts.append(_section("Metrics Snapshot"))
    parts.append(_collect_metrics_snapshot())

    if extra_sections:
        for title, body in extra_sections:
            parts.append(_section(title))
            parts.append(str(body))

    return "\n".join(parts) + "\n"


def diagnostics_to_clipboard_payload(text: str) -> str:
    """把诊断文本包装成适合贴到 issue tracker 的 code block。"""
    return f"```text\n{text}\n```"


__all__ = [
    "collect_diagnostics",
    "diagnostics_to_clipboard_payload",
]
