---
title: 贡献指南
description: 如何参与 SceneFab 的开发与贡献。
---

# 贡献指南

## 欢迎贡献

SceneFab 采用 MIT 协议开源，欢迎任何形式的贡献！

## 开发环境

```bash
git clone https://github.com/Agions/scene-fab.git
cd SceneFab
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -e ".[dev]"
```

## 分支管理

| 分支 | 用途 |
|------|------|
| `main` | 稳定版本 |
| `develop` | 开发分支 |
| `feat/*` | 新功能 |
| `fix/*` | 修复 |

```bash
# 创建功能分支
git checkout -b feat/your-feature main

# 开发完成后
git push origin feat/your-feature
```

## 代码规范

```bash
# 运行检查
ruff check .
ruff format .

# 运行测试
pytest tests/
```

## 提交规范

```
feat: 新功能
fix: 修复 bug
docs: 文档更新
style: 代码格式（不影响功能）
refactor: 重构
test: 测试相关
chore: 构建/工具
```

## Pull Request

1. Fork 本仓库
2. 创建功能分支
3. 编写代码和测试
4. 提交并 push
5. 发起 PR，描述改动内容

:::tip
重大改动请先开 Issue 讨论！
:::
