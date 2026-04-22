"""
Voxplore Auto-Update Checker

启动时检测 GitHub Releases 最新版本。
有新版时提示用户下载，不自动下载/安装（安全优先）。
"""
import logging
import re
from dataclasses import dataclass
from typing import Optional

import httpx

from app.utils.version import get_version_string, Version

logger = logging.getLogger(__name__)

GITHUB_API_RELEASES = "https://api.github.com/repos/Agions/Voxplore/releases/latest"
GITHUB_RELEASES_PAGE = "https://github.com/Agions/Voxplore/releases"

# HTTP 客户端配置（10s 超时，防止阻塞启动）
_client_config = {
    "timeout": httpx.Timeout(10.0, connect=5.0),
    "headers": {"Accept": "application/vnd.github.v3+json", "User-Agent": "Voxplore"},
}


@dataclass
class UpdateInfo:
    """更新信息"""

    current_version: str  # 当前版本
    latest_version: str  # 最新版本
    release_url: str  # 发布页面
    release_notes: str  # 发布说明（摘要）
    is_newer: bool  # 是否有新版本


def _parse_version(v: str) -> Version:
    """解析版本字符串，返回 Version 对象用于比较"""
    try:
        return Version.parse(v.lstrip("v"))
    except ValueError:
        # 降级为 tuple 比较
        nums = tuple(int(x) for x in re.findall(r"\d+", v))
        return nums  # type: ignore[return-value]


def _strip_tag(tag: str) -> str:
    """去掉 'v' 前缀"""
    return tag.lstrip("vV")


def check_update() -> Optional[UpdateInfo]:
    """
    检测是否有新版本。

    Returns:
        UpdateInfo if detected, None if check failed (network error, etc.)
    """
    current = get_version_string()
    try:
        with httpx.Client(**_client_config) as client:
            response = client.get(GITHUB_API_RELEASES)
            response.raise_for_status()
            data = response.json()

        latest = _strip_tag(data.get("tag_name", ""))
        release_url = data.get("html_url", GITHUB_RELEASES_PAGE)

        # 发布说明（前 300 字符）
        body = data.get("body", "")
        release_notes = body[:300].strip() + ("..." if len(body) > 300 else "")

        # 版本比较
        try:
            is_newer = Version.parse(latest) > Version.parse(current)
        except ValueError:
            # 格式不对，用 tuple 比较
            is_newer = _parse_version(latest) > _parse_version(current)

        logger.info(
            "Update check: current=%s, latest=%s, is_newer=%s",
            current,
            latest,
            is_newer,
        )

        return UpdateInfo(
            current_version=current,
            latest_version=latest,
            release_url=release_url,
            release_notes=release_notes,
            is_newer=is_newer,
        )

    except httpx.HTTPStatusError as e:
        logger.warning("Update check failed (HTTP %d): %s", e.response.status_code, e)
        return None
    except httpx.RequestError as e:
        logger.warning("Update check failed (network): %s", e)
        return None
    except Exception as e:
        logger.warning("Update check failed (unexpected): %s", e)
        return None


def format_update_message(info: UpdateInfo) -> str:
    """格式化更新提示消息"""
    return (
        f"发现新版本 Voxplore {info.latest_version}！\n\n"
        f"当前版本：{info.current_version}\n"
        f"最新版本：{info.latest_version}\n\n"
        f"发布说明：\n{info.release_notes}\n\n"
        f"点击确定前往下载：\n{info.release_url}"
    )
