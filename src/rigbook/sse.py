"""Server-Sent Events bus.

Provides a simple pub/sub mechanism: any part of the backend can broadcast
events, and connected SSE clients receive them in real time.
"""

import asyncio
import json
import logging
import time
from collections.abc import Callable

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

logger = logging.getLogger("rigbook.sse")

router = APIRouter(prefix="/api/events", tags=["events"])

_subscribers: list[asyncio.Queue[str]] = []
_shutdown_event: asyncio.Event | None = None
_last_client_disconnected_at: float | None = None
_on_connect_callbacks: list[Callable[[], None]] = []
_on_disconnect_callbacks: list[Callable[[], None]] = []


def subscriber_count() -> int:
    """Return the number of connected SSE clients."""
    return len(_subscribers)


def get_last_disconnect_time() -> float | None:
    """Return the timestamp when the last SSE client disconnected, or None."""
    return _last_client_disconnected_at


def register_connect_callback(fn: Callable[[], None]) -> None:
    _on_connect_callbacks.append(fn)


def register_disconnect_callback(fn: Callable[[], None]) -> None:
    _on_disconnect_callbacks.append(fn)


def _get_shutdown_event() -> asyncio.Event:
    global _shutdown_event
    if _shutdown_event is None:
        _shutdown_event = asyncio.Event()
    return _shutdown_event


def broadcast(event: str, data: dict) -> None:
    """Send an SSE event to all connected clients."""
    msg = f"event: {event}\ndata: {json.dumps(data)}\n\n"
    for q in list(_subscribers):
        try:
            q.put_nowait(msg)
        except asyncio.QueueFull:
            pass


def notify_shutdown() -> None:
    """Broadcast shutdown event and signal all SSE generators to stop."""
    broadcast("shutdown", {})
    evt = _get_shutdown_event()
    evt.set()


async def _sse_generator(queue: asyncio.Queue[str]):
    shutdown_evt = _get_shutdown_event()
    try:
        while not shutdown_evt.is_set():
            try:
                msg = await asyncio.wait_for(queue.get(), timeout=30)
                yield msg
            except asyncio.TimeoutError:
                # Send keepalive comment to detect dead connections
                yield ": keepalive\n\n"
            if shutdown_evt.is_set():
                # Drain any remaining messages (including shutdown broadcast)
                while not queue.empty():
                    yield queue.get_nowait()
                return
    except (asyncio.CancelledError, GeneratorExit):
        return


@router.get("/stream")
async def event_stream():
    global _last_client_disconnected_at
    queue: asyncio.Queue[str] = asyncio.Queue(maxsize=64)
    _subscribers.append(queue)
    logger.info("SSE client connected (total: %d)", len(_subscribers))
    for cb in _on_connect_callbacks:
        cb()

    async def cleanup_generator():
        global _last_client_disconnected_at
        try:
            async for msg in _sse_generator(queue):
                yield msg
        except (asyncio.CancelledError, GeneratorExit):
            pass
        finally:
            if queue in _subscribers:
                _subscribers.remove(queue)
            if len(_subscribers) == 0:
                _last_client_disconnected_at = time.time()
            logger.info("SSE client disconnected (total: %d)", len(_subscribers))
            for cb in _on_disconnect_callbacks:
                cb()

    return StreamingResponse(
        cleanup_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
