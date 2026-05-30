# 贡献指南

SceneFab 采用 MIT 协议开源，欢迎任何形式的贡献！

## 开发环境

```bash
git clone https://github.com/Agions/scene-fab.git
cd scene-fab
python -m venv venv
source venv/bin/activate
pip install -e ".[dev]"
```

## 分支管理

| 分支 | 用途 |
|------|------|
| `main` | 稳定版本 |
| `feat/*` | 新功能 |
| `fix/*` | 修复 |

```bash
git checkout -b feat/your-feature main
git push origin feat/your-feature
```

## 代码规范

```bash
ruff check .
ruff format .
pytest tests/
```

## 提交规范

```
feat: 新功能
fix: 修复 bug
docs: 文档更新
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

::: tip
重大改动请先开 Issue 讨论！
:::