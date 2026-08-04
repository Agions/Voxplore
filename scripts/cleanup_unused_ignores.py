#!/usr/bin/env python3
"""清理 mypy unused-ignore 注释。

遍历 mypy 输出,定位"Unused type: ignore"位置,删除对应的 type: ignore 注释行。
约束:只删除 mypy 报告为未使用的注释,不删除真实需要的 ignore。
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path("/Users/zfkc/Desktop/04-AI/scene-fab")
SRC = ROOT / "src"


def find_unused_ignores() -> list[tuple[Path, int]]:
    """运行 mypy,返回所有 unused-ignore 错误的 (file, line) 列表。"""
    result = subprocess.run(
        [
            sys.executable, "-m", "mypy", str(SRC), "--no-error-summary",
        ],
        capture_output=True, text=True, cwd=ROOT, timeout=600,
    )
    pattern = re.compile(
        r"^(?P<file>src/app/[^:]+):(?P<line>\d+): error: Unused\b"
    )
    out: list[tuple[Path, int]] = []
    lines = result.stdout.splitlines()
    for i, line in enumerate(lines):
        m = pattern.match(line)
        if m and i + 1 < len(lines) and '"type: ignore"' in lines[i + 1]:
            out.append((ROOT / m.group("file"), int(m.group("line"))))
    return out


def remove_type_ignore_at(file: Path, line_num: int) -> bool:
    """删除文件中第 line_num 行的 `# type: ignore[...]` 注释(整行)。"""
    text = file.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=False)
    if line_num < 1 or line_num > len(lines):
        return False
    target = lines[line_num - 1]
    cleaned = re.sub(r"\s*#\s*type:\s*ignore(\[[^\]]*\])?\s*$", "", target)
    if cleaned == target:
        return False
    lines[line_num - 1] = cleaned
    file.write_text("\n".join(lines) +
                    ("\n" if text.endswith("\n") else ""), encoding="utf-8")
    return True


def main() -> int:
    print("=== Cleanup mypy unused-ignore comments ===")
    ignores = find_unused_ignores()
    if not ignores:
        print("[OK] No unused-ignore comments found.")
        return 0
    print(f"Found {len(ignores)} unused-ignore comments to remove.")

    removed = 0
    for file, line in ignores:
        if remove_type_ignore_at(file, line):
            rel = file.relative_to(ROOT)
            print(f"  [removed] {rel}:{line}")
            removed += 1

    print(f"\n[DONE] Removed {removed}/{len(ignores)} unused-ignore comments.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
