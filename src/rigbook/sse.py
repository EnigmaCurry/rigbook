"""Server-Sent Events bus.

Provides a simple pub/sub mechanism: any part of the backend can broadcast
events, and connected SSE clients receive them in real time.
"""

import asyncio
import json
import logging

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

logger = logging.getLogger("rigbook.sse")

router = APIRouter(prefix="/api/events", tags=["events"])

_subscribers: list[asyncio.Queue[str]] = []
_shutdown_event: asyncio.Event | None = None


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
            get_task = asyncio.ensure_future(queue.get())
            shutdown_task = asyncio.ensure_future(shutdown_evt.wait())
            done, pending = await asyncio.wait(
                [get_task, shutdown_task], return_when=asyncio.FIRST_COMPLETED
            )
            for t in pending:
                t.cancel()
            if get_task in done:
                yield get_task.result()
            if shutdown_evt.is_set():
                # Drain any remaining messages (including shutdown broadcast)
                while not queue.empty():
                    yield queue.get_nowait()
                return
    except asyncio.CancelledError:
        return


@router.get("/stream")
async def event_stream():
    queue: asyncio.Queue[str] = asyncio.Queue(maxsize=64)
    _subscribers.append(queue)

    async def cleanup_generator():
        try:
            async for msg in _sse_generator(queue):
                yield msg
        finally:
            if queue in _subscribers:
                _subscribers.remove(queue)

    return StreamingResponse(
        cleanup_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
