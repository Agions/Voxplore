# Task 11: 更新 CI 与 conftest

## 位置
项目根目录: `/Users/zfkc/Desktop/04-AI/scene-fab`

## 任务描述
更新 CI workflows 中被忽略的测试文件路径，使其与 Task 10 后的新文件名一致。

## 执行步骤

### Step 1: 更新 CI workflows 中的 --ignore 路径

Two files need updating:
- `.github/workflows/ci.yml`
- `.github/workflows/pr-check.yml`

Both contain these lines:
```
--ignore=tests/test_project_settings_manager.py \
--ignore=tests/test_project_template_manager.py \
```

Replace them with the new names:
```
--ignore=tests/test_settings_mgr.py \
--ignore=tests/test_template_mgr.py \
```

```bash
sed -i '' 's|tests/test_project_settings_manager.py|tests/test_settings_mgr.py|g' \
  .github/workflows/ci.yml .github/workflows/pr-check.yml

sed -i '' 's|tests/test_project_template_manager.py|tests/test_template_mgr.py|g' \
  .github/workflows/ci.yml .github/workflows/pr-check.yml
```

### Step 2: 验证

```bash
echo "=== ci.yml ==="
grep "test_settings_mgr\|test_template_mgr\|test_project_settings_manager\|test_project_template_manager" .github/workflows/ci.yml

echo "=== pr-check.yml ==="
grep "test_settings_mgr\|test_template_mgr\|test_project_settings_manager\|test_project_template_manager" .github/workflows/pr-check.yml
```

Expected: Only `test_settings_mgr` and `test_template_mgr` should appear. The old names should NOT appear.

### Step 3: Commit

```bash
git add -A
git commit -m "ci: 更新 CI workflows 中的测试文件路径"
```

## 验证
执行 Step 2 确认 CI 引用的测试路径已更新。

## 全局约束
- 只修改测试文件路径引用，不改变其他 CI 配置
