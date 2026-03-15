import httpx
from fastapi import APIRouter

router = APIRouter(prefix="/api/pota", tags=["pota"])

POTA_SPOTS_URL = "https://api.pota.app/v1/spots"


@router.get("/spots")
async def get_spots():
    async with httpx.AsyncClient(timeout=10) as client:
        res = await client.get(
            POTA_SPOTS_URL,
            headers={"Accept": "application/json"},
        )
        res.raise_for_status()
        return res.json()
