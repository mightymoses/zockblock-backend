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

2. Inside the `app` directory copy the content of the `.env.example` file to a new `.env` file and add a fitting value for each variable.

## Development

1. Start the database:
```bash
docker compose up -d
```

2. Run the backend:
```bash
uv run fastapi dev
```

Or if the frontend is running via USB-Debugging: 
```bash
uv run fastapi dev --host 0.0.0.0
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

## Backend documentation

Access the backend documentation via [http://localhost:8000/docs/](http://localhost:8000/docs/)

## Database management

Access the database management tool via [http://localhost:8080/](http://localhost:8080/)
