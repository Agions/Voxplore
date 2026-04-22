#!/bin/bash
# Narrafiilm Nuitka 打包脚本
# 性能优势：启动速度提升 2-3x，包体积减少 40%+
# 使用方法: ./build_nuitka.sh

set -e

# 配置
APP_NAME="Narrafiilm"
VERSION=$(grep '^version = ' pyproject.toml | sed 's/version = "//' | sed 's/"//')
OUTPUT_DIR="dist-nuitka"

echo "========================================"
echo "  Narrafiilm Nuitka 打包工具"
echo "  版本: ${VERSION}"
echo "========================================"
echo ""

# 检查 Nuitka
if ! command -v nuitka &> /dev/null; then
    echo "错误: Nuitka 未安装"
    echo "请运行: pip install nuitka"
    exit 1
fi

# 清理
echo "[1/3] 清理旧构建..."
rm -rf build dist-nuitka dist/${APP_NAME}-${VERSION}
mkdir -p "${OUTPUT_DIR}"

# 安装依赖
echo "[2/3] 安装依赖..."
uv pip install --system -e .

# Nuitka 编译选项
# --standalone: 独立环境
# --onefile: 打包成单个文件
# --enable-plugin=pyside6: PySide6 插件支持
# --include-qt-plugins: 包含 Qt 插件
echo "[3/3] Nuitka 编译..."
nuitka \
    --standalone \
    --onefile \
    --enable-plugin=pyside6 \
    --include-qt-plugins=accessible,iconengines,imageformats,platforms,styles \
    --remove-output \
    --output-dir="${OUTPUT_DIR}" \
    --output-filename="${APP_NAME}-${VERSION}" \
    --windows-icon-from-ico="resources/icons/app_icon.ico" \
    --enable-console=no \
    --show-progress \
    --show-memory \
    app/main.py

# 打包成 tar.gz
echo ""
echo "打包成压缩文件..."
tar -czvf "${APP_NAME}-${VERSION}-linux-x86_64.tar.gz" -C "${OUTPUT_DIR}" .

# 完成
echo ""
echo "========================================"
echo "  构建成功!"
echo "========================================"
echo ""
echo "输出文件:"
echo "  - ${OUTPUT_DIR}/${APP_NAME}"
echo "  - ${APP_NAME}-${VERSION}-linux-x86_64.tar.gz"
echo ""
echo "Nuitka 优势:"
echo "  - 启动速度提升 2-3x"
echo "  - 包体积减少 40%+"
echo "  - C 编译级别保护"
echo ""
