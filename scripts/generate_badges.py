#!/usr/bin/env python3
"""Generate SceneFab version badge SVG from pyproject.toml.

Usage:
    python scripts/generate_badges.py
    python scripts/generate_badges.py --version 1.2.0
    python scripts/generate_badges.py --check   # CI check (fail if drift)
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PYPROJECT = ROOT / "pyproject.toml"
BADGE_PATH = ROOT / "assets" / "badges" / "version.svg"


def read_pyproject_version() -> str:
    """Extract `version = "X.Y.Z"` from pyproject.toml."""
    if not PYPROJECT.exists():
        sys.exit(f"❌ pyproject.toml not found at {PYPROJECT}")
    content = PYPROJECT.read_text(encoding="utf-8")
    match = re.search(r'^version\s*=\s*"([^"]+)"', content, re.MULTILINE)
    if not match:
        sys.exit(f"❌ No version field found in {PYPROJECT}")
    return match.group(1)


def render_version_badge(version: str) -> str:
    """Render the version badge SVG with the given version string."""
    svg = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="98" height="28" role="img" aria-label="SceneFab v{version}">
  <title>SceneFab v{version}</title>
  <defs>
    <linearGradient id="bgVersion" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#555555"/>
      <stop offset="100%" stop-color="#333333"/>
    </linearGradient>
    <linearGradient id="bgValueVersion" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#ff8a5b"/>
      <stop offset="100%" stop-color="#e63946"/>
    </linearGradient>
  </defs>
  <g shape-rendering="crispEdges">
    <rect width="44" height="28" rx="4" ry="4" fill="url(#bgVersion)"/>
    <rect x="44" width="54" height="28" rx="4" ry="4" fill="url(#bgValueVersion)"/>
    <rect x="40" width="8" height="28" fill="url(#bgValueVersion)"/>
  </g>
  <g font-family="Verdana, Geneva, Tahoma, sans-serif" font-weight="700" font-size="11" text-anchor="middle" fill="#ffffff">
    <text x="22" y="18">version</text>
    <text x="71" y="18">v{version}</text>
  </g>
</svg>
'''
    return svg


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate SceneFab version badge.")
    parser.add_argument(
        "--version", help="Override version (default: read from pyproject.toml)"
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="CI check: exit 1 if badge is out of sync with pyproject.toml",
    )
    args = parser.parse_args()

    version = args.version or read_pyproject_version()

    if args.check:
        if not BADGE_PATH.exists():
            print(f"❌ Badge not found at {BADGE_PATH}")
            return 1
        existing = BADGE_PATH.read_text(encoding="utf-8")
        expected = render_version_badge(version)
        if existing == expected:
            print(f"✅ Badge in sync (v{version})")
            return 0
        print(f"❌ Badge drift: expected v{version}, file is out of sync")
        print(f"   Run: python scripts/generate_badges.py")
        return 1

    BADGE_PATH.parent.mkdir(parents=True, exist_ok=True)
    BADGE_PATH.write_text(render_version_badge(version), encoding="utf-8")
    print(f"✅ Wrote {BADGE_PATH} (v{version})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
