"""Server-Sent Events bus.

Provides a simple pub/sub mechanism: any part of the backend can broadcast
events, and connected SSE clients receive them in real time.
"""

import asyncio
import json
import logging
import os
import signal
import time
from collections.abc import Callable

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

logger = logging.getLogger("guidebook.sse")

router = APIRouter(prefix="/api/events", tags=["events"])

_subscribers: list[asyncio.Queue[str]] = []
_shutdown_event: asyncio.Event | None = None
_last_client_disconnected_at: float | None = None
_on_connect_callbacks: list[Callable[[], None]] = []
_on_disconnect_callbacks: list[Callable[[], None]] = []
_ever_had_client: bool = False
_auto_shutdown_task: asyncio.Task | None = None

AUTO_SHUTDOWN_DELAY_DEFAULT = 300  # seconds
_auto_shutdown_delay: int = AUTO_SHUTDOWN_DELAY_DEFAULT


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


async def _auto_shutdown_loop() -> None:
    """Background task: shut down server when no SSE clients are connected.

    Triggers after the configured delay seconds with zero clients, whether
    a client connected and then left, or no client ever connected at all.
    """
    started_at = time.time()
    while True:
        await asyncio.sleep(5)
        if len(_subscribers) > 0:
            continue
        # Use last-disconnect time if a client was seen, otherwise use start time
        reference = _last_client_disconnected_at if _ever_had_client else started_at
        elapsed = time.time() - reference
        if elapsed >= _auto_shutdown_delay:
            logger.info("No SSE clients for %.0fs — shutting down now", elapsed)
            notify_shutdown()
            os.kill(os.getpid(), signal.SIGTERM)
            return


async def start_auto_shutdown() -> None:
    """Start the auto-shutdown watcher task."""
    global _auto_shutdown_task, _auto_shutdown_delay
    if _auto_shutdown_task is not None:
        return
    # Read delay from global DB
    try:
        from guidebook.db import GlobalSetting, global_async_session

        async with global_async_session() as gdb:
            from sqlalchemy import select

            row = (
                await gdb.execute(
                    select(GlobalSetting.value).where(
                        GlobalSetting.key == "auto_shutdown_delay"
                    )
                )
            ).scalar_one_or_none()
            if row:
                _auto_shutdown_delay = max(5, int(row))
    except Exception:
        pass
    _auto_shutdown_task = asyncio.create_task(_auto_shutdown_loop())
    logger.info("Auto-shutdown watcher started (delay=%ds)", _auto_shutdown_delay)


async def stop_auto_shutdown() -> None:
    """Stop the auto-shutdown watcher task."""
    global _auto_shutdown_task
    if _auto_shutdown_task is not None:
        _auto_shutdown_task.cancel()
        try:
            await _auto_shutdown_task
        except asyncio.CancelledError:
            pass
        _auto_shutdown_task = None


def notify_shutdown() -> None:
    """Broadcast shutdown event and signal all SSE generators to stop."""
    broadcast("shutdown", {})
    evt = _get_shutdown_event()
    evt.set()


async def _sse_generator(queue: asyncio.Queue[str], request: Request):
    shutdown_evt = _get_shutdown_event()
    try:
        while not shutdown_evt.is_set():
            if await request.is_disconnected():
                return
            try:
                msg = await asyncio.wait_for(queue.get(), timeout=5)
                yield msg
            except asyncio.TimeoutError:
                # Send keepalive event; clients use this to detect server death
                yield "event: keepalive\ndata: {}\n\n"
            if shutdown_evt.is_set():
                # Drain any remaining messages (including shutdown broadcast)
                while not queue.empty():
                    yield queue.get_nowait()
                return
    except (asyncio.CancelledError, GeneratorExit):
        return


def _broadcast_client_count() -> None:
    """Notify all connected clients of the current subscriber count."""
    broadcast("clients", {"count": len(_subscribers)})


@router.get("/clients")
async def get_client_count():
    return {"count": subscriber_count()}


@router.post("/disconnect-others")
async def disconnect_others(request: Request):
    body = await request.json()
    nonce = body.get("nonce", "")
    broadcast("disconnect", {"nonce": nonce})
    return {"ok": True}


@router.get("/stream")
async def event_stream(request: Request):
    global _last_client_disconnected_at, _ever_had_client
    client = request.client
    client_addr = f"{client.host}:{client.port}" if client else "unknown"
    queue: asyncio.Queue[str] = asyncio.Queue(maxsize=64)
    _subscribers.append(queue)
    _ever_had_client = True
    logger.info(
        "SSE client    connected from %s (total: %d)", client_addr, len(_subscribers)
    )
    _broadcast_client_count()
    for cb in _on_connect_callbacks:
        cb()

    async def cleanup_generator():
        global _last_client_disconnected_at
        try:
            async for msg in _sse_generator(queue, request):
                yield msg
        except (asyncio.CancelledError, GeneratorExit):
            pass
        finally:
            if queue in _subscribers:
                _subscribers.remove(queue)
            if len(_subscribers) == 0:
                _last_client_disconnected_at = time.time()
            logger.info(
                "SSE client disconnected from %s (total: %d)",
                client_addr,
                len(_subscribers),
            )
            _broadcast_client_count()
            for cb in _on_disconnect_callbacks:
                cb()

    return StreamingResponse(
        cleanup_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
