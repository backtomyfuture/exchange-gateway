import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.api.v1.auditlog.auditlog import get_audit_log_list


class _AwaitableQuery:
    def __init__(self, items):
        self.items = items
        self.calls = []

    async def count(self):
        self.calls.append("count")
        return len(self.items)

    def order_by(self, value):
        self.calls.append(("order_by", value))
        return self

    def offset(self, value):
        self.calls.append(("offset", value))
        return self

    def limit(self, value):
        self.calls.append(("limit", value))
        return self

    def __await__(self):
        async def resolve():
            self.calls.append("await")
            return self.items

        return resolve().__await__()


@pytest.mark.asyncio
async def test_audit_log_sorts_before_pagination():
    audit_log = MagicMock()
    audit_log.to_dict = AsyncMock(return_value={"id": 1})
    queryset = _AwaitableQuery([audit_log])

    with patch("app.api.v1.auditlog.auditlog.AuditLog.filter", return_value=queryset):
        response = await get_audit_log_list(page=2, page_size=10)

    assert queryset.calls == ["count", ("order_by", "-created_at"), ("offset", 10), ("limit", 10), "await"]
    assert json.loads(response.body) == {
        "code": 200,
        "msg": None,
        "data": [{"id": 1}],
        "total": 1,
        "page": 2,
        "page_size": 10,
    }
    audit_log.to_dict.assert_awaited_once_with(exclude_fields=["request_args", "response_body"])
