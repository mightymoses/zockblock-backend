# zockblock_backend

This is the backend for the zockblock app.

## Prerequisites

The following needs to be installed:
- [git](https://git-scm.com/)
- [python v3.14](https://www.python.org/)
- [uv](https://docs.astral.sh/uv/)
- [docker](https://docs.docker.com/)

## Setup

1. Install the python packages:
```bash
uv sync
```

2. In the project root, copy the content of the `.env.example` file to a new `.env` file and add a fitting value for each variable.

## Development

1. Start the database:
```bash
docker compose up -d
```

2. Apply the database migrations:
```bash
uv run alembic upgrade head
```

3. Run the backend:
```bash
uv run fastapi dev
```

Or if the frontend is running via USB-Debugging: 
```bash
uv run fastapi dev --host 0.0.0.0
```

If you change a model, generate a new migration for it instead of applying the change manually:
```bash
uv run alembic revision --autogenerate -m "<description>"
```

## Linter

Run the linter:
```bash
uv run ruff check
```

Run the linter and resolve issues automatically:
```bash
uv run ruff check --fix
```

## Formatter

Run the formatter:
```bash
uv run ruff format
```

## Tests

Tests need Docker running (a real Postgres is started automatically per test session via testcontainers).

Run the tests:
```bash
uv run pytest
```

Run the tests with a coverage report:
```bash
uv run pytest --cov=app --cov-report=term-missing
```

## Typecheck

Run the type checker:
```bash
uv run pyright
```

## Module boundaries

Check that features don't reach into each other's internals:
```bash
uv run lint-imports
```

## Backend documentation

Access the backend documentation via [http://localhost:8000/docs/](http://localhost:8000/docs/)

## Database management

Access the database management tool via [http://localhost:8080/](http://localhost:8080/)
