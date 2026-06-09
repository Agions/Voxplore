"""
SceneFab WebSocket 推送层 v2.1

让 FastAPI router 可以把任务状态变化实时推送到前端。

设计要点：

1. **基于 UnifiedEventBus**：订阅 `task.*` / `pipeline.*` 事件，转推到 WS 连接
2. **连接管理**：每个 WS 连接持有一个订阅，支持按 `task_id` / `pipeline_id` 过滤
3. **可注入**：通过 `set_ws_hub()` 全局替换
4. **优雅降级**：无 WS 客户端时事件不阻塞

使用::

    from scenefab.core.ws_hub import WSHub, get_ws_hub

    hub = get_ws_hub()
    # 在 FastAPI 端点里：
    @router.websocket("/ws/tasks/{task_id}")
    async def task_ws(websocket, task_id):
        await hub.connect(websocket, filter={"task_id": task_id})
        try:
            while True:
                await websocket.receive_text()  # 保持连接
        except WebSocketDisconnect:
            await hub.disconnect(websocket)
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any

try:
    from fastapi import WebSocket
    from starlette.websockets import WebSocketState

    _HAS_FASTAPI_WS = True
except ImportError:
    _HAS_FASTAPI_WS = False
    WebSocket = None  # type: ignore[assignment,misc]
    WebSocketState = None  # type: ignore[assignment,misc]


logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────
# 连接包装
# ──────────────────────────────────────────────────────────


@dataclass
class WSConnection:
    """单个 WebSocket 连接（v2.1）"""

    websocket: Any  # WebSocket
    client_id: str
    connected_at: float = field(default_factory=time.time)
    event_filter: dict[str, Any] = field(default_factory=dict)  # {"task_id": "t1"}
    event_names: list[str] = field(default_factory=list)  # 订阅的事件名，[] 表示所有
    send_count: int = 0
    last_error: str | None = None

    def matches(self, event_name: str, payload: Any) -> bool:
        """检查事件是否应推送给本连接"""
        if self.event_names and event_name not in self.event_names:
            return False
        if self.event_filter:
            for k, v in self.event_filter.items():
                # payload 可能是 DomainEvent / dict
                if hasattr(payload, k):
                    if getattr(payload, k) != v:
                        return False
                elif isinstance(payload, dict):
                    if payload.get(k) != v:
                        return False
        return True

    async def send_json(self, message: dict[str, Any]) -> bool:
        """发送 JSON 消息（v2.1 异常安全）"""
        if not _HAS_FASTAPI_WS or WebSocketState is None:
            return False
        try:
            if self.websocket.client_state != WebSocketState.CONNECTED:
                return False
            await self.websocket.send_json(message)
            self.send_count += 1
            return True
        except Exception as e:
            self.last_error = str(e)
            logger.debug(f"WS send failed for {self.client_id}: {e}")
            return False


# ──────────────────────────────────────────────────────────
# Hub
# ──────────────────────────────────────────────────────────


class WSHub:
    """
    WebSocket 中心（v2.1）

    维护一组 WS 连接，统一从 UnifiedEventBus 接收事件后分发。
    """

    def __init__(
        self, *, name: str = "default", loop: asyncio.AbstractEventLoop | None = None
    ):
        self.name = name
        self._connections: dict[str, WSConnection] = {}
        self._lock = asyncio.Lock()
        self._started = False
        self._unsubscribe_fn: Any = None
        self._loop = loop  # 主事件循环（start 时如未提供则获取）

    async def start(self) -> None:
        """启动 hub：订阅事件总线"""
        if self._started:
            return
        from scenefab.core.unified_event_bus import get_event_bus

        bus = get_event_bus()
        # 缓存主事件循环（hub 的 loop）
        try:
            self._loop = self._loop or asyncio.get_running_loop()
        except RuntimeError:
            self._loop = None
        self._unsubscribe_fn = bus.subscribe(
            "*", self._on_event, name=f"ws_hub_{self.name}"
        )
        self._started = True
        logger.info(f"WSHub '{self.name}' started")

    async def stop(self) -> None:
        """停止 hub"""
        if self._unsubscribe_fn is not None:
            try:
                self._unsubscribe_fn()
            except Exception:
                pass
            self._unsubscribe_fn = None
        self._started = False
        # 关闭所有连接
        for conn in list(self._connections.values()):
            try:
                await conn.websocket.close()
            except Exception:
                pass
        self._connections.clear()

    def _on_event(self, payload: Any) -> None:
        """事件总线回调（v2.1 异步安全）"""
        event_name: str = (
            getattr(payload, "event_name", None)
            or (payload.get("event_name") if isinstance(payload, dict) else None)
            or "?"
        )
        # 派发：优先用 hub 持有的 loop；否则尝试当前运行 loop；最后退同步
        target_loop = self._loop
        if target_loop is not None and not target_loop.is_closed():
            try:
                asyncio.run_coroutine_threadsafe(
                    self._dispatch(event_name, payload), target_loop
                )
                return
            except RuntimeError:
                pass
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running() and loop is not target_loop:
                loop.create_task(self._dispatch(event_name, payload))
            elif not loop.is_running():
                loop.run_until_complete(self._dispatch(event_name, payload))
            else:
                # loop running 但是不同的 - run_coroutine_threadsafe 失败
                self._dispatch_sync(event_name, payload)
        except RuntimeError:
            # 没有事件循环，回退到同步分发
            self._dispatch_sync(event_name, payload)

    async def _dispatch(self, event_name: str, payload: Any) -> None:
        for conn in list(self._connections.values()):
            if conn.matches(event_name, payload):
                msg = {
                    "event": event_name,
                    "data": _payload_to_dict(payload),
                    "ts": time.time(),
                }
                await conn.send_json(msg)

    def _dispatch_sync(self, event_name: str, payload: Any) -> None:
        """同步分发（v2.1 - 离线/单元测试）"""
        for conn in list(self._connections.values()):
            if conn.matches(event_name, payload):
                msg = {
                    "event": event_name,
                    "data": _payload_to_dict(payload),
                    "ts": time.time(),
                }
                try:
                    if (
                        _HAS_FASTAPI_WS
                        and WebSocketState is not None
                        and conn.websocket.client_state == WebSocketState.CONNECTED
                    ):
                        # 同步客户端测试时可注入 mock
                        conn.websocket.send_json_sync(msg)
                        conn.send_count += 1
                except Exception as e:
                    conn.last_error = str(e)

    async def connect(
        self,
        websocket: Any,
        *,
        client_id: str | None = None,
        event_names: list[str] | None = None,
        event_filter: dict[str, Any] | None = None,
    ) -> WSConnection:
        """注册一个 WebSocket 连接"""
        if not self._started:
            await self.start()
        import uuid as _uuid

        cid = client_id or str(_uuid.uuid4())[:8]
        conn = WSConnection(
            websocket=websocket,
            client_id=cid,
            event_names=event_names or [],
            event_filter=event_filter or {},
        )
        async with self._lock:
            self._connections[cid] = conn
        await conn.send_json(
            {"event": "connected", "data": {"client_id": cid}, "ts": time.time()}
        )
        logger.info(f"WS connected: {cid} (total: {len(self._connections)})")
        return conn

    async def disconnect(self, websocket: Any) -> None:
        """移除连接"""
        async with self._lock:
            for cid, conn in list(self._connections.items()):
                if conn.websocket is websocket:
                    del self._connections[cid]
                    logger.info(
                        f"WS disconnected: {cid} (remaining: {len(self._connections)})"
                    )
                    return

    def list_clients(self) -> list[dict[str, Any]]:
        return [
            {
                "client_id": c.client_id,
                "connected_at": c.connected_at,
                "event_names": c.event_names,
                "event_filter": c.event_filter,
                "send_count": c.send_count,
                "last_error": c.last_error,
            }
            for c in self._connections.values()
        ]

    def count(self) -> int:
        return len(self._connections)


def _payload_to_dict(payload: Any) -> dict[str, Any]:
    """统一 payload → dict（DomainEvent 优先）"""
    if hasattr(payload, "to_dict"):
        try:
            return payload.to_dict()
        except Exception:
            pass
    if isinstance(payload, dict):
        return dict(payload)
    return {"_raw": str(payload)}


# ──────────────────────────────────────────────────────────
# 全局 hub
# ──────────────────────────────────────────────────────────


_global_hub: WSHub | None = None


def get_ws_hub() -> WSHub:
    """获取全局 WS hub（v2.1）"""
    global _global_hub
    if _global_hub is None:
        _global_hub = WSHub()
    return _global_hub


def set_ws_hub(hub: WSHub) -> None:
    """注入全局 WS hub（v2.1）"""
    global _global_hub
    _global_hub = hub


__all__ = [
    "WSHub",
    "WSConnection",
    "get_ws_hub",
    "set_ws_hub",
]
