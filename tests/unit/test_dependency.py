from app.core.dependency import extract_token


def test_extract_token_bearer():
    assert extract_token("Bearer abc123") == "abc123"


def test_extract_token_raw():
    assert extract_token("raw_token_value") == "raw_token_value"


def test_extract_token_case_insensitive():
    assert extract_token("bearer xyz789") == "xyz789"
    assert extract_token("BEARER foo") == "foo"
