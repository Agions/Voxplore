#!/usr/bin/env python3
"""Tests for :pymod:`app.updater.manifest`."""

from __future__ import annotations

from app.updater.manifest import (
    UpdateChannel,
    UpdateManifest,
    parse_release_manifest,
    select_best_manifest,
)


def _payload(tag: str = "2.5.0", assets=None, body: str = "release notes") -> dict:
    return {
        "tag_name": tag,
        "body": body,
        "assets": assets or [],
    }


def _asset(
    name: str,
    *,
    url: str = "https://example.com/dl",
    size: int = 1024,
) -> dict:
    return {
        "name": name,
        "browser_download_url": url,
        "size": size,
    }


class TestParseReleaseManifest:
    """parse_release_manifest 用例"""

    def test_empty_when_no_tag(self):
        assert parse_release_manifest({}, UpdateChannel.STABLE) == []

    def test_skips_assets_with_unmatched_name(self):
        payload = _payload(
            tag="2.5.0",
            assets=[_asset("random.zip"), _asset(
                "OtherTool-2.5.0-stable.zip")],
        )
        assert parse_release_manifest(payload, UpdateChannel.STABLE) == []

    def test_filters_by_channel(self):
        payload = _payload(
            tag="2.5.0",
            assets=[
                _asset("SceneFab-2.5.0-stable.zip"),
                _asset("SceneFab-2.5.0-beta.zip"),
            ],
        )
        stable = parse_release_manifest(payload, UpdateChannel.STABLE)
        beta = parse_release_manifest(payload, UpdateChannel.BETA)
        assert len(stable) == 1 and len(beta) == 1
        assert stable[0].asset_name.endswith("stable.zip")
        assert beta[0].asset_name.endswith("beta.zip")

    def test_rejects_when_asset_version_mismatch(self):
        payload = _payload(
            tag="2.5.0",
            assets=[_asset("SceneFab-2.4.9-stable.zip")],
        )
        # asset file version must equal tag version
        assert parse_release_manifest(payload, UpdateChannel.STABLE) == []

    def test_picks_up_full_and_delta(self):
        payload = _payload(
            tag="2.5.0",
            assets=[
                _asset("SceneFab-2.5.0-stable.zip"),
                _asset("SceneFab-2.5.0-delta-from-2.4.0-stable.zip"),
            ],
        )
        manifests = parse_release_manifest(payload, UpdateChannel.STABLE)
        assert len(manifests) == 2
        # Delta comes first
        assert manifests[0].is_delta is True
        assert manifests[0].base_version == "2.4.0"
        assert manifests[1].is_delta is False

    def test_release_notes_truncation(self):
        long = "x" * 800
        payload = _payload(
            tag="2.5.0",
            assets=[_asset("SceneFab-2.5.0-stable.zip")],
            body=long,
        )
        manifests = parse_release_manifest(payload, UpdateChannel.STABLE)
        assert len(manifests) == 1
        note = manifests[0].release_notes
        # 500 chars + "..."
        assert len(note) == 503
        assert note.endswith("...")

    def test_size_parsed_when_int(self):
        payload = _payload(
            tag="2.5.0",
            assets=[{**_asset("SceneFab-2.5.0-stable.zip"), "size": 42}],
        )
        manifests = parse_release_manifest(payload, UpdateChannel.STABLE)
        assert manifests[0].size_bytes == 42

    def test_size_none_when_missing(self):
        payload = _payload(
            tag="2.5.0",
            assets=[
                {"name": "SceneFab-2.5.0-stable.zip",
                 "browser_download_url": "u", "size": "not-int"}
            ],
        )
        manifests = parse_release_manifest(payload, UpdateChannel.STABLE)
        assert manifests[0].size_bytes is None


class TestSelectBestManifest:
    """select_best_manifest 用例"""

    def test_returns_none_for_empty(self):
        assert select_best_manifest([], "2.4.0") is None

    def test_skips_manifests_without_sha256(self):
        m = UpdateManifest(
            version="2.5.0",
            channel=UpdateChannel.STABLE,
            download_url="u",
            sha256="",  # empty → unsafe
        )
        assert select_best_manifest([m], "2.4.0") is None

    def test_prefers_matching_delta(self):
        full = UpdateManifest(
            version="2.5.0",
            channel=UpdateChannel.STABLE,
            download_url="full",
            sha256="a" * 64,
        )
        delta = UpdateManifest(
            version="2.5.0",
            channel=UpdateChannel.STABLE,
            download_url="delta",
            sha256="b" * 64,
            is_delta=True,
            base_version="2.4.0",
        )
        best = select_best_manifest([full, delta], current_version="2.4.0")
        assert best is delta

    def test_full_fallback_when_no_matching_delta(self):
        full = UpdateManifest(
            version="2.5.0",
            channel=UpdateChannel.STABLE,
            download_url="full",
            sha256="a" * 64,
        )
        delta_for_other_version = UpdateManifest(
            version="2.5.0",
            channel=UpdateChannel.STABLE,
            download_url="delta",
            sha256="b" * 64,
            is_delta=True,
            base_version="2.0.0",
        )
        best = select_best_manifest(
            [full, delta_for_other_version], current_version="2.4.0"
        )
        assert best is full

    def test_unrelated_delta_is_ignored(self):
        # delta for unrelated base doesn't help — should fall back to full
        full = UpdateManifest(
            version="2.5.0",
            channel=UpdateChannel.STABLE,
            download_url="full",
            sha256="a" * 64,
        )
        delta = UpdateManifest(
            version="2.5.0",
            channel=UpdateChannel.STABLE,
            download_url="delta",
            sha256="b" * 64,
            is_delta=True,
            base_version="9.9.9",  # not current
        )
        best = select_best_manifest([full, delta], current_version="2.4.0")
        assert best is full


class TestUpdateManifestShortId:
    def test_full_short_id(self):
        m = UpdateManifest(
            version="2.5.0",
            channel=UpdateChannel.STABLE,
            download_url="u",
            sha256="a" * 64,
        )
        assert m.short_id() == "2.5.0 (full)"

    def test_delta_short_id(self):
        m = UpdateManifest(
            version="2.5.0",
            channel=UpdateChannel.STABLE,
            download_url="u",
            sha256="a" * 64,
            is_delta=True,
            base_version="2.4.0",
        )
        assert m.short_id() == "2.5.0 (delta from 2.4.0)"
