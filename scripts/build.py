#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
打包和发布脚本
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path


def check_dependencies():
    """检查依赖"""
    print("检查依赖...")
    
    required = ["PyQt6", "httpx", "openai"]
    optional = ["pyinstaller", "pytest"]
    
    for pkg in required:
        try:
            __import__(pkg.lower().replace("-", "_"))
            print(f"  ✓ {pkg}")
        except ImportError:
            print(f"  ✗ {pkg} (required)")
            return False
            
    for pkg in optional:
        try:
            __import__(pkg.lower().replace("-", "_"))
            print(f"  ✓ {pkg}")
        except ImportError:
            print(f"  - {pkg} (optional)")
            
    return True


def clean_build():
    """清理构建目录"""
    print("清理构建目录...")
    
    dirs_to_clean = ["build", "dist", "__pycache__"]
    
    for d in dirs_to_clean:
        if Path(d).exists():
            shutil.rmtree(d)
            print(f"  删除 {d}/")
    
    # 清理 .pyc 文件
    for pyc in Path(".").rglob("*.pyc"):
        pyc.unlink()
        
    for pycache in Path(".").rglob("__pycache__"):
        shutil.rmtree(pycache)


def build_exe(platform="auto"):
    """
    构建可执行文件
    
    Args:
        platform: auto/windows/macos/linux
    """
    print(f"构建 {platform} 可执行文件...")
    
    if platform == "auto":
        import platform as plat
        system = plat.system().lower()
        if "darwin" in system:
            platform = "macos"
        elif "windows" in system:
            platform = "windows"
        else:
            platform = "linux"
    
    # 检查 pyinstaller
    try:
        import PyInstaller
    except ImportError:
        print("安装 PyInstaller...")
        subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"])
    
    # 构建命令
    cmd = [
        "pyinstaller",
        "main.py",
        "--name=Voxplore",
        "--onedir",
        "--windowed",
        "--icon=resources/icon.ico",
        f"--distpath=dist/{platform}",
        "--clean",
    ]
    
    if platform == "windows":
        cmd.append("--icon=resources/icon.ico")
    elif platform == "macos":
        cmd.append("--icon=resources/icon.icns")
        
    subprocess.run(cmd)
    print(f"✓ 构建完成: dist/{platform}/Voxplore")


def create_portable():
    """创建便携版"""
    print("创建便携版...")
    
    import zipfile
    
    version = "1.0.0"
    archive_name = f"Voxplore-{version}-portable.zip"
    
    with zipfile.ZipFile(archive_name, 'w', zipfile.ZIP_DEFLATED) as zf:
        # 添加可执行文件
        dist_path = Path("dist/windows/Voxplore")
        if dist_path.exists():
            for f in dist_path.rglob("*"):
                if f.is_file():
                    zf.write(f, f.relative_to(dist_path.parent))
    
    print(f"✓ 便携版创建: {archive_name}")


def run_tests():
    """运行测试"""
    print("运行测试...")
    
    result = subprocess.run([
        sys.executable, "-m", "pytest",
        "tests/",
        "-v",
        "--ignore=tests/test_ui_components.py",
        "--ignore=tests/test_integration.py",
    ], capture_output=True, text=True)
    
    print(result.stdout)
    
    if result.returncode != 0:
        print("⚠ 测试有失败")
        return False
        
    return True


def publish_pypi():
    """发布到 PyPI"""
    print("发布到 PyPI...")
    
    # 构建源码包
    subprocess.run([
        sys.executable, "-m", "pip", "install", "build"
    ])
    
    subprocess.run([
        sys.executable, "-m", "build"
    ])
    
    # 上传
    subprocess.run([
        sys.executable, "-m", "pip", "upload",
        "--skip-existing",
    ])
    
    print("✓ 已发布到 PyPI")


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Voxplore 构建工具")
    parser.add_argument("action", choices=["check", "clean", "build", "test", "publish", "all"])
    parser.add_argument("--platform", default="auto")
    
    args = parser.parse_args()
    
    if args.action == "check":
        check_dependencies()
    elif args.action == "clean":
        clean_build()
    elif args.action == "build":
        build_exe(args.platform)
    elif args.action == "test":
        run_tests()
    elif args.action == "publish":
        publish_pypi()
    elif args.action == "all":
        check_dependencies()
        run_tests()
        clean_build()
        build_exe(args.platform)


if __name__ == "__main__":
    main()
