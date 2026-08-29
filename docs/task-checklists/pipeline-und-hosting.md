# CI/CD-Pipeline & erste gehostete Umgebung (Render)

Kontext: Erste echte Deploy-Pipeline, parallel zur weiteren Feature-Arbeit, damit Deploy-Probleme
jetzt (bei nur einem Feature) auffallen statt erst bei einem "richtigen" Launch. Ziel ist eine
**Staging/Produktions-Umgebung**, kein öffentlicher Nutzer-Launch (siehe Diskussion dazu). Hosting:
Render, EU-Region (Frankfurt) wegen Auth0-EU-Tenant. Details/Preisrecherche siehe Chat-Verlauf.

## 1. Dockerfile (inkl. Health-Check-Endpoint)
- [x] `/health`-Endpoint in `app/main.py` ergänzen (einfache 200-Antwort, kein eigenes Feature)
- [x] `.dockerignore` anlegen (`.venv`, `__pycache__`, `tests/`, `docs/`, `.git`, ...)
- [x] Build-Stage: `uv`-Binary via Multi-Stage-`COPY` aus dem offiziellen `uv`-Image, zweistufiges `uv sync --locked` (erst nur Dependencies mit `--no-install-project` für optimales Layer-Caching, danach das Projekt selbst), `UV_NO_DEV=1` (keine Dev-Dependencies im Produktions-Image)
- [x] Runtime-Stage: nur fertiges venv + Code aus der Build-Stage kopieren (schlankes Image), non-root User, `CMD` mit `fastapi run app/main.py --port 8000` (Produktions-Befehl, nicht `fastapi dev`), Docker-`HEALTHCHECK` gegen `/health`
- [x] Lokal bauen & starten, gegen die lokale Compose-Postgres-DB testen — Build erfolgreich, Container im Compose-Netzwerk gestartet, `/health` antwortet, Docker meldet `healthy`

## 2. GitHub-Actions-Workflow (CI)
- [x] `.github/workflows/ci.yml`: vier parallele Jobs (Lint/Typecheck/Modulgrenzen/Tests) statt ein sequenzieller Job — unabhängig voneinander, schnelleres Feedback, eigene benannte Checks in der PR-Übersicht
- [x] Trigger: `pull_request` gegen `main` — läuft beim Öffnen des PRs und bei jedem weiteren Push, solange er offen ist (nicht erst nach Merge)
- [x] `uv`-Caching über `astral-sh/setup-uv`s eingebautes `enable-cache: true` (statt manuellem Cache-Key-Aufbau)
- [x] GitHub-gehostete Runner haben Docker bereits verfügbar — kein Docker-in-Docker-Setup nötig für die testcontainers-Tests
- [x] Über einen echten PR verifizieren, dass alle vier Jobs tatsächlich grün durchlaufen — dabei zwei echte Bugs gefunden und behoben: `astral-sh/setup-uv@v9` existiert nicht als Tag (→ `v10.0.1`), und `app/db/db.py`/`app/dependencies.py` bauten DB-Engine und Auth0-Client beim Import statt lazy, was lokal nur wegen der (gitignoreten) `.env` nicht auffiel

## 3. Render-Setup, Deploy-Anbindung & Migrationen (via `render.yaml`-Blueprint)
Zusammengelegt, weil Render Blueprints das alles in einer Datei abdecken (Infrastructure-as-Code
statt Klick-Konfiguration im Dashboard).
- [x] `app/config.py`: optionales `database_url`-Feld ergänzt, hat Vorrang vor den einzelnen `postgres_*`-Feldern — nötig, weil Render bei `fromDatabase` nur `user`/`password`/`database`/`connectionString` durchreicht, kein `host`/`port` einzeln
- [x] `render.yaml` anlegen: Postgres-Instanz (Frankfurt, `basic-256mb`) + Web-Service (Docker, Frankfurt, `starter`), `healthCheckPath: /health`, `preDeployCommand` mit den Migrationen (Migrationen laufen so vor jedem Deploy)
- [x] `autoDeployTrigger: checksPass` im Web-Service — deployt nur, wenn die GitHub-Status-Checks grün sind
- [x] `.github/workflows/ci.yml`: zusätzlich auf `push` gegen `main` triggern (nicht nur `pull_request`), damit der Merge-Commit selbst Status-Checks bekommt, auf die `checksPass` warten kann
- [x] Blueprint einmalig im Render-Dashboard mit dem GitHub-Repo verbunden, `AUTH0_DOMAIN`/`AUTH0_API_AUDIENCE` eingetragen — dabei Bug gefunden: `preDeployCommand: uv run alembic upgrade head` schlug fehl (Exit 128), weil `uv` nur in der Docker-Build-Stage liegt, nicht im schlanken Runtime-Image. Fix: `alembic upgrade head` direkt (liegt im venv, das per `PATH` aktiv ist — genau wie `fastapi` im `CMD`), lokal gegen die Compose-DB verifiziert
- [ ] Ersten Deploy abwarten/prüfen, `/health` extern (nicht mehr nur lokal) testen
