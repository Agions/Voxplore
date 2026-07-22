#!/usr/bin/env python3
"""
LLM 流式输出 UI Worker — v2.0 重构

为 PySide6 UI 提供 LLM 流式输出的 Worker 封装：
- 接收 token 流
- 通过 Signal 推送至 UI
- 错误处理
- 取消支持

依赖注入:
    本模块位于 core 层，不直接依赖 services 层。
    调用方（UI 层）通过 generator_factory 参数注入流式生成器实例，
    实现依赖反转，保持 core → services 的单向依赖。

使用示例:
    from scenefab.core.stream_worker import StreamingLLMWorker
    from scenefab.services.ai.script_stream import StreamingScriptGenerator

    worker = StreamingLLMWorker(
        prompt="生成《流浪地球》的解说文案",
        provider="deepseek",
        style="documentary",
        generator_factory=StreamingScriptGenerator,
    )
    worker.token_received.connect(lambda t: text_edit.insertPlainText(t))
    worker.finished.connect(lambda s: status_label.setText("完成"))
    worker.error.connect(lambda e: error_label.setText(e))
    worker.start()
"""

import logging
from collections.abc import Callable
from typing import Any

from scenefab.core.audit import AuditLogger
from scenefab.core.base_worker import BaseWorker

logger = logging.getLogger(__name__)


class StreamingLLMWorker(BaseWorker):
    """
    LLM 流式输出 Worker

    通过 PySide6 Signal 逐 token 推送生成结果
    """

    # 额外 Signals（继承自 BaseWorker）
    try:
        from PySide6.QtCore import Signal as _Signal

        token_received = _Signal(str)  # 收到新 token
        sentence_completed = _Signal(str)  # 一句话完成
    except ImportError:
        # Headless 模式
        token_received = BaseWorker.progress
        sentence_completed = BaseWorker.status

    def __init__(
        self,
        prompt: str,
        provider: str = "deepseek",
        model: str | None = None,
        style: str = "documentary",
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        on_token: Callable[[str], None] | None = None,
        on_sentence: Callable[[str], None] | None = None,
        generator_factory: Callable[[], Any] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(name=f"StreamingLLMWorker[{provider}]", cancellable=True)
        self.prompt = prompt
        self.provider = provider
        self.model = model
        self.style = style
        self.system_prompt = system_prompt
        self.temperature = temperature
        self.max_tokens = max_tokens
        self._on_token = on_token
        self._on_sentence = on_sentence
        self._generator_factory = generator_factory
        self._accumulated = ""
        self._audit = AuditLogger()

    def _run(self) -> None:
        """
        子类实现：调用实际 LLM 流式接口

        使用注入的 generator_factory 创建生成器；未注入时回退到模拟流式。
        由 BaseWorker.run() → _execute() 统一调度，无需自行处理异常包装。
        """
        # 标记为流式开始
        self.emit_status(f"开始流式生成 ({self.provider})")
        self._audit.log_action(
            action="llm_stream_start",
            parameters={
                "provider": self.provider,
                "model": self.model or "default",
                "prompt_length": len(self.prompt),
            },
        )

        try:
            if self._generator_factory is not None:
                gen = self._generator_factory()
                # 同步包装异步流式
                for token in self._consume_streaming(gen):
                    if self.is_cancelled():
                        self.emit_status("已取消")
                        return
                    self._accumulated += token
                    self._dispatch_token(token)
            else:
                # 未注入生成器工厂，使用模拟流式（测试/无 LLM 环境）
                self._mock_streaming()

        except Exception as e:
            logger.error(f"Streaming LLM failed: {e}")
            raise

    def _consume_streaming(self, gen: Any) -> Any:
        """
        消费异步流（实际项目用 asyncio.run 或类似机制）

        简化实现：使用回调模式
        """
        # 实际项目会更复杂，这里用回调模拟
        chunks_received: list[str] = []

        def callback(chunk: str) -> None:
            if not self.is_cancelled():
                chunks_received.append(chunk)

        # 实际生成（同步等待）
        gen.generate_streaming(
            topic=self.prompt,
            callback=callback,
        )

        return iter(chunks_received)

    def _mock_streaming(self) -> None:
        """模拟流式输出（无 LLM 环境用于测试）"""
        import time

        mock_text = (
            f"这是 [{self.provider}] 模型的模拟流式输出。"
            f"实际生产环境会调用真实 LLM API。 "
            f"提示词: {self.prompt[:50]}... "
        )
        for char in mock_text:
            if self.is_cancelled():
                return
            self._accumulated += char
            self._dispatch_token(char)
            time.sleep(0.02)  # 模拟网络延迟

    def _dispatch_token(self, token: str) -> None:
        """分发 token 到 Signal + 回调"""
        try:
            self.token_received.emit(token)
        except Exception:
            pass
        if self._on_token:
            try:
                self._on_token(token)
            except Exception as e:
                logger.debug(f"on_token callback error: {e}")

        # 检测句子结束（中文/英文句末标点）
        if token in ("。", "！", "？", ".", "!", "?", "\n"):
            sentence = self._extract_last_sentence()
            if sentence:
                try:
                    self.sentence_completed.emit(sentence)
                except Exception:
                    pass
                if self._on_sentence:
                    try:
                        self._on_sentence(sentence)
                    except Exception as e:
                        logger.debug(f"on_sentence callback error: {e}")

    def _extract_last_sentence(self) -> str:
        """提取最近的一句话"""
        text = self._accumulated.strip()
        for sep in ("。", "！", "？", "\n"):
            if sep in text:
                parts = text.rsplit(sep, 1)
                if len(parts) >= 2:
                    return parts[-2].strip() + sep
        return ""

    def get_accumulated(self) -> str:
        """获取已累积的完整文本"""
        return self._accumulated


__all__ = [
    "StreamingLLMWorker",
]
