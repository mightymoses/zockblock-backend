# Einwilligungen: Nutzungsbedingungen + Crashreports

## Ziel
Pro Nutzer wird festgehalten,
- ob und wann er welcher Version der Nutzungsbedingungen zugestimmt hat (mit Verlauf, als Nachweis),
- ob Crashreports gesendet werden dürfen (und wann das zuletzt geändert wurde).

Beides muss beim Anlegen des Profils mitgeschickt werden.

## Entscheidungen aus der Planung
- **Nutzungsbedingungen in eigener Tabelle `terms_acceptance`** (Verlauf: eine Zeile pro
  Zustimmung zu einer Version), nicht als Spalten am User – gehört fachlich nicht ins Profil und
  belegt später, wer wann welcher Version zugestimmt hat. Liegt trotzdem im `users`-Package
  (wird zusammen mit dem User in derselben Transaktion angelegt, kein eigenes Feature nötig).
- **Crashreport-Einwilligung als Spalten am User** (`crash_reports_consent`,
  `crash_reports_consent_updated_at`) – ist eine änderbare Einstellung, kein Dokument mit Versionen.
  `NULL` = noch nicht gefragt (nur bei Bestandsnutzern möglich).
- **Erste Version:** `2026-11-01`
- **Versionsformat:** Datum als String, `YYYY-MM-DD` (z. B. `"2026-11-01"`), lesbar und sortierbar.
- **Backend kennt die aktuelle Version:** neue Setting `current_terms_version` (Env
  `CURRENT_TERMS_VERSION`). Create/Update akzeptieren nur exakt diese Version, alles andere → 400
  (`OutdatedTermsVersionException`). Fachliche Regel mit Konfiguration dahinter → Prüfung im
  Service (analog "Username vergeben"); das Format (`YYYY-MM-DD`) wird am Router per Pydantic geprüft.
- **Zeitpunkte setzt das Backend** (`accepted_at`, `crash_reports_consent_updated_at`), die App
  schickt nie einen Zeitstempel mit.
- **`UserResponse.hasAcceptedCurrentTerms`:** berechnet aus "neueste akzeptierte Version ==
  `current_terms_version`". Die App zeigt den Zustimmungsdialog, wenn `false` – muss die aktuelle
  Version also nicht selbst kennen (kein App-Update bei einem Bump nötig).
- **API-Felder:**
  | Feld | `UserCreate` | `UserUpdate` | `UserResponse` |
  | --- | --- | --- | --- |
  | `crashReportsConsent` | Pflicht, `bool` | optional, `bool` (explizites `null` → 422) | `bool \| null` |
  | `crashReportsConsentUpdatedAt` | – | – | `datetime \| null` |
  | `acceptedTermsVersion` | Pflicht, `YYYY-MM-DD` | optional, `YYYY-MM-DD` (explizites `null` → 422) | `str \| null` (neueste) |
  | `acceptedTermsAt` | – | – | `datetime \| null` (zur neuesten) |
  | `hasAcceptedCurrentTerms` | – | – | `bool` |
- **Idempotenz:** Erneute Zustimmung zu einer schon akzeptierten Version legt keine zweite Zeile an
  (Unique-Constraint `(user_id, terms_version)` + Prüfung im Service). Gleicher
  Crashreport-Wert wie bisher → `updated_at` bleibt unverändert.
- **Bestandsnutzer:** keine Daten-Migration, Felder bleiben leer → `hasAcceptedCurrentTerms = false`,
  `crashReportsConsent = null` → App fragt beim nächsten Start nach beidem und schickt ein PATCH.
- **Löschen:** Nutzer werden nur soft-gelöscht (`deleted_at`), Zustimmungen bleiben als Nachweis
  stehen – kein `ON DELETE CASCADE`.

## Dateien
- [x] `app/config.py`
  - [x] `current_terms_version: str = ""`
- [x] `.env.example` + `render.yaml`: `CURRENT_TERMS_VERSION` ergänzen (in `render.yaml` als
  normaler Wert, kein Secret)
- [x] `app/users/models.py`
  - [x] `User`: `crash_reports_consent: bool | None`, `crash_reports_consent_updated_at: datetime | None`
  - [x] neue Tabellenklasse `TermsAcceptance` (`terms_acceptance`): `id` (uuid), `user_id` (FK
    `user.id`, Index), `terms_version` (`max_length=10`), `accepted_at` (tz-aware, Default jetzt),
    `UniqueConstraint("user_id", "terms_version")`
  - [x] `User.terms_acceptances` als `Relationship` (`lazy="selectin"`), damit die Response ohne
    extra Query auskommt
  - [x] Properties auf `User` (Domänenlogik im Modell): `latest_terms_acceptance`,
    `accepted_terms_version`, `accepted_terms_at`, `has_accepted_current_terms`
    (vergleicht mit `get_settings().current_terms_version`), `has_accepted_terms(version)`
- [x] `app/users/schemas.py`
  - [x] `TERMS_VERSION_PATTERN = r"^\d{4}-\d{2}-\d{2}$"`
  - [x] `UserCreate`: `crash_reports_consent: bool`, `accepted_terms_version: str` (Pattern)
  - [x] `UserUpdate`: beide optional, `field_validator`, der explizites `null` ablehnt (läuft nur,
    wenn das Feld gesendet wurde – weggelassen bleibt erlaubt)
  - [x] `UserResponse`: die fünf Felder aus der Tabelle oben
- [x] `app/users/exceptions.py`: `OutdatedTermsVersionException`
- [x] `app/main.py`: Exception-Handler → 400
- [x] `app/users/application/command/user_command_service.py`
  - [x] `create_user(..., crash_reports_consent: bool, accepted_terms_version: str)`: Version gegen
    `current_terms_version` prüfen, `crash_reports_consent_updated_at` setzen, `TermsAcceptance`
    über die Relationship anhängen (eine Transaktion mit dem User)
  - [x] `update_user`: `accepted_terms_version` aus `changes` herausnehmen (keine User-Spalte),
    prüfen, nur neue Version anhängen; bei geändertem `crash_reports_consent` den Zeitstempel setzen
  - [x] `_validate_terms_version(version)` als Hilfsfunktion
- [x] Migration: `uv run alembic revision --autogenerate -m "add consents"` (User-Spalten +
  Tabelle `terms_acceptance`), Unique-Constraint/FK benennen, lokal anwenden + per `\d` prüfen
  – angewendet (upgrade → downgrade → upgrade) gegen einen temporären Postgres-Container, da die
  lokale DB auf `localhost:5432` gerade nicht erreichbar war (Passwort-Auth schlägt fehl, zwei
  Prozesse lauschen auf 5432 – vermutlich eine native Postgres-Installation neben dem Docker-Container)
- [x] `tests/conftest.py`: `CURRENT_TERMS_VERSION` per `os.environ.setdefault` setzen
- [x] Tests (`tests/users/test_user_router.py`)
  - [x] bestehende Create-Requests um die beiden Pflichtfelder ergänzen (Hilfs-Payload), ebenso
    direkte `create_user`-Aufrufe in Tests (auch `tests/users/test_user_flow.py`)
  - [x] Create ohne `crashReportsConsent` / ohne `acceptedTermsVersion` → 422
  - [x] Create mit falschem Format → 422, mit veralteter Version → 400
  - [x] Create: Response enthält Version, `acceptedTermsAt`, `hasAcceptedCurrentTerms = true`,
    `crashReportsConsentUpdatedAt` gesetzt
  - [x] Update mit neuer aktueller Version (Setting im Test hochsetzen) → neue Zeile, Response zeigt
    neue Version; vorher `hasAcceptedCurrentTerms = false`
  - [x] Update mit schon akzeptierter Version → keine zweite Zeile
  - [x] Update `crashReportsConsent` geändert → `updatedAt` neu; gleicher Wert → unverändert
  - [x] Update mit explizitem `null` für eines der beiden Felder → 422
- [x] `docs/db/schema.dbml`: neue Spalten + Tabelle `terms_acceptance`
