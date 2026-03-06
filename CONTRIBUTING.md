# Contributing to driftwatch

Thanks for your interest in contributing to driftwatch! This guide covers everything you need to get started.

## Setup

### Prerequisites

- Python 3.11 or later
- PostgreSQL 16 (or use Docker Compose)
- Git

### Dev Environment

1. Fork and clone the repository:

```bash
git clone https://github.com/<your-username>/driftwatch.git
cd driftwatch
```

2. Create a virtual environment and install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

3. Start PostgreSQL (via Docker Compose):

```bash
docker compose up -d postgres
```

4. Set the required environment variables:

```bash
export DRIFTWATCH_DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5432/driftwatch"
export DRIFTWATCH_SECRET_KEY="dev-secret-key"
```

5. Run database migrations:

```bash
alembic upgrade head
```

6. Start the development server:

```bash
uvicorn driftwatch.app:app --reload
```

## Test

We use **pytest** with async support. The full test suite includes unit tests, integration tests, linting, type checking, and security scanning.

### Running Tests

```bash
# Run the full test suite with coverage
pytest --cov=src/driftwatch -v

# Run a specific test file
pytest tests/test_app.py -v

# Run a specific test by name
pytest -k "test_health" -v
```

### Linting and Type Checking

```bash
# Lint with ruff
ruff check src/

# Type check with mypy
mypy src/driftwatch/ --ignore-missing-imports

# Security scan with bandit
bandit -r src/driftwatch/ -q
```

All of these checks run automatically in CI on every push and pull request. Make sure they pass locally before submitting a PR.

### Test Database

Tests require a running PostgreSQL instance. The simplest approach is to use the bundled Docker Compose service:

```bash
docker compose up -d postgres
```

The CI pipeline uses a PostgreSQL 16 Alpine service container with the default credentials (`postgres`/`postgres`).

## Pull Request

### Before You Start

- Check existing issues and PRs to avoid duplicate work.
- For larger changes, open an issue first to discuss your approach.

### Workflow

1. Create a feature branch from `main`:

```bash
git checkout -b feature/your-feature main
```

2. Make your changes. Follow the existing code patterns:
   - FastAPI with async/await for all endpoints
   - Pydantic models for request/response schemas
   - SQLAlchemy async sessions for database operations
   - Proper HTTP status codes and error responses

3. Write or update tests for your changes.

4. Ensure all checks pass:

```bash
pytest --cov=src/driftwatch -v
ruff check src/
mypy src/driftwatch/ --ignore-missing-imports
bandit -r src/driftwatch/ -q
```

5. Commit with a clear, descriptive message:

```bash
git commit -m "Add snapshot diffing for crontab entries"
```

6. Push and open a pull request against `main`.

### PR Guidelines

- Keep PRs focused on a single change.
- Include a description of what changed and why.
- Link to any related issues.
- All CI checks must pass before merge.
- Maintainers may request changes before approving.

## Code Style

This project uses [ruff](https://docs.astral.sh/ruff/) for linting and formatting. The configuration is in `pyproject.toml` with a line length of 100 characters. Run `ruff check src/` to verify your code follows the project style.

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
