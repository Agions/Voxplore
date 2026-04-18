#!/usr/bin/env python3
"""
脚本：为所有 Python 文件添加版权头
"""

import os
from pathlib import Path

COPYRIGHT_HEADER = '''"""
Voxplore - AI Video Editor
Copyright (c) 2025 Agions. All rights reserved.
Licensed under the MIT License.
"""

'''

def add_copyright_to_file(filepath: Path) -> bool:
    """为单个文件添加版权头"""
    try:
        content = filepath.read_text(encoding='utf-8')
        lines = content.split('\n')
        
        # 检查是否已有版权头
        if 'Copyright (c) 2025 Agions' in content:
            print(f"  ⏭️  跳过 (已有版权): {filepath}")
            return False
        
        # 确定插入位置 (在 shebang 和 encoding 之后)
        new_lines = []
        skip_next = 0
        
        for i, line in enumerate(lines):
            if skip_next > 0:
                skip_next -= 1
                continue
                
            new_lines.append(line)
            
            # 在 shebang 后标记
            if line.startswith('#!/'):
                # 检查下一行是否是 encoding
                if i + 1 < len(lines) and ('coding' in lines[i+1] or 'utf-8' in lines[i+1]):
                    new_lines.append(lines[i+1])
                    skip_next = 1
                # 插入版权头
                new_lines.append('')
                new_lines.extend(COPYRIGHT_HEADER.split('\n'))
                break
            # 如果没有 shebang，看是否有 encoding
            elif '# -*- coding:' in line or '# coding:' in line:
                continue
            # docstring 文件，直接在开头添加
            elif line.startswith('"""') or line.startswith("'''"):
                # 在 docstring 之前插入版权头
                new_lines = [''] + COPYRIGHT_HEADER.split('\n') + [''] + [line]
                # 找到 docstring 结尾
                for j in range(i+1, len(lines)):
                    new_lines.append(lines[j])
                    if '"""' in lines[j] or "'''" in lines[j]:
                        break
                new_lines.extend(lines[j+1:])
                break
        else:
            # 没有匹配到上述情况，在文件开头插入
            new_lines = COPYRIGHT_HEADER.split('\n') + [''] + lines
        
        filepath.write_text('\n'.join(new_lines), encoding='utf-8')
        print(f"  ✅ 添加版权: {filepath}")
        return True
        
    except Exception as e:
        print(f"  ❌ 错误: {filepath} - {e}")
        return False

def main():
    project_root = Path('/root/.openclaw/workspace/Voxplore')
    app_dir = project_root / 'app'
    
    print("开始为 Python 文件添加版权头...")
    
    py_files = list(app_dir.glob('**/*.py'))
    py_files.extend([project_root / 'main.py', project_root / 'setup.py'])
    
    added = 0
    skipped = 0
    
    for f in sorted(set(py_files)):
        # 跳过 node_modules 和 __pycache__
        if '__pycache__' in str(f) or 'node_modules' in str(f):
            continue
            
        if add_copyright_to_file(f):
            added += 1
        else:
            skipped += 1
    
    print(f"\n完成! 添加: {added}, 跳过: {skipped}")

if __name__ == '__main__':
    main()
