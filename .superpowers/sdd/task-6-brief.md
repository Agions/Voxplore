# Task 6: 删除旧目录与空子包

## 位置
项目根目录: `/Users/zfkc/Desktop/04-AI/scene-fab`

## 任务描述
删除 3 个已空的旧目录：`services/video_tools/`（文件已全部移走）、`services/video/grouping/`（空子包）、`services/video/selection/`（空子包）。

## 执行步骤

### Step 1: 确认 video_tools/ 已空（仅剩 __pycache__）

```bash
find src/scenefab/services/video_tools -type f -name '*.py' 2>/dev/null && echo "FAIL: 还有 .py 文件" || echo "OK: video_tools/ 已空（仅 __pycache__）"
```

Expected output: `OK: video_tools/ 已空（仅 __pycache__）`

### Step 2: 删除空目录

```bash
rm -rf src/scenefab/services/video_tools
rm -rf src/scenefab/services/video/grouping
rm -rf src/scenefab/services/video/selection
```

### Step 3: 验证

```bash
test ! -d src/scenefab/services/video_tools && echo "OK: video_tools/ deleted" || echo "FAIL"
test ! -d src/scenefab/services/video/grouping && echo "OK: grouping/ deleted" || echo "FAIL"
test ! -d src/scenefab/services/video/selection && echo "OK: selection/ deleted" || echo "FAIL"
```

All three should print "OK".

### Step 4: Commit

```bash
git add -A
git commit -m "refactor: 删除 video_tools/ 空目录及 grouping/ selection/ 空子包"
```

## 验证
执行 Step 3 确认三个目录已删除。

## 全局约束
- 只删除空目录，不删除任何包含 .py 文件的目录
- 不做功能变更
