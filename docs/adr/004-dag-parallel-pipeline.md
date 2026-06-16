# ADR-004: DAG 并行流水线 vs 串行流水线

- **状态**: ✅ Accepted (v2.0)
- **日期**: 2026-06-04
- **作者**: 架构团队
- **关联版本**: v2.0.0

## 背景

v1.x 流水线为严格串行（5 步按顺序执行）：
```
Step1 语义拆条 → Step2 情感选段 → Step3 解说稿 → Step4 TTS → Step5 视频合成
```

实测 10 分钟视频：~70 秒

分析依赖关系后发现：
- Step3（解说稿）只依赖 Step1+Step2
- Step4（TTS）只依赖 Step3
- Step5（视频合成）依赖 Step3+Step4

**Step3 与 Step4 之间不存在数据依赖关系，理论上可与其他独立步骤并行**。

## 决策

引入 **DAG（Directed Acyclic Graph）并行流水线**，支持按 `parallel_group` 分组并行执行。

## 依赖图

```
                    ┌──→ Step3 解说稿生成 ──┐
                    │                        │
Step1 语义拆条 ──→ Step2 情感选段 ──┬──→ Step3 续 ──→ Step4 TTS配音 ──→ Step5 合成
                                  │                                  ↑
                                  └──→ [可选] 封面生成 ────────────────┘
                                       (与 Step3/4 并行)
```

## 性能预期

| 模式 | 10min 视频耗时 | 短剧整季（25 集） |
|------|:---:|:---:|
| 串行（v1.x） | ~70s | ~29min |
| DAG 并行（v2.0） | ~40s | ~15min (2 并行) |
| 提升 | ↓ 43% | ↓ 48% |

## 实施细节

### 1. Pipeline 引擎（`src/scenefab/core/pipeline_engine.py`）

```python
@dataclass
class PipelineStep:
    name: str
    dependencies: List[str]
    parallel_group: Optional[str] = None
    always_run: bool = False

class PipelineEngine:
    def run(self, context: Dict) -> Dict:
        """拓扑排序 + 并行执行"""
        # 1. 找出所有依赖就绪的步骤
        # 2. 按 parallel_group 分组
        # 3. ThreadPoolExecutor 并行执行
        # 4. 收集结果，更新 context
        # 5. 循环直到所有步骤完成
```

### 2. YAML 流水线配置（v2.0 P1）

```yaml
steps:
  - id: generate_script
    parallel_group: "stage_a"
  - id: synthesize_tts
    parallel_group: "stage_a"
  - id: generate_cover
    parallel_group: "stage_a"
  - id: composite_video
    depends_on: [generate_script, synthesize_tts, generate_cover]
```

### 3. 资源限制

- 默认 `max_workers=2`（避免 OOM）
- UI 层可配置（通过 `PipelineConfig.max_workers`）
- 任务监控：内存使用峰值实时上报

## 风险与缓解

| 风险 | 缓解措施 |
|------|----------|
| 资源竞争 / OOM | 默认 2 worker + 内存监控 + 串行降级模式 |
| 调试困难 | 步骤 ID 命名规范 + AuditLogger 记录每步开始/结束 |
| 错误传播 | 步骤失败时下游 `depends_on` 自动跳过，标记 FAILED |
| UI 进度反馈 | 合并多步骤进度为加权平均（按步骤耗时权重） |

## 后果

- ✅ 短剧整季生产效率提升 48%
- ✅ 单视频处理从 70s 降至 40s
- ✅ 用户感知：批量处理不再是"等待 N 集"
- ⚠️ 错误处理更复杂（需要 `always_run` 兜底步骤）
- ⚠️ 步骤执行顺序在 UI 上不直观（需详细日志）

## 评审

- v1.x 串行模式保留为回退（`enable_parallel=False`）
- 当前落地形态见[架构概览 § 解说状态机与数据流](../architecture)
