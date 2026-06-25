#!/usr/bin/env python3
"""
Test update/checker.py

覆盖范围:
- _parse_version: 正常版本号 / 带 v 前缀 / 非标准格式
- _strip_tag: v / V / 无前缀
- check_update: 网络错误 / HTTP 错误 / 正常更新 / 无更新 / 版本比较
- format_update_message: 消息格式
"""

from unittest.mock import MagicMock, patch

import httpx
import pytest

from scenefab.update.checker import (
    GITHUB_API_RELEASES,
    GITHUB_RELEASES_PAGE,
    UpdateInfo,
    _parse_version,
    _strip_tag,
    check_update,
    format_update_message,
)
from scenefab.utils.version import Version, get_version_string


class TestParseVersion:
    """_parse_version 测试"""

    def test_standard_version(self):
        """标准 semver 解析"""
        result = _parse_version("1.2.3")
        assert isinstance(result, Version)
        assert result.major == 1
        assert result.minor == 2
        assert result.patch == 3

    def test_version_with_v_prefix(self):
        """带 v 前缀的版本 (常见 Git tag 格式)"""
        result = _parse_version("v1.2.3")
        assert isinstance(result, Version)
        assert result.major == 1

    def test_version_with_V_prefix(self):
        """带 V 前缀 — _parse_version 接受大小写 v (lstrip [quote]vV[/quote])"""
        result = _parse_version("V2.0.0")
        assert isinstance(result, Version)
        assert result.major == 2

    def test_non_standard_fallback(self):
        """带 prerelease 的 semver 解析"""
        result = _parse_version("2.0.0-rc1")
        assert isinstance(result, Version)
        assert result.major == 2
        assert result.prerelease == "rc1"

    def test_truly_garbage_version(self):
        """完全无法解析的字符串 → tuple 降级"""
        result = _parse_version("not.a.version.at.all")
        # "not.a.version.at.all" 抛 ValueError, 走 tuple
        # re.findall(r"\d+") → ("0", "0") 不对, 没数字, 返回 ()
        # 但 type ignore 允许, 实际结果是 ()
        assert result == ()


class TestStripTag:
    """_strip_tag 测试"""

    def test_strip_v(self):
        assert _strip_tag("v1.2.3") == "1.2.3"

    def test_strip_V(self):
        assert _strip_tag("V1.2.3") == "1.2.3"

    def test_no_prefix(self):
        assert _strip_tag("1.2.3") == "1.2.3"

    def test_empty(self):
        assert _strip_tag("") == ""


class TestCheckUpdate:
    """check_update 测试 - mock httpx 避免真实网络请求"""

    def _mock_response(self, json_data: dict, status_code: int = 200):
        """构造 mock response"""
        response = MagicMock()
        response.status_code = status_code
        response.json.return_value = json_data
        response.raise_for_status = MagicMock()
        if status_code >= 400:
            response.raise_for_status.side_effect = httpx.HTTPStatusError(
                "error", request=MagicMock(), response=response
            )
        return response

    def test_newer_version_available(self):
        """检测到新版本"""
        current = get_version_string()
        # 构造一个明显更新的版本号
        newer_tag = f"v{_bump_version(current, major_bump=99)}"

        mock_resp = self._mock_response({
            "tag_name": newer_tag,
            "html_url": "https://github.com/Agions/scene-fab/releases",
            "body": "New release notes",
        })

        with patch("scenefab.update.checker.httpx.Client") as MockClient:
            MockClient.return_value.__enter__.return_value.get.return_value = mock_resp
            info = check_update()

        assert info is not None
        assert info.latest_version == _strip_tag(newer_tag)
        assert info.is_newer is True
        assert info.current_version == current
        assert info.release_notes == "New release notes"

    def test_no_newer_version(self):
        """没有新版本"""
        current = get_version_string()
        mock_resp = self._mock_response({
            "tag_name": f"v{current}",
            "html_url": "https://github.com/Agions/scene-fab/releases",
            "body": "Same version",
        })

        with patch("scenefab.update.checker.httpx.Client") as MockClient:
            MockClient.return_value.__enter__.return_value.get.return_value = mock_resp
            info = check_update()

        assert info is not None
        assert info.is_newer is False
        assert info.latest_version == current

    def test_older_version(self):
        """远端版本低于当前"""
        current = get_version_string()
        # 构造一个明显更老的版本
        major = int(current.split(".")[0])
        if major > 0:
            older_tag = f"v{major - 1}.0.0"
        else:
            older_tag = "v0.0.1"

        mock_resp = self._mock_response({
            "tag_name": older_tag,
            "html_url": "https://github.com/Agions/scene-fab/releases",
            "body": "Old",
        })

        with patch("scenefab.update.checker.httpx.Client") as MockClient:
            MockClient.return_value.__enter__.return_value.get.return_value = mock_resp
            info = check_update()

        assert info is not None
        assert info.is_newer is False

    def test_release_notes_truncated(self):
        """发布说明超过 300 字符应被截断"""
        long_body = "x" * 500
        current = get_version_string()
        newer_tag = f"v{_bump_version(current, major_bump=99)}"

        mock_resp = self._mock_response({
            "tag_name": newer_tag,
            "html_url": "https://github.com/Agions/scene-fab/releases",
            "body": long_body,
        })

        with patch("scenefab.update.checker.httpx.Client") as MockClient:
            MockClient.return_value.__enter__.return_value.get.return_value = mock_resp
            info = check_update()

        assert info is not None
        # 300 字符 + "..." 后缀
        assert len(info.release_notes) == 303
        assert info.release_notes.endswith("...")

    def test_release_notes_short(self):
        """发布说明短于 300 不加省略号"""
        short_body = "x" * 50
        current = get_version_string()
        newer_tag = f"v{_bump_version(current, major_bump=99)}"

        mock_resp = self._mock_response({
            "tag_name": newer_tag,
            "html_url": "https://github.com/Agions/scene-fab/releases",
            "body": short_body,
        })

        with patch("scenefab.update.checker.httpx.Client") as MockClient:
            MockClient.return_value.__enter__.return_value.get.return_value = mock_resp
            info = check_update()

        assert info is not None
        assert not info.release_notes.endswith("...")
        assert info.release_notes == "x" * 50

    def test_release_notes_stripped(self):
        """发布说明前后空白应被 strip"""
        current = get_version_string()
        newer_tag = f"v{_bump_version(current, major_bump=99)}"

        mock_resp = self._mock_response({
            "tag_name": newer_tag,
            "html_url": "https://github.com/Agions/scene-fab/releases",
            "body": "  hello world  ",
        })

        with patch("scenefab.update.checker.httpx.Client") as MockClient:
            MockClient.return_value.__enter__.return_value.get.return_value = mock_resp
            info = check_update()

        assert info is not None
        assert info.release_notes == "hello world"

    def test_http_error_returns_none(self):
        """HTTP 错误返回 None (不抛异常)"""
        mock_resp = self._mock_response({}, status_code=404)

        with patch("scenefab.update.checker.httpx.Client") as MockClient:
            MockClient.return_value.__enter__.return_value.get.return_value = mock_resp
            info = check_update()

        assert info is None

    def test_network_error_returns_none(self):
        """网络错误返回 None"""
        with patch("scenefab.update.checker.httpx.Client") as MockClient:
            MockClient.return_value.__enter__.return_value.get.side_effect = httpx.ConnectError("network down")
            info = check_update()

        assert info is None

    def test_unexpected_error_returns_none(self):
        """其他异常 (e.g. JSON 解析失败) 返回 None"""
        with patch("scenefab.update.checker.httpx.Client") as MockClient:
            mock_resp = MagicMock()
            mock_resp.raise_for_status = MagicMock()
            mock_resp.json.side_effect = ValueError("bad json")
            MockClient.return_value.__enter__.return_value.get.return_value = mock_resp
            info = check_update()

        assert info is None

    def test_missing_tag_name_falls_back(self):
        """tag_name 缺失时不应崩溃"""
        current = get_version_string()
        mock_resp = self._mock_response({
            "html_url": "https://github.com/Agions/scene-fab/releases",
            "body": "no tag",
        })

        with patch("scenefab.update.checker.httpx.Client") as MockClient:
            MockClient.return_value.__enter__.return_value.get.return_value = mock_resp
            info = check_update()

        # 没有 tag_name 时, latest 解析为 "" → _parse_version 走 tuple 降级
        # 空字符串的 tuple 是 (), Version.parse("") 抛 ValueError
        # is_newer 比较走 tuple 降级路径, () > current_version 应当 False
        # 但要确保不 crash
        assert info is not None
        assert info.latest_version == ""


class TestFormatUpdateMessage:
    """format_update_message 测试"""

    def test_basic_format(self):
        """基本消息格式"""
        info = UpdateInfo(
            current_version="2.1.2",
            latest_version="2.2.0",
            release_url="https://github.com/Agions/scene-fab/releases",
            release_notes="新功能",
            is_newer=True,
        )
        msg = format_update_message(info)
        assert "2.2.0" in msg
        assert "2.1.2" in msg
        assert "https://github.com/Agions/scene-fab/releases" in msg
        assert "新功能" in msg
        assert "SceneFab" in msg


# ──────────────────────────────────────────────────────────
# 辅助函数
# ──────────────────────────────────────────────────────────


def _bump_version(current: str, major_bump: int = 99) -> str:
    """构造一个明显更新的版本号 (大版本 bump 99)"""
    parts = current.split(".")
    parts[0] = str(int(parts[0]) + major_bump)
    return ".".join(parts)
