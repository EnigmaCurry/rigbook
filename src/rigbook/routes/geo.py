import pycountry
from fastapi import APIRouter

from rigbook.dxcc import ISO_TO_DXCC, dxcc_country
from rigbook.normalize import COUNTRY_ALIASES, COUNTRY_NAME_OVERRIDES

router = APIRouter(prefix="/api/geo", tags=["geo"])


@router.get("/countries")
async def list_countries():
    results = []
    for c in sorted(pycountry.countries, key=lambda c: c.name):
        name = COUNTRY_NAME_OVERRIDES.get(c.alpha_2, c.name)
        aliases = [c.alpha_2]
        if c.alpha_2 in COUNTRY_ALIASES:
            aliases = COUNTRY_ALIASES[c.alpha_2]
        entry = {"code": c.alpha_2, "name": name, "aliases": aliases}
        dxcc_code = ISO_TO_DXCC.get(c.alpha_2)
        if dxcc_code is not None:
            entry["dxcc"] = dxcc_code
            entry["dxcc_name"] = dxcc_country(dxcc_code) or ""
        results.append(entry)
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
