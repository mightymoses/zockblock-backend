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
- [ ] `.github/workflows/ci.yml`: Lint (`ruff check`) → Typecheck (`pyright`) → Modulgrenzen (`lint-imports`) → Tests (`pytest --cov`)
- [ ] Trigger: auf jedem Pull Request gegen `main`
- [ ] `uv`-Dependency-Cache einrichten (Cache-Key auf Basis von `uv.lock`), damit die Pipeline nicht jedes Mal alles neu installiert
- [ ] Hinweis: GitHub-gehostete Runner haben Docker bereits verfügbar — kein Docker-in-Docker-Setup nötig für die testcontainers-Tests

## 3. Render-Setup
- [ ] Render-Workspace (kostenloser Hobby-Tarif reicht für Solo-Entwicklung)
- [ ] Postgres-Instanz anlegen (Frankfurt/EU-Region, kleinste bezahlte Stufe — Free-Tier läuft nach 30 Tagen ab, ungeeignet für Dauerbetrieb)
- [ ] Web-Service anlegen (Docker-Deploy aus dem `Dockerfile`, Starter-Tarif, EU-Region)
- [ ] Umgebungsvariablen/Secrets in Render hinterlegen (`POSTGRES_*`, `AUTH0_*`, `ENVIRONMENT=production`)

## 4. Deploy-Anbindung
- [ ] Entscheiden: Render Auto-Deploy bei Push auf `main`, oder expliziter Deploy-Schritt am Ende des GitHub-Actions-Workflows
- [ ] Entsprechend einrichten

## 5. Migrationen beim Deploy
- [ ] Render **Pre-Deploy Command** auf `uv run alembic upgrade head` setzen (läuft nach Build, vor Start — https://render.com/changelog/predeploy-command)
