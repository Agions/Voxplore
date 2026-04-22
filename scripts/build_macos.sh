#!/bin/bash
# Voxplore macOS 构建脚本
# 用法: ./build_macos.sh [x64|arm64]
#   默认 x64（Intel）
#   arm64 = Apple Silicon

set -e
cd "$(dirname "$0")/.."
source scripts/common.sh

ARCH=${1:-x64}
PLATFORM="macos-${ARCH}"
OUTPUT_NAME="Voxplore-${VERSION}-${PLATFORM}.dmg"
APP_BUNDLE="Voxplore.app"
PY_NAME="Voxplore-${VERSION}-${PLATFORM}"

info "========================================"
info "  Voxplore macOS 构建"
info "  版本: ${VERSION}"
info "  架构: ${ARCH}"
info "========================================"

# ── 清理 ──────────────────────────────────────────────────────
step "[1/6] 清理旧构建..."
rm -rf build dist "${APP_BUNDLE}" "${OUTPUT_NAME}"
mkdir -p dist

# ── 依赖检查 ───────────────────────────────────────────────────
step "[2/6] 检查依赖..."
if ! command -v pyinstaller &> /dev/null; then
    warn "PyInstaller 未安装，正在安装..."
    pip install pyinstaller
fi

if ! command -v create-dmg &> /dev/null && ! command -v hdiutil &> /dev/null; then
    warn "create-dmg 和 hdiutil 均不可用，将使用 hdiutil"
fi

# ── 安装依赖 ───────────────────────────────────────────────────
step "[3/6] 安装依赖..."
pip install -e .

# ── PyInstaller 构建 ───────────────────────────────────────────
step "[4/6] PyInstaller 构建..."
pyinstaller \
    --clean \
    --onedir \
    --name "${PY_NAME}" \
    --windowed \
    --add-data="resources:resources" \
    --hidden-import=PySide6 \
    --hidden-import=PySide6.QtCore \
    --hidden-import=PySide6.QtGui \
    --hidden-import=PySide6.QtWidgets \
    --hidden-import=PySide6.QtMultimedia \
    --hidden-import=cv2 \
    --hidden-import=numpy \
    --hidden-import=PIL \
    --hidden-import=librosa \
    --hidden-import=soundfile \
    --hidden-import=pydub \
    --hidden-import=faster_whisper \
    --hidden-import=edge_tts \
    --hidden-import=openai \
    --hidden-import=cryptography \
    --hidden-import=keyring \
    --hidden-import=httpx \
    --hidden-import=dotenv \
    --hidden-import=yaml \
    --collect-all=PySide6 \
    --noconfirm \
    app/main.py

# ── 创建 .app bundle ───────────────────────────────────────────
step "[5/6] 创建 .app 捆绑包..."
mkdir -p "${APP_BUNDLE}/Contents/MacOS"
mkdir -p "${APP_BUNDLE}/Contents/Resources"
cp -r "dist/${PY_NAME}/"* "${APP_BUNDLE}/Contents/MacOS/"
cp -r resources "${APP_BUNDLE}/Contents/"

# Info.plist
cat > "${APP_BUNDLE}/Contents/Info.plist" << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleDevelopmentRegion</key><string>zh_CN</string>
    <key>CFBundleExecutable</key><string>Voxplore</string>
    <key>CFBundleIdentifier</key><string>com.voxplore.app</string>
    <key>CFBundleInfoDictionaryVersion</key><string>6.0</string>
    <key>CFBundleName</key><string>Voxplore</string>
    <key>CFBundleDisplayName</key><string>Voxplore</string>
    <key>CFBundlePackageType</key><string>APPL</string>
    <key>CFBundleShortVersionString</key><string>$VERSION</string>
    <key>CFBundleVersion</key><string>1</string>
    <key>LSMinimumSystemVersion</key><string>10.15</string>
    <key>NSHumanReadableCopyright</key><string>Copyright © 2025-2026 Agions. All rights reserved.</string>
    <key>NSPrincipalClass</key><string>NSApplication</string>
    <key>NSHighResolutionCapable</key><true/>
</dict>
</plist>
EOF

chmod -R a+rX "${APP_BUNDLE}"
chmod +x "${APP_BUNDLE}/Contents/MacOS/"* 2>/dev/null || true

# ── 打包 DMG ───────────────────────────────────────────────────
step "[6/6] 打包 DMG..."
if command -v create-dmg &> /dev/null; then
    create-dmg \
        --volname "Voxplore" \
        --window-pos 200 120 \
        --window-size 600 400 \
        --icon-size 100 \
        --icon "${APP_BUNDLE}" 150 185 \
        --app-drop-link 450 185 \
        "${OUTPUT_NAME}" \
        "${APP_BUNDLE}"
else
    hdiutil create \
        -volname "Voxplore" \
        -srcfolder "${APP_BUNDLE}" \
        -ov -format UDZO \
        "${OUTPUT_NAME}"
fi

info ""
info "========================================"
info "  ✅ 构建成功！"
info "========================================"
info "  输出文件: ${OUTPUT_NAME}"
info ""
