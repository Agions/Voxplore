# Voxplore 多系统版本打包与 GitHub 发布策略

**日期：** 2026-04-22
**版本：** v1.0
**负责人：** claw
**状态：** 设计中

---

## 1. 目标

建立一套**自动化、跨平台、可维护**的构建发布体系：

- **Hybrid 构建**：PyInstaller（Win/macOS）+ Nuitka（Linux）
- **自动发布**：push tag → GitHub Actions 构建 → 自动上传到 Releases
- **Auto-update**：启动时检测最新版本，提示用户下载
- **统一命名**：`Voxplore-{version}-{os}-{arch}.{ext}`

---

## 2. 构建策略

### 2.1 平台矩阵

| 平台 | 架构 | 打包工具 | 输出格式 | 文件名 |
|------|------|----------|----------|--------|
| Windows | x64 | PyInstaller | .zip | `Voxplore-{ver}-windows-x64.zip` |
| macOS | x64 | PyInstaller | .dmg | `Voxplore-{ver}-macos-x64.dmg` |
| macOS | ARM64 | PyInstaller | .dmg | `Voxplore-{ver}-macos-arm64.dmg` |
| Linux | x86_64 | Nuitka | .AppImage | `Voxplore-{ver}-linux-x86_64.AppImage` |

### 2.2 PyInstaller（Windows / macOS）

**理由：** 成熟稳定，跨平台兼容性好，Qt 生态支持完善。

**关键配置：**
```spec
# main.spec
a = Analysis(
    ['app/main.py'],
    hiddenimports=[
        'PySide6', 'PySide6.QtCore', 'PySide6.QtGui', 'PySide6.QtWidgets',
        'cv2', 'numpy', 'PIL', 'librosa', 'soundfile', 'pydub',
        'faster_whisper', 'edge_tts', 'openai',
        'cryptography', 'keyring', 'httpx', 'dotenv', 'yaml',
    ],
    datas=[('resources', 'resources')],
)
```

**macOS 特殊处理：**
- 生成 `.app` 捆绑包后用 `create-dmg` 或 `hdiutil` 打包成 `.dmg`
- 需要处理 Apple Silicon (ARM64) 的 universal2 支持或单独构建

**Windows 特殊处理：**
- 打包为 `onedir` 后压缩成 `.zip`（不解压直接分发）
- 可选 UPX 压缩减少体积

### 2.3 Nuitka（Linux）

**理由：** 编译成 C 代码静态链接，启动速度 2-3x，包体积减少 40%+。

**关键配置：**
```bash
nuitka \
    --standalone \
    --onefile \
    --enable-plugin=pyside6 \
    --include-qt-plugins=accessible,iconengines,imageformats,platforms,styles \
    --output-dir="dist-nuitka" \
    --output-filename="Voxplore-{version}-linux-x86_64" \
    --windows-icon-from-ico="resources/icons/app_icon.ico" \
    --enable-console=no \
    app/main.py
```

**生成 AppImage：**
```bash
# 使用 linuxdeployqt 或 appimagetool 打包
appimagetool "Voxplore-{version}-linux-x86_64" Voxplore-{version}-linux-x86_64.AppImage
```

---

## 3. CI/CD 流程

### 3.1 触发条件

```yaml
on:
  push:
    tags:
      - 'v*'        # e.g. v4.0.0
  workflow_dispatch:  # 手动触发
    inputs:
      version:
        description: 'Version (without v)'
        required: false
```

### 3.2 矩阵构建

```yaml
strategy:
  matrix:
    include:
      - os: windows-latest
        platform: windows-x64
        ext: zip
        tool: pyinstaller
      - os: macos-latest
        platform: macos-x64
        ext: dmg
        tool: pyinstaller
      - os: macos-14-latest
        platform: macos-arm64
        ext: dmg
        tool: pyinstaller
      - os: ubuntu-latest
        platform: linux-x86_64
        ext: AppImage
        tool: nuitka
```

### 3.3 构建步骤（每个 Job）

```
1. Checkout code
2. Set up Python 3.11
3. Install dependencies (pip install -e .)
4. Build with PyInstaller/Nuitka
5. Package artifact (.zip / .dmg / .AppImage)
6. Upload to GitHub Release (via softprops/action-gh-release)
```

### 3.4 GitHub Release 自动创建

```yaml
- name: Create GitHub Release
  uses: softprops/action-gh-release@v1
  with:
    files: dist/*
    generate_release_notes: true
    draft: false
  env:
    GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

### 3.5 完整 Workflow 文件

见 `docs/plans/YYYY-MM-DD-release-strategy-design.md` 附件，或直接查看 `.github/workflows/release-build.yml`。

---

## 4. 构建脚本重构

### 4.1 统一 Makefile

```makefile
# Voxplore Makefile
VERSION := $(shell grep '^version = ' pyproject.toml | sed 's/version = "//;s/"//')
PYINSTALLER := pyinstaller

.PHONY: help build build:win build:mac build:mac-arm build:linux clean test

help:
	@echo "Voxplore Build System (v$(VERSION))"
	@echo "  build         - 构建当前平台版本"
	@echo "  build:win     - Windows x64 (.zip)"
	@echo "  build:mac     - macOS x64 (.dmg)"
	@echo "  build:mac-arm - macOS ARM64 (.dmg)"
	@echo "  build:linux   - Linux x86_64 (.AppImage)"

build: build:$(shell python3 -c "import sys; print('win' if sys.platform=='win32' else 'mac' if sys.platform=='darwin' else 'linux'))
build:win:
	$(PYINSTALLER) --clean --onedir --name Voxplore-$(VERSION)-windows-x64 \
		--add-data "resources;resources" app/main.py
	cd dist && powershell -Command "Compress-Archive -Path 'Voxplore-$(VERSION)-windows-x64' -DestinationPath 'Voxplore-$(VERSION)-windows-x64.zip'"

build:mac:
	./scripts/build_macos.sh x64

build:mac-arm:
	./scripts/build_macos.sh arm64

build:linux:
	./scripts/build_linux.sh

clean:
	rm -rf build/ dist/ dist-nuitka/ *.egg-info
```

### 4.2 统一脚本目录结构

```
scripts/
├── build_macos.sh      # macOS 构建（x64 / arm64）
├── build_linux.sh      # Linux Nuitka + AppImage
├── build_windows.ps1   # Windows 构建（可选 PowerShell）
└── common.sh           # 共享函数（版本号读取等）
```

### 4.3 build_macos.sh

```bash
#!/bin/bash
set -e
source scripts/common.sh

ARCH=${1:-x64}
DMG_NAME="Voxplore-${VERSION}-macos-${ARCH}.dmg"
APP_NAME="Voxplore.app"

echo "=== Building Voxplore for macOS ${ARCH} ==="

pip install -e .

pyinstaller \
    --name="Voxplore-${VERSION}-macos-${ARCH}" \
    --windowed \
    --onedir \
    --add-data="resources:resources" \
    --hidden-import=PySide6 \
    --collect-all=PySide6 \
    --noconfirm \
    app/main.py

# 创建 .app bundle
./scripts/create_app_bundle.sh "dist/Voxplore-${VERSION}-macos-${ARCH}" "${APP_NAME}"

# 打包 DMG
create-dmg \
    --volname "Voxplore" \
    --window-size 600 400 \
    --icon "${APP_NAME}" 150 185 \
    --app-drop-link 450 185 \
    "${DMG_NAME}" \
    "${APP_NAME}" || \
hdiutil create -volname "Voxplore" -srcfolder "${APP_NAME}" -ov -format UDZO "${DMG_NAME}"

echo "=== Output: ${DMG_NAME} ==="
```

### 4.4 build_linux.sh

```bash
#!/bin/bash
set -e
source scripts/common.sh

APPIMAGE_NAME="Voxplore-${VERSION}-linux-x86_64.AppImage"

echo "=== Building Voxplore for Linux (Nuitka) ==="

pip install -e . nuitka

nuitka \
    --standalone \
    --onefile \
    --enable-plugin=pyside6 \
    --include-qt-plugins=accessible,iconengines,imageformats,platforms,styles \
    --remove-output \
    --output-dir="dist-nuitka" \
    --output-filename="Voxplore-${VERSION}-linux-x86_64" \
    --enable-console=no \
    app/main.py

# 打包 AppImage（使用 appimagetool）
wget -q "https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage"
chmod +x appimagetool-x86_64.AppImage
ARCH=x86_64 ./appimagetool-x86_64.AppImage \
    "dist-nuitka/Voxplore-${VERSION}-linux-x86_64" \
    "${APPIMAGE_NAME}"

echo "=== Output: ${APPIMAGE_NAME} ==="
```

---

## 5. Auto-Update 模块

### 5.1 设计

**原则：** 轻量、安全、无需签名。只检测版本 + 显示下载链接，不自动下载安装。

```
启动 → 检测最新 Release → 比较版本 → 有新版本则弹窗提示
```

### 5.2 实现方案

**文件：** `app/update/checker.py`

```python
"""
Voxplore Auto-Update Checker
启动时检测 GitHub Releases 最新版本，有新版本时提示用户下载。
"""
import httpx
import re
from dataclasses import dataclass
from typing import Optional
from app.utils.version import __version__

GITHUB_API = "https://api.github.com/repos/Agions/Voxplore/releases/latest"
GITHUB_RELEASES = "https://github.com/Agions/Voxplore/releases"

@dataclass
class UpdateInfo:
    version: str          # e.g. "4.0.0"
    url: str              # 下载地址
    body: str             # 发布说明
    is_newer: bool        # 是否有新版本

def parse_version(v: str) -> tuple:
    """解析版本号为 tuple，用于比较"""
    return tuple(int(x) for x in re.findall(r'\d+', v))

def check_update() -> Optional[UpdateInfo]:
    """检测更新。返回 UpdateInfo 或 None（检测失败）"""
    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(GITHUB_API, headers={"Accept": "application/vnd.github.v3+json"})
            resp.raise_for_status()
            data = resp.json()

        latest = data.get("tag_name", "").lstrip("v")
        current = __version__

        is_newer = parse_version(latest) > parse_version(current)

        # 构造下载链接（从 assets 获取）
        assets = data.get("assets", [])
        download_url = GITHUB_RELEASES  # fallback

        return UpdateInfo(
            version=latest,
            url=GITHUB_RELEASES,
            body=data.get("body", ""),
            is_newer=is_newer,
        )
    except Exception:
        return None  # 网络失败，静默忽略
```

### 5.3 集成到主程序

在 `app/main.py` 的 `main()` 函数中，GUI 启动后异步检测：

```python
def main():
    # ... 启动 GUI ...
    window.show()

    # 启动后 3 秒检测更新（非阻塞）
    from PySide6.QtCore import QTimer
    QTimer.singleShot(3000, lambda: _check_update_async(window))

    sys.exit(qt_app.exec())

def _check_update_async(window):
    info = check_update()
    if info and info.is_newer:
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.information(
            window,
            "🎉 发现新版本",
            f"Voxplore {info.version} 已发布！\n\n"
            f"当前版本：{__version__}\n"
            f"最新版本：{info.version}\n\n"
            f"点击确定前往下载：\n{info.url}"
        )
```

### 5.4 版本号来源

版本号统一从 `pyproject.toml` 读取：

```python
import re
from pathlib import Path

def get_version() -> str:
    root = Path(__file__).parent.parent.parent
    text = (root / "pyproject.toml").read_text()
    m = re.search(r'^version = "(.+)"', text, re.M)
    return m.group(1) if m else "0.0.0"
```

---

## 6. 实施计划

### Phase 1：完善 CI/CD Workflow
1. 重写 `.github/workflows/release-build.yml`，支持 4 个平台矩阵
2. 配置 `softprops/action-gh-release` 自动创建 Release + 上传 assets
3. 添加 `workflow_dispatch` 手动触发能力

### Phase 2：重构构建脚本
1. 创建 `scripts/` 目录，统一构建脚本
2. 重写 `build_dmg.sh` → `scripts/build_macos.sh`（支持 arch 参数）
3. 重写 `build_nuitka.sh` → `scripts/build_linux.sh`
4. 更新 `Makefile` 引用新脚本路径

### Phase 3：Auto-update 模块
1. 创建 `app/update/checker.py`
2. 集成到 `app/main.py` 启动流程
3. 确保网络失败时静默忽略（不阻塞用户使用）

### Phase 4：清理与测试
1. 清理 `main.spec` 中的 `Narrafiilm` 残留命名
2. 更新 `main.spec` 版本号为动态读取
3. 本地测试各平台构建流程

---

## 7. 关键文件清单

| 文件 | 操作 |
|------|------|
| `.github/workflows/release-build.yml` | 重写（Phase 1）|
| `scripts/build_macos.sh` | 新建（Phase 2）|
| `scripts/build_linux.sh` | 新建（Phase 2）|
| `scripts/common.sh` | 新建（Phase 2）|
| `Makefile` | 更新（Phase 2）|
| `main.spec` | 清理 + 动态版本（Phase 4）|
| `app/update/checker.py` | 新建（Phase 3）|
| `app/main.py` | 集成 update checker（Phase 3）|

---

## 8. 版本号管理

**单一真相来源：** `pyproject.toml` 的 `version` 字段。

所有脚本通过以下方式读取版本：
```bash
VERSION=$(grep '^version = ' pyproject.toml | sed 's/version = "//;s/"//')
```

CI/CD / 构建脚本 / auto-update checker 均引用同一版本号，无需手动维护多份。
