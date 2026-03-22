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


def broadcast(event: str, data: dict) -> None:
    """Send an SSE event to all connected clients."""
    msg = f"event: {event}\ndata: {json.dumps(data)}\n\n"
    for q in list(_subscribers):
        try:
            q.put_nowait(msg)
        except asyncio.QueueFull:
            pass


async def _sse_generator(queue: asyncio.Queue[str]):
    try:
        while True:
            msg = await queue.get()
            yield msg
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
            _subscribers.remove(queue)

    return StreamingResponse(
        cleanup_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
