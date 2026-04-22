# Voxplore Windows 构建脚本 (PowerShell)
# 用法: .\build_windows.ps1
# 输出: Voxplore-{version}-windows-x64.zip

param(
    [string]$Version
)

$ErrorActionPreference = "Stop"

# 版本号
if (-not $Version) {
    $Version = (Select-String -Path "pyproject.toml" -Pattern '^version = "(.+)"' | ForEach-Object { $_.Matches.Groups[1].Value })
}

$Platform = "windows-x64"
$OutputZip = "Voxplore-${Version}-${Platform}.zip"
$AppDir = "dist\Voxplore-${Version}-${Platform}"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Voxplore Windows 构建 (PyInstaller)" -ForegroundColor Cyan
Write-Host "  版本: ${Version}" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# 清理
Write-Host "[1/5] 清理旧构建..." -ForegroundColor Yellow
if (Test-Path build) { Remove-Item -Recurse -Force build }
if (Test-Path dist) { Remove-Item -Recurse -Force dist }
New-Item -ItemType Directory -Path dist -Force | Out-Null

# 依赖检查
Write-Host "[2/5] 检查依赖..." -ForegroundColor Yellow
try {
    Get-Command pyinstaller -ErrorAction Stop | Out-Null
} catch {
    Write-Host "  PyInstaller 未安装，正在安装..." -ForegroundColor Yellow
    pip install pyinstaller
}

# 安装依赖
Write-Host "[3/5] 安装依赖..." -ForegroundColor Yellow
pip install -e .

# PyInstaller 构建
Write-Host "[4/5] PyInstaller 构建..." -ForegroundColor Yellow
pyinstaller `
    --clean `
    --onedir `
    --name "Voxplore-${Version}-${Platform}" `
    --add-data "resources;resources" `
    --hidden-import=PySide6 `
    --hidden-import=PySide6.QtCore `
    --hidden-import=PySide6.QtGui `
    --hidden-import=PySide6.QtWidgets `
    --hidden-import=PySide6.QtMultimedia `
    --hidden-import=cv2 `
    --hidden-import=numpy `
    --hidden-import=PIL `
    --hidden-import=librosa `
    --hidden-import=soundfile `
    --hidden-import=pydub `
    --hidden-import=faster_whisper `
    --hidden-import=edge_tts `
    --hidden-import=openai `
    --hidden-import=cryptography `
    --hidden-import=keyring `
    --hidden-import=httpx `
    --hidden-import=dotenv `
    --hidden-import=yaml `
    --collect-all=PySide6 `
    --noconfirm `
    app/main.py

# 打包 zip
Write-Host "[5/5] 打包 zip..." -ForegroundColor Yellow
if (Test-Path "dist\${OutputZip}") { Remove-Item "dist\${OutputZip}" }
Compress-Archive -Path "${AppDir}\*" -DestinationPath "dist\${OutputZip}" -Force

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  ✅ 构建成功！" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host "  输出文件: dist\${OutputZip}" -ForegroundColor Green
Write-Host ""
