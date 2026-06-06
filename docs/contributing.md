---
title: 贡献指南
description: SceneFab 开源社区贡献指南，包含开发环境、代码规范与提交流程。
---

# 贡献指南

感谢你对 SceneFab 的关注！SceneFab 采用 MIT 协议开源，欢迎任何形式的贡献。

---

## 开发环境

### 前置条件

| 工具 | 版本要求 | 说明 |
|------|----------|------|
| Python | 3.10+ | 推荐 3.12 |
| FFmpeg | 6.0+ | 视频处理依赖 |
| Git | 2.30+ | 版本控制 |

### 快速开始

```bash
# 1. Fork 并克隆仓库
git clone https://github.com/<your-username>/scene-fab.git
cd scene-fab

# 2. 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. 安装开发依赖
pip install -e ".[dev]"

# 4. 运行测试
pytest tests/
```

---

## 分支管理

| 分支 | 用途 | 命名规范 |
|------|------|----------|
| `main` | 稳定版本，始终可发布 | — |
| `feat/*` | 新功能开发 | `feat/semantic-slicer-v2` |
| `fix/*` | Bug 修复 | `fix/subtitle-sync-issue` |
| `docs/*` | 文档更新 | `docs/api-reference` |
| `refactor/*` | 代码重构 | `refactor/service-container` |

```bash
# 创建功能分支
git checkout -b feat/your-feature main

# 推送并创建 PR
git push origin feat/your-feature
```

---

## 代码规范

### 风格检查

```bash
# Lint 检查
ruff check .

# 自动修复
ruff check --fix .

# 格式化
ruff format .
```

### 类型检查

```bash
mypy src/scenefab --ignore-missing-imports
```

### 测试

```bash
# 运行全部测试
pytest tests/

# 运行特定测试
pytest tests/test_services/test_llm.py

# 带覆盖率
pytest tests/ --cov=scenefab --cov-report=html
```

---

## 提交规范

采用 [Conventional Commits](https://www.conventionalcommits.org/) 规范：

| 类型 | 说明 | 示例 |
|------|------|------|
| `feat` | 新功能 | `feat: 添加 F5-TTS 音色克隆` |
| `fix` | 修复 Bug | `fix: 修复字幕时间戳偏移问题` |
| `docs` | 文档更新 | `docs: 更新 API 配置指南` |
| `refactor` | 重构 | `refactor: 拆分 AI 服务模块` |
| `test` | 测试相关 | `test: 添加 LLM 服务单元测试` |
| `chore` | 构建/工具 | `chore: 更新 ruff 配置` |
| `perf` | 性能优化 | `perf: 优化视频帧缓存策略` |

### 提交消息格式

```
<type>(<scope>): <subject>

<body>

<footer>
```

**示例**：

```
feat(tts): 添加 F5-TTS 零样本音色克隆

- 集成 F5-TTS 推理引擎
- 支持 15-30 秒参考音频克隆
- 添加音色管理界面

Closes #42
```

---

## Pull Request 流程

1. **Fork** 本仓库
2. **创建功能分支**：从 `main` 创建
3. **编写代码和测试**：确保测试通过
4. **提交并推送**：遵循提交规范
5. **发起 PR**：填写 PR 模板
6. **代码审查**：维护者会审查你的代码
7. **合并**：审查通过后合并到 `main`

### PR 检查清单

- [ ] 代码通过 `ruff check` 和 `ruff format`
- [ ] 新增功能有对应测试
- [ ] 测试全部通过 (`pytest tests/`)
- [ ] 文档已更新（如有必要）
- [ ] 提交消息遵循规范

---

## 报告问题

### Bug 报告

使用 [GitHub Issues](https://github.com/Agions/scene-fab/issues/new?template=bug_report.md) 报告 Bug，请包含：

- SceneFab 版本
- 操作系统和版本
- 复现步骤
- 预期行为 vs 实际行为
- 日志/截图（如有）

### 功能建议

使用 [Feature Request](https://github.com/Agions/scene-fab/issues/new?template=feature_request.md) 提交建议。

---

## 社区

- **GitHub Discussions**：[讨论区](https://github.com/Agions/scene-fab/discussions)
- **Issues**：[问题追踪](https://github.com/Agions/scene-fab/issues)

---

## 许可证

贡献即表示你同意你的代码将在 [MIT License](https://github.com/Agions/scene-fab/blob/main/LICENSE) 下发布。

::: tip
重大改动请先开 Issue 讨论！
:::
