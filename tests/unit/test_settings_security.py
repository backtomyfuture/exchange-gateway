import pytest
from pydantic import ValidationError

from app.settings.config import Settings


def test_audit_log_retention_must_stay_within_security_bounds():
    with pytest.raises(ValidationError, match="AUDIT_LOG_RETENTION_DAYS"):
        Settings(AUDIT_LOG_RETENTION_DAYS=31)
