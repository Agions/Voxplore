#!/usr/bin/env python3
"""Tests for :pymod:`app.updater.verifier`."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from app.updater.verifier import VerificationError, compute_sha256, verify_sha256


def _write(tmp_path: Path, data: bytes) -> Path:
    p = tmp_path / "f.bin"
    p.write_bytes(data)
    return p


class TestComputeSha256:
    def test_known_value(self, tmp_path: Path):
        data = b"hello world"
        expected = hashlib.sha256(data).hexdigest()
        p = _write(tmp_path, data)
        assert compute_sha256(p) == expected

    def test_large_file_chunked(self, tmp_path: Path):
        # 1 MB random-ish data
        data = (b"abcdefgh" * (128 * 1024))
        p = _write(tmp_path, data)
        assert compute_sha256(p) == hashlib.sha256(data).hexdigest()


class TestVerifySha256:
    def test_happy_path(self, tmp_path: Path):
        data = b"SceneFab-upgrade-package"
        expected = hashlib.sha256(data).hexdigest()
        p = _write(tmp_path, data)
        assert verify_sha256(p, expected) is True

    def test_case_insensitive_expected(self, tmp_path: Path):
        data = b"package"
        expected = hashlib.sha256(data).hexdigest().upper()
        p = _write(tmp_path, data)
        assert verify_sha256(p, expected) is True

    def test_mismatch_raises(self, tmp_path: Path):
        data = b"package"
        bad_hash = "0" * 64
        p = _write(tmp_path, data)
        with pytest.raises(VerificationError):
            verify_sha256(p, bad_hash)

    def test_empty_expected_raises(self, tmp_path: Path):
        p = _write(tmp_path, b"data")
        with pytest.raises(VerificationError):
            verify_sha256(p, "")

    def test_invalid_hex_raises(self, tmp_path: Path):
        p = _write(tmp_path, b"data")
        with pytest.raises(VerificationError):
            verify_sha256(p, "not-a-hex")

    def test_short_hex_raises(self, tmp_path: Path):
        p = _write(tmp_path, b"data")
        with pytest.raises(VerificationError):
            verify_sha256(p, "abc123")

    def test_missing_file_raises(self, tmp_path: Path):
        with pytest.raises(VerificationError):
            verify_sha256(tmp_path / "nope.bin", "0" * 64)
