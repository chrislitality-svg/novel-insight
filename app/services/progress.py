"""WebSocket 进度推送管理。按 book_id 维护连接,广播进度快照。"""
import asyncio
from typing import Any

from app.utils.logger import get_logger

logger = get_logger("progress")


class ProgressManager:
    def __init__(self) -> None:
        self._connections: dict[int, set[Any]] = {}
        self._latest: dict[int, dict[str, Any]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, book_id: int, ws: Any) -> None:
        async with self._lock:
            self._connections.setdefault(book_id, set()).add(ws)
        # 新连接立即推送最近一次快照
        snapshot = self._latest.get(book_id)
        if snapshot:
            try:
                await ws.send_json(snapshot)
            except Exception:  # noqa: BLE001
                pass

    async def disconnect(self, book_id: int, ws: Any) -> None:
        async with self._lock:
            conns = self._connections.get(book_id)
            if conns:
                conns.discard(ws)
                if not conns:
                    self._connections.pop(book_id, None)

    async def broadcast(self, book_id: int, payload: dict[str, Any]) -> None:
        self._latest[book_id] = payload
        conns = list(self._connections.get(book_id, set()))
        dead = []
        for ws in conns:
            try:
                await ws.send_json(payload)
            except Exception:  # noqa: BLE001
                dead.append(ws)
        for ws in dead:
            await self.disconnect(book_id, ws)


progress_manager = ProgressManager()
