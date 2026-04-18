---
title: 贡献指南
description: 如何参与 Voxplore 的开发、报告问题和完善文档。
---

# 贡献指南

感谢你愿意为 Voxplore 贡献力量！无论是报告 Bug、提交代码还是完善文档，每一份贡献都让这个项目变得更好。 🎉

---

## 贡献方式

| 方式 | 说明 | 入口 |
|------|------|------|
| 🐛 报告 Bug | 帮助我们发现和修复问题 | [GitHub Issues](https://github.com/Agions/Voxplore/issues/new?template=bug_report.md) |
| 💡 功能建议 | 提出新功能想法 | [Feature Request](https://github.com/Agions/Voxplore/issues/new?template=feature_request.md) |
| 📝 完善文档 | 修正错别字、补充说明、翻译 | 直接提交 PR |
| 🔧 提交代码 | Bug 修复、新功能实现 | 提交 Pull Request |
| ⭐ 推广项目 | 分享给更多人 | Star、Fork、在社交媒体介绍 |

---

## 开发环境搭建

### 前置条件

| 依赖 | 版本要求 | 安装方式 |
|------|----------|----------|
| Python | 3.10+ | [python.org](https://www.python.org/) |
| Git | 2.30+ | [git-scm.com](https://git-scm.com/) |
| FFmpeg | 5.0+ | `brew install ffmpeg` |

### 快速搭建

```bash
# 1. Fork 项目到你的 GitHub 账户
# 访问 https://github.com/Agions/Voxplore 点击 Fork

# 2. 克隆你的 Fork
git clone https://github.com/YOUR_USERNAME/Voxplore.git
cd Voxplore

# 3. 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate    # Windows

# 4. 安装依赖
pip install -r requirements.txt
pip install -e ".[dev]"    # 安装开发依赖（含测试工具）

# 5. 复制环境配置
cp .env.example .env
# 编辑 .env，填入测试用 API Key（AI 功能需要）

# 6. 运行应用验证环境
python app/main.py

# 7. 运行测试确保一切正常
pytest tests/ -v
```

### 开发工具

```bash
# 代码格式化
pip install black isort
black app/ tests/
isort app/ tests/

# 代码检查
pip install flake8 mypy
flake8 app/ --max-line-length=120
mypy app/

# 类型检查（推荐）
mypy app/ --strict
```

---

## 代码提交流程

### 分支命名规范

| 类型 | 分支名示例 | 说明 |
|------|-----------|------|
| 功能开发 | `feature/emotion-style-refinement` | 新功能 |
| Bug 修复 | `fix/audio-sync-on-windows` | Bug 修复 |
| 文档更新 | `docs/update-installation-guide` | 文档改进 |
| 重构 | `refactor/ai-provider-abstract` | 代码重构 |

### 提交流程

```bash
# 1. 从 main 创建功能分支
git checkout main
git pull origin main
git checkout -b feature/your-feature-name

# 2. 进行开发（遵循代码规范）
# ... 修改代码 ...

# 3. 提交代码（遵循 Conventional Commits）
git add .
git commit -m "feat: add batch processing queue management"
git commit -m "fix: resolve audio sync delay on Windows platform"
git commit -m "docs: expand troubleshooting section for FFmpeg errors"

# 4. 推送分支到你的 Fork
git push origin feature/your-feature-name

# 5. 在 GitHub 上创建 Pull Request
# 访问 https://github.com/Agions/Voxplore 点击 "Compare & pull request"
```

### Commit 规范

Voxplore 遵循 [Conventional Commits](https://www.conventionalcommits.org/) 规范：

| 类型 | 说明 | 示例 |
|------|------|------|
| `feat` | 新功能 | `feat: add template market page` |
| `fix` | Bug 修复 | `fix: resolve crash on empty project load` |
| `docs` | 文档更新 | `docs: update AI configuration guide` |
| `style` | 代码格式（不影响逻辑） | `style: format code with black` |
| `refactor` | 重构 | `refactor: abstract LLM provider interface` |
| `test` | 测试相关 | `test: add unit tests for voice generator` |
| `chore` | 构建/工具链 | `chore: upgrade PySide6 to 6.6` |
| `perf` | 性能优化 | `perf: optimize video thumbnail loading` |
| `ci` | CI/CD | `ci: add GitHub Actions workflow` |

---

## Pull Request 检查清单

提交 PR 前请确认：

- [ ] 代码通过了 `pytest tests/` 测试
- [ ] 代码通过了 `flake8 app/` 检查
- [ ] 新功能已添加对应测试（测试覆盖率不低于 80%）
- [ ] 文档已同步更新（如有新功能或 API 变更）
- [ ] PR 描述清晰说明了改动的目的和影响范围
- [ ] 如果是 Bug 修复，附上了相关 Issue 链接
- [ ] 分支是从最新的 `main` 创建的（已 rebase）

### PR 描述模板

```markdown
## 描述
<!-- 简述这次改动的目的 -->

## 改动类型
- [ ] Bug 修复
- [ ] 新功能
- [ ] 文档更新
- [ ] 重构
- [ ] 其他

## 相关 Issue
<!-- 如果有，附上链接：Closes #123 -->

## 测试情况
<!-- 描述你如何测试这些改动 -->

## 截图/录屏
<!-- 如果有 UI 改动，附上截图 -->
```

---

## 优先贡献方向

以下方向是当前最需要帮助的，欢迎优先贡献：

| 方向 | 优先级 | 说明 |
|------|--------|------|
| 🪟 **Windows 平台测试** | ⭐⭐⭐ | 我们主要在 macOS 开发，需要 Windows 真实用户反馈 |
| 🌐 **英文文档完善** | ⭐⭐⭐ | 帮助国际用户使用，需要 native English speaker 审核 |
| 🤖 **新 AI 模型接入** | ⭐⭐ | 接入更多 AI 模型（如 Grok、 Mistral 等） |
| 🎨 **UI/UX 改进** | ⭐⭐ | 界面体验优化，需要设计反馈 |
| ⚡ **性能优化** | ⭐⭐ | 大文件处理速度、内存占用优化 |
| 🧪 **测试覆盖** | ⭐ | 增加自动化测试覆盖率 |
| 📦 **新导出格式** | ⭐ | 支持更多专业软件格式 |

---

## 项目结构参考

```
Voxplore/
├── app/
│   ├── core/           # 核心模块（配置、事件、依赖注入）
│   ├── services/       # 业务服务层（AI、视频处理、导出）
│   ├── plugins/        # 插件系统
│   └── ui/            # PySide6 界面层
├── tests/             # 测试
├── docs/              # 文档（VitePress）
├── scripts/           # 工具脚本
└── resources/         # 静态资源
```

请遵循现有代码的目录结构和命名约定。

---

## 行为准则

作为 Voxplore 的贡献者，请遵守以下原则：

- **尊重** — 尊重所有参与者的观点和背景
- **包容** — 欢迎各种经验水平的贡献者
- **专业** — 保持建设性的技术讨论
- **透明** — 公开讨论决策过程

---

## 交流渠道

| 渠道 | 用途 |
|------|------|
| [GitHub Issues](https://github.com/Agions/Voxplore/issues) | Bug 报告、功能请求 |
| [GitHub Discussions](https://github.com/Agions/Voxplore/discussions) | 提问、讨论 |
| [Discord 社区](https://discord.gg/narrafiilm) | 实时交流 |

---

## 致谢

感谢每一位贡献者！你们的名字将在项目主页和 CHANGELOG 中展示。 ❤️

如果你有任何问题，欢迎在 GitHub Discussions 中提问，或者直接提交 Issue。
