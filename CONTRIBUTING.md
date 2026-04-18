# 贡献指南 · Contributing Guide

感谢你对 Voxplore 的关注！我们欢迎任何形式的贡献 🎉

---

## 🌟 贡献方式

- 🐛 **报告 Bug** — [提交 Issue](https://github.com/Agions/Voxplore/issues/new?template=bug_report.md)
- 💡 **功能建议** — [提交 Feature Request](https://github.com/Agions/Voxplore/issues/new?template=feature_request.md)
- 📝 **改进文档** — 修正错别字、补充说明、翻译
- 🔧 **提交代码** — Bug 修复、新功能实现
- ⭐ **推广项目** — 分享给更多人

---

## 🚀 开发环境搭建

```bash
# 1. Fork 并克隆
git clone https://github.com/YOUR_USERNAME/Voxplore.git
cd Voxplore

# 2. 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. 安装开发依赖
pip install -r requirements.txt
pip install -e ".[dev]"

# 4. 配置环境变量
cp .env.example .env
# 编辑 .env 填入测试用 API Key

# 5. 运行测试确认环境正常
pytest tests/ -v
```

---

## 📋 提交代码流程

```bash
# 1. 从 main 创建功能分支
git checkout -b feature/your-feature-name
# 或 bug 修复分支
git checkout -b fix/issue-123

# 2. 开发并提交（遵循 Conventional Commits）
git commit -m "feat: add batch processing mode"
git commit -m "fix: resolve audio sync issue on Windows"
git commit -m "docs: update installation guide"

# 3. 推送并创建 PR
git push origin feature/your-feature-name
```

---

## 📝 Commit 规范

遵循 [Conventional Commits](https://www.conventionalcommits.org/)：

| 类型 | 说明 |
|------|------|
| `feat` | 新功能 |
| `fix` | Bug 修复 |
| `docs` | 文档更新 |
| `style` | 代码格式（不影响逻辑） |
| `refactor` | 重构 |
| `test` | 测试相关 |
| `chore` | 构建/工具链 |

---

## ✅ PR 检查清单

提交 PR 前请确认：

- [ ] 代码通过 `pytest tests/` 测试
- [ ] 代码通过 `flake8 app/` 检查
- [ ] 新功能已添加对应测试
- [ ] 文档已更新（如有必要）
- [ ] PR 描述清晰说明了改动内容

---

## 🎯 优先贡献方向

当前最需要帮助的方向：

1. **Windows 平台测试** — 我们主要在 macOS 开发，需要 Windows 用户反馈
2. **英文文档完善** — 帮助国际用户使用
3. **新 LLM 接入** — 接入更多 AI 模型
4. **UI/UX 改进** — 界面体验优化
5. **性能优化** — 大文件处理速度

---

## 💬 交流

- 提问和讨论：[GitHub Discussions](https://github.com/Agions/Voxplore/discussions)
- Bug 报告：[GitHub Issues](https://github.com/Agions/Voxplore/issues)

---

感谢每一位贡献者！你们让这个项目变得更好 ❤️
