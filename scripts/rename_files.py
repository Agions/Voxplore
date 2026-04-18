#!/usr/bin/env python3
"""
Voxplore 文件命名结构化改造脚本

修复以下问题:
1. 删除重复/废弃文件
2. 统一命名规范 (snake_case)
3. 移除空文件/存根文件
4. 整理目录结构
"""

import os
import shutil
from pathlib import Path

PROJECT_ROOT = Path('/root/.openclaw/workspace/Voxplore')

# 需要删除的文件
FILES_TO_DELETE = [
    # 废弃的迁移脚本
    'app/ui/macOS_migration.py',
    # 空的存根文件
    'app/ui/components/pro_components.py',
    # 重复的 base 文件 (page_base.py 是空壳，base_page.py 才是实现)
    'app/ui/main/pages/page_base.py',
]

# 需要重命名的文件
RENAME_MAP = {
    # pro_components 命名不清晰
    'app/ui/components/pro_components/__init__.py': 'app/ui/components/pro_ui/__init__.py',
    'app/ui/components/pro_components/pro_components.py': 'app/ui/components/pro_ui/components.py',
}

def delete_file(filepath: str) -> bool:
    """删除文件"""
    full_path = PROJECT_ROOT / filepath
    if full_path.exists():
        try:
            full_path.unlink()
            print(f"  ✅ 删除: {filepath}")
            return True
        except Exception as e:
            print(f"  ❌ 删除失败: {filepath} - {e}")
            return False
    else:
        print(f"  ⏭️  跳过 (不存在): {filepath}")
        return False

def rename_file(src: str, dst: str) -> bool:
    """重命名文件"""
    src_path = PROJECT_ROOT / src
    dst_path = PROJECT_ROOT / dst
    
    if src_path.exists():
        # 确保目标目录存在
        dst_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            src_path.rename(dst_path)
            print(f"  ✅ 重命名: {src} → {dst}")
            return True
        except Exception as e:
            print(f"  ❌ 重命名失败: {src} → {dst} - {e}")
            return False
    else:
        print(f"  ⏭️  跳过 (不存在): {src}")
        return False

def remove_empty_dirs() -> None:
    """删除空目录"""
    print("\n🧹 清理空目录...")
    for dirpath in sorted(PROJECT_ROOT.rglob('*')):
        if dirpath.is_dir():
            try:
                if not any(dirpath.iterdir()):
                    dirpath.rmdir()
                    print(f"  ✅ 删除空目录: {dirpath.relative_to(PROJECT_ROOT)}")
            except Exception:
                pass

def main():
    print("🔄 Voxplore 文件命名结构化改造")
    print("=" * 50)
    
    # 1. 删除废弃文件
    print("\n📦 删除废弃文件...")
    for filepath in FILES_TO_DELETE:
        delete_file(filepath)
    
    # 2. 重命名文件
    print("\n📝 重命名文件...")
    for src, dst in RENAME_MAP.items():
        rename_file(src, dst)
    
    # 3. 清理空目录
    remove_empty_dirs()
    
    print("\n" + "=" * 50)
    print("✅ 文件命名结构化改造完成!")

if __name__ == '__main__':
    main()
