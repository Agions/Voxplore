#!/bin/bash
# Voxplore Linux 构建脚本（Nuitka + AppImage）
# 用法: ./build_linux.sh

set -e
cd "$(dirname "$0")/.."
source scripts/common.sh

PLATFORM="linux-x86_64"
APPIMAGE_NAME="Voxplore-${VERSION}-${PLATFORM}.AppImage"
APP_DIR="Voxplore-${VERSION}-${PLATFORM}.AppDir"
PY_NAME="Voxplore-${VERSION}-${PLATFORM}"

info "========================================"
info "  Voxplore Linux 构建（Nuitka）"
info "  版本: ${VERSION}"
info "========================================"

# ── 清理 ──────────────────────────────────────────────────────
step "[1/6] 清理旧构建..."
rm -rf build dist-nuitka dist/*.AppImage "${APP_DIR}"
mkdir -p dist-nuitka

# ── 依赖检查 ───────────────────────────────────────────────────
step "[2/6] 检查依赖..."
if ! command -v nuitka &> /dev/null; then
    warn "Nuitka 未安装，正在安装..."
    pip install nuitka
fi

# ── 安装依赖 ───────────────────────────────────────────────────
step "[3/6] 安装依赖..."
pip install -e .

# ── Nuitka 编译 ────────────────────────────────────────────────
step "[4/6] Nuitka 编译（这可能需要 5-15 分钟）..."
nuitka \
    --standalone \
    --onefile \
    --enable-plugin=pyside6 \
    --include-qt-plugins=accessible,iconengines,imageformats,platforms,styles \
    --remove-output \
    --output-dir="dist-nuitka" \
    --output-filename="${PY_NAME}" \
    --linux-icon="resources/icons/app_icon.png" \
    --enable-console=no \
    --follow-imports \
    app/main.py

info "  Nuitka 编译完成: dist-nuitka/${PY_NAME}"

# ── 准备 AppDir ─────────────────────────────────────────────────
step "[5/6] 准备 AppDir..."
mkdir -p "${APP_DIR}/"

# 复制可执行文件
cp "dist-nuitka/${PY_NAME}" "${APP_DIR}/"

# 复制资源
cp -r resources "${APP_DIR}/" 2>/dev/null || true

# AppRun（启动脚本）
cat > "${APP_DIR}/AppRun" << 'APPRUN'
#!/bin/bash
SELF=$(readlink -f "$0")
DIR=$(dirname "$SELF")
exec "${DIR}/Voxplore-${VERSION}-${PLATFORM}" "$@"
APPRUN
chmod +x "${APP_DIR}/AppRun"

# Voxplore.desktop（桌面快捷方式）
cat > "${APP_DIR}/Voxplore.desktop" << 'DESKTOP'
[Desktop Entry]
Name=Voxplore
Comment=AI First-Person Video Narrator
Exec=Voxplore-${VERSION}-${PLATFORM}
Icon=Voxplore
Type=Application
Categories=AudioVideo;Video;Audio;Graphics;
DESKTOP

# AppImage.yml
cat > "${APP_DIR}/AppImage.yml" << 'YML'
appid: com.voxplore.app
version: "${VERSION}"
name: Voxplore
exec: Voxplore-${VERSION}-${PLATFORM}
DESKTOP

# ── 打包 AppImage ───────────────────────────────────────────────
step "[6/6] 打包 AppImage..."

# 下载 appimagetool（如果不存在）
if [ ! -f "appimagetool" ]; then
    info "  下载 appimagetool..."
    wget -q "https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage" -O appimagetool
    chmod +x appimagetool
fi

ARCH=x86_64 ./appimagetool "${APP_DIR}" "${APPIMAGE_NAME}"

info ""
info "========================================"
info "  ✅ 构建成功！"
info "========================================"
info "  输出文件: ${APPIMAGE_NAME}"
info ""
