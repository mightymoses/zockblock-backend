# Architektur

Dieses Dokument beschreibt die Architektur des Zockblock-Backends.

## Überblick

Zockblock ist eine Python-REST-API für eine Spieleblock-App: Festhalten/Führen von Spielständen, Anzeigen von Statistiken und Social-Media-Funktionen für Brett-, Karten- und Würfelspiele.

## Tech-Stack

| Bereich              | Entscheidung                                                                 |
| --------------------- | ----------------------------------------------------------------------------|
| Web-Layer             | FastAPI (async, automatische Request/Response-Validierung + OpenAPI-Doku)   |
| Persistenz            | SQLModel (Pydantic + SQLAlchemy in einer Klasse)                            |
| Schema-Migration      | Alembic, autogeneriert aus den SQLModel-Klassen                             |
| Datenbank             | PostgreSQL                                                                  |
| Hintergrundjobs       | APScheduler, Fan-out über eigene DB-Job-Tabelle                             |
| Tests                 | pytest + testcontainers-python (echtes Postgres), Coverage via pytest-cov   |
| Logging               | structlog (JSON in Produktion, Plain-Text lokal)                            |
| Package-Manager       | uv                                                                          |
| Typisierung           | Pyright                                                                     |
| Login/Berechtigungen  | Auth0, JWT-basiert (stateless)                                              |
| API-Dokumentation     | automatisch generiert, Swagger-UI unter `/docs`                             |
| Modulgrenzen          | import-linter (Feature-Grenzen) + pytest-archon (Layer-Regeln)              |

## Architekturprinzipien

**Package-by-Feature:** Jedes fachliche Feature liegt in einem eigenen Package unter `app/` und enthält seine komplette Schichtenkette (Router, Service, Repository, SQLModel-Tabellenklasse, Pydantic-Schemas, eigene Exceptions). Ausnahme ist `common/` für Code, der bewusst quer zu allen Features steht (z. B. geteilte Basis-Exceptions).

**Schichtenkette:** Jedes Feature durchläuft dieselbe Kette: **Router → Service → Repository**.
- Der **Router** übersetzt HTTP ↔ Domäne und enthält selbst keine Business-Logik.
- Der **Service** enthält die Business-Logik, aufgeteilt nach CQS (Command Query Separation) in `application/command/` (schreibend) und `application/query/` (lesend). Die Transaktionsgrenze (Commit) liegt hier, nicht im Repository.
- Das **Repository** ist reiner Datenzugriff, ohne Business-Logik.

**Schema-Trennung:** Die SQLModel-Tabellenklasse (z. B. `User`) ist zugleich das Domänenmodell (ORM-Mapping und fachliche Methoden in derselben Klasse), wird aber nie direkt als API-Antwort zurückgegeben. An der Router-Grenze stehen eigene, schlankere Pydantic-Schemas (Request/Response getrennt) – so landen z. B. interne Felder wie Soft-Delete-Marker nie versehentlich in einer Antwort. Das Mapping zwischen beidem passiert über `model_validate(obj, from_attributes=True)`.

**Validierung** findet ausschließlich an der Router-Grenze über Pydantic statt (Field-Constraints auf den Request-Schemas).

**Modulgrenzen** werden automatisiert geprüft statt nur per Konvention einzuhalten: import-linter kontrolliert, dass Features nicht direkt ineinander importieren (Contracts in `pyproject.toml`), pytest-archon prüft die Schichtenkette innerhalb eines Features (z. B. darf das Repository nicht den Router importieren) – beide laufen als Teil der normalen Test-Suite.

## Verzeichnisstruktur

```
app
├── users/
│   ├── router.py
│   ├── schemas.py                 (Request-/Response-Pydantic-Modelle)
│   ├── models.py                  (SQLModel-Tabellenklasse)
│   ├── repository.py
│   ├── exceptions.py
│   └── application/
│       ├── command/
│       │   └── user_command_service.py
│       └── query/
│           └── user_query_service.py
├── games/
│   └── ...
├── ...
├── common/
│   └── exceptions.py
alembic/                            (Migrationsskripte)
tests/                              (gespiegelt nach Feature, z. B. tests/users/)
docs/
├── architecture.md                 (dieses Dokument)
├── db/schema.dbml                  (Datenmodell, siehe unten)
└── task-checklists/                (Umsetzungspläne einzelner Umbauten)
```

## Feature-Zuschnitt

| Package                  | Inhalt                                                                           |
| ------------------------- | --------------------------------------------------------------------------------|
| `users`                   | Nutzerkonto, Profil (Avatar, Tiername, Farbe)                                   |
| `social`                  | Freundschaften                                                                  |
| `games`                   | Spiele-Katalog (`game_definitions`)                                             |
| `games/kniffel`           | Kniffel-Sessionergebnisse, -Events, -Statistiken                                |
| `games/<weiteres-spiel>`  | analog, je ein Unter-Package pro Spiel, sobald implementiert                    |
| `sessions`                | Gespielte Partien, Teilnehmer, Bilder, Kommentare, Likes                        |
| `ratings`                 | Skill-Rating pro Nutzer/Spiel (TrueSkill-artig) + Verlauf, Leaderboard          |
| `common/`                 | Auth-Konfiguration, GlobalExceptionHandler, geteilte Utilities                  |

Aktuell ist nur `users` tatsächlich implementiert, der Rest ist der geplante Zuschnitt für die nächsten Features.

## Datenmodell

Das vollständige Datenmodell (alle Tabellen, Spalten, Relationen) liegt als [DBML](https://dbml.dbdiagram.io/) in [`docs/db/schema.dbml`](db/schema.dbml). DBML ist eine kleine Textsprache, um Datenbankschemata zu beschreiben – lesbar als reiner Text, oder visuell z. B. unter [dbdiagram.io](https://dbdiagram.io/) (Datei importieren) als ER-Diagramm.

Wichtig: Die `.dbml`-Datei ist reine Dokumentation/Planungsgrundlage, keine ausführbare Schema-Quelle – die tatsächliche, verbindliche Struktur der Datenbank ergibt sich aus den SQLModel-Tabellenklassen (`app/<feature>/models.py`) und den daraus generierten Alembic-Migrationen unter `alembic/versions/`. Bei Abweichungen zwischen `schema.dbml` und dem Code gilt der Code.

## Qualitätssicherung

- `uv run pytest` – Tests (inkl. Architektur-Regeln), gegen echtes Postgres via testcontainers
- `uv run pytest --cov=app --cov-report=term-missing` – mit Coverage-Report
- `uv run ruff check` / `uv run ruff format` – Linting/Formatting
- `uv run pyright` – Typprüfung
- `uv run lint-imports` – Modulgrenzen zwischen Features
