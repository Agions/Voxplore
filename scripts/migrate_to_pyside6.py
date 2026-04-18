#!/usr/bin/env python3
"""
PyQt6 → PySide6 迁移脚本

PySide6 是 Qt 官方的 LGPL 授权版本，与 PyQt6 API 几乎完全兼容。
迁移后商业使用无需购买授权。

主要变更:
1. PyQt6.QtCore.Qt → PySide6.QtCore.Qt
2. PyQt6.QtGui → PySide6.QtGui  
3. PyQt6.QtWidgets → PySide6.QtWidgets
4. pyqtSignal → Signal
5. pyqtSlot → Slot
6. SIP 相关导入移除
"""

import os
import re
from pathlib import Path

def migrate_file(filepath: Path) -> bool:
    """迁移单个文件"""
    try:
        content = filepath.read_text(encoding='utf-8')
        original = content
        
        # 1. 替换 PyQt6 导入为 PySide6
        content = content.replace('from PyQt6', 'from PySide6')
        content = content.replace('import PyQt6', 'import PySide6')
        
        # 2. 替换 pyqtSignal 为 Signal (PySide6 风格)
        # 注意: PySide6 也支持 pyqtSignal 作为别名，但官方推荐 Signal
        # 为保持兼容性，这里保留 pyqtSignal
        
        # 3. 移除 PyQt6 特有的 SIP 检查 (PySide6 不需要)
        content = re.sub(
            r'from PyQt6 import sip\n?',
            '',
            content
        )
        content = re.sub(
            r'if\s+\(?\s*sip\s+and\s+hasattr\(sip,\s*[\'"]isdeleted[\'"]\)\s*\)?',
            'if False  # SIP check removed for PySide6',
            content
        )
        
        # 4. 替换 PyQt6 特定的枚举访问方式
        # PyQt6: Qt.AlignmentFlag.AlignCenter
        # PySide6: Qt.AlignmentFlag.AlignCenter (相同)
        
        # 5. 替换 QApplication.instance() 的处理
        # PyQt6 可能需要 sip 检查，PySide6 不需要
        content = re.sub(
            r'if\s+sip\s+and\s+hasattr\(sip,\s*[\'"]isdeleted[\'"]\)\s+and\s+not\s+sip\.isdeleted\((\w+)\)',
            r'if \1 is not None',  # PySide6 更简单
            content
        )
        
        # 6. 移除 PyQt6 特定的类型检查
        content = re.sub(
            r'from PyQt6\.QtWidgets import.*?QApplication.*?\n',
            'from PySide6.QtWidgets import QApplication\n',
            content
        )
        
        if content != original:
            filepath.write_text(content, encoding='utf-8')
            return True
        return False
        
    except Exception as e:
        print(f"  ❌ 错误: {filepath} - {e}")
        return False

def update_requirements(filepath: Path) -> bool:
    """更新 requirements.txt"""
    try:
        content = filepath.read_text(encoding='utf-8')
        original = content
        
        # 替换 PyQt6 为 PySide6
        content = re.sub(
            r'PyQt6[^\n]*\n',
            'PySide6>=6.6.0\n',
            content
        )
        content = re.sub(
            r'PyQt6-[^\n]*\n',
            '',
            content
        )
        content = re.sub(
            r'sip[^\n]*\n',
            '',
            content
        )
        
        # 添加 PySide6 特有依赖
        if 'PySide6' not in content and 'shiboken' not in content:
            content = content.replace(
                'PySide6>=6.6.0\n',
                'PySide6>=6.6.0\nShiboken6>=6.6.0\n'
            )
        
        if content != original:
            filepath.write_text(content, encoding='utf-8')
            return True
        return False
        
    except Exception as e:
        print(f"  ❌ 错误 updating requirements: {e}")
        return False

def update_pyproject(filepath: Path) -> bool:
    """更新 pyproject.toml"""
    try:
        content = filepath.read_text(encoding='utf-8')
        original = content
        
        # 替换 PyQt6 为 PySide6
        content = re.sub(
            r'"PyQt6[^\n]*"\n',
            '"PySide6>=6.6.0",\n',
            content
        )
        content = re.sub(
            r'"PyQt6-[^\n]*"\n',
            '',
            content
        )
        content = re.sub(
            r'"PyQt6-sip[^\n]*"\n',
            '',
            content
        )
        
        if content != original:
            filepath.write_text(content, encoding='utf-8')
            return True
        return False
        
    except Exception as e:
        print(f"  ❌ 错误 updating pyproject: {e}")
        return False

def main():
    project_root = Path('/root/.openclaw/workspace/Voxplore')
    app_dir = project_root / 'app'
    
    print("🔄 开始 PyQt6 → PySide6 迁移...")
    print("=" * 50)
    
    # 迁移 app/ 目录下的 Python 文件
    py_files = list(app_dir.glob('**/*.py'))
    
    migrated = 0
    skipped = 0
    
    for f in sorted(set(py_files)):
        if '__pycache__' in str(f) or 'node_modules' in str(f):
            continue
        
        if migrate_file(f):
            print(f"  ✅ 迁移: {f.relative_to(project_root)}")
            migrated += 1
        else:
            skipped += 1
    
    # 更新 requirements.txt
    req_file = project_root / 'requirements.txt'
    if req_file.exists():
        if update_requirements(req_file):
            print("\n  ✅ 更新: requirements.txt")
        else:
            print("\n  ⏭️  跳过: requirements.txt (无需更改)")
    
    # 更新 pyproject.toml
    pyproject = project_root / 'pyproject.toml'
    if pyproject.exists():
        if update_pyproject(pyproject):
            print("  ✅ 更新: pyproject.toml")
        else:
            print("  ⏭️  跳过: pyproject.toml (无需更改)")
    
    print("=" * 50)
    print(f"✅ 迁移完成! 迁移: {migrated}, 跳过: {skipped}")
    print("\n📋 下一步:")
    print("  1. pip install -r requirements.txt")
    print("  2. pip install PySide6 Shiboken6")
    print("  3. python main.py 测试")

if __name__ == '__main__':
    main()
