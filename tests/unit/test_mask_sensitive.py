from app.core.middlewares import _mask_sensitive


def test_mask_password():
    result = _mask_sensitive({"password": "secret123"})
    assert result == {"password": "***"}


def test_mask_nested():
    data = {"user": {"password": "secret", "name": "Alice"}}
    result = _mask_sensitive(data)
    assert result["user"]["password"] == "***"
    assert result["user"]["name"] == "Alice"


def test_mask_case_insensitive():
    result = _mask_sensitive({"Password": "secret123"})
    assert result["Password"] == "***"


def test_non_sensitive_preserved():
    data = {"username": "admin", "email": "a@b.com"}
    result = _mask_sensitive(data)
    assert result == {"username": "admin", "email": "a@b.com"}


def test_mask_list_of_dicts():
    data = {"items": [{"token": "abc"}, {"name": "ok"}]}
    result = _mask_sensitive(data)
    assert result["items"][0]["token"] == "***"
    assert result["items"][1]["name"] == "ok"


def test_non_dict_passthrough():
    assert _mask_sensitive("hello") == "hello"
    assert _mask_sensitive(42) == 42
    assert _mask_sensitive(None) is None
