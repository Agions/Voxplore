# Task 9: 更新文档与 VitePress 配置

## 位置
项目根目录: `/Users/zfkc/Desktop/04-AI/scene-fab`

## 任务描述
重命名超长文档文件，并同步更新 VitePress 路由配置。

## 执行步骤

### Step 1: 重命名文档

```bash
git mv docs/guide/first-person-narration-production.md docs/guide/narration-spec.md
```

### Step 2: 更新 VitePress config.ts

**File:** `docs/.vitepress/config.ts`

Use sed to update both sidebar and nav links:

```bash
sed -i '' "s|first-person-narration-production|narration-spec|g" docs/.vitepress/config.ts
```

### Step 3: 验证

```bash
echo "=== 文档文件 ==="
ls docs/guide/narration-spec.md && echo "OK: narration-spec.md exists" || echo "FAIL"

echo "=== VitePress 路由 ==="
grep "narration-spec" docs/.vitepress/config.ts && echo "OK: routes updated" || echo "FAIL"

echo "=== 旧文件应不存在 ==="
test ! -f docs/guide/first-person-narration-production.md && echo "OK: old file gone" || echo "FAIL"
```

All checks should pass.

### Step 4: Commit

```bash
git add -A
git commit -m "docs: 重命名过长文档文件并同步 VitePress 路由"
```

## 验证
执行 Step 3 确认文档已重命名且 VitePress 路由已同步。

## 全局约束
- 必须使用 `git mv` 重命名文档
- VitePress config.ts 中两处链接必须同步更新
