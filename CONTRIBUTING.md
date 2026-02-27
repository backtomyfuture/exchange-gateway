# Contributing

## Setup

```bash
pip install -r requirements.txt
cd web && pnpm install
```

## Code Style

We use [Ruff](https://docs.astral.sh/ruff/) — CI will reject any violations.

```bash
ruff check app/ tests/ scripts/   # lint
ruff format app/ tests/ scripts/  # format
```

## Testing

```bash
pytest tests/ -v --ignore=tests/integration/ --ignore=tests/manual/
```

Add tests for new functionality. The test DB is SQLite in-memory (see `tests/conftest.py`).

## Pull Request Checklist

- [ ] `ruff check` and `ruff format` pass
- [ ] All tests pass
- [ ] New code has test coverage
- [ ] Commit messages are clear and descriptive

## Reporting Issues

Include: version, Python version, steps to reproduce, expected vs actual behavior, logs.

## License

Contributions are licensed under [Apache 2.0](LICENSE).
