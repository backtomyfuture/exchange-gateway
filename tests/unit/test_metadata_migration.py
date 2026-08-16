import importlib

import pytest

MIGRATION = importlib.import_module("migrations.models.3_20260816100000_metadata_only_auditlog")


class FakeDatabase:
    def __init__(self, *, column_exists: bool, index_exists: bool):
        self.column_exists = column_exists
        self.index_exists = index_exists
        self.scripts: list[str] = []

    async def execute_query(self, query: str, values: list[str]):
        name = values[1]
        exists = self.column_exists if name == "request_id" else self.index_exists
        return 1, [{"exists": 1}] if exists else []

    async def execute_script(self, query: str):
        self.scripts.append(query)


@pytest.mark.asyncio
async def test_upgrade_only_adds_missing_auditlog_objects():
    db = FakeDatabase(column_exists=False, index_exists=False)

    result = await MIGRATION.upgrade(db)

    assert result == "SELECT 1;"
    assert len(db.scripts) == 2
    assert "ADD COLUMN" in db.scripts[0]
    assert "CREATE INDEX" in db.scripts[1]


@pytest.mark.asyncio
async def test_upgrade_is_safe_when_schema_sync_already_added_objects():
    db = FakeDatabase(column_exists=True, index_exists=True)

    result = await MIGRATION.upgrade(db)

    assert result == "SELECT 1;"
    assert db.scripts == []
