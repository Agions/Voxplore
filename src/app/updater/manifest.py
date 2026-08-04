"""升级清单解析与匹配。

负责把 GitHub Releases API 返回的 JSON 解析成结构化的
:class:`UpdateManifest`，并按当前版本与目标通道挑选最佳升级包。

设计要点：

* 同一 release 可能附带多个 asset（如完整 zip + delta patch），
  ``parse_release_manifest`` 一次性把它们都识别出来；
* ``select_best_manifest`` 实现升级策略：优先选择 delta 包（若适用），
  否则退到完整包；任一缺失 SHA256 都视为不安全并跳过；
* 命名约定：``SceneFab-{version}-{channel}.zip`` 为完整包；
  ``SceneFab-{version}-delta-from-{base_version}.zip`` 为增量包。
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from enum import Enum
from typing import Any


class UpdateChannel(str, Enum):
    """升级通道。"""

    STABLE = "stable"
    BETA = "beta"


@dataclass(frozen=True)
class UpdateManifest:
    """单次升级的描述信息。

    Attributes:
        version: 目标版本（去除 ``v`` 前缀），如 ``"2.5.0"``。
        channel: 升级通道（stable/beta）。
        download_url: 资产下载 URL（绝对地址）。
        sha256: 资产 SHA256 校验值（小写十六进制）。
        size_bytes: 资产大小（字节）。``None`` 表示服务器未提供。
        release_notes: Markdown 格式的发布说明（已截断到 500 字符）。
        is_delta: 是否为增量包。增量包必须配合 ``base_version`` 使用。
        base_version: 增量包所基于的旧版本（``is_delta=True`` 时必填）。
        asset_name: GitHub release 中 asset 的文件名（用于审计）。
    """

    version: str
    channel: UpdateChannel
    download_url: str
    sha256: str
    size_bytes: int | None = None
    release_notes: str = ""
    is_delta: bool = False
    base_version: str | None = None
    asset_name: str = ""

    def short_id(self) -> str:
        """返回便于日志展示的简短标识。"""

        if self.is_delta:
            return f"{self.version} (delta from {self.base_version})"
        return f"{self.version} (full)"


_ASSET_PATTERN = re.compile(
    r"^SceneFab-(?P<version>\d+\.\d+\.\d+(?:-[A-Za-z0-9.]+)?)"
    r"(?:-delta-from-(?P<base>\d+\.\d+\.\d+(?:-[A-Za-z0-9.]+)?))?"
    r"-(?P<channel>stable|beta)\.zip$"
)


def parse_release_manifest(
    release_payload: dict[str, Any],
    channel: UpdateChannel,
) -> list[UpdateManifest]:
    """从 GitHub ``/releases/latest``（或 ``/releases``）返回的 JSON 解析 manifest 列表。

    Args:
        release_payload: GitHub release JSON。
        channel: 当前通道；只保留匹配该通道的 asset。

    Returns:
        按 ``is_delta`` 排序的 manifest 列表（delta 在前）。
    """
    tag_name = str(release_payload.get("tag_name", "")).lstrip("vV")
    if not tag_name:
        return []

    body = str(release_payload.get("body", "") or "")
    notes = (body[:500] + "...") if len(body) > 500 else body

    manifests: list[UpdateManifest] = []
    for asset in release_payload.get("assets", []) or []:
        name = str(asset.get("name", ""))
        match = _ASSET_PATTERN.match(name)
        if match is None:
            continue
        if match.group("channel") != channel.value:
            continue
        if match.group("version") != tag_name:
            # 防御：asset 文件名版本必须与 tag 一致
            continue

        sha256 = ""
        for entry in release_payload.get("assets_meta", []) or []:
            if entry.get("name") == name:
                sha256 = str(entry.get("sha256", "")).lower()
                break

        # 兜底：部分 GitHub release asset 不暴露 sha256，
        # 升级器使用 strict-mode 时会拒绝该 asset。
        if not sha256:
            sha256 = ""

        base = match.group("base")
        manifests.append(
            UpdateManifest(
                version=match.group("version"),
                channel=channel,
                download_url=str(asset.get("browser_download_url", "")),
                sha256=sha256,
                size_bytes=(
                    int(asset["size"]) if isinstance(
                        asset.get("size"), int) else None
                ),
                release_notes=notes,
                is_delta=base is not None,
                base_version=base,
                asset_name=name,
            )
        )

    manifests.sort(key=lambda m: (not m.is_delta, m.asset_name))
    return manifests


def select_best_manifest(
    manifests: Iterable[UpdateManifest],
    current_version: str,
) -> UpdateManifest | None:
    """在多个候选 manifest 中挑选最合适的一个。

    策略：
        1. 若存在 ``base_version == current_version`` 的 delta 包，优先使用；
        2. 否则退到完整包；
        3. 任一 ``sha256`` 为空的候选被跳过（不安全）；
        4. 返回 ``None`` 表示无可用升级。
    """

    candidates = [m for m in manifests if m.sha256]
    if not candidates:
        return None

    deltas = [
        m for m in candidates
        if m.is_delta and m.base_version == current_version
    ]
    if deltas:
        return deltas[0]

    fulls = [m for m in candidates if not m.is_delta]
    if fulls:
        return fulls[0]

    return None


__all__ = [
    "UpdateChannel",
    "UpdateManifest",
    "parse_release_manifest",
    "select_best_manifest",
]
