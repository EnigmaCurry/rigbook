"""Normalize country, state, and DXCC fields to canonical formats.

Canonical formats:
  - country: pycountry display name (e.g. "United States")
  - state: 2-letter subdivision code (e.g. "UT")
  - dxcc: integer DXCC entity code (e.g. 291)
"""

import pycountry

from rigbook.dxcc import DXCC_ENTITIES, ISO_TO_DXCC

# Shared constants (also used by routes/geo.py)
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

# --- Lookup tables (built once at import time) ---

# DXCC entity name (uppercase) → DXCC code
_DXCC_NAME_TO_CODE: dict[str, int] = {
    name: code for code, name in DXCC_ENTITIES.items()
}

# DXCC code → ISO alpha-2 (reverse of ISO_TO_DXCC)
_DXCC_TO_ISO: dict[int, str] = {v: k for k, v in ISO_TO_DXCC.items()}

# ISO alpha-3 → alpha-2
_ALPHA3_TO_ALPHA2: dict[str, str] = {}
for _c in pycountry.countries:
    if hasattr(_c, "alpha_3"):
        _ALPHA3_TO_ALPHA2[_c.alpha_3.upper()] = _c.alpha_2

# pycountry name (uppercase) → alpha-2
_NAME_UPPER_TO_ALPHA2: dict[str, str] = {}
for _c in pycountry.countries:
    _NAME_UPPER_TO_ALPHA2[_c.name.upper()] = _c.alpha_2
    if hasattr(_c, "official_name"):
        _NAME_UPPER_TO_ALPHA2[_c.official_name.upper()] = _c.alpha_2
    if hasattr(_c, "common_name"):
        _NAME_UPPER_TO_ALPHA2[_c.common_name.upper()] = _c.alpha_2
# Add overrides
for _code, _name in COUNTRY_NAME_OVERRIDES.items():
    _NAME_UPPER_TO_ALPHA2[_name.upper()] = _code

# Alias (uppercase) → alpha-2
_ALIAS_TO_ALPHA2: dict[str, str] = {}
for _code, _aliases in COUNTRY_ALIASES.items():
    for _alias in _aliases:
        _ALIAS_TO_ALPHA2[_alias.upper()] = _code


def _alpha2_to_display_name(alpha2: str) -> str:
    """Convert ISO alpha-2 code to canonical display name."""
    if alpha2 in COUNTRY_NAME_OVERRIDES:
        return COUNTRY_NAME_OVERRIDES[alpha2]
    c = pycountry.countries.get(alpha_2=alpha2)
    return c.name if c else alpha2


def normalize_country(value: str | None) -> str | None:
    """Normalize a country string to pycountry display name.

    Returns None if input is None or empty.
    Returns input unchanged if no match is found.
    """
    if not value or not value.strip():
        return None
    value = value.strip()
    upper = value.upper()

    # Already a canonical display name?
    if upper in _NAME_UPPER_TO_ALPHA2:
        return _alpha2_to_display_name(_NAME_UPPER_TO_ALPHA2[upper])

    # ISO alpha-2 code (e.g. "US")
    if len(upper) == 2:
        c = pycountry.countries.get(alpha_2=upper)
        if c:
            return _alpha2_to_display_name(c.alpha_2)

    # ISO alpha-3 code (e.g. "USA")
    if len(upper) == 3 and upper in _ALPHA3_TO_ALPHA2:
        return _alpha2_to_display_name(_ALPHA3_TO_ALPHA2[upper])

    # Alias (e.g. "UK", "USA")
    if upper in _ALIAS_TO_ALPHA2:
        return _alpha2_to_display_name(_ALIAS_TO_ALPHA2[upper])

    # DXCC entity name (e.g. "UNITED STATES OF AMERICA")
    if upper in _DXCC_NAME_TO_CODE:
        dxcc_code = _DXCC_NAME_TO_CODE[upper]
        iso_code = _DXCC_TO_ISO.get(dxcc_code)
        if iso_code:
            return _alpha2_to_display_name(iso_code)
        # DXCC entity with no ISO mapping (e.g. "ALASKA") — return as-is
        return value

    # No match — return unchanged
    return value


def normalize_state(value: str | None, country_code: str | None = None) -> str | None:
    """Normalize a state/subdivision to 2-letter code.

    Returns None if input is None or empty.
    Returns input unchanged if no match is found.
    """
    if not value or not value.strip():
        return None
    value = value.strip()
    upper = value.upper()

    # "US-UT" format → "UT"
    if "-" in upper:
        parts = upper.split("-", 1)
        if len(parts) == 2 and len(parts[1]) <= 3:
            # Validate against pycountry
            cc = parts[0]
            subs = pycountry.subdivisions.get(country_code=cc)
            if subs:
                for s in subs:
                    if s.code.upper() == upper:
                        return s.code.split("-")[-1]
            # Even without validation, extract the suffix
            return parts[1]

    if not country_code:
        return value

    cc = country_code.upper()
    subs = pycountry.subdivisions.get(country_code=cc)
    if not subs:
        return value

    # Already a 2-letter code? Validate it.
    if len(upper) <= 3:
        full_code = f"{cc}-{upper}"
        for s in subs:
            if s.code.upper() == full_code:
                return s.code.split("-")[-1]

    # Full name → code
    for s in subs:
        if s.name.upper() == upper:
            return s.code.split("-")[-1]

    return value


def country_to_alpha2(country_name: str | None) -> str | None:
    """Get ISO alpha-2 code from a canonical country name."""
    if not country_name:
        return None
    upper = country_name.upper().strip()
    if upper in _NAME_UPPER_TO_ALPHA2:
        return _NAME_UPPER_TO_ALPHA2[upper]
    # Try as alpha-2 directly
    if len(upper) == 2:
        c = pycountry.countries.get(alpha_2=upper)
        if c:
            return c.alpha_2
    return None


def country_to_dxcc(country_name: str | None) -> int | None:
    """Derive DXCC code from a canonical country name."""
    alpha2 = country_to_alpha2(country_name)
    if alpha2:
        return ISO_TO_DXCC.get(alpha2)
    return None


def normalize_contact_fields(
    country: str | None = None,
    state: str | None = None,
    dxcc: int | None = None,
) -> dict:
    """Normalize country/state/dxcc together, deriving missing values.

    Returns dict with keys: country, state, dxcc (any may be None).
    """
    norm_country = normalize_country(country)
    alpha2 = country_to_alpha2(norm_country) if norm_country else None
    norm_state = normalize_state(state, alpha2)

    if dxcc is None and norm_country:
        dxcc = country_to_dxcc(norm_country)

    return {"country": norm_country, "state": norm_state, "dxcc": dxcc}
