# -*- mode: python ; coding: utf-8 -*-
"""
Voxplore PyInstaller 构建配置
使用方法: pyinstaller main.spec

版本: 1.2.0
"""

import sys
import os

block_cipher = None

# 版本
VERSION = "3.8.1"

# 分析入口点
app_main = 'app/main.py'

a = Analysis(
    [app_main],
    pathex=[],
    binaries=[],
    datas=[
        ('resources', 'resources'),
    ],
    hiddenimports=[
        'PySide6',
        'PySide6.QtCore',
        'PySide6.QtGui',
        'PySide6.QtWidgets',
        'cv2',
        'numpy',
        'PIL',
        'librosa',
        'soundfile',
        'pydub',
        'faster_whisper',
        'edge_tts',
        'openai',
        'google_generativeai',
        'requests',
        'httpx',
        'dotenv',
        'yaml',
        'cryptography',
        'keyring',
        'psutil',
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=f'Voxplore-{VERSION}',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    name=f'Voxplore-{VERSION}',
)
