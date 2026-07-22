#!/usr/bin/env python3
"""
v2.2 解说生成状态机 — 5 状态 + 评估循环

状态流转:
    INGEST → UNDERSTAND → STORYGRAPH → DRAFT ⇄ HOOK_REWRITE
                                          ↑          │
                                          │          ↓
                                     REJECT ←─ EVALUATE → ACCEPT
                                                        │
                                                        ↓
                                                TTS_LENGTH_ADJUST → TTS → ASSEMBLE → DONE

设计原则:
- 5 状态枚举 + StepResult 数据类
- 每个状态是一个 Step 函数, 签名 (ctx: NarrationContext) -> StepResult
- 状态转移由 NarrationEvaluator 决定 (Phase 2 实现)
- 集成到 core.unified_event_bus, 发 NarrationStageChanged 事件
- 失败处理: max_attempts=2, 强制退出循环

v2.2 决策: 见 docs/adr/007-narration-state-machine.md
"""

from __future__ import annotations

import logging
import time
import traceback
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from .context import NarrationContext

logger = logging.getLogger(__name__)


# ============================================
# 状态枚举 — v2.2 状态机的 9 个状态
# ============================================


class NarrationState(str, Enum):
    """解说生成状态机的 9 个状态"""

    # —— 主路径 (5 状态) ——
    INGEST = "ingest"  # ① 加载视频 + 校验 + 创建工作目录
    UNDERSTAND = "understand"  # ② 视觉模型理解场景 (Qwen3.7/Gemini)
    STORYGRAPH = "storygraph"  # ③ 长视频剧情图谱 (LongVideoUnderstanding)
    DRAFT = "draft"  # ④ LLM 生成初稿
    HOOK_REWRITE = "hook_rewrite"  # ⑤ 开场 Hook 改写 (前 2 句强化留人)

    # —— 评估循环 (3 状态) ——
    EVALUATE = "evaluate"  # ⑥ 评估器打分 (Qwen3.7-flash)
    ACCEPT = "accept"  # ⑦ 接受, 进入 TTS 流程
    REJECT = "reject"  # ⑧ 拒绝, 带 suggestion 回 DRAFT

    # —— TTS 流程 (3 状态) ——
    TTS_LENGTH_ADJUST = "tts_length_adjust"  # ⑨ TTS 实测时长反向约束文案
    TTS = "tts"  # ⑩ 配音合成 (Edge-TTS / F5-TTS)
    ASSEMBLE = "assemble"  # ⑪ 字幕对齐 + 视频合成 + 剪映草稿

    # —— 终态 (2 状态) ——
    DONE = "done"  # ✓ 完成
    ERROR = "error"  # ✗ 错误


class TransitionReason(str, Enum):
    """状态转移原因 (用于可观测性)"""

    INITIAL = "initial"  # 初始进入
    SUCCESS = "success"  # 状态执行成功
    EVAL_ACCEPT = "eval_accept"  # 评估通过
    EVAL_REJECT = "eval_reject"  # 评估拒绝
    MAX_ATTEMPTS = "max_attempts"  # DRAFT 达到最大重试
    EXCEPTION = "exception"  # 异常
    USER_CANCEL = "user_cancel"  # 用户取消 (预留)


# ============================================
# 数据模型
# ============================================


@dataclass(slots=True)
class StepResult:
    """单步执行结果"""

    success: bool
    state: NarrationState
    next_state: NarrationState | None = None  # None = 由状态机决定
    duration_ms: float = 0.0
    message: str = ""
    data: dict[str, Any] = field(default_factory=dict)
    error: str | None = None


@dataclass(slots=True)
class StateTransition:
    """状态转移记录 (用于审计)"""

    from_state: NarrationState
    to_state: NarrationState
    reason: TransitionReason
    timestamp: float
    trace_id: str
    message: str = ""


@dataclass(slots=True)
class NarrationConfig:
    """状态机配置"""

    max_draft_attempts: int = 2  # DRAFT 最多重试 2 次
    eval_accept_threshold: float = 7.5  # 评估 ≥ 7.5 接受
    enable_tts_length_adjust: bool = True  # 启用 TTS 反向约束
    step_timeout_sec: int = 300  # 单步超时 (秒)
    enable_event_publish: bool = True  # 发布到 unified_event_bus


# ============================================
# 事件发布 (Phase 2 完善)
# ============================================


def _publish_stage_event(  # pragma: no cover - 阶段占位
    trace_id: str,
    from_state: NarrationState,
    to_state: NarrationState,
    reason: TransitionReason,
    message: str = "",
) -> None:
    """发布状态转移事件到 unified_event_bus (Phase 2 完善 payload)

    异常时静默失败 (event_bus 是可选依赖)
    """
    try:
        from scenefab.core.unified_event_bus import get_event_bus

        bus = get_event_bus()
        # 字符串事件 + 结构化 payload (v1.x 兼容)
        bus.publish(
            "narration.stage_changed",
            {
                "trace_id": trace_id,
                "from_state": from_state.value,
                "to_state": to_state.value,
                "reason": reason.value,
                "message": message,
            },
        )
    except Exception as e:  # noqa: BLE001
        logger.debug(f"narration.stage_changed 事件发布失败 (非阻塞): {e}")


# ============================================
# Step 函数类型 — Phase 2/3/4 实现具体步骤
# ============================================


# 签名: (ctx) -> StepResult
StepFunction = Callable[[NarrationContext], StepResult]


# ============================================
# 状态机主体
# ============================================


class NarrationStateMachine:
    """v2.2 解说生成状态机

    使用示例 (Phase 2 完善):
        sm = NarrationStateMachine(config=NarrationConfig())
        sm.register_step(NarrationState.INGEST, ingest_step)
        sm.register_step(NarrationState.UNDERSTAND, understand_step)
        # ...
        result = sm.run(ctx)
    """

    def __init__(self, config: NarrationConfig | None = None) -> None:
        self.config = config or NarrationConfig()
        self._steps: dict[NarrationState, StepFunction] = {}
        self._transitions: list[StateTransition] = []
        self._current_state: NarrationState = NarrationState.INGEST
        self._trace_id: str = uuid.uuid4().hex

    # ============================================================
    # 公共 API
    # ============================================================

    def register_step(
        self, state: NarrationState, func: StepFunction
    ) -> NarrationStateMachine:
        """注册状态对应的 Step 函数 (链式 API)"""
        if not callable(func):
            raise TypeError(f"Step 函数必须可调用: {state}")
        self._steps[state] = func
        return self

    def current_state(self) -> NarrationState:
        return self._current_state

    def transitions(self) -> list[StateTransition]:
        return list(self._transitions)

    # ============================================================
    # 状态转移
    # ============================================================

    def _transition(
        self,
        from_state: NarrationState,
        to_state: NarrationState,
        reason: TransitionReason,
        message: str = "",
    ) -> None:
        """记录一次状态转移, 发布事件"""
        transition = StateTransition(
            from_state=from_state,
            to_state=to_state,
            reason=reason,
            timestamp=time.time(),
            trace_id=self._trace_id,
            message=message,
        )
        self._transitions.append(transition)
        self._current_state = to_state

        if self.config.enable_event_publish:
            _publish_stage_event(self._trace_id, from_state, to_state, reason, message)

        logger.info(
            f"[{self._trace_id[:8]}] {from_state.value} → {to_state.value} "
            f"({reason.value}) {message}"
        )

    # ============================================================
    # 单步执行
    # ============================================================

    def _execute_step(self, state: NarrationState, ctx: NarrationContext) -> StepResult:
        """执行单步, 捕获异常, 应用超时"""
        if state not in self._steps:
            return StepResult(
                success=False,
                state=state,
                message=f"State {state.value} 未注册 Step 函数",
                error="StepNotRegistered",
            )

        step_func = self._steps[state]
        start = time.time()
        try:
            logger.debug(
                f"[{self._trace_id[:8]}] 执行 {state.value} "
                f"(attempt={ctx.draft_attempts})"
            )
            result = step_func(ctx)
            result.duration_ms = (time.time() - start) * 1000
            return result
        except Exception as e:  # noqa: BLE001
            err_msg = f"{type(e).__name__}: {e}\n{traceback.format_exc()}"
            logger.error(f"[{self._trace_id[:8]}] {state.value} 异常: {err_msg}")
            return StepResult(
                success=False,
                state=state,
                duration_ms=(time.time() - start) * 1000,
                message=f"Step 异常: {type(e).__name__}",
                error=err_msg,
            )

    # ============================================================
    # 主循环
    # ============================================================

    def run(self, ctx: NarrationContext) -> StepResult:
        """运行状态机直到终态 (DONE / ERROR)

        Args:
            ctx: 解说上下文 (含源视频/平台/风格等)

        Returns:
            最终 StepResult (DONE 成功 / ERROR 失败)
        """
        self._trace_id = ctx.trace_id
        self._current_state = NarrationState.INGEST
        self._transitions.clear()

        self._transition(
            NarrationState.INGEST,  # 初始占位
            NarrationState.INGEST,
            TransitionReason.INITIAL,
            "状态机启动",
        )

        # —— 状态流转表 (硬编码, v2.2 范围内足够, Phase 3 可改为声明式 YAML) ——
        # state -> [(next_state, reason, condition_fn)]
        # condition_fn: (ctx, step_result) -> bool
        FLOW: dict[
            NarrationState, list[tuple[NarrationState, TransitionReason, Any]]
        ] = {
            NarrationState.INGEST: [
                (NarrationState.UNDERSTAND, TransitionReason.SUCCESS, None),
            ],
            NarrationState.UNDERSTAND: [
                (NarrationState.STORYGRAPH, TransitionReason.SUCCESS, None),
            ],
            NarrationState.STORYGRAPH: [
                (NarrationState.DRAFT, TransitionReason.SUCCESS, None),
            ],
            NarrationState.DRAFT: [
                (NarrationState.EVALUATE, TransitionReason.SUCCESS, None),
            ],
            NarrationState.EVALUATE: [
                (NarrationState.ACCEPT, TransitionReason.EVAL_ACCEPT, None),
                (NarrationState.REJECT, TransitionReason.EVAL_REJECT, None),
            ],
            NarrationState.ACCEPT: [
                (NarrationState.HOOK_REWRITE, TransitionReason.SUCCESS, None),
            ],
            NarrationState.HOOK_REWRITE: [
                (
                    NarrationState.TTS_LENGTH_ADJUST,
                    TransitionReason.SUCCESS,
                    None,
                ),
            ],
            NarrationState.REJECT: [
                (NarrationState.DRAFT, TransitionReason.EVAL_REJECT, None),
                (NarrationState.ERROR, TransitionReason.MAX_ATTEMPTS, None),
            ],
            NarrationState.TTS_LENGTH_ADJUST: [
                (NarrationState.TTS, TransitionReason.SUCCESS, None),
            ],
            NarrationState.TTS: [
                (NarrationState.ASSEMBLE, TransitionReason.SUCCESS, None),
            ],
            NarrationState.ASSEMBLE: [
                (NarrationState.DONE, TransitionReason.SUCCESS, None),
            ],
            NarrationState.DONE: [],
            NarrationState.ERROR: [],
        }

        max_iterations = 50  # 防止死循环
        iteration = 0

        while self._current_state not in (NarrationState.DONE, NarrationState.ERROR):
            iteration += 1
            if iteration > max_iterations:
                logger.error(
                    f"[{self._trace_id[:8]}] 状态机超过 {max_iterations} 次迭代, 强制终止"
                )
                self._transition(
                    self._current_state,
                    NarrationState.ERROR,
                    TransitionReason.EXCEPTION,
                    "超过最大迭代次数 (可能死循环)",
                )
                break

            current = self._current_state

            # 1. 执行当前状态
            result = self._execute_step(current, ctx)

            if not result.success:
                self._transition(
                    current,
                    NarrationState.ERROR,
                    TransitionReason.EXCEPTION,
                    result.error or result.message or "Step 失败",
                )
                # 返回反映终态的 result
                result.state = NarrationState.ERROR
                return result

            # 2. 决定下一步
            if current not in FLOW:
                self._transition(
                    current,
                    NarrationState.ERROR,
                    TransitionReason.EXCEPTION,
                    f"State {current.value} 无转移规则",
                )
                result.state = NarrationState.ERROR
                break

            candidates = FLOW[current]
            next_state: NarrationState | None = None
            reason: TransitionReason = TransitionReason.SUCCESS

            for candidate_state, candidate_reason, _cond_fn in candidates:
                # EVALUATE 分支: 根据 eval_score 选 ACCEPT/REJECT
                if current == NarrationState.EVALUATE:
                    if (
                        candidate_state == NarrationState.ACCEPT
                        and ctx.eval_score >= self.config.eval_accept_threshold
                    ):
                        next_state = candidate_state
                        reason = candidate_reason
                        break
                    if (
                        candidate_state == NarrationState.REJECT
                        and ctx.eval_score < self.config.eval_accept_threshold
                    ):
                        next_state = candidate_state
                        reason = candidate_reason
                        break
                # REJECT 分支: max_attempts 决定回 DRAFT 还是 ERROR
                elif current == NarrationState.REJECT:
                    if (
                        candidate_state == NarrationState.DRAFT
                        and not ctx.is_max_attempts_reached(
                            self.config.max_draft_attempts
                        )
                    ):
                        next_state = candidate_state
                        reason = candidate_reason
                        break
                    if (
                        candidate_state == NarrationState.ERROR
                        and ctx.is_max_attempts_reached(self.config.max_draft_attempts)
                    ):
                        next_state = candidate_state
                        reason = candidate_reason
                        break
                # 其余状态: 取第一个候选
                else:
                    next_state = candidate_state
                    reason = candidate_reason
                    break

            if next_state is None:
                # 未匹配到转移条件 (理论上不应发生)
                self._transition(
                    current,
                    NarrationState.ERROR,
                    TransitionReason.EXCEPTION,
                    f"State {current.value} 未匹配转移条件",
                )
                break

            self._transition(current, next_state, reason, result.message)

        # 返回最终结果
        if self._current_state == NarrationState.DONE:
            return StepResult(
                success=True,
                state=NarrationState.DONE,
                message=f"状态机完成 ({len(self._transitions)} 转移)",
                data={"transitions": len(self._transitions)},
            )

        return StepResult(
            success=False,
            state=self._current_state,
            message=f"状态机终止于 {self._current_state.value}",
            data={"transitions": len(self._transitions)},
        )

