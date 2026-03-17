import pycountry
from fastapi import APIRouter

router = APIRouter(prefix="/api/geo", tags=["geo"])

COUNTRY_NAME_OVERRIDES: dict[str, str] = {
    "VN": "Vietnam",
    "TW": "Taiwan",
}

COUNTRY_ALIASES: dict[str, list[str]] = {
    "US": ["US", "USA"],
    "GB": ["UK"],
    "KR": ["South Korea"],
    "KP": ["North Korea"],
    "RU": ["Russia"],
    "TW": ["Taiwan"],
}


@router.get("/countries")
async def list_countries():
    results = []
    for c in sorted(pycountry.countries, key=lambda c: c.name):
        name = COUNTRY_NAME_OVERRIDES.get(c.alpha_2, c.name)
        aliases = [c.alpha_2]
        if c.alpha_2 in COUNTRY_ALIASES:
            aliases = COUNTRY_ALIASES[c.alpha_2]
        results.append({"code": c.alpha_2, "name": name, "aliases": aliases})
    return results


@router.get("/subdivisions/{country_code}")
async def list_subdivisions(country_code: str):
    subs = pycountry.subdivisions.get(country_code=country_code.upper())
    if not subs:
        return []
    return [
        {"code": s.code, "name": s.name, "type": s.type}
        for s in sorted(subs, key=lambda s: s.name)
    ]
