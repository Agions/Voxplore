#!/bin/bash
# Narrafiilm DMG 打包脚本
# 使用方法: ./build_dmg.sh

set -e

# 配置
APP_NAME="Narrafiilm"
VERSION=$(grep '^version = ' pyproject.toml | sed 's/version = "//' | sed 's/"//')
APP_BUNDLE="${APP_NAME}.app"
DMG_NAME="${APP_NAME}-${VERSION}-macOS.dmg"
TEMP_DIR="/tmp/${APP_NAME}_build"
RESOURCES_DIR="resources/icons"

echo "========================================"
echo "  Narrafiilm DMG 打包工具"
echo "  版本: ${VERSION}"
echo "========================================"
echo ""

# 清理
echo "[1/6] 清理旧构建..."
rm -rf build dist "${APP_BUNDLE}" *.dmg
mkdir -p "${TEMP_DIR}"

# 检查依赖
echo "[2/6] 检查依赖..."
if ! command -v pyinstaller &> /dev/null; then
    echo "错误: PyInstaller 未安装"
    echo "请运行: pip install pyinstaller"
    exit 1
fi

if [ ! -d "resources" ]; then
    echo "警告: resources 目录不存在"
fi

# 安装依赖
echo "[3/6] 安装依赖..."
pip install -e .

# 使用 PyInstaller 构建
echo "[4/6] 构建应用..."
pyinstaller \
    --name="${APP_NAME}" \
    --windowed \
    --onedir \
    --add-data="resources:resources" \
    --hidden-import="PySide6" \
    --hidden-import="PySide6.QtCore" \
    --hidden-import="PySide6.QtGui" \
    --hidden-import="PySide6.QtWidgets" \
    --hidden-import="PySide6.QtMultimedia" \
    --hidden-import="cryptography" \
    --hidden-import="cryptography.fernet" \
    --hidden-import="cryptography.hazmat" \
    --hidden-import="keyring" \
    --hidden-import="keyring.backends" \
    --collect-all="PySide6" \
    --noconfirm \
    main.py

# 创建 .app 捆绑包
echo "[5/6] 创建应用捆绑包..."
mkdir -p "${APP_BUNDLE}/Contents/MacOS"
mkdir -p "${APP_BUNDLE}/Contents/Resources"

# 复制可执行文件
cp -r "dist/${APP_NAME}/"* "${APP_BUNDLE}/Contents/MacOS/"

# 复制资源
cp -r resources "${APP_BUNDLE}/Contents/"

# 复制图标
if [ -f "${RESOURCES_DIR}/${APP_NAME}.icns" ]; then
    cp "${RESOURCES_DIR}/${APP_NAME}.icns" "${APP_BUNDLE}/Contents/Resources/"
fi

# 创建 Info.plist
cat > "${APP_BUNDLE}/Contents/Info.plist" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleDevelopmentRegion</key>
    <string>zh_CN</string>
    <key>CFBundleExecutable</key>
    <string>${APP_NAME}</string>
    <key>CFBundleIconFile</key>
    <string>${APP_NAME}</string>
    <key>CFBundleIdentifier</key>
    <string>com.narrafiilm.${APP_NAME}</string>
    <key>CFBundleInfoDictionaryVersion</key>
    <string>6.0</string>
    <key>CFBundleName</key>
    <string>${APP_NAME}</string>
    <key>CFBundleDisplayName</key>
    <string>${APP_NAME}</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleShortVersionString</key>
    <string>${VERSION}</string>
    <key>CFBundleVersion</key>
    <string>1</string>
    <key>LSMinimumSystemVersion</key>
    <string>10.15</string>
    <key>NSHumanReadableCopyright</key>
    <string>Copyright © 2024-2026 Agions. All rights reserved.</string>
    <key>NSPrincipalClass</key>
    <string>NSApplication</string>
    <key>NSHighResolutionCapable</key>
    <true/>
</dict>
</plist>
EOF

# 设置权限
chmod -R a+rX "${APP_BUNDLE}"
chmod +x "${APP_BUNDLE}/Contents/MacOS/"*

# 创建 DMG
echo "[6/6] 创建 DMG..."
if command -v create-dmg &> /dev/null; then
    create-dmg \
        --volname "${APP_NAME}" \
        --volicon "${RESOURCES_DIR}/${APP_NAME}.icns" \
        --window-pos 200 120 \
        --window-size 600 400 \
        --icon-size 100 \
        --icon "${APP_BUNDLE}" 150 185 \
        --app-drop-link 450 185 \
        "${DMG_NAME}" \
        "${APP_BUNDLE}"
else
    # 使用 hdiutil 作为备选
    hdiutil create -volname "${APP_NAME}" -srcfolder "${APP_BUNDLE}" -ov -format UDZO "${DMG_NAME}"
fi

# 完成
echo ""
echo "========================================"
echo "  构建成功!"
echo "========================================"
echo ""
echo "输出文件:"
echo "  - ${APP_BUNDLE}"
echo "  - ${DMG_NAME}"
echo ""
echo "下一步:"
echo "  1. 检查 .app 文件是否可以正常运行"
echo "  2. 分发 .dmg 文件给用户"
echo ""
