import base64
import os

from app.utils.key_rotator import KeyRotator


def _make_valid_key() -> str:
    return base64.b64encode(os.urandom(32)).decode("utf-8")


def test_verify_keys_valid():
    old_key = _make_valid_key()
    new_key = _make_valid_key()
    rotator = KeyRotator(old_key, new_key)
    result = rotator.verify_keys()
    assert result["old_key_valid"] is True
    assert result["new_key_valid"] is True


def test_verify_keys_invalid():
    valid_key = _make_valid_key()
    invalid_key = "not-a-valid-base64-key"
    rotator = KeyRotator(valid_key, valid_key)

    result = rotator.verify_keys()
    assert result["old_key_valid"] is True
    assert result["new_key_valid"] is True

    try:
        rotator_bad = KeyRotator(invalid_key, valid_key)
        result_bad = rotator_bad.verify_keys()
        assert result_bad["old_key_valid"] is False
    except ValueError:
        pass
