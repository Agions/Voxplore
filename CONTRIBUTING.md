# 贡献指南

感谢你对 SceneFab 的关注！我们欢迎任何形式的贡献 🎉

---

## 贡献方式

- 🐛 **报告 Bug** — [提交 Issue](https://github.com/Agions/scene-fab/issues/new?template=bug_report.md)
- 💡 **功能建议** — [提交 Feature Request](https://github.com/Agions/scene-fab/issues/new?template=feature_request.md)
- 📝 **改进文档** — 修正错别字、补充说明
- 🔧 **提交代码** — Bug 修复、新功能实现
- ⭐ **推广项目** — 分享给更多人

---

## 开发环境

```bash
# 1. Fork 并克隆
git clone https://github.com/YOUR_USERNAME/SceneFab.git
cd SceneFab

# 2. 创建虚拟环境
python -m venv .venv
source .venv/bin/activate        # Linux / macOS
.venv\Scripts\activate           # Windows

# 3. 安装依赖
pip install -r requirements.txt

# 4. 验证环境
pytest tests/ -q
```

---

## 分支规范

```bash
# 功能分支
git checkout -b feature/your-feature-name

# Bug 修复分支
git checkout -b fix/issue-description
```

---

## Commit 规范

遵循 [Conventional Commits](https://www.conventionalcommits.org/)：

| 类型 | 说明 |
|------|------|
| `feat` | 新功能 |
| `fix` | Bug 修复 |
| `docs` | 文档更新 |
| `refactor` | 重构（无功能变化）|
| `test` | 测试相关 |
| `chore` | 构建/工具链变更 |

**示例**：

```bash
git commit -m "feat: add 7th emotion style — documentary narration"
git commit -m "fix(jianying): resolve AttributeError in JianyingMaterials.to_dict()"
git commit -m "docs: update quick-start guide with new installation steps"
```

---

## 代码质量

提交前请确认：

```bash
# 测试通过
pytest tests/ -q

# Lint 检查
ruff check app/
```

新功能请同步添加测试用例。

---

## 优先贡献方向

1. **Windows 平台测试** — 主要在 macOS 开发，需要 Windows 反馈
2. **英文文档完善** — 帮助国际用户
3. **新模型接入** — 接入更多 AI 模型
4. **性能优化** — 大文件处理速度

---

## 交流

- 提问和讨论：[GitHub Discussions](https://github.com/Agions/scene-fab/discussions)
- Bug 报告：[GitHub Issues](https://github.com/Agions/scene-fab/issues)

---

感谢每一位贡献者！你们让这个项目变得更好 ❤️
