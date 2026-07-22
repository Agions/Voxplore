# Task 8: 精简 .gitignore

## 位置
项目根目录: `/Users/zfkc/Desktop/04-AI/scene-fab`

## 任务描述
将 .gitignore 从 392 行精简至 ~80 行，删除 Django/Flask/Scrapy/Celery 等无关条目及重复段落。

## 执行步骤

### Step 1: 备份旧文件

```bash
cp .gitignore .gitignore.bak
```

### Step 2: 写入精简后的 .gitignore

Write the following content to `.gitignore` (completely replace the file):

```gitignore
# ── Python ──────────────────────────────────────
__pycache__/
*.py[cod]
*.so
*.egg-info/
*.egg
dist/
build/
wheels/

# ── 虚拟环境 ────────────────────────────────────
.venv/
venv/
env/

# ── 测试/覆盖率 ─────────────────────────────────
.pytest_cache/
.mypy_cache/
.ruff_cache/
htmlcov/
.coverage
.coverage.*
coverage.xml

# ── IDE / 编辑器 ────────────────────────────────
.vscode/
.idea/
*.iml
*.swp
*.swo
*~

# ── macOS / Windows / Linux ─────────────────────
.DS_Store
Thumbs.db
desktop.ini

# ── 环境变量 ────────────────────────────────────
.env
.env.local
.env.*.local

# ── 应用运行时 ──────────────────────────────────
*.log
temp/
cache/
output/
exports/

# ── AI 模型文件 ─────────────────────────────────
*.pt
*.pth
*.onnx
*.h5

# ── 媒体文件（不入库）────────────────────────────
*.mp4
*.avi
*.mov
*.mkv
*.wav
*.mp3
*.flac

# ── 文档构建产物 ─────────────────────────────────
docs/.vitepress/dist/
docs/.vitepress/cache/
docs/.vitepress/.temp/
docs/node_modules/
docs/package-lock.json

# ── 本地开发文档（不入库）────────────────────────
DEVELOPMENT.md
TODO.md
SPEC.md
PLAN.md
notes/
research/
.learnings/
_DEAD/
```

### Step 3: 验证行数

```bash
wc -l .gitignore
```

Expected: ~80 lines (between 75 and 85 is acceptable).

### Step 4: 验证关键规则存在

```bash
echo "=== 关键规则检查 ==="
grep -q "__pycache__" .gitignore && echo "OK: __pycache__" || echo "FAIL"
grep -q ".venv" .gitignore && echo "OK: .venv" || echo "FAIL"
grep -q ".DS_Store" .gitignore && echo "OK: .DS_Store" || echo "FAIL"
grep -q "docs/.vitepress" .gitignore && echo "OK: docs/.vitepress" || echo "FAIL"
grep -q "node_modules" .gitignore && echo "OK: node_modules" || echo "FAIL"
grep -q "Django" .gitignore && echo "FAIL: Django still present" || echo "OK: Django removed"
grep -q "Scrapy" .gitignore && echo "FAIL: Scrapy still present" || echo "OK: Scrapy removed"
```

All checks should pass (OK). The last two should confirm removal.

### Step 5: Commit

```bash
git add .gitignore
git commit -m "chore: 精简 .gitignore 从 392 行到 ~80 行"
```

## 验证
执行 Step 3-4 确认行数和关键规则。

## 全局约束
- 必须删除所有与项目无关的模板条目（Django/Flask/Scrapy/Celery 等）
- 必须删除重复段落
- 必须保留项目实际需要的规则
