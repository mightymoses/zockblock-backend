# User-Profil vervollständigen (Onboarding-Screen nach Signup)

Kontext: Nach dem Signup soll ein Screen alle profilrelevanten Nutzerdaten abfragen und ans
Backend speichern. Dafür wird das `users`-Feature um neue Profilfelder, einen Bearbeiten-Endpunkt
und eine Foto-Upload-Anbindung erweitert.

**Entscheidungen aus der Planung:**
- `owner_user_id` (verwaltete Profile, z. B. Kinder-/Gastprofile ohne eigenen Auth0-Account) wird
  nur als nullable Feld vorbereitet – kein eigener Endpunkt zum Anlegen/Auflisten in diesem Schritt.
- Foto-Upload läuft entkoppelt: Sobald im UI ein Foto gewählt wird, fragt die App direkt eine
  Presigned-Upload-URL an und lädt im Hintergrund zu Cloudflare R2 hoch. Der finale
  Speichern-Request enthält dann nur noch die bereits bekannte `avatar_url` – kein Warten beim
  eigentlichen Onboarding-Abschluss.
- `avatar_url` (Foto) überschreibt in der Anzeige den Tier-Avatar (`animal_asset_name` +
  `avatar_color`), beide Wertepaare bleiben aber gespeichert (Fallback, falls Foto entfernt wird).
- Tier-Avatare selbst (Bild-Assets) werden im App-Code gebündelt, nicht vom Backend gehostet – das
  Backend speichert nur den gewählten Asset-Key als String.
- Such-Endpoint per Username kommt später mit dem `social`-Feature; jetzt nur die DB-Unique-
  Constraint (bereits vorhanden).
- Storage-Anbieter für Fotos: Cloudflare R2 (S3-kompatibel, kein Egress, Free Tier passend zur
  aktuellen Größenordnung).

## 1. Datenmodell (`user`) + Migration
- [x] `app/users/models.py`: neue Felder auf `User` ergänzen
  - `avatar_url: str | None = Field(default=None)` (hochgeladenes Foto)
  - `animal_asset_name: str | None = Field(default=None, max_length=100)` (Key des gewählten Tier-Assets im App-Bundle)
  - `avatar_color: int | None = Field(default=None)` (Bedeutung/Palette liegt beim Frontend, keine Backend-Validierung)
  - `bio_line_1: str | None = Field(default=None, max_length=100)`, `bio_line_2: str | None = Field(default=None, max_length=100)` – zwei freie Profil-Zeilen
  - `owner_user_id: uuid.UUID | None = Field(default=None, foreign_key="user.id", index=True)` (self-referencing FK, für später geplante verwaltete Profile; `index=True` für ein künftiges "meine verwalteten Profile auflisten")
- [x] `external_auth_id` auf `str | None` ändern (Typ), restliche Field-Constraints bleiben (`unique=True, index=True, min_length=6`) – Vorbereitung für verwaltete Profile ohne eigenen Auth0-Account; `unique`-Constraint bleibt gültig (Postgres erlaubt mehrere NULLs)
- [x] Migration generieren: `uv run alembic revision --autogenerate -m "add profile fields to user"` (neue Datei, bestehende `08c1823e78c8_initial_schema.py` nicht angefasst) – dabei den unbenannten FK-Constraint aus dem Autogenerate manuell benannt (`fk_user_owner_user_id_user`), sonst wäre `downgrade()` kaputt gewesen (erster FK im Projekt, noch keine Naming-Convention)
- [x] Migration lokal angewendet & per `\d "user"` in der DB verifiziert
- [x] `docs/db/schema.dbml` aktualisiert: `id` auf `uuid`, Tabellenname von `users` auf `user` korrigiert, `username [unique]` markiert, neue Felder ergänzt, alle FK-Spalten, die auf `user.id` zeigen (`session_participants`, `session_likes`, `session_comments`, `comment_likes`, `kniffel_events`, `kniffel_session_results`, `ratings`, `rating_history`, `friendships`), von `integer` auf `uuid` korrigiert – `kniffel_stats.user_id` bewusst nicht angefasst (hatte schon vorher keine `ref`-Annotation, kein echtes Feature bisher)

## 2. Foto-Storage-Anbindung (Cloudflare R2)
- [x] Cloudflare R2 Bucket angelegt (Account API Token, Object Read & Write, auf den Bucket beschränkt; Public Development URL aktiviert für öffentlichen Lesezugriff)
- [x] `boto3` als Dependency ergänzt: `uv add boto3`
- [x] `app/config.py`: neue Settings (`r2_endpoint_url`, `r2_bucket_name`, `r2_access_key_id`, `r2_secret_access_key`, `r2_public_base_url`, `presigned_url_expiry_seconds`, Default 300)
- [x] `.env.example` um die neuen Variablen ergänzt
- [x] `app/common/storage.py` angelegt (erstes Modul in `common/`): lazy boto3-S3-Client (analog `get_auth0_client`, per `lru_cache`), Funktion `generate_presigned_upload_url(key, content_type) -> (upload_url, public_url)` – bewusst **kein** `StorageDep` in `dependencies.py`, da der S3-Client wie der Auth0-Client ein zustandsloser Singleton ohne Pro-Request-Zustand ist (Services rufen `storage.generate_presigned_upload_url(...)` direkt)
- [x] `render.yaml`: neue Secret-`envVars` (`sync: false`) ergänzt
- [ ] Tatsächliche Werte im Render-Dashboard eintragen (offen bis zum nächsten Deploy)
- [ ] Überlegen (kann auch später): Presigned PUT erzwingt kein Size-/Content-Type-Limit serverseitig – ggf. später auf Presigned POST mit Policy umstellen, falls nötig

## 3. Endpunkte: User-Profil

**Entscheidungen aus der Planung:**
- Kein gemeinsamer Endpunkt mit dem später geplanten "verwaltetes Profil anlegen" – unterschiedliche Identitätsquelle (eigenes Auth0-Token vs. Owner-Token), sicherheitsrelevante Verzweigung gehört nicht in einen Endpunkt.
- PATCH-Semantik: `body.model_dump(exclude_unset=True)` – weggelassene Felder bleiben unangetastet, explizites `null` löscht (z. B. Foto entfernen → Rückfall auf Tier-Avatar).
- `avatar-upload-url` nutzt `external_auth_id` als Storage-Key-Präfix (nicht `user.id`), da Foto schon vor dem finalen `POST /users/` gewählt werden kann – Endpunkt braucht nur `AuthDep`, keine DB-Session.
- Presigned Upload akzeptiert nur `image/jpeg`, `image/png`, `image/webp` (Allowlist gegen Missbrauch als Datei-Host). HEIC (iOS-Kamera-Standard) wird clientseitig vor dem Upload zu JPEG konvertiert – Backend-Thema erledigt sich damit von selbst.
- `avatar_url` beim Speichern validieren: muss mit `settings.r2_public_base_url` beginnen (verhindert, dass Nutzer beliebige externe URLs als Avatar hinterlegen).
- Username-Format: 3–20 Zeichen, Buchstaben/Zahlen/`.`/`_`/`-`, erstes und letztes Zeichen muss alphanumerisch sein, keine zwei Sonderzeichen hintereinander. Als Pydantic-`pattern` (zusätzlich `min_length=3, max_length=20` für klare Längen-Fehlermeldungen) auf dem Request-Schema:
  `^[a-zA-Z0-9]+(?:[._-][a-zA-Z0-9]+)*$` (kein Lookahead – pydantic-core nutzt eine Rust-Regex-Engine ohne Lookahead/Lookbehind-Unterstützung; Konstruktion über abwechselnde alphanumerische Blöcke/Sonderzeichen erreicht dieselbe Regel)
- Live-Verfügbarkeitsprüfung für Username wird mitgebaut (`GET /users/username-availability`).

**Dateien:**
- [x] `schemas.py`:
  - `UserCreate` erweitert: `username` (mit Format-Constraint), `animalAssetName`, `avatarColor`, `bioLine1`, `bioLine2`, `avatarUrl` (alle außer `username` optional)
  - `UserUpdate` neu: alle Felder optional, gleiche Constraints wie `UserCreate`
  - `UserResponse` um neue Felder erweitert
  - `AvatarUploadRequest` neu: `contentType` (Literal auf die 3 erlaubten Typen)
  - `AvatarUploadResponse` neu: `uploadUrl`, `avatarUrl`
  - `UsernameAvailabilityResponse` neu: `isAvailable: bool`
- [x] `router.py`:
  - `POST /users/` (bestehend) auf neue Felder erweitert
  - `PATCH /users/current` neu (holt den User erst über den Query-Service, dann Command-Service)
  - `POST /users/current/avatar-upload-url` neu (nur `AuthDep`, kein `SessionDep`)
  - `GET /users/username-availability?username=` neu (mit `AuthDep`, verhindert anonymes Scraping)
- [x] `user_command_service.py`: `create_user` erweitert, `update_user` neu (inkl. `avatar_url`-Präfix-Validierung), `request_avatar_upload_url` neu (ruft nur `storage.generate_presigned_upload_url`, keine DB)
- [x] `user_query_service.py`: `is_username_available` neu
- [x] `repository.py`: `exists_by_username(session, username)` neu – kein separates `save()`: für ein bereits getracktes Objekt macht `add()` + `flush()` dasselbe wie beim Neuanlegen, kein zweites, identisches `save()` nötig
- [x] `exceptions.py`: `UsernameAlreadyTakenException` – proaktiv geprüft (bessere UX) **und** als Fallback bei `IntegrityError` aus dem Commit gefangen (Race-Condition-Schutz); zusätzlich `InvalidAvatarUrlException` für die `avatar_url`-Präfix-Validierung. Beide Handler in `main.py` registriert (409 bzw. 400)

## 4. Tests
- [x] Beim Schreiben der Tests einen echten kleinen Bug gefunden: `_validate_avatar_url` prüfte `avatar_url.startswith(r2_public_base_url)` – bei fehlender Konfiguration (leerer String, Default) matched das immer, die Prüfung wäre lautlos wirkungslos gewesen. Jetzt fail-closed: ohne konfigurierte `r2_public_base_url` wird jede `avatar_url` abgelehnt.
- [x] `tests/conftest.py`: `R2_PUBLIC_BASE_URL`-Test-Default ergänzt (analog `POSTGRES_*`)
- [x] `tests/users/test_user_router.py`: 13 neue Tests – volle Profilfelder, doppelter Username (409) bei Create/Update, ungültiges Username-Format (422), ungültige `avatarUrl` (400), PATCH Teil-Update, PATCH `null` löscht Foto, Avatar-Upload-URL (Storage gemockt via `monkeypatch`), nicht erlaubter Content-Type (422), Username-Verfügbarkeit
- [x] `test_user_flow.py` bewusst unangetastet gelassen (kein Mehrwert, alles über Router beobachtbar)
