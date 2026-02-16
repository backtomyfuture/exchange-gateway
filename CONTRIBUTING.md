# Contributing to Exchange Gateway

Thank you for your interest in contributing to Exchange Gateway! This document provides guidelines for contributing to the project.

## Development Setup

### Prerequisites
- Python 3.11+
- Docker & Docker Compose
- Node.js 18+ (for frontend development)
- pnpm (for frontend dependencies)

### Local Development

1. **Clone the repository**
   ```bash
   git clone https://github.com/f148002/exchange-gateway.git
   cd exchange-gateway
   ```

2. **Set up environment**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run with Docker Compose**
   ```bash
   docker compose up -d
   ```

5. **Access the application**
   - Admin Dashboard: http://localhost
   - API Docs: http://localhost/docs
   - Direct API: http://localhost:18001

## Code Style

We use [Ruff](https://docs.astral.sh/ruff/) for linting and formatting.

```bash
# Check code style
ruff check app/ tests/ scripts/

# Auto-fix issues
ruff check --fix app/ tests/ scripts/

# Format code
ruff format app/ tests/ scripts/
```

## Testing

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=app --cov-report=html
```

## Pull Request Process

1. **Fork the repository** and create your branch from `main`
2. **Make your changes** following the code style guidelines
3. **Add tests** for any new functionality
4. **Run tests** to ensure everything passes
5. **Update documentation** if needed
6. **Submit a pull request** with a clear description of changes

### PR Guidelines
- Keep changes focused and atomic
- Write clear commit messages
- Reference any related issues
- Ensure CI checks pass

## Reporting Issues

When reporting issues, please include:
- Exchange Gateway version
- Python version
- Operating system
- Steps to reproduce
- Expected vs actual behavior
- Relevant logs or error messages

## License

By contributing, you agree that your contributions will be licensed under the Apache License 2.0.
