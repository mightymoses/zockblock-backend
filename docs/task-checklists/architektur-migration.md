# Architektur-Migration: Clean-Stand für FastAPI-Backend

Kontext: `CLAUDE.local.md` wurde von einem Java/Spring-Boot-Template (Tipply) auf den tatsächlichen Python/FastAPI-Stack von zockblock-backend überarbeitet (Technologie-Tabelle, Architektur, Anti-Patterns). Diese Checkliste bringt den bestehenden Code auf den dort festgelegten Zielstand.

Ausgangslage: flaches `app/models/`, `app/routes/` (nach Schicht statt Feature sortiert), kein Service-/Repository-Layer, `SQLModel.metadata.create_all()` statt Migrationen, keine Tests, kein Logging-Setup, kein Typecheck/Modulgrenzen-Check.

## 1. Schema-Migration (Alembic)
- [ ] Alembic als Dependency hinzufügen (`uv add alembic`)
- [ ] `alembic init` ausführen, `env.py` auf SQLModel-Metadata + `postgres_url` aus `app.config.Settings` verdrahten
- [ ] Erste Migration aus bestehendem `User`-Modell autogenerieren (`alembic revision --autogenerate -m "initial schema"`)
- [ ] `create_db_and_tables()` / `SQLModel.metadata.create_all()`-Aufruf aus `app/main.py` / `app/db/db.py` entfernen
- [ ] Migration lokal gegen die Compose-Postgres-DB testen (`alembic upgrade head`)

## 2. `users`-Feature auf neue Struktur umziehen
- [ ] Verzeichnis `app/users/` anlegen mit `router.py`, `schemas.py`, `models.py`, `repository.py`, `exceptions.py`, `application/command/`, `application/query/`
- [ ] `app/models/users.py` → `app/users/models.py` verschieben
- [ ] Eigene Pydantic-Schemas `UserCreate` (Request) und `UserResponse` (Response) in `app/users/schemas.py` anlegen
- [ ] `app/users/repository.py`: reine DB-Zugriffsfunktionen (z. B. `get_by_external_auth_id`, `create`)
- [ ] `app/users/application/query/user_query_service.py`: `get_current_user`-Logik
- [ ] `app/users/application/command/user_command_service.py`: `create_user`-Logik
- [ ] `app/users/router.py`: Router nutzt nur noch Service-Funktionen, mapped über `model_validate(obj, from_attributes=True)` auf `UserResponse`
- [ ] `app/models/`, `app/routes/`-Ordner entfernen, sobald leer
- [ ] Import in `app/main.py` auf `app.users.router` anpassen

## 3. Logging (structlog)
- [ ] `structlog` als Dependency hinzufügen
- [ ] Konfiguration (JSON in Produktion, Plain-Text lokal) zentral anlegen (z. B. `app/logging.py`), beim Start in `app/main.py` initialisieren

## 4. Tests
- [ ] `pytest` + `testcontainers[postgres]` als Dev-Dependency hinzufügen
- [ ] `tests/`-Verzeichnis anlegen, pytest-Fixture für Postgres-Testcontainer + DB-Session
- [ ] Ersten Test für `users`-Feature schreiben (z. B. `create_user` → `get_current_user`)

## 5. Typecheck & Modulgrenzen
- [ ] `pyright` als Dev-Dependency hinzufügen, Konfiguration in `pyproject.toml` (`[tool.pyright]`) anlegen
- [ ] `import-linter` als Dev-Dependency hinzufügen, erste Contracts in `pyproject.toml` definieren (Layers: `router → service → repository`; Independence zwischen Features)
- [ ] `pytest-archon` als Dev-Dependency hinzufügen, erste Architektur-Regel(n) als Test anlegen
