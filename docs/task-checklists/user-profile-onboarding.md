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
- [ ] Cloudflare R2 Bucket anlegen (manueller Schritt im Cloudflare-Dashboard, EU Location Hint setzen)
- [ ] `boto3` als Dependency ergänzen: `uv add boto3`
- [ ] `app/config.py`: neue Settings (`r2_endpoint_url`, `r2_bucket_name`, `r2_access_key_id`, `r2_secret_access_key`, `r2_public_base_url`, `presigned_url_expiry_seconds` mit sinnvollem Default)
- [ ] `.env.example` um die neuen Variablen ergänzen
- [ ] `app/common/storage.py` anlegen (erstes Modul in `common/`): lazy boto3-S3-Client (analog `get_auth0_client`, per `lru_cache`), Funktion `generate_presigned_upload_url(key, content_type) -> (upload_url, public_url)`
- [ ] `app/dependencies.py`: `StorageDep` ergänzen
- [ ] `render.yaml`: neue Secret-`envVars` (`sync: false`) ergänzen, in Render-Dashboard eintragen
- [ ] Überlegen (kann auch später): Presigned PUT erzwingt kein Size-/Content-Type-Limit serverseitig – ggf. später auf Presigned POST mit Policy umstellen, falls nötig

## 3. Endpunkte: User-Profil
- [ ] `schemas.py`: `UserCreate` um `animalAssetName`, `avatarColor`, `bioLine1`, `bioLine2`, `avatarUrl` erweitern (alle bis auf `username` optional)
- [ ] `UserUpdate`-Schema neu (alle Felder optional) für PATCH
- [ ] `UserResponse` um neue Felder erweitern
- [ ] `POST /users/` (bestehend) auf neue Felder erweitern
- [ ] `PATCH /users/current` neu: Profil nachträglich bearbeiten
- [ ] `POST /users/current/avatar-upload-url` neu: liefert Presigned-Upload-URL + finale `avatar_url` zurück (reiner Storage-Aufruf, kein DB-Write)
- [ ] `user_command_service.py`: `create_user` erweitern, `update_user` neu, `request_avatar_upload_url` neu
- [ ] `repository.py`: Update-Funktion ergänzen (reiner Datenzugriff)
- [ ] `exceptions.py`: `UsernameAlreadyTakenException` (bei Unique-Constraint-Verletzung beim Anlegen), Handler in `main.py` registrieren (409)

## 4. Tests
- [ ] Tests für erweiterten `POST /users/`, neuen `PATCH /users/current`, `avatar-upload-url`-Endpoint (Storage-Aufruf mocken statt echtem R2-Call)
- [ ] Test für `UsernameAlreadyTakenException` (409 bei doppeltem Username)
