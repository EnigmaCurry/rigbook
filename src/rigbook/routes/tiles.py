import httpx
from fastapi import APIRouter
from fastapi.responses import Response

router = APIRouter(prefix="/api/tiles", tags=["tiles"])

OSM_URL = "https://tile.openstreetmap.org/{z}/{x}/{y}.png"


@router.get("/{z}/{x}/{y}.png")
async def proxy_tile(z: int, x: int, y: int):
    url = OSM_URL.format(z=z, x=x, y=y)
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            res = await client.get(
                url,
                headers={"User-Agent": "Rigbook/0.1 (ham radio logbook)"},
            )
            return Response(
                content=res.content,
                media_type="image/png",
                headers={"Cache-Control": "public, max-age=86400"},
            )
    except (httpx.HTTPError, OSError):
        return Response(status_code=502)
