# Contributing

## Setup

```bash
make init             # generate secrets, copy .env, install deps
docker compose up -d  # start all services
```

Or step by step:

```bash
./scripts/init-secrets.sh
cp .env.example .env
pip install -r requirements.txt
cd web && pnpm install
```

## Code Style

We use [Ruff](https://docs.astral.sh/ruff/) — CI will reject any violations.

```bash
make lint             # ruff check + eslint
make format           # ruff format
```

## Testing

```bash
make test             # runs pytest (189 tests, SQLite in-memory)
```

Add tests for new functionality. See `tests/conftest.py` for the test DB setup.

## Pull Request Checklist

- [ ] `make lint` passes
- [ ] `make test` passes
- [ ] New code has test coverage
- [ ] Commit messages are clear and descriptive

## Reporting Issues

Include: version, Python version, steps to reproduce, expected vs actual behavior, logs.

## License

Contributions are licensed under [Apache 2.0](LICENSE).
