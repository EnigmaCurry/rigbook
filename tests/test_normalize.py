from rigbook.normalize import (
    country_to_alpha2,
    country_to_dxcc,
    normalize_contact_fields,
    normalize_country,
    normalize_state,
)


class TestNormalizeCountry:
    def test_alpha2_code(self):
        assert normalize_country("US") == "United States"

    def test_alpha3_code(self):
        assert normalize_country("USA") == "United States"

    def test_canada_alpha3(self):
        assert normalize_country("CAN") == "Canada"

    def test_alias_uk(self):
        assert normalize_country("UK") == "United Kingdom"

    def test_dxcc_entity_name(self):
        assert normalize_country("UNITED STATES OF AMERICA") == "United States"

    def test_override_vietnam(self):
        assert normalize_country("VN") == "Vietnam"

    def test_override_taiwan(self):
        assert normalize_country("TW") == "Taiwan"

    def test_already_canonical(self):
        assert normalize_country("United States") == "United States"

    def test_case_insensitive(self):
        assert normalize_country("united states") == "United States"

    def test_none(self):
        assert normalize_country(None) is None

    def test_empty(self):
        assert normalize_country("") is None

    def test_whitespace(self):
        assert normalize_country("  ") is None

    def test_unknown_passthrough(self):
        assert normalize_country("Narnia") == "Narnia"

    def test_dxcc_entity_no_iso(self):
        # ALASKA is DXCC=6 but has no ISO country — preserved as-is
        assert normalize_country("ALASKA") == "ALASKA"

    def test_canada(self):
        assert normalize_country("CA") == "Canada"

    def test_germany(self):
        assert normalize_country("DE") == "Germany"
        assert normalize_country("DEU") == "Germany"

    def test_stripped(self):
        assert normalize_country("  US  ") == "United States"


class TestNormalizeState:
    def test_code_with_country(self):
        assert normalize_state("UT", "US") == "UT"

    def test_full_name_to_code(self):
        assert normalize_state("Utah", "US") == "UT"

    def test_full_code_format(self):
        assert normalize_state("US-UT") == "UT"

    def test_none(self):
        assert normalize_state(None) is None

    def test_empty(self):
        assert normalize_state("") is None

    def test_no_country(self):
        assert normalize_state("UT") == "UT"

    def test_unknown_passthrough(self):
        assert normalize_state("XX", "US") == "XX"

    def test_case_insensitive(self):
        assert normalize_state("utah", "US") == "UT"

    def test_canadian_province(self):
        assert normalize_state("Ontario", "CA") == "ON"

    def test_canadian_code(self):
        assert normalize_state("ON", "CA") == "ON"


class TestCountryToDxcc:
    def test_united_states(self):
        assert country_to_dxcc("United States") == 291

    def test_canada(self):
        assert country_to_dxcc("Canada") == 1

    def test_none(self):
        assert country_to_dxcc(None) is None

    def test_unknown(self):
        assert country_to_dxcc("Narnia") is None


class TestCountryToAlpha2:
    def test_united_states(self):
        assert country_to_alpha2("United States") == "US"

    def test_vietnam_override(self):
        assert country_to_alpha2("Vietnam") == "VN"

    def test_none(self):
        assert country_to_alpha2(None) is None


class TestNormalizeContactFields:
    def test_full_normalization(self):
        result = normalize_contact_fields(country="US", state="Utah", dxcc=None)
        assert result["country"] == "United States"
        assert result["state"] == "UT"
        assert result["dxcc"] == 291

    def test_preserves_existing_dxcc(self):
        result = normalize_contact_fields(country=None, state=None, dxcc=6)
        assert result["dxcc"] == 6

    def test_dxcc_name_to_country(self):
        result = normalize_contact_fields(
            country="UNITED STATES OF AMERICA", state=None, dxcc=None
        )
        assert result["country"] == "United States"
        assert result["dxcc"] == 291

    def test_all_none(self):
        result = normalize_contact_fields(country=None, state=None, dxcc=None)
        assert result["country"] is None
        assert result["state"] is None
        assert result["dxcc"] is None

    def test_alpha3_country_with_state(self):
        result = normalize_contact_fields(country="CAN", state="Ontario", dxcc=None)
        assert result["country"] == "Canada"
        assert result["state"] == "ON"
        assert result["dxcc"] == 1
