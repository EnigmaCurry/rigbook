"""Unit tests for ADIF import parsing functions."""

from rigbook.routes.adif import (
    _apply_skcc_exchange,
    _is_skcclogger_file,
    _is_valid_skcc_number,
    _normalize_freq,
    _parse_segment_value,
    _segment_match_remainder,
    _segment_matches,
    _suggest_comment_template,
    _validate_import_record,
    adif_record_to_contact_dict,
    record_to_adif_line,
    strip_comment_prefix,
)


# ---------------------------------------------------------------------------
# _normalize_freq
# ---------------------------------------------------------------------------


class TestNormalizeFreq:
    def test_khz_matches_mhz(self):
        assert _normalize_freq("14050", "14.050") is True

    def test_khz_does_not_match(self):
        assert _normalize_freq("14050", "7.050") is False

    def test_invalid_values(self):
        assert _normalize_freq("abc", "14.050") is False
        assert _normalize_freq("14050", "abc") is False

    def test_empty_strings(self):
        assert _normalize_freq("", "") is False


# ---------------------------------------------------------------------------
# _parse_segment_value
# ---------------------------------------------------------------------------


class TestParseSegmentValue:
    def test_colon_format_single_word(self):
        result = _parse_segment_value("SKCC: 12486S", "SKCC")
        assert result == ("12486S", "")

    def test_colon_format_with_remainder(self):
        result = _parse_segment_value("SKCC: 12486S Hank", "SKCC")
        assert result == ("12486S", "Hank")

    def test_colon_format_multi_word_remainder(self):
        result = _parse_segment_value("Name: John Smith Jr", "Name")
        assert result == ("John", "Smith Jr")

    def test_space_format_no_match(self):
        assert _parse_segment_value("SKCC 12486S", "SKCC") is None

    def test_space_format_with_remainder_no_match(self):
        assert _parse_segment_value("SKCC 12486S Hank", "SKCC") is None

    def test_no_match(self):
        assert _parse_segment_value("Foo: bar", "SKCC") is None

    def test_empty_value(self):
        assert _parse_segment_value("SKCC: ", "SKCC") is None
        assert _parse_segment_value("SKCC ", "SKCC") is None

    def test_leading_trailing_whitespace(self):
        result = _parse_segment_value("  SKCC: 12486S  ", "SKCC")
        assert result == ("12486S", "")


# ---------------------------------------------------------------------------
# _segment_matches
# ---------------------------------------------------------------------------


class TestSegmentMatches:
    def test_exact_match(self):
        assert _segment_matches("SKCC: 12486S", "SKCC", "12486S") is True

    def test_first_word_match_with_trailing_text(self):
        assert _segment_matches("SKCC: 12486S Hank", "SKCC", "12486S") is True

    def test_value_mismatch(self):
        assert _segment_matches("SKCC: 99999", "SKCC", "12486S") is False

    def test_freq_khz_mhz(self):
        assert _segment_matches("Freq: 14050", "Freq", "14.050", "freq") is True

    def test_freq_mismatch(self):
        assert _segment_matches("Freq: 14050", "Freq", "7.050", "freq") is False

    def test_wrong_label(self):
        assert _segment_matches("Name: John", "SKCC", "John") is False


# ---------------------------------------------------------------------------
# _segment_match_remainder
# ---------------------------------------------------------------------------


class TestSegmentMatchRemainder:
    def test_match_no_remainder(self):
        result = _segment_match_remainder("SKCC: 12486S", "SKCC", "12486S")
        assert result == ""

    def test_match_with_remainder(self):
        result = _segment_match_remainder("SKCC: 12486S Hank", "SKCC", "12486S")
        assert result == "Hank"

    def test_match_multi_word_remainder(self):
        result = _segment_match_remainder(
            "SKCC: 12486S Hank from CT", "SKCC", "12486S"
        )
        assert result == "Hank from CT"

    def test_no_match(self):
        assert _segment_match_remainder("SKCC: 99999", "SKCC", "12486S") is None

    def test_freq_match_remainder(self):
        result = _segment_match_remainder(
            "Freq: 14050 extra", "Freq", "14.050", "freq"
        )
        assert result == "extra"


# ---------------------------------------------------------------------------
# strip_comment_prefix
# ---------------------------------------------------------------------------


class TestStripCommentPrefix:
    def _template(self, *fields):
        """Helper to build template_fields list."""
        label_map = {
            "skcc": "SKCC",
            "freq": "Freq",
            "mode": "Mode",
            "call": "Call",
            "name": "Name",
            "rst_sent": "RST Sent",
            "grid": "Grid",
        }
        return [{"field": f, "label": label_map.get(f, f)} for f in fields]

    def test_strip_single_segment_exact(self):
        record = {"SKCC": "12486S"}
        result = strip_comment_prefix("SKCC: 12486S", record, self._template("skcc"), "|")
        assert result == ""

    def test_strip_single_segment_with_remainder(self):
        record = {"SKCC": "12486S"}
        result = strip_comment_prefix(
            "SKCC: 12486S Hank", record, self._template("skcc"), "|"
        )
        assert result == "Hank"

    def test_strip_multi_segment(self):
        record = {"SKCC": "12486S", "MODE": "CW"}
        result = strip_comment_prefix(
            "SKCC: 12486S | Mode: CW", record, self._template("skcc", "mode"), "|"
        )
        assert result == ""

    def test_strip_multi_segment_with_user_comment(self):
        record = {"SKCC": "12486S", "MODE": "CW"}
        result = strip_comment_prefix(
            "SKCC: 12486S | Mode: CW | nice signal",
            record,
            self._template("skcc", "mode"),
            "|",
        )
        assert result == "nice signal"

    def test_strip_multi_segment_with_remainder(self):
        record = {"SKCC": "12486S", "MODE": "CW"}
        result = strip_comment_prefix(
            "SKCC: 12486S Hank | Mode: CW",
            record,
            self._template("skcc", "mode"),
            "|",
        )
        assert result == "Hank"

    def test_strip_multi_segment_remainder_and_user_comment(self):
        record = {"SKCC": "12486S", "MODE": "CW"}
        result = strip_comment_prefix(
            "SKCC: 12486S Hank | Mode: CW | nice signal",
            record,
            self._template("skcc", "mode"),
            "|",
        )
        assert result == "Hank | nice signal"

    def test_no_template_returns_original(self):
        result = strip_comment_prefix("hello world", {}, [], "|")
        assert result == "hello world"

    def test_no_match_returns_original(self):
        record = {"SKCC": "12486S"}
        result = strip_comment_prefix(
            "random comment", record, self._template("skcc"), "|"
        )
        assert result == "random comment"

    def test_empty_comment(self):
        result = strip_comment_prefix("", {}, self._template("skcc"), "|")
        assert result == ""

    def test_custom_separator(self):
        record = {"SKCC": "12486S", "MODE": "CW"}
        result = strip_comment_prefix(
            "SKCC: 12486S - Mode: CW - user text",
            record,
            self._template("skcc", "mode"),
            "-",
        )
        assert result == "user text"

    def test_app_rigbook_comment_fmt_overrides_separator(self):
        record = {"SKCC": "12486S", "MODE": "CW", "APP_RIGBOOK_COMMENT_FMT": "-"}
        result = strip_comment_prefix(
            "SKCC: 12486S - Mode: CW - user text",
            record,
            self._template("skcc", "mode"),
            "|",
        )
        assert result == "user text"

    def test_freq_khz_strip(self):
        record = {"FREQ": "14.050"}
        result = strip_comment_prefix(
            "Freq: 14050", record, self._template("freq"), "|"
        )
        assert result == ""


# ---------------------------------------------------------------------------
# _validate_import_record
# ---------------------------------------------------------------------------


class TestValidateImportRecord:
    def _template(self, *fields):
        label_map = {
            "skcc": "SKCC",
            "freq": "Freq",
            "mode": "Mode",
            "call": "Call",
            "name": "Name",
        }
        return [{"field": f, "label": label_map.get(f, f)} for f in fields]

    def test_no_warnings_when_matching(self):
        record = {"COMMENT": "SKCC: 12486S", "SKCC": "12486S"}
        warnings = _validate_import_record(record, self._template("skcc"), "|")
        assert warnings == []

    def test_first_word_mismatch_warns(self):
        record = {"COMMENT": "SKCC: 99999", "SKCC": "12486S"}
        warnings = _validate_import_record(record, self._template("skcc"), "|")
        assert len(warnings) >= 1
        assert any(w["field"] == "skcc" for w in warnings)

    def test_multi_word_value_uses_first_word(self):
        """SKCC: 12486S Hank — first word 12486S matches ADIF field, no warning."""
        record = {"COMMENT": "SKCC: 12486S Hank", "SKCC": "12486S"}
        warnings = _validate_import_record(record, self._template("skcc"), "|")
        # Should not warn about SKCC mismatch (first word matches)
        skcc_mismatch = [w for w in warnings if w["field"] == "skcc" and "comment has" in w["message"]]
        assert skcc_mismatch == []

    def test_skcc_with_spaces_warns(self):
        """SKCC ADIF field containing spaces triggers validation warning."""
        record = {"COMMENT": "", "SKCC": "12486S Hank"}
        warnings = _validate_import_record(record, self._template("skcc"), "|")
        assert any("not a valid SKCC number" in w["message"] for w in warnings)

    def test_skcc_not_starting_with_digit_warns(self):
        record = {"COMMENT": "", "SKCC": "ABC"}
        warnings = _validate_import_record(record, self._template("skcc"), "|")
        assert any("not a valid SKCC number" in w["message"] for w in warnings)

    def test_no_comment_no_warnings(self):
        record = {"SKCC": "12486S"}
        warnings = _validate_import_record(record, self._template("skcc"), "|")
        assert warnings == []

    def test_multi_segment_mismatch(self):
        record = {
            "COMMENT": "SKCC: 99999 | Mode: CW",
            "SKCC": "12486S",
            "MODE": "CW",
        }
        warnings = _validate_import_record(
            record, self._template("skcc", "mode"), "|"
        )
        assert any(
            w["field"] == "skcc" and w["comment_val"] == "99999" for w in warnings
        )

    def test_missing_field_value_warns(self):
        """Comment has a value but the ADIF field is empty."""
        record = {"COMMENT": "SKCC: 12486S"}
        warnings = _validate_import_record(record, self._template("skcc"), "|")
        assert any("no normalized field" in w["message"] for w in warnings)


# ---------------------------------------------------------------------------
# _suggest_comment_template
# ---------------------------------------------------------------------------


class TestSuggestCommentTemplate:
    def test_detects_pipe_separator(self):
        records = [
            {"COMMENT": "SKCC: 12486S | Mode: CW", "SKCC": "12486S", "MODE": "CW"},
            {"COMMENT": "SKCC: 2240S | Mode: CW", "SKCC": "2240S", "MODE": "CW"},
        ]
        result = _suggest_comment_template(records)
        assert result["separator"] == "|"
        fields = {f["field"] for f in result["fields"]}
        assert "skcc" in fields
        assert "mode" in fields

    def test_single_word_value_matching(self):
        """Ensure multi-word comment values only match first word to ADIF field."""
        records = [
            {
                "COMMENT": "SKCC: 12486S Hank | Mode: CW",
                "SKCC": "12486S",
                "MODE": "CW",
            },
        ]
        result = _suggest_comment_template(records)
        fields = {f["field"] for f in result["fields"]}
        assert "skcc" in fields

    def test_no_comments(self):
        result = _suggest_comment_template([{"CALL": "W1AW"}])
        assert result == {"separator": "|", "fields": []}

    def test_dash_separator(self):
        records = [
            {"COMMENT": "SKCC: 12486S - Mode: CW", "SKCC": "12486S", "MODE": "CW"},
        ]
        result = _suggest_comment_template(records)
        assert result["separator"] == "-"


# ---------------------------------------------------------------------------
# adif_record_to_contact_dict
# ---------------------------------------------------------------------------


class TestAdifRecordToContactDict:
    def test_basic_fields(self):
        record = {
            "CALL": "K1PUG",
            "FREQ": "14.050000",
            "MODE": "CW",
            "QSO_DATE": "20250331",
            "TIME_ON": "200504",
        }
        result = adif_record_to_contact_dict(record)
        assert result["call"] == "K1PUG"
        assert result["mode"] == "CW"
        assert float(result["freq"]) == 14050.0
        assert result["timestamp"].year == 2025
        assert result["timestamp"].month == 3
        assert result["timestamp"].day == 31
        assert result["timestamp"].hour == 20
        assert result["timestamp"].minute == 5
        assert result["timestamp"].second == 4

    def test_skcc_field(self):
        record = {"CALL": "W1AW", "FREQ": "14.050", "MODE": "CW", "SKCC": "12486S"}
        result = adif_record_to_contact_dict(record)
        assert result["skcc"] == "12486S"

    def test_dxcc_parsed_as_int(self):
        record = {"CALL": "W1AW", "FREQ": "14.050", "MODE": "CW", "DXCC": "291"}
        result = adif_record_to_contact_dict(record)
        assert result["dxcc"] == 291

    def test_empty_fields_excluded(self):
        record = {"CALL": "W1AW", "FREQ": "14.050", "MODE": "CW", "NAME": ""}
        result = adif_record_to_contact_dict(record)
        assert "name" not in result

    def test_uuid_preserved(self):
        record = {
            "CALL": "W1AW",
            "FREQ": "14.050",
            "MODE": "CW",
            "APP_RIGBOOK_UUID": "abc-123",
        }
        result = adif_record_to_contact_dict(record)
        assert result["uuid"] == "abc-123"

    def test_time_off(self):
        record = {
            "CALL": "W1AW",
            "FREQ": "14.050",
            "MODE": "CW",
            "QSO_DATE": "20250331",
            "TIME_ON": "200504",
            "QSO_DATE_OFF": "20250331",
            "TIME_OFF": "200916",
        }
        result = adif_record_to_contact_dict(record)
        assert result["timestamp_off"].hour == 20
        assert result["timestamp_off"].minute == 9
        assert result["timestamp_off"].second == 16

    def test_skcc_exch(self):
        record = {
            "CALL": "W1AW",
            "FREQ": "14.050",
            "MODE": "CW",
            "APP_RIGBOOK_SKCC_EXCH": "Y",
        }
        result = adif_record_to_contact_dict(record)
        assert result["skcc_exch"] == 1


# ---------------------------------------------------------------------------
# record_to_adif_line
# ---------------------------------------------------------------------------


class TestRecordToAdifLine:
    def test_basic(self):
        line = record_to_adif_line({"CALL": "W1AW", "FREQ": "14.050"})
        assert "<CALL:4>W1AW" in line
        assert "<FREQ:6>14.050" in line
        assert line.endswith("<eor>")

    def test_empty_values_excluded(self):
        line = record_to_adif_line({"CALL": "W1AW", "NAME": "", "QTH": None})
        assert "NAME" not in line
        assert "QTH" not in line

    def test_skcc_logger_roundtrip(self):
        """Verify a record matching SKCC Logger format serializes correctly."""
        record = {
            "BAND": "20m",
            "CALL": "K1PUG",
            "FREQ": "14.050000",
            "MODE": "CW",
            "RST_SENT": "559",
            "RST_RCVD": "559",
            "SKCC": "12486S",
        }
        line = record_to_adif_line(record)
        assert "<SKCC:6>12486S" in line


# ---------------------------------------------------------------------------
# _is_valid_skcc_number
# ---------------------------------------------------------------------------


class TestIsValidSkccNumber:
    def test_valid_number_only(self):
        assert _is_valid_skcc_number("12486") is True

    def test_valid_with_suffix(self):
        assert _is_valid_skcc_number("12486S") is True
        assert _is_valid_skcc_number("12486T") is True
        assert _is_valid_skcc_number("12486C") is True

    def test_six_digits(self):
        assert _is_valid_skcc_number("123456") is True

    def test_six_digits_with_suffix(self):
        assert _is_valid_skcc_number("123456S") is True

    def test_single_digit(self):
        assert _is_valid_skcc_number("1") is True

    def test_empty_string(self):
        assert _is_valid_skcc_number("") is False

    def test_too_many_digits(self):
        assert _is_valid_skcc_number("1234567") is False

    def test_letters_only(self):
        assert _is_valid_skcc_number("ABC") is False

    def test_lowercase_suffix(self):
        assert _is_valid_skcc_number("12486s") is False

    def test_multiple_letters(self):
        assert _is_valid_skcc_number("12486ST") is False

    def test_spaces(self):
        assert _is_valid_skcc_number("12486 S") is False


# ---------------------------------------------------------------------------
# _is_skcclogger_file
# ---------------------------------------------------------------------------


class TestIsSkccloggerFile:
    def test_skcclogger_header(self):
        header = "ADIF export\nADIF Log Created by SKCCLogger v1.2\n<eoh>"
        assert _is_skcclogger_file(header) is True

    def test_other_header(self):
        assert _is_skcclogger_file("Generated by WSJT-X") is False

    def test_empty_header(self):
        assert _is_skcclogger_file("") is False

    def test_partial_match(self):
        assert _is_skcclogger_file("SKCCLogger") is False


# ---------------------------------------------------------------------------
# _apply_skcc_exchange
# ---------------------------------------------------------------------------


class TestApplySkccExchange:
    def test_skcclogger_valid_skcc_auto_applied(self):
        records = [
            ({"skcc": "12486S"}, {}),
            ({"skcc": "999T"}, {}),
        ]
        auto, decision = _apply_skcc_exchange(records, is_skcclogger=True)
        assert auto == 2
        assert decision == 0
        assert records[0][0]["skcc_exch"] == 1
        assert records[1][0]["skcc_exch"] == 1

    def test_skcclogger_invalid_skcc_not_applied(self):
        records = [({"skcc": "ABCDEF"}, {})]
        auto, decision = _apply_skcc_exchange(records, is_skcclogger=True)
        assert auto == 0
        assert decision == 0
        assert "skcc_exch" not in records[0][0]

    def test_skcclogger_already_has_exch(self):
        records = [({"skcc": "12486S", "skcc_exch": 1}, {})]
        auto, decision = _apply_skcc_exchange(records, is_skcclogger=True)
        assert auto == 0
        assert decision == 0

    def test_non_skcclogger_valid_skcc_needs_decision(self):
        records = [({"skcc": "12486S"}, {})]
        auto, decision = _apply_skcc_exchange(records, is_skcclogger=False)
        assert auto == 0
        assert decision == 1
        assert "skcc_exch" not in records[0][0]

    def test_non_skcclogger_already_has_exch(self):
        records = [({"skcc": "12486S", "skcc_exch": 1}, {})]
        auto, decision = _apply_skcc_exchange(records, is_skcclogger=False)
        assert auto == 0
        assert decision == 0

    def test_non_skcclogger_invalid_skcc(self):
        records = [({"skcc": "INVALID"}, {})]
        auto, decision = _apply_skcc_exchange(records, is_skcclogger=False)
        assert auto == 0
        assert decision == 0

    def test_no_skcc_field(self):
        records = [({"call": "W1AW"}, {})]
        auto, decision = _apply_skcc_exchange(records, is_skcclogger=True)
        assert auto == 0
        assert decision == 0

    def test_empty_skcc_field(self):
        records = [({"skcc": ""}, {})]
        auto, decision = _apply_skcc_exchange(records, is_skcclogger=True)
        assert auto == 0
        assert decision == 0
