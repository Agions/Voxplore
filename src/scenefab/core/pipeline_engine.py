#!/usr/bin/env python3
"""
DAG 并行流水线引擎 — v2.0 重构

支持声明式流水线定义 + 拓扑排序 + 并行执行。

特性:
- 步骤可声明 dependencies（前置步骤）和 parallel_group（并行组）
- 自动拓扑排序，检测循环依赖
- ThreadPoolExecutor 并行执行同组步骤
- 失败处理：always_run 步骤即便上游失败也执行
- 可选 YAML 加载（见 pipeline_templates/*.yaml）
- 审计日志自动集成

使用示例:
    engine = PipelineEngine(max_workers=4)

    engine.add_step(PipelineStep(
        id="analyze",
        func=analyze_video,
        dependencies=[],
    ))
    engine.add_step(PipelineStep(
        id="script",
        func=generate_script,
        dependencies=["analyze"],
        parallel_group="post_process",  # 与 cover 并行
    ))
    engine.add_step(PipelineStep(
        id="cover",
        func=generate_cover,
        dependencies=["analyze"],
        parallel_group="post_process",
    ))
    engine.add_step(PipelineStep(
        id="composite",
        func=composite_video,
        dependencies=["script", "cover"],
    ))

    results = engine.run({"video_path": "input.mp4"})
"""

import logging
import time
import uuid
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

# v2.1: 领域事件发布（可选，未注入则跳过）
try:
    from scenefab.core.event_types import (
        PipelineCompleted,
        PipelineStarted,
        PipelineStepCompleted,
    )
    _HAS_V21_PIPELINE_EVENTS = True
except ImportError:  # pragma: no cover
    _HAS_V21_PIPELINE_EVENTS = False

from scenefab.core.audit import AuditLogger

logger = logging.getLogger(__name__)


# ============================================
# 状态
# ============================================


class StepStatus(str, Enum):
    """步骤执行状态"""

    PENDING = "pending"
    READY = "ready"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


# ============================================
# 数据模型
# ============================================


@dataclass
class PipelineConfig:
    """流水线配置"""

    max_workers: int = 2
    step_timeout_sec: int = 600
    fail_fast: bool = True  # 任一步失败时是否立即停止
    enable_parallel: bool = True


@dataclass
class StepResult:
    """单步执行结果"""

    step_id: str
    status: StepStatus
    output: Any = None
    error: str | None = None
    error_type: str | None = None
    duration_ms: int = 0
    start_time: float = 0.0


@dataclass
class PipelineStep:
    """
    流水线步骤定义

    Args:
        id: 步骤唯一 ID
        func: 实际执行函数，签名 (context: dict) -> Any
        dependencies: 前置步骤 ID 列表
        parallel_group: 同组步骤可并行执行（组内 ID 一致）
        always_run: 即便上游失败也执行（如清理步骤）
        timeout_sec: 单步超时（覆盖全局）
    """

    id: str
    func: Callable[[dict], Any]
    dependencies: list[str] = field(default_factory=list)
    parallel_group: str | None = None
    always_run: bool = False
    timeout_sec: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


# ============================================
# 引擎
# ============================================


class PipelineEngine:
    """
    DAG 并行流水线引擎

    核心算法:
    1. 维护 steps: Dict[id, PipelineStep]
    2. 维护 states: Dict[id, StepStatus]
    3. 维护 results: Dict[id, Any] (步骤输出，供下游访问)
    4. 循环：找出所有依赖已满足的步骤 → 按 parallel_group 分组 → 并行执行
    5. 直至所有步骤状态终态
    """

    def __init__(
        self,
        max_workers: int = 2,
        *,
        event_bus: Any = None,  # v2.1: UnifiedEventBus 可选注入
        pipeline_id: str | None = None,  # v2.1: 自定义 pipeline ID
        **kwargs: Any,
    ) -> None:
        self.config = PipelineConfig(max_workers=max_workers, **kwargs)
        self.steps: dict[str, PipelineStep] = {}
        self.states: dict[str, StepStatus] = {}
        self.results: dict[str, StepResult] = {}
        self._lock = __import__("threading").RLock()
        self._audit = AuditLogger()
        # v2.1: 事件总线（None 时不发布事件）
        self._event_bus = event_bus
        self._pipeline_id = pipeline_id or str(uuid.uuid4())[:8]

    # ==============================================================
    # 注册
    # ==============================================================

    def add_step(self, step: PipelineStep) -> "PipelineEngine":
        """注册一个步骤（链式调用）"""
        with self._lock:
            if step.id in self.steps:
                raise ValueError(f"Duplicate step id: {step.id}")
            self.steps[step.id] = step
            self.states[step.id] = StepStatus.PENDING
            self.results[step.id] = StepResult(
                step_id=step.id,
                status=StepStatus.PENDING,
            )
        return self

    def add_steps(self, steps: list[PipelineStep]) -> "PipelineEngine":
        """批量注册"""
        for s in steps:
            self.add_step(s)
        return self

    # ==============================================================
    # 校验
    # ==============================================================

    def validate(self) -> None:
        """校验流水线定义（依赖存在、无循环）"""
        # 依赖存在
        for step in self.steps.values():
            for dep in step.dependencies:
                if dep not in self.steps:
                    raise ValueError(f"Step '{step.id}' has unknown dependency '{dep}'")

        # 无循环依赖（拓扑排序检测）
        visiting: set[str] = set()
        visited: set[str] = set()

        def dfs(step_id: str, path: list[str]) -> None:
            if step_id in visited:
                return
            if step_id in visiting:
                cycle = " -> ".join(path + [step_id])
                raise ValueError(f"Circular dependency detected: {cycle}")
            visiting.add(step_id)
            step = self.steps[step_id]
            for dep in step.dependencies:
                dfs(dep, path + [step_id])
            visiting.remove(step_id)
            visited.add(step_id)

        for sid in self.steps:
            dfs(sid, [])
        logger.info(f"Pipeline validated: {len(self.steps)} steps, no cycles")

    # ==============================================================
    # 执行
    # ==============================================================

    def run(self, context: dict | None = None) -> dict[str, Any]:
        """
        执行流水线

        Args:
            context: 初始 context（含 "input" 键 + 任意全局变量）

        Returns:
            最终 context（包含 "input" + "steps" 字典）
        """
        self.validate()
        context = dict(context or {})
        context.setdefault("input", {})
        context.setdefault("steps", {})

        logger.info(
            f"Pipeline start: {len(self.steps)} steps, "
            f"max_workers={self.config.max_workers}"
        )
        overall_start = time.time()

        # v2.1: 发布 PipelineStarted
        if _HAS_V21_PIPELINE_EVENTS and self._event_bus is not None:
            try:
                self._event_bus.publish_event(
                    PipelineStarted(
                        pipeline_id=self._pipeline_id,
                        total_steps=len(self.steps),
                        inputs=context.get("input", {}),
                    )
                )
            except Exception:
                logger.debug("PipelineStarted event publish failed", exc_info=True)

        with ThreadPoolExecutor(max_workers=self.config.max_workers) as executor:
            pending_futures: dict[Future, PipelineStep] = {}

            while not self._is_finished():
                # 找出所有可执行的步骤
                ready_steps = self._get_ready_steps()

                if not ready_steps and not pending_futures:
                    # 没有可执行且无正在运行 → 死锁
                    stuck = [
                        sid
                        for sid, st in self.states.items()
                        if st == StepStatus.PENDING
                    ]
                    raise RuntimeError(
                        f"Pipeline stuck: pending steps have unresolvable deps: {stuck}"
                    )

                # 按 parallel_group 分组
                groups = self._group_by_parallel(ready_steps)
                for group in groups:
                    for step in group:
                        if self.config.enable_parallel and len(group) > 1:
                            # 并行执行
                            future = executor.submit(self._execute_step, step, context)
                            pending_futures[future] = step
                        else:
                            # 串行执行（单步）
                            self._execute_step(step, context)

                # 等待至少一个 future 完成
                if pending_futures:
                    done_futures = []
                    for future in list(pending_futures.keys()):
                        if future.done():
                            done_futures.append(future)
                    if done_futures:
                        for f in done_futures:
                            pending_futures.pop(f)
                    else:
                        # 等待任一完成（短超时）
                        import concurrent.futures

                        try:
                            concurrent.futures.wait(
                                pending_futures.keys(),
                                timeout=0.1,
                                return_when=concurrent.futures.FIRST_COMPLETED,
                            )
                        except Exception:
                            pass

                # 失败快速终止
                if self.config.fail_fast:
                    if any(
                        self.states[s.id] == StepStatus.FAILED and not s.always_run
                        for s in self.steps.values()
                    ):
                        logger.warning("Pipeline fail_fast triggered, skipping pending")
                        # 在退出前，先让 always_run 步骤执行
                        self._mark_skipped()
                        # 再次获取 ready（包含 always_run）
                        always_ready = self._get_ready_steps()
                        if always_ready:
                            logger.info(
                                f"Running {len(always_ready)} always_run step(s) before exit"
                            )
                            for step in always_ready:
                                self._execute_step(step, context)
                        break

        total_duration = int((time.time() - overall_start) * 1000)
        completed = sum(1 for s in self.states.values() if s == StepStatus.COMPLETED)
        failed = sum(1 for s in self.states.values() if s == StepStatus.FAILED)
        logger.info(
            f"Pipeline finished: {completed} completed, {failed} failed, "
            f"{total_duration}ms total"
        )

        # v2.1: 发布 PipelineCompleted
        if _HAS_V21_PIPELINE_EVENTS and self._event_bus is not None:
            try:
                self._event_bus.publish_event(
                    PipelineCompleted(
                        pipeline_id=self._pipeline_id,
                        total_duration_ms=total_duration,
                        success_count=completed,
                        failure_count=failed,
                    )
                )
            except Exception:
                logger.debug("PipelineCompleted event publish failed", exc_info=True)

        self._audit.log_action(
            action="pipeline_run",
            parameters={
                "total_steps": len(self.steps),
                "max_workers": self.config.max_workers,
            },
            result="success" if failed == 0 else "failure",
            duration_ms=total_duration,
            error_message=f"{failed} steps failed" if failed else "",
        )

        return context

    # ==============================================================
    # 内部
    # ==============================================================

    def _is_finished(self) -> bool:
        return all(
            s in (StepStatus.COMPLETED, StepStatus.FAILED, StepStatus.SKIPPED)
            for s in self.states.values()
        )

    def _get_ready_steps(self) -> list[PipelineStep]:
        """找出所有依赖已就绪且未执行/未失败的步骤"""
        ready = []
        for step in self.steps.values():
            if self.states[step.id] != StepStatus.PENDING:
                continue
            # always_run 步骤：只要依赖都已"终止"（COMPLETED/FAILED）即可执行
            if step.always_run:
                if all(
                    self.states[dep]
                    in (StepStatus.COMPLETED, StepStatus.FAILED, StepStatus.SKIPPED)
                    for dep in step.dependencies
                ):
                    ready.append(step)
                continue
            # 普通步骤：依赖必须全部 COMPLETED
            if all(
                self.states[dep] == StepStatus.COMPLETED for dep in step.dependencies
            ):
                # 如果有任一依赖 FAILED 则 SKIPPED
                if any(
                    self.states[dep] == StepStatus.FAILED for dep in step.dependencies
                ):
                    self.states[step.id] = StepStatus.SKIPPED
                    self.results[step.id] = StepResult(
                        step_id=step.id,
                        status=StepStatus.SKIPPED,
                        error="upstream failed",
                    )
                    logger.info(f"Step {step.id} skipped (upstream failed)")
                else:
                    ready.append(step)
        return ready

    def _group_by_parallel(self, steps: list[PipelineStep]) -> list[list[PipelineStep]]:
        """按 parallel_group 分组，保留组内步骤一起并行"""
        groups: dict[str, list[PipelineStep]] = {}
        order: list[str] = []
        for step in steps:
            key = step.parallel_group or f"_solo_{step.id}"
            if key not in groups:
                groups[key] = []
                order.append(key)
            groups[key].append(step)
        return [groups[k] for k in order]

    def _execute_step(self, step: PipelineStep, context: dict) -> None:
        """执行单个步骤"""
        with self._lock:
            self.states[step.id] = StepStatus.RUNNING
        start_time = time.time()

        logger.info(
            f"Step '{step.id}' start "
            f"(deps: {step.dependencies}, group: {step.parallel_group})"
        )
        self._audit.log_action(
            action="pipeline_step_start",
            parameters={"step_id": step.id, "deps": step.dependencies},
            task_id=context.get("input", {}).get("task_id", ""),
            step_id=step.id,
        )

        try:
            output = step.func(context)
            duration_ms = int((time.time() - start_time) * 1000)

            with self._lock:
                self.states[step.id] = StepStatus.COMPLETED
                self.results[step.id] = StepResult(
                    step_id=step.id,
                    status=StepStatus.COMPLETED,
                    output=output,
                    duration_ms=duration_ms,
                    start_time=start_time,
                )
                context["steps"][step.id] = output

            self._audit.log_action(
                action="pipeline_step_done",
                parameters={"step_id": step.id},
                result="success",
                duration_ms=duration_ms,
                step_id=step.id,
            )
            logger.info(f"Step '{step.id}' completed in {duration_ms}ms")

            # v2.1: 发布 PipelineStepCompleted
            if _HAS_V21_PIPELINE_EVENTS and self._event_bus is not None:
                try:
                    self._event_bus.publish_event(
                        PipelineStepCompleted(
                            pipeline_id=self._pipeline_id,
                            step_id=step.id,
                            status="success",
                            duration_ms=duration_ms,
                            result=output,
                        )
                    )
                except Exception:
                    logger.debug("PipelineStepCompleted event publish failed", exc_info=True)

        except Exception as e:
            import traceback

            duration_ms = int((time.time() - start_time) * 1000)
            tb = traceback.format_exc()
            err_type = type(e).__name__

            with self._lock:
                self.states[step.id] = StepStatus.FAILED
                self.results[step.id] = StepResult(
                    step_id=step.id,
                    status=StepStatus.FAILED,
                    error=str(e),
                    error_type=err_type,
                    duration_ms=duration_ms,
                )

            self._audit.log_action(
                action="pipeline_step_failed",
                parameters={"step_id": step.id},
                result="failure",
                duration_ms=duration_ms,
                error_message=str(e)[:500],
                error_type=err_type,
                step_id=step.id,
            )
            logger.error(f"Step '{step.id}' failed: {err_type}: {e}\n{tb}")

            # v2.1: 发布 PipelineStepCompleted (failed)
            if _HAS_V21_PIPELINE_EVENTS and self._event_bus is not None:
                try:
                    self._event_bus.publish_event(
                        PipelineStepCompleted(
                            pipeline_id=self._pipeline_id,
                            step_id=step.id,
                            status="failed",
                            duration_ms=duration_ms,
                            error=str(e)[:500],
                        )
                    )
                except Exception:
                    logger.debug("PipelineStepCompleted(failed) event publish failed", exc_info=True)

    def _mark_skipped(self) -> None:
        """将所有 PENDING 步骤标记为 SKIPPED（保留 always_run 步骤以便执行）"""
        with self._lock:
            for sid, state in self.states.items():
                if state == StepStatus.PENDING:
                    step = self.steps[sid]
                    if step.always_run:
                        # always_run 步骤保留为 PENDING，等待执行
                        logger.debug(f"Step {sid} kept PENDING (always_run)")
                        continue
                    self.states[sid] = StepStatus.SKIPPED
                    self.results[sid] = StepResult(
                        step_id=sid,
                        status=StepStatus.SKIPPED,
                        error="fail_fast triggered",
                    )

    # ==============================================================
    # 查询
    # ==============================================================

    def get_state(self, step_id: str) -> StepStatus:
        return self.states.get(step_id, StepStatus.PENDING)

    def get_result(self, step_id: str) -> StepResult | None:
        return self.results.get(step_id)

    def summary(self) -> dict:
        return {
            "total": len(self.steps),
            "completed": sum(
                1 for s in self.states.values() if s == StepStatus.COMPLETED
            ),
            "failed": sum(1 for s in self.states.values() if s == StepStatus.FAILED),
            "skipped": sum(1 for s in self.states.values() if s == StepStatus.SKIPPED),
            "states": {sid: s.value for sid, s in self.states.items()},
        }


__all__ = [
    "PipelineEngine",
    "PipelineStep",
    "PipelineConfig",
    "StepResult",
    "StepStatus",
]
