# Voxplore 架构升级路线图

> 本文档已被 [ARCHITECTURE.md](./ARCHITECTURE.md)（当前系统架构）替代。
> 本文档记录未来的升级方向和待办事项。

---

## 当前架构

详见 [ARCHITECTURE.md](./ARCHITECTURE.md)

---

## 架构原则

1. **核心层不依赖 UI**：Core 层（`app/core/`）不应导入 PySide6，需由 UI 层按需导入
2. **服务层无状态**：所有服务类应为无状态工具或使用依赖注入
3. **subprocess 安全**：所有外部命令通过 `SecureExecutor` 统一执行
4. **异步优先**：I/O 操作使用 `asyncio`，FFmpeg 等 CPU 操作使用线程池

---

## 待升级项目

### 高优先级

#### 1. 核心层解耦 PySide6

**问题**：`core/project_manager.py`、`core/project_settings_manager.py`、`core/project_version_manager.py` 等模块在文件顶部导入 PySide6，导致核心层无法在无头环境（CI）运行。

**方案**：
- 将 Qt 依赖推迟到运行时（延迟导入）
- 或将 UI 相关代码完全移出 `core/`

**影响文件**：
- `app/core/project_manager.py`
- `app/core/project_settings_manager.py`
- `app/core/project_template_manager.py`
- `app/core/project_version_manager.py`

#### 2. API 层持久化任务存储

**问题**：`app/api/routers/pipeline.py` 中任务状态存储在内存 dict，重启后丢失。

**方案**：引入 Redis 作为任务队列后端（参考 Phase 3）。

---

### 中优先级

#### 3. subprocess 收敛补全

**问题**：音频/视频服务仍有约 40 处 subprocess 调用未收敛到 SecureExecutor。

**方案**：逐一审查并迁移 `scene_analyzer.py`、`voice_generator.py`、`base_maker.py`、`subtitle_extractor.py` 中的 subprocess 调用。

#### 4. Plugin System 增强

**现状**：已有 `PluginLoader` / `PluginRegistry` / 3 个接口，但插件发现机制基于 JSON Schema。

**改进方向**：
- 支持 entry_point 自动发现（替代纯 Schema）
- 增加 `SubtitleStylePlugin` 接口
- 增加 `VoiceClonePlugin` 接口

#### 5. 多轨字幕增强

**现状**：`SubtitleGenerator` 已支持基本字幕生成。

**改进方向**：
- 多语言字幕轨道
- 动态字幕样式（基于情绪强度）
- 卡拉 OK 效果字幕

---

### 低优先级

#### 6. Web 前端

**现状**：FastAPI 后端已完成，前端尚未开发。

**方向**：Vue3 + Vite，根据 [index.md](./index.md) 路线图推进。

#### 7. Docker 部署

- 多平台 Dockerfile（Linux x86_64 / ARM64, macOS）
- docker-compose 本地开发环境
- CI/CD 优化

#### 8. SDK (Python / JS)

- 提供 `voxplore-sdk` Python 包
- 提供 `@voxplore/api-client` JS/TS 包

---

## 技术选型参考

| 层级 | 当前 | 可升级方向 |
|------|------|-----------|
| **任务队列** | 内存 dict | Celery + Redis |
| **消息总线** | EventBus（内存） | + RabbitMQ（可选，集群部署时） |
| **缓存** | 内存 + 磁盘 | Redis（多实例共享） |
| **数据库** | SQLite（本地） | + PostgreSQL（远程 API 生产环境） |

> 注：升级依赖外部服务（Redis/RabbitMQ/PostgreSQL）需配套 DevOps 工作，当前本地桌面场景非必需。

---

## 实施路线图

### Phase 1: 核心解耦（1-2 周）
- [ ] `core/` 模块延迟导入 PySide6
- [ ] 所有 core 模块测试可在无头环境运行
- [ ] pytest 通过率 ≥ 95%

### Phase 2: 功能完善（2-3 周）
- [ ] 完成 subprocess 收敛（40+ 处）
- [ ] Plugin System 自动发现机制
- [ ] 多轨字幕支持

### Phase 3: API 生产化（2 周）
- [ ] Redis 任务队列
- [ ] API 认证（JWT）
- [ ] API 限流

### Phase 4: 前端（2-3 周）
- [ ] Vue3 Web 界面原型
- [ ] 项目管理 UI
- [ ] 流水线监控 UI

### Phase 5: 生态（持续）
- [ ] Docker 部署
- [ ] Python/JS SDK
- [ ] 插件市场文档
