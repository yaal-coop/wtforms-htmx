import pytest

from wtforms_htmx.headers import _parse_request


def test_htmx2_headers_carry_raw_ids():
    """The htmx 2 headers give the source and target ids as is."""
    info = _parse_request({"HX-Trigger": "email", "HX-Target": "email-wrapper"})
    assert info.source_id == "email"
    assert info.target_id == "email-wrapper"
    assert not info.htmx4


def test_htmx4_headers_strip_the_tag_prefix():
    """The htmx 4 ``tag#id`` headers give the bare ids."""
    info = _parse_request(
        {"HX-Source": "input#email", "HX-Target": "div#email-wrapper"}
    )
    assert info.source_id == "email"
    assert info.target_id == "email-wrapper"
    assert info.htmx4


def test_htmx4_element_without_id_yields_none():
    """An htmx 4 element without an id gives ``None``."""
    info = _parse_request({"HX-Source": "form", "HX-Target": "div"})
    assert info.source_id is None
    assert info.target_id is None


def test_htmx4_wins_over_a_stale_htmx2_header():
    """``HX-Source`` takes precedence over ``HX-Trigger`` when both are present."""
    info = _parse_request({"HX-Source": "input#email", "HX-Trigger": "stale"})
    assert info.source_id == "email"


def test_trigger_name_is_never_read():
    """Guard: the library never reads ``HX-Trigger-Name`` (see ``headers.py``)."""
    info = _parse_request({"HX-Trigger-Name": "email"})
    assert info.source_id is None


def test_htmx4_source_id_is_percent_decoded():
    """A percent-encoded htmx 4 source id is decoded."""
    info = _parse_request({"HX-Source": "input#soci%C3%A9t%C3%A9"})
    assert info.source_id == "société"


def test_htmx4_target_id_is_percent_decoded():
    """A percent-encoded htmx 4 target id is decoded."""
    info = _parse_request(
        {"HX-Source": "input#a", "HX-Target": "div#soci%C3%A9t%C3%A9-wrapper"}
    )
    assert info.target_id == "société-wrapper"


def test_htmx2_ids_are_not_decoded():
    """The htmx 2 ids are kept as is, without percent-decoding."""
    info = _parse_request({"HX-Trigger": "a%20b", "HX-Target": "c%20d"})
    assert info.source_id == "a%20b"
    assert info.target_id == "c%20d"


@pytest.mark.parametrize("headers", [None, {}])
def test_no_headers_yields_empty_info(headers):
    """Missing or empty headers describe a plain request with no source and no target."""
    assert _parse_request(headers) == (False, False, None, None, False)


def test_header_names_are_case_insensitive():
    """Lowercase header names, as ASGI servers send them, are read too."""
    info = _parse_request(
        {"hx-request": "true", "hx-boosted": "true", "hx-source": "input#email"}
    )
    assert info == (True, True, "email", None, True)
