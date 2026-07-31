#!/usr/bin/env python3
"""Extract user-facing UI strings and validate SceneFab i18n catalogs.

The scanner uses Python's AST rather than regular expressions.  It reports:

* literal strings passed to common Qt text APIs and widget constructors;
* translation keys referenced through ``t(...)`` or ``Translator.tr(...)``;
* keys missing from either zh-CN or en-US;
* catalog keys not declared in ``message_keys.py``.

By default the report is written to ``i18n_extracted.json`` at the repository
root.  ``--check`` exits non-zero for catalog/key inconsistencies, while
``--fail-on-literals`` can be enabled by CI after the Phase C migration.
"""

from __future__ import annotations

import argparse
import ast
import json
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

_TEXT_METHODS = {
    "addItem",
    "addMenu",
    "setAccessibleDescription",
    "setAccessibleName",
    "setPlaceholderText",
    "setStatusTip",
    "setText",
    "setTitle",
    "setToolTip",
    "setWindowTitle",
}
_TEXT_CONSTRUCTORS = {
    "QAction",
    "QCheckBox",
    "QCommandLinkButton",
    "QGroupBox",
    "QLabel",
    "QPushButton",
    "QRadioButton",
}
_TRANSLATION_FUNCTIONS = {"t", "tr"}


@dataclass(frozen=True)
class ExtractedLiteral:
    file: str
    line: int
    call: str
    text: str


@dataclass(frozen=True)
class UsedKey:
    file: str
    line: int
    key: str


def _call_name(node: ast.Call) -> str:
    func = node.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return ""


def _literal_string(node: ast.AST | None) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):
        parts = [part.value for part in node.values if isinstance(
            part, ast.Constant)]
        return "".join(str(part) for part in parts)
    return None


def _text_argument(call: ast.Call, call_name: str) -> ast.AST | None:
    for keyword in call.keywords:
        if keyword.arg in {"text", "title", "label"}:
            return keyword.value
    if not call.args:
        return None
    if call_name == "QAction" and len(call.args) > 1:
        # QAction(icon, text, parent) overload.
        first = _literal_string(call.args[0])
        return call.args[0] if first is not None else call.args[1]
    return call.args[0]


class I18nVisitor(ast.NodeVisitor):
    def __init__(self, source_file: Path, source_root: Path) -> None:
        self.relative_file = source_file.relative_to(
            source_root.parent).as_posix()
        self.literals: list[ExtractedLiteral] = []
        self.used_keys: list[UsedKey] = []

    def visit_Call(self, node: ast.Call) -> None:  # noqa: N802 - ast API
        name = _call_name(node)
        if name in _TRANSLATION_FUNCTIONS and node.args:
            key = _literal_string(node.args[0])
            if key:
                self.used_keys.append(
                    UsedKey(self.relative_file, node.lineno, key))
        elif name in _TEXT_METHODS or name in _TEXT_CONSTRUCTORS:
            text = _literal_string(_text_argument(node, name))
            if text and text.strip():
                self.literals.append(
                    ExtractedLiteral(self.relative_file,
                                     node.lineno, name, text)
                )
        self.generic_visit(node)


def scan_python_files(source_root: Path) -> tuple[list[ExtractedLiteral], list[UsedKey]]:
    literals: list[ExtractedLiteral] = []
    used_keys: list[UsedKey] = []
    for path in sorted(source_root.rglob("*.py")):
        try:
            tree = ast.parse(path.read_text(
                encoding="utf-8"), filename=str(path))
        except (OSError, SyntaxError) as exc:
            raise RuntimeError(f"无法扫描 {path}: {exc}") from exc
        visitor = I18nVisitor(path, source_root)
        visitor.visit(tree)
        literals.extend(visitor.literals)
        used_keys.extend(visitor.used_keys)
    return literals, used_keys


def _assignment_dict(path: Path, variable: str) -> dict[str, str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in tree.body:
        if isinstance(node, ast.Assign | ast.AnnAssign):
            targets: Iterable[ast.expr]
            value: ast.AST | None
            if isinstance(node, ast.Assign):
                targets, value = node.targets, node.value
            else:
                targets, value = (node.target,), node.value
            if any(isinstance(target, ast.Name) and target.id == variable for target in targets):
                parsed = ast.literal_eval(value)
                if not isinstance(parsed, dict):
                    break
                return {str(key): str(item) for key, item in parsed.items()}
    raise RuntimeError(f"{path} 中未找到字典 {variable}")


def _declared_keys(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    keys: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign | ast.AnnAssign):
            value = node.value
            text = _literal_string(value)
            if text and "." in text:
                keys.add(text)
    return keys


def build_report(repo_root: Path, source_root: Path) -> dict[str, Any]:
    i18n_dir = source_root / "ui" / "i18n"
    zh = _assignment_dict(i18n_dir / "messages_zh_CN.py", "MESSAGES")
    en = _assignment_dict(i18n_dir / "messages_en_US.py", "MESSAGES")
    declared = _declared_keys(i18n_dir / "message_keys.py")
    literals, used = scan_python_files(source_root)
    used_names = {item.key for item in used}
    catalog_keys = set(zh) | set(en)

    return {
        "source_root": source_root.relative_to(repo_root).as_posix(),
        "summary": {
            "hardcoded_literals": len(literals),
            "used_translation_keys": len(used_names),
            "zh_CN_keys": len(zh),
            "en_US_keys": len(en),
        },
        "hardcoded_literals": [asdict(item) for item in literals],
        "used_translation_keys": sorted(used_names),
        "missing": {
            "zh-CN": sorted((set(en) | used_names | declared) - set(zh)),
            "en-US": sorted((set(zh) | used_names | declared) - set(en)),
            "message_keys": sorted(catalog_keys - declared),
        },
        "unused_catalog_keys": sorted(catalog_keys - used_names),
    }


def _parse_args() -> argparse.Namespace:
    repo_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path,
                        default=repo_root / "src" / "app")
    parser.add_argument("--output", type=Path,
                        default=repo_root / "i18n_extracted.json")
    parser.add_argument("--check", action="store_true", help="校验目录和 key 完整性")
    parser.add_argument(
        "--fail-on-literals",
        action="store_true",
        help="发现未迁移的 UI 字面量时返回非零（Phase C CI 使用）",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    repo_root = Path(__file__).resolve().parents[1]
    source_root = args.source.resolve()
    report = build_report(repo_root, source_root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    print(
        "i18n scan:",
        f"{report['summary']['hardcoded_literals']} literals,",
        f"{report['summary']['used_translation_keys']} used keys,",
        f"report={args.output}",
    )
    has_missing = any(report["missing"].values())
    if args.check and has_missing:
        return 1
    if args.fail_on_literals and report["hardcoded_literals"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
